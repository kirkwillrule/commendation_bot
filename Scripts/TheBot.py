import discord
from discord.ext import commands
#import ect_bot_changes
import functions #THE BASE FUNCTIONALITY OF THE BOT, INCLUDES MOST CURRENT ACTIVE FUNCTIONS AND COMMANADS
import listening   #USED TO VERIFY THE BOT IS CONNECTED
import test_bench  #THE MODULE FOR TALKING TO THE BOT IN THE DISCORD TEST SERVER
from dotenv import dotenv_values, load_dotenv  #USED TO LOAD THE ENVIROMENT VARIABLES SUCH AS PASSWORDS AND API KEYS

load_dotenv('.env')  #VERIFY WHERE TO GET THE LOCAL VARIABLES
secrets = dotenv_values() #CREATE A WAY TO CALL LOCAL VARIABLE IN THE ENVIROMENT
intents = discord.Intents.all() #controls what discord events are sent to the bot
intents.members = True  #tell discordd api the bot is allowed to access the things it needs
bot = commands.Bot(command_prefix='!', intents=intents) 

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    
    permissions = discord.Permissions(2064000588865)  # Create Permissions object from the permission integer, this verifys the kinds of things the bot is allowed to do 

listening.setup(bot)

test_bench.setup(bot)

functions.setup(bot)

bot.run(secrets['bot_token'])
