import os
import json
import subprocess
import sys
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

# message_id -> pending parse model/details
PENDING_PARSE_CONFIRMATIONS = {}
data_manager = TestDataManager(Path(__file__).resolve().parent / "signups-test.txt")

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
            disc, sub = await cm.build_group_threads(name=n)
            output.append([n, cm.get_thread_link_from_obj(disc), cm.get_thread_link_from_obj(sub)])
    else:
        disc, sub = await cm.build_group_threads(name=name)
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
        model_path = Path(tmp_dir) / "groups-model.json"
        await csv_file.save(temp_path)

        completed = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parent / "parse-sheet.py"),
                str(temp_path),
                "-o", str(output_path),
                "--model-output", str(model_path),
            ],
            cwd=Path(__file__).resolve().parent,
            capture_output=True,
            text=True,
        )

        if completed.returncode != 0:
            await ctx.followup.send(
                f"Parsing failed.\n```\n{completed.stderr.strip() or completed.stdout.strip()}\n```"
            )
            return

        if not output_path.exists():
            await ctx.followup.send("Parsing completed, but no report file was produced.")
            return

        if not model_path.exists():
            await ctx.followup.send("Parsing completed, but no model file was produced.")
            return

        with model_path.open("r", encoding="utf-8") as handle:
            model = json.load(handle)

        data_manager.save_signups_to_db(
            None,
            ctx.guild.id,
            model.get("users", []),
            [],
        )

        result_message = await ctx.followup.send(
            file=discord.File(output_path, filename=output_path.name),
            wait=True,
        )
        await result_message.add_reaction(APPROVE_EMOJI)
        await result_message.add_reaction(REJECT_EMOJI)

        PENDING_PARSE_CONFIRMATIONS[result_message.id] = {
            "invoker_id": ctx.author.id,
            "guild_id": ctx.guild.id,
            "timestamp": model.get("group_timestamp", 0),
            "model": model,
            "saved": False,
        }


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    pending = PENDING_PARSE_CONFIRMATIONS.get(payload.message_id)
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

    if reaction == APPROVE_EMOJI:
        if pending["saved"]:
            return

        data_manager.save_groups_to_db(
            pending["timestamp"],
            pending["guild_id"],
            pending["model"].get("groups", []),
        )
        pending["saved"] = True
        if send_fn is not None:
            await send_fn("Saved parsed groups to the database.")
        PENDING_PARSE_CONFIRMATIONS.pop(payload.message_id, None)
        return

    if send_fn is not None:
        await send_fn("Rejected parsed groups. Model kept in memory and not saved.")

bot.run(os.getenv('TOKEN'))
