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