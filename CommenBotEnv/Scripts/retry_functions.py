import discord
from discord.ext import commands
import asyncio
import pymongo
import functools
from functools import partial
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
yes_role_name = 'YesRep'
no_role_name = 'NoRep'
dnr_timer = 15.0 #how long you have to reply to thumbsup/down
yes_rep_id = 1119125752311447572
no_rep_id = 1119125876320239638
cooldown_dict = {}
valid_thankies = []
invalid_thankies = []

cooldown_time = 10  # change to however long you want the cooldown time to be. anything 0 or greater
def setup(bot): # Create a bot instance
    @bot.command()

    async def thanks(ctx, *args):
        thanker = ctx.author
        valid_thankies.clear()
        invalid_thankies.clear()

        # Lists to collect users who can receive points immediately and those who need opt-in/opt-out
        valid_users = []
        opt_in_out_users = []

        for arg in args:
            thankee = None
            try:
                thankee = await commands.MemberConverter().convert(ctx, arg)
            except commands.BadArgument:
                pass

            if thankee:
                if thankee == thanker:
                    invalid_thankies.append(thankee)
                elif discord.utils.get(thankee.roles, name=yes_role_name) is not None:
                    valid_users.append(thankee)
                elif discord.utils.get(thankee.roles, name=no_role_name) is not None:
                    invalid_thankies.append(thankee)
                else:
                    opt_in_out_users.append(thank_single(ctx, arg, thanker, valid_thankies, invalid_thankies))

        # Process users with 'yesrep' role immediately
        for thankee in valid_users:
            await handle_thanks(ctx, thanker, thankee)

        # Concurrently process opt-in/opt-out for users without roles
        await asyncio.gather(*opt_in_out_users)

        if invalid_thankies:
            invalid_mention_list = ', '.join([str(thankee) for thankee in invalid_thankies])
            await ctx.send(f"The following mentions are invalid: {invalid_mention_list}")



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

        add_to_cooldown(ctx, thanker, thankee) #append thanker:thankee pair to cooldown dict after handling thanks

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
    
    def add_to_cooldown(ctx, thanker, thankee):
        if thankee.id not in cooldown_dict:
            cooldown_dict[thankee.id] = {}
        cooldown_dict[thankee.id][thanker.id] = datetime.now(timezone.utc)

    async def thank_single(ctx, arg, thanker, valid_thankies, invalid_thankies):
        try:
            thankee = await commands.MemberConverter().convert(ctx, arg)
        except commands.BadArgument:
            return

        if thankee:
            if thankee == thanker:
                invalid_thankies.append(thankee)
            elif discord.utils.get(thankee.roles, name=yes_role_name) is not None:
                valid_thankies.append(thankee)
            elif discord.utils.get(thankee.roles, name=no_role_name) is not None:
                invalid_thankies.append(thankee)
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
                    reaction, _ = await bot.wait_for('reaction_add', timeout=dnr_timer, check=check)

                    if str(reaction.emoji) == thumbs_up:
                        role = ctx.guild.get_role(yes_rep_id)
                        await thankee.add_roles(role)
                        await ctx.send(opt_in_message.format(thankee_mention=thankee.mention))
                        valid_thankies.append(thankee)

                        # After opting in, assign points
                        await handle_thanks(ctx, thanker, thankee)

                    elif str(reaction.emoji) == thumbs_down:
                        role = ctx.guild.get_role(no_rep_id)
                        await thankee.add_roles(role)
                        await ctx.send(opt_out_message.format(thankee_mention=thankee.mention))
                        invalid_thankies.append(thankee)

                except asyncio.TimeoutError:
                    await ctx.send(f"{thankee.mention}, you didn't respond in time. Please try again later.")
                    invalid_thankies.append(thankee)
