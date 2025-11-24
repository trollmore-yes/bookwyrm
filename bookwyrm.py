import discord
import os
from dotenv import load_dotenv
import channel_manager

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
async def make_thread_in_forum(ctx, channel : discord.ForumChannel):
    await channel.create_thread(name="test thread", content="this is a test thread")



bot.run(os.getenv('TOKEN'))
