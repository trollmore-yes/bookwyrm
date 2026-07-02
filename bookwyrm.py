import asyncio
import importlib.util
import os
import json
import re
import tempfile
from pathlib import Path
from typing import Any, Awaitable, Callable, cast

import discord
from dotenv import load_dotenv

from channel_manager import ChannelManager
from data_manager import TestDataManager

ALLOWED_GUILDS = [1274792500975894589, 687838172348284995]


load_dotenv()
bot = discord.Bot()

cm = ChannelManager()

APPROVE_EMOJI = "✅"
REJECT_EMOJI = "❌"
REVIEW_TIMEOUT_SECONDS = 15 * 60

# message_id -> pending review details
PENDING_MODEL_REVIEWS = {}
# (guild_id, user_id) -> most recent rejected/expired model
EDITABLE_MODELS = {}
data_manager = TestDataManager(Path(__file__).resolve().parent / "signups-test.txt")
PARSE_SHEET_MODULE = None


def _editable_model_key(guild_id: int, user_id: int) -> tuple[int, int]:
    return guild_id, user_id


def _load_parse_sheet_module():
    global PARSE_SHEET_MODULE
    if PARSE_SHEET_MODULE is not None:
        return PARSE_SHEET_MODULE

    script_path = Path(__file__).resolve().parent / "parse-sheet.py"
    spec = importlib.util.spec_from_file_location("parse_sheet_runtime", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load parse-sheet.py runtime module")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    PARSE_SHEET_MODULE = module
    return module


def _promote_model_for_editing(pending: dict) -> None:
    key = _editable_model_key(pending["guild_id"], pending["invoker_id"])
    EDITABLE_MODELS[key] = pending["model"]


def _cancel_pending_timeout(pending: dict) -> None:
    timeout_task = pending.get("timeout_task")
    if timeout_task is not None and not timeout_task.done():
        timeout_task.cancel()


async def _timeout_pending_review(message_id: int) -> None:
    await asyncio.sleep(REVIEW_TIMEOUT_SECONDS)

    pending = PENDING_MODEL_REVIEWS.pop(message_id, None)
    if pending is None:
        return

    _promote_model_for_editing(pending)

    channel = bot.get_channel(pending["channel_id"])
    if channel is None:
        try:
            channel = await bot.fetch_channel(pending["channel_id"])
        except Exception:
            return

    send_fn = cast(Callable[[str], Awaitable[Any]] | None, getattr(channel, "send", None))
    if send_fn is not None:
        await send_fn(
            "No reaction received before timeout. The proposed model was kept in memory for `/edit_groups`."
        )


def _parse_groups_list(text: str) -> list[dict]:
    normalized = re.sub(r"^\s*GROUPS\s*:\s*", "", text.strip(), flags=re.IGNORECASE)
    entries = [entry.strip() for entry in re.split(r"[;\n]+", normalized) if entry.strip()]

    groups = []
    for entry in entries:
        match = re.match(r"\s*-\s*([^:]+):\s*(.+)$", entry)
        if not match:
            continue

        group_name = match.group(1).strip()
        members = [name.strip() for name in match.group(2).split(",") if name.strip()]
        if not members:
            raise ValueError(f"Group '{group_name}' is missing member names")

        groups.append({"name": group_name, "members": [{"name": member} for member in members]})

    if not groups:
        raise ValueError("No valid group lines found. Expected format: '- GroupName: user1, user2'")

    return groups


def _rebuild_model_from_groups(base_model: dict, edited_groups: list[dict]) -> dict:
    users = base_model.get("users", [])
    user_lookup = {str(user.get("name", "")).replace(" ", "").lower(): user for user in users}
    expected = set(user_lookup.keys())

    seen = []
    rebuilt_groups = []
    for group in edited_groups:
        rebuilt_members = []
        for member in group.get("members", []):
            raw_name = str(member.get("name", "")).strip()
            key = raw_name.replace(" ", "").lower()
            if key not in user_lookup:
                raise ValueError(f"Unknown user in groups list: '{raw_name}'")
            seen.append(key)
            rebuilt_members.append({"name": user_lookup[key]["name"]})

        rebuilt_groups.append({"name": group.get("name", ""), "members": rebuilt_members})

    if len(seen) != len(set(seen)):
        raise ValueError("Each user must appear exactly once in the GROUPS list (duplicate detected)")

    if set(seen) != expected:
        missing = sorted(expected - set(seen))
        extra = sorted(set(seen) - expected)
        details = []
        if missing:
            details.append(f"missing users: {', '.join(missing)}")
        if extra:
            details.append(f"unexpected users: {', '.join(extra)}")
        raise ValueError("Edited GROUPS list must use the same user set; " + "; ".join(details))

    return {
        "group_timestamp": base_model.get("group_timestamp", 0),
        "users": users,
        "groups": rebuilt_groups,
    }


def _render_report_text(model_payload: dict) -> str:
    parse_sheet = _load_parse_sheet_module()

    people = []
    people_by_name = {}
    for user in model_payload.get("users", []):
        person = parse_sheet.Person(
            user.get("name", ""),
            timestamp=user.get("timestamp"),
            words_wr=user.get("words_wr", 0),
            words_r=user.get("words_r", 0),
            genre_wr=user.get("genre_wr", []),
            genre_r=user.get("genre_r", []),
            cw_wr=user.get("cw_wr", []),
            cw_veto=user.get("cw_veto", []),
            size_pref=user.get("size_pref", []),
            match_pref=user.get("match_pref", ""),
            match_veto=user.get("match_veto", ""),
            prev_month=user.get("prev_month", ""),
            prev_group=user.get("prev_group", ""),
        )
        people.append(person)
        people_by_name[person.name.lower()] = person

    groups = []
    for group in model_payload.get("groups", []):
        members = []
        for member in group.get("members", []):
            name = str(member.get("name", "")).replace(" ", "").lower()
            person = people_by_name.get(name)
            if person is None:
                raise ValueError(f"Cannot render report: unknown member '{member.get('name', '')}'")
            members.append(person)

        groups.append(parse_sheet.Group(name=group.get("name", ""), members=members))

    model = parse_sheet.Model(groups=groups, users=people)
    visualizer = parse_sheet.Visualizer(model)
    auditor = parse_sheet.Auditor(model)

    output = []
    output.append(visualizer.model_info() + "\n\n")
    output.append(visualizer.group_info(summary=False, wc=True, cw=True, prev=True))
    output.append(auditor.check_submissions())
    output.append(auditor.check_groups())
    output.append("\nPROBLEM MEMBER REPORTS:\n")
    output.append("----\n")
    output.append(visualizer.print_formatted_group_list())
    return "".join(output)


async def _send_review_response(ctx, model_payload: dict, report_path: Path) -> None:
    result_message = await ctx.followup.send(
        file=discord.File(report_path, filename=report_path.name),
        wait=True,
    )
    await result_message.add_reaction(APPROVE_EMOJI)
    await result_message.add_reaction(REJECT_EMOJI)

    pending = {
        "invoker_id": ctx.author.id,
        "guild_id": ctx.guild.id,
        "channel_id": ctx.channel.id,
        "timestamp": model_payload.get("group_timestamp", 0),
        "model": model_payload,
        "saved": False,
    }
    pending["timeout_task"] = asyncio.create_task(_timeout_pending_review(result_message.id))
    PENDING_MODEL_REVIEWS[result_message.id] = pending

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# @bot.slash_command(guild_ids=[1274792500975894589])
# async def hello(ctx):
#     await ctx.respond("Hello!")

@bot.slash_command(guild_ids=ALLOWED_GUILDS)
async def set_forum_ids(ctx, disc_forum : discord.ForumChannel, sub_forum : discord.ForumChannel):
    cm.set_channels(disc=disc_forum, sub=sub_forum)
    cm.guild_id = ctx.guild.id
    print(f"guild_id = {cm.guild_id}")
    await ctx.respond(f"we are in: **{str(ctx.guild).upper()}**\nset discussion forum to **{disc_forum}** \nset submission forum to **{sub_forum}**")

@bot.slash_command(guild_ids=ALLOWED_GUILDS)
async def build_group(ctx, name):
    await ctx.defer()

    output = []
    if ", " in name:
        names = name.split(", ")
        print(names)
        for n in names:
            disc, sub = await cm.build_group_threads(name=n, guild=ctx.guild)
            output.append([n, cm.get_thread_link_from_obj(disc), cm.get_thread_link_from_obj(sub)])
    else:
        disc, sub = await cm.build_group_threads(name=name, guild=ctx.guild)
        output.append([name, cm.get_thread_link_from_obj(disc), cm.get_thread_link_from_obj(sub)])

    result = "\n".join([f"**{obj[0]}**\nDiscussion: {obj[1]}\nSubmission: {obj[2]}" for obj in output])
    await ctx.followup.send(result)

@bot.slash_command(guild_ids=ALLOWED_GUILDS)
async def parse_signup_sheet(ctx, csv_file: discord.Attachment):
    await ctx.defer()

    if not csv_file or not csv_file.filename.lower().endswith(".csv"):
        await ctx.followup.send("Please upload the CSV file from the signup form.")
        return

    data_manager.init_database()

    with tempfile.TemporaryDirectory(prefix="bookwyrm-", dir=str(Path(__file__).resolve().parent)) as tmp_dir:
        temp_path = Path(tmp_dir) / csv_file.filename
        output_path = Path(tmp_dir) / "groups-report.txt"
        await csv_file.save(temp_path)

        parse_sheet = _load_parse_sheet_module()
        signup_manager = parse_sheet.SignupManager()

        try:
            signup_manager.process(input_path=temp_path, output_path=output_path)
            model = signup_manager.build_model_payload()
        except Exception as exc:
            await ctx.followup.send(f"Parsing failed.\n```\n{exc}\n```")
            return

        if not output_path.exists():
            await ctx.followup.send("Parsing completed, but no report file was produced.")
            return

        data_manager.save_signups_to_db(
            None,
            ctx.guild.id,
            model.get("users", []),
            [],
        )

        await _send_review_response(ctx, model, output_path)


@bot.slash_command(guild_ids=ALLOWED_GUILDS)
async def edit_groups(ctx, groups_text: str):
    await ctx.defer()

    if not groups_text or not groups_text.strip():
        await ctx.followup.send("Please provide a GROUPS list as text.")
        return

    editable_key = _editable_model_key(ctx.guild.id, ctx.author.id)
    base_model = EDITABLE_MODELS.get(editable_key)
    if base_model is None:
        await ctx.followup.send("No editable model found. Reject or timeout a parse suggestion first.")
        return

    with tempfile.TemporaryDirectory(prefix="bookwyrm-edit-", dir=str(Path(__file__).resolve().parent)) as tmp_dir:
        report_path = Path(tmp_dir) / "groups-report-edited.txt"

        try:
            edited_groups = _parse_groups_list(groups_text)
            edited_model = _rebuild_model_from_groups(base_model, edited_groups)
            report_text = _render_report_text(edited_model)
        except ValueError as exc:
            await ctx.followup.send(f"Could not apply edited groups: {exc}")
            return

        report_path.write_text(report_text, encoding="utf-8")
        await _send_review_response(ctx, edited_model, report_path)


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    pending = PENDING_MODEL_REVIEWS.get(payload.message_id)
    if not pending:
        return

    if payload.user_id != pending["invoker_id"]:
        return

    reaction = str(payload.emoji)
    if reaction not in {APPROVE_EMOJI, REJECT_EMOJI}:
        return

    channel = bot.get_channel(payload.channel_id)
    if channel is None:
        channel = await bot.fetch_channel(payload.channel_id)
    send_fn = cast(Callable[[str], Awaitable[Any]] | None, getattr(channel, "send", None))

    guild = getattr(channel, "guild", None)
    if guild is None:
        guild = bot.get_guild(pending["guild_id"])

    if reaction == APPROVE_EMOJI:
        if pending["saved"]:
            return

        _cancel_pending_timeout(pending)

        groups = pending["model"].get("groups", [])
        cm.guild_id = pending["guild_id"]

        for group in groups:
            group_name = group.get("name", "")
            discussion_thread, _ = await cm.build_group_threads(name=group_name, guild=guild)
            thread_id = getattr(discussion_thread, "id", None)
            if thread_id is None:
                raise ValueError(f"Could not determine discussion thread id for group '{group_name}'")
            group["thread_id"] = int(thread_id)

        data_manager.save_groups_to_db(
            pending["timestamp"],
            pending["guild_id"],
            groups,
        )
        pending["saved"] = True
        if send_fn is not None:
            await send_fn("Saved parsed groups to the database.")
        PENDING_MODEL_REVIEWS.pop(payload.message_id, None)
        return

    _cancel_pending_timeout(pending)
    _promote_model_for_editing(pending)
    PENDING_MODEL_REVIEWS.pop(payload.message_id, None)

    if send_fn is not None:
        await send_fn("Rejected parsed groups. Model kept in memory for `/edit_groups` and not saved.")

bot.run(os.getenv('TOKEN'))
