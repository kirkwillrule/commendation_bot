import discord
from discord.ext import commands

def setup(bot):
    @bot.command()
    async def listen(ctx):
        await ctx.send("I'm listening!")