import os
import subprocess
import sys
import tempfile
from pathlib import Path

import discord
from dotenv import load_dotenv

from channel_manager import ChannelManager

ALLOWED_GUILDS = [1274792500975894589, 687838172348284995]


load_dotenv()
bot = discord.Bot()

cm = ChannelManager()

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

    await ctx.respond(f"Building `{name}`...")

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
    if not csv_file or not csv_file.filename.lower().endswith(".csv"):
        await ctx.respond("Please upload the CSV file from the signup form.", ephemeral=True)
        return

    await ctx.defer()

    with tempfile.TemporaryDirectory(prefix="bookwyrm-", dir=str(Path(__file__).resolve().parent)) as tmp_dir:
        temp_path = Path(tmp_dir) / csv_file.filename
        output_path = Path(tmp_dir) / "groups-report.txt"
        await csv_file.save(temp_path)

        completed = subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parent / "parse-sheet.py"), str(temp_path), "-o", str(output_path)],
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

        await ctx.followup.send(file=discord.File(output_path, filename=output_path.name))

bot.run(os.getenv('TOKEN'))
