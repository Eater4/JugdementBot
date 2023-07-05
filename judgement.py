import discord
from discord.ext import commands
from discord import Embed
import asyncio

intents = discord.Intents.default()
intents.reactions = True
intents.members = True
intents.message_content = True  

bot = commands.Bot(command_prefix='^', intents=intents, help_command=None)
is_judging = False
muted_users = {}  # Dictionary to store muted users and their durations
default_mute_duration = 60
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    await bot.change_presence(activity=discord.Game('Court'))


async def extract_text_and_image_url(ctx, message):
    if message.startswith('https://discord.com/channels/') or message.startswith ('https://cdn.discordapp.com/attachemets/'):
        try:
            guild_id, channel_id, message_id = message.split('/')[-3:]
            guild = discord.utils.find(lambda g: g.id == int(guild_id), bot.guilds)
            channel = discord.utils.find(lambda c: c.id == int(channel_id), guild.text_channels)
            fetched_message = await channel.fetch_message(int(message_id))
            extracted_text = fetched_message.content
                    
            image_url = None

            if fetched_message.attachments:
                attachment = fetched_message.attachments[0]
                if attachment.url.endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    image_url = attachment.url
                if attachment.url.endswith(('.mov','.mp4', '.avi')):
                    if extracted_text == ("") and attachment.url.endswith(('.mov','.mp4', '.avi')):
                        extracted_text = "this video: " + "https://discord.com/channels/" + str(guild_id) + "/" + str(channel_id) + "/" + str(message_id)
                    else:
                        extracted_text = extracted_text + " __and this video__" + "https://discord.com/channels/" + str(guild_id) + "/" + str(channel_id) + "/" + str(message_id)
                if extracted_text == ("") and attachment.url.endswith(('.png', '.jpg', '.jpeg')):
                    extracted_text = "**this picture**"
                if extracted_text == ("") and attachment.url.endswith(('.gif')):
                    extracted_text = "**this gif**"
                if extracted_text == (""):
                    extracted_text = "**this file **" + "https://discord.com/channels/" + str(guild_id) + "/" + str(channel_id) + "/" + str(message_id)      
            return extracted_text, image_url

        except (ValueError, discord.NotFound):
            pass

    return message, None


@bot.event
async def mute_user(ctx,user,duration):
    global muted_users
    global is_judging
    is_judging = False
    await bot.change_presence(activity=discord.Game('Court'))

    if user.id in muted_users:
        muted_users[user.id] += duration
    else:
        muted_users[user.id] = duration
        mute_role = discord.utils.get(user.guild.roles, name="Muted")
        if not mute_role:
            mute_role = await user.guild.create_role(name="Muted")
            for channel in user.guild.channels:
                await channel.set_permissions(mute_role, send_messages=False)
        await user.add_roles(mute_role)
    await asyncio.sleep(duration)
    await user.remove_roles(mute_role)
    if muted_users[user.id] > duration:
        muted_users[user.id] -= duration
        await mute_user(user, muted_users[user.id])
    else:
        del muted_users[user.id]
    embed = Embed(
            title="Unmuted",
            description=f"Mute ended for {user.display_name}.",
            color=discord.Color.green()
        )
    await ctx.send(embed=embed)



@bot.command()
@commands.has_role('Admin')
async def jt(ctx, userbeingjudged: discord.Member, *, message=None):
    global is_judging

    if is_judging:
        await ctx.send("A judgement process is already in progress. Please wait until it is completed.")
        return

    if not userbeingjudged:
        await ctx.send("Please provide the user to be judged.")
        return

    extracted_text = None
    image_url = None

    if message:
        if message != "no reason given":
            if message.startswith("http") and message.endswith(('.png','.jpg','jpeg')):                
                if not 'discord.com/channels'in message:
                    image_url = message
                    extracted_text = "**this picture**"
                if message.startswith("http") and message.endswith(('.gif')):
                    image_url = message 
                    extracted_text = "**this gif**"
                if message.startswith("http") and message.endswith(('.mov','.mp4', '.avi')):
                    extracted_text = "**the linked video**"
            else:
                extracted_text, image_url = await extract_text_and_image_url(ctx, message)

    if extracted_text is None:
        extracted_text = "**no reason given**"

    embed = Embed(
        title="Judgement Time!",
        description=f"We are judging **{userbeingjudged.display_name}** "
                    f"because of {extracted_text} "
                    f"Should they get a mute?",
        color=discord.Color.orange()
    )

    embed.set_thumbnail(url=userbeingjudged.avatar.url)

    if image_url:
        embed.set_image(url=image_url)

    msg = await ctx.send(embed=embed)
    await msg.add_reaction('⬆️')
    await msg.add_reaction('⬇️')
    await bot.change_presence(activity=discord.Game('Now Judging'))
    is_judging = True
    await asyncio.sleep(15)

    channel = await bot.fetch_channel(ctx.channel.id)
    msg = await channel.fetch_message(msg.id)
    upvotes = 0
    downvotes = 0
    try:
        for reaction in msg.reactions:
            if str(reaction.emoji) == '⬆️':
                upvotes = reaction.count - 1
            elif str(reaction.emoji) == '⬇️':
                downvotes = reaction.count - 1
    except:
        print ("Process Canceled by User")         
    if upvotes > downvotes and is_judging is True:
        if msg.author == bot.user and msg.embeds and "Judgement Time!" in msg.embeds[0].title:
            await msg.delete()
        embed = Embed(
            title="Mute",
            description=f"Muting {userbeingjudged.display_name} for {default_mute_duration} seconds because of {extracted_text}.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        await mute_user(ctx, userbeingjudged, default_mute_duration)
        await bot.change_presence(activity=discord.Game('Court'))
    else:
        if msg.author == bot.user and msg.embeds and "Judgement Time!" in msg.embeds[0].title:
            await msg.delete()
        embed = Embed(
            title="Mute Averted",
            description=f"Mute averted for {userbeingjudged.display_name}.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        await bot.change_presence(activity=discord.Game('Court'))
    is_judging = False


@bot.command()
@commands.has_role('Admin')
async def cancel(ctx):
    global is_judging

    if is_judging:
        is_judging = False
        await ctx.send("Judgement process has been canceled.")
        await bot.change_presence(activity=discord.Game('Court'))


    else:
        await ctx.send("No judgement process is currently running.")
        return

    channel = await bot.fetch_channel(ctx.channel.id)
    async for msg in channel.history():
        if msg.author == bot.user and msg.embeds and "Judgement Time!" in msg.embeds[0].title:
            await msg.delete()
            break

@bot.command()
@commands.has_role('Admin')
async def sm(ctx, duration):
    global default_mute_duration

    try:
        duration_seconds = int(duration)
        if duration_seconds <= 0:
            await ctx.send("tryna catch me lacking huh")
            return
        elif duration_seconds > 86000:
            await ctx.send("just ban them at this point gawd mf damn")
            return

        default_mute_duration = duration_seconds
        await ctx.send(f"Default mute duration set to {default_mute_duration} seconds.")
    except ValueError:
        await ctx.send("invalid input")



@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send("kunth probably ran this command. YOU HAVE NO RIGHT TO USE THIS COMMAND **BEGONE**")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Usage: !jt (user) (reason[optional])")
    

@bot.command()
@commands.has_role('Admin')
async def help(ctx):
    embed = Embed(
        title="Help",
        description="**!jt command**:\nStarts a judgement process for a user.\n\n**!cancel command**:\nCancels the ongoing judgement process.\n\n",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

@bot.command()
async def info(ctx):
    embed = Embed(
        title="I love.....",
        description="Democracy",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)


bot.run('your bot token')
