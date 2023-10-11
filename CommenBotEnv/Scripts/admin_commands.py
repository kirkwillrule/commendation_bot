import discord
from discord.ext import commands
import asyncio
import pymongo
from motor.motor_asyncio import AsyncIOMotorClient # https://motor.readthedocs.io/en/stable/tutorial-asyncio.html
from dotenv import dotenv_values, load_dotenv
from datetime import datetime, timezone 

# Define constants
award_message = "{thankee_mention} has been awarded points!  They now have {thankee_total} points!"
opt_out_message = "{thankee_mention} has opted out of the program. Points not assigned."
opt_in_message = "{thankee_mention} has opted in. Points will be assigned."
giving_to_self = " Dont be silly {thankee_mention}, you cant thank yourself!"
still_on_cooldown = "you have already thanked {thankee_mention} today, they sure are awesome!"

#secrets setup, mongodb setup, 
db_name = "commendation"
load_dotenv('.env')  #VERIFY WHERE TO GET THE LOCAL VARIABLES
secrets = dotenv_values()
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)
mongodb_uri = secrets["mongodb_encoded_connection"]
client = AsyncIOMotorClient(mongodb_uri)
db = client[db_name]
users = db.users
users_thanks  = db.users_thanks
user_nickname = db.user_nickname
yes_rep_id = secrets['yes_rep_role_id']
no_rep_id = secrets['no_rep_role_id']
cooldown_dict = {}
cooldown_time = 10  # change to however long you want the cooldown time to be. anything 0 or greater
def setup(bot):
    @bot.command()
    async def admin_command(ctx):
        # Check if the user invoking the command has the admin role
        if secrets["admin_role_title"] in [role.name for role in ctx.author.roles]:
            await ctx.send("you can use this command because you have the admin role.")
            # Add your admin-specific functionality here
        else:
            await ctx.send("You don't have permission to use this command.")


    @bot.command()

    async def points_change(ctx, member, points):
        # Check if the user invoking the command has the admin role
        if not await commands.has_role(secrets["admin_role_title"]).predicate(ctx):
            await ctx.send("You don't have permission to use this command.")
            return

        try:
            points_int = int(points)
        except ValueError:
            print(f"Conversion to int failed. Type of 'points': {type(points)}")        
        # Check if the points parameter is a positive integer
        if points_int < 0:
            print(type(points)) 
            await ctx.send("Invalid points value. Please provide a positive integer.")
            return
        user_data = await get_user_data(member)

        if user_data:
            total_thanks = user_data.get("total_thanks", 0)
            if total_thanks >= points_int:
                total_thanks -= points_int
                await users.update_one({'user': member.id}, {'$set': {'total_thanks': total_thanks}})
                await ctx.send(f"Removed {points} points from {member.display_name}. They now have {total_thanks} points.")
            else:
                await ctx.send(f"{member.display_name} doesn't have enough points to remove.")
        else:
            await ctx.send("User data not found.")

    async def get_user_data(user):
        user_data = await users.find_one({'user': user.id})
        return user_data