import discord
import os
from dotenv import load_dotenv

load_dotenv()
bot = discord.Bot()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.slash_command(guild_ids=[1274792500975894589])
async def hello(ctx):
    await ctx.respond("Hello!")

bot.run(os.getenv('TOKEN'))
