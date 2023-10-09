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
def setup(bot): # Create a bot instance
    
    @bot.command()
    async def thanks(ctx, thankee: discord.Member):
        thanker = ctx.author
    
        if discord.utils.get(thankee.roles, name="YesRep") is not None:
            await handle_thanks(ctx, thanker, thankee)
        elif discord.utils.get(thankee.roles, name="NoRep") is not None:
            await ctx.send(opt_out_message.format(thankee_mention=thankee))
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
                    role = ctx.guild.get_role(yes_rep_id)
                    await ctx.send(opt_in_message.format(thankee_mention=thankee.mention))
                    await handle_thanks(ctx, thanker, thankee)
                elif str(reaction.emoji) == thumbs_down:
                    role = ctx.guild.get_role(no_rep_id)
                    await thankee.add_roles(role)
                    await ctx.send(opt_out_message.format(thankee_mention=thankee.mention))

            except asyncio.TimeoutError:
                await ctx.send(f"{thankee.mention}, you didn't respond in time. Please try again later.")
        

         # Update the cooldown dictionary with the current time for the thanker-thankee pair
        if thankee.id not in cooldown_dict:
            cooldown_dict[thankee.id] = {}
        cooldown_dict[thankee.id][thanker.id] = ctx.message.created_at




    @bot.command()
    async def scorecard(ctx, user: discord.Member = None):
        if user is None:
            user = ctx.author

        user_data = await get_user_data(user)
    
        if user_data:
            total_thanks = user_data.get("total_thanks", 0)
            await ctx.send(f"{user.display_name} has received {total_thanks} thanks!")
        else:
            await ctx.send("User data not found.")
    
    @bot.command()
    async def leaderboard(ctx):
        top_users = await get_top_users(5)  # Change 5 to the number of top users you want to display

        leaderboard_message = "Leaderboard:\n"
        for index, user in enumerate(top_users, start=1):
            leaderboard_message += f"{index}. {user['nickname']} - {user['total_thanks']} thanks\n"

        await ctx.send(leaderboard_message)            



    async def handle_thanks(ctx, thanker, thankee):
        if thanker.id == thankee.id:
            await ctx.send(giving_to_self.format(thankee_mention=thankee.mention))
            return
        elif in_cooldown(ctx, thanker, thankee):
            await ctx.send(still_on_cooldown.format(thankee_mention=thankee.mention))
            return   
        await save_user_thanks(ctx, thanker, thankee)
        thankee_total = await update_user_total(thankee)
        await ctx.send(award_message.format(thankee_mention=thankee.mention, thankee_total=thankee_total))

    async def save_user_thanks(ctx, thanker, thankee):
        user_thanks = {'thanker': thanker.id, 'thankee': thankee.id, 'created_at': ctx.message.created_at.timestamp()}
        await users_thanks.insert_one(user_thanks)

    async def update_user_total(thankee):
        total_thanks = 0
        user = await users.find_one({'user': thankee.id})
        if user:
            total_thanks = user["total_thanks"]
            total_thanks += 1
            await users.update_one({'_id': user['_id']}, {'$set': {'total_thanks': total_thanks}})
        else:
            user = {'user': thankee.id, 'nickname': thankee.display_name, 'total_thanks': 1}
            total_thanks += 1
            await users.insert_one(user)
        return total_thanks
    
    def in_cooldown(ctx, thanker, thankee): #Check if the thanker ID is in the cooldown_dict, Calculate the elapsed time in seconds and if greater than cooldown_time, remove the entry
        if thankee.id not in cooldown_dict:
            return False
        created_at = cooldown_dict[thankee.id].get(thanker.id)
        if not created_at:
            return False
        elapsed_time = (datetime.now(timezone.utc) - created_at).total_seconds() + 5
        if elapsed_time > cooldown_time:
            del cooldown_dict[thankee.id][thanker.id]
        if thanker.id in cooldown_dict[thankee.id]:
            return True
        else:
            return False
        
    async def get_user_data(user):
        user_data = await users.find_one({'user': user.id})
        return user_data
    
    async def get_top_users(limit):
        cursor = users.find().sort("total_thanks", pymongo.DESCENDING).limit(limit)
        top_users = await cursor.to_list(length=limit)
        return top_users

