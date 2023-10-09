import discord
from discord.ext import commands
import asyncio
from dotenv import dotenv_values
# Define constants
yes_rep_role_id = 1119125752311447572
no_rep_role_id = 1119125876320239638
award_message = "{thankee_mention} has been awarded points!"
opt_out_message = "{thankee_mention} has opted out of the program. Points not assigned."
opt_in_message = "{thankee_mention} has opted in. Points will be assigned."

cooldown_dict = {}
cooldown_time = 7200  # 2 hours cooldown

# Create a bot instance
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)



def setup(bot):
    
    @bot.command()
    async def thanks(ctx, thankee: discord.Member):
        thanker = ctx.author
    
        if discord.utils.get(thankee.roles, name="YesRep") is not None:
            await ctx.send(award_message.format(thankee_mention=thankee.mention))
        elif discord.utils.get(thankee.roles, name="NoRep") is not None:
            await ctx.send(opt_out_message.format(thankee_mention=thankee.mention))
        else:
            thumbs_up = '👍'
            thumbs_down = '👎'
            
            message = await ctx.send(f"{thankee.mention}, would you like to opt in or out? React with {thumbs_up} for opt-in or {thumbs_down} for opt-out.")

            await message.add_reaction(thumbs_up)
            await message.add_reaction(thumbs_down)

            def check(reaction, user):
                return (
                    user == thankee
                    and str(reaction.emoji) in [thumbs_up, thumbs_down]
                    and reaction.message.id == message.id
                )

            try:
                reaction, _ = await bot.wait_for('reaction_add', timeout=10.0, check=check)

                if str(reaction.emoji) == thumbs_up:
                    role = ctx.guild.get_role(yes_rep_role_id)
                    await thankee.add_roles(role)
                    await ctx.send(opt_in_message.format(thankee_mention=thankee.mention))
                elif str(reaction.emoji) == thumbs_down:
                    role = ctx.guild.get_role(no_rep_role_id)
                    await thankee.add_roles(role)
                    await ctx.send(opt_out_message.format(thankee_mention=thankee.mention))

            except asyncio.TimeoutError:
                await ctx.send(f"{thankee.mention}, you didn't respond in time. Please try again later.")
         
         # Update the cooldown dictionary with the current time for the thanker-thankee pair
        if thankee.id not in cooldown_dict:
            cooldown_dict[thankee.id] = {}
        cooldown_dict[thankee.id][thanker.id] = ctx.message.created_at