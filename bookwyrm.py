import discord
import os
from dotenv import load_dotenv
from channel_manager import ChannelManager

load_dotenv()
bot = discord.Bot()

c_manager = ChannelManager()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# @bot.slash_command(guild_ids=[1274792500975894589])
# async def hello(ctx):
#     await ctx.respond("Hello!")

@bot.slash_command(guild_ids=[1274792500975894589])
async def set_forum_ids(ctx, disc_forum : discord.ForumChannel, sub_forum : discord.ForumChannel):
    c_manager.set_channels(disc=disc_forum, sub=sub_forum)
    await ctx.respond(f"set discussion forum to {disc_forum} and submission forum to {sub_forum}")

@bot.slash_command(guild_ids=[1274792500975894589])
async def build_group(ctx):
    await c_manager.discussion_forum.create_thread(name="Hippohammer Discussion", content="test thread")
    await ctx.respond("built 1 group")


bot.run(os.getenv('TOKEN'))
