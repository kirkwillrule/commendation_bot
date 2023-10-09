import discord
from discord.ext import commands
import asyncio
import pymongo
from motor.motor_asyncio import AsyncIOMotorClient
# https://motor.readthedocs.io/en/stable/tutorial-asyncio.html
from dotenv import dotenv_values, load_dotenv
from datetime import datetime, timezone 
# Define constants

db_name = "commendation"

load_dotenv('.env')  #VERIFY WHERE TO GET THE LOCAL VARIABLES
secrets = dotenv_values()
# Create a bot instance
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)
mongodb_uri = secrets["mongodb_encoded_connection"]
client = AsyncIOMotorClient(mongodb_uri)
db = client[db_name]
users = db.users
users_thanks  = db.users_thanks
user_nickname = db.user_nickname

def setup(bot):
    @bot.command()

    async def leaderboard(ctx):
        top_users = await get_top_users(5)  # Change 5 to the number of top users you want to display

        leaderboard_message = "Leaderboard:\n"
        for index, user in enumerate(top_users, start=1):
            leaderboard_message += f"{index}. {user['nickname']} - {user['total_thanks']} thanks\n"

        await ctx.send(leaderboard_message)

    async def scorecard(ctx, user: discord.Member = None):
        if user is None:
            user = ctx.author

        user_data = await get_user_data(user)
        
        if user_data:
            total_thanks = user_data.get("total_thanks", 0)
            await ctx.send(f"{user.display_name} has received {total_thanks} thanks!")
        else:
            await ctx.send("User data not found.")

    async def get_user_data(user):
        user_data = await users.find_one({'user': user.id})
        return user_data
    
    async def get_top_users(limit):
        cursor = users.find().sort("total_thanks", pymongo.DESCENDING).limit(limit)
        top_users = await cursor.to_list(length=limit)
        return top_users
