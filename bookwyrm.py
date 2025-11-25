import discord
import os
from dotenv import load_dotenv
from channel_manager import ChannelManager
from resource_manager import ResourceManager

load_dotenv()
bot = discord.Bot()

cm = ChannelManager(ResourceManager())

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# @bot.slash_command(guild_ids=[1274792500975894589])
# async def hello(ctx):
#     await ctx.respond("Hello!")

@bot.slash_command(guild_ids=[1274792500975894589])
async def set_forum_ids(ctx, disc_forum : discord.ForumChannel, sub_forum : discord.ForumChannel):
    cm.set_channels(disc=disc_forum, sub=sub_forum)
    cm.guild_id = ctx.guild.id
    print(f"guild_id = {cm.guild_id}")
    await ctx.respond(f"we are in: **{str(ctx.guild).upper()}**\nset discussion forum to **{disc_forum}** \nset submission forum to **{sub_forum}**")

@bot.slash_command(guild_ids=[1274792500975894589])
async def build_group(ctx, name):
    if ", " in name:
        names = name.split(", ")
        for n in names:
            await cm.build_group_threads(name=n)
        await ctx.respond(f"built {len(names)} groups")
    else:
        disc, sub = await cm.build_group_threads(name=name)
        
        await ctx.respond(f"built groups for {name}")

bot.run(os.getenv('TOKEN'))
