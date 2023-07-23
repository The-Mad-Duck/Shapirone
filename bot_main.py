import concurrent.futures
import time

import discord
from discord import app_commands
from discord.utils import get
import sqlite3
import os
import pandas as pd
import enum
import datetime
import typing
import threading
from concurrent.futures import ThreadPoolExecutor
from time import sleep
import asyncio
import requests
import re


intents = discord.Intents.default()
intents.message_content = True
intents.guild_messages = True
intents.members = True
client = discord.Client(intents = intents)
tree = app_commands.CommandTree(client)

stack = []
rolesindex = ['II ', 'III ', 'IV ', 'V ', 'VI ', 'VII ', 'VIII ', 'IX ', 'X ']

ban = 1
week = 2
day = 3
hour = 4
min_10 = 5

mutetimes = {
    "Gore":                     ban,
    "CP":                       ban,
    "Illegal content":          ban,
    "Zoophilia":                ban,
    "Severe Doxxing":           ban,
    "Repulsive Porn":           ban,
    "Pedophilia":               ban,
    "ToS Name":                 day,
    "Pedo Jokes":               day,
    "Cropped Porn":             hour,
    "Cartoon Porn":             hour,
    "Porn":                     day,
    "Pedo Framing":             hour,
    "Banned Slurs":             min_10,
    "Slurs":                    min_10,
    "Suicide Jokes":            min_10,
    "Death Threats":            min_10,
    "Advertising":              min_10,
    "Non-English":              min_10,
    "Spam Ping":                min_10,
    "Spam":                     min_10,
    "Nazi":                     min_10,
    "Sensitive Topics":         min_10,
    "Disrespecting Religions":  min_10,
    "Harassment":               min_10,
    "Racism":                   min_10,
}


con = sqlite3.connect("BotDatabase")
cur = con.cursor()
# con.execute("""DROP TABLE IF EXISTS Warns""")
con.execute("""CREATE TABLE IF NOT EXISTS Warns(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild INTEGER,
    uid INTEGER,
    mid INTEGER,
    reason TEXT,
    timewarned DATETIME)""")

# con.execute("DROP TABLE IF EXISTS Voting_Channels")
con.execute("""CREATE TABLE IF NOT EXISTS Voting_Channels(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild INTEGER,
    channel_id INTEGER UNIQUE,
    top_channel INTEGER)""")

# con.execute("DROP TABLE IF EXISTS Top_Vote_Channels")
con.execute("""CREATE TABLE IF NOT EXISTS Top_Vote_Channels(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild INTEGER,
    channel_id INTEGER UNIQUE)""")

con.execute("""CREATE TABLE IF NOT EXISTS Guild_Config(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild INTEGER,
    vote_ratio INTEGER,
    warn_cooldown INTEGER,
    mute_warncount INTEGER,
    ban_warncount INTEGER)""")

# con.execute("DROP TABLE IF EXISTS Message_Counts")
con.execute("""CREATE TABLE IF NOT EXISTS Message_Counts(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild INTEGER,
    uid INTEGER,
    messagecount INTEGER)""")

con.commit()


# This will keep a time checking loop running
async def checkTime():
    # This function runs periodically every 1 second
    while(1):
        await asyncio.sleep(1)
        now = datetime.datetime.now()
        day = now.weekday()
        current_time = now.strftime("%H:%M:%S")
        if (current_time == '18:00:00'):  # check if matches with the desired time
            await doTopScans()

async def check_channel(channel: int, top: int):
    channel1 = client.get_channel(channel)
    channel2 = client.get_channel(top)
    topmes = None
    topint = 0
    messages = [message async for message in channel1.history(after=datetime.datetime.now() - datetime.timedelta(days=1))]
    for message in messages:
        reacts = message.reactions
        try:
            if message.reactions[0].emoji == '👍' and message.reactions[1].emoji == '👎':
                if message.reactions[0].count - message.reactions[1].count >= topint:
                    topint = message.reactions[0].count - message.reactions[1].count
                    topmes = message
        except:
            continue
    if topmes is not None:
        print("Top message: " + topmes.content)
        con.execute(f"""INSERT INTO TOPS(mesid, chnid, topid, votes) VALUES ({topmes.id}, {channel}, {top}, {topint})""")
        # await channel2.send(f"{topint} votes, in channel {channel1.name}, from {topmes.author}:\n{topmes.content}")

async def doTopScans():
    con.execute("""DROP TABLE IF EXISTS TOPS""")
    con.execute("""CREATE TABLE TOPS(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mesid INTEGER,
    chnid INTEGER,
    topid INTEGER,
    votes INTEGER)""")
    query = pd.read_sql_query(f"""SELECT channel_id, top_channel, guild FROM Voting_Channels""", con)
    query.sort_values(by=['guild'])
    for index in query.index:
        await check_channel(query['channel_id'][index], query['top_channel'][index])
    query = pd.read_sql_query(f""";WITH val AS (
        SELECT *, ROW_NUMBER() OVER (PARTITION BY topid ORDER BY votes DESC) AS rn
        FROM TOPS)
        SELECT *
        FROM val
        WHERE rn = 1""", con)
    print(query)
    for index in query.index:
        channel1 = client.get_channel(query['chnid'][index])
        mes = await channel1.fetch_message(query['mesid'][index])
        channel2 = client.get_channel(query['topid'][index])
        # TODO: ADD ROLE MENTION FOR @Best of pings
        role = get(channel2.guild.roles, name='Best of pings')
        await channel2.send("Today's best song is...\n\n" + mes.content + " \n\nStay tuned for tomorrow!" + (role.mention if role is not None else ""))


class warns_view(discord.ui.View):
    def __int__(self):
        super().__init__(timeout=None)

    @discord.ui.button(custom_id="Left", emoji="⬅")
    async def go_left(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("left arrow")

    @discord.ui.button(custom_id="Right", emoji="➡")
    async def go_right(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("right arrow")


# Boot
@client.event
async def on_ready():
    await tree.sync()
    print('logged in as {0.user}'.format(client))
    query = pd.read_sql_query("""SELECT * FROM Top_Vote_Channels""", con)
    print (query)
    asyncio.create_task(checkTime())


@tree.command(
    name = "help",
    description="Lists all commands"
)
@app_commands.checks.has_permissions(mute_members=True)
async def help(interaction: discord.Interaction):
    str = "```"
    for cmd in tree.get_commands():
        str += f"{'{:<22}'.format(cmd.name)}: {cmd.description}\n"
    str += "```"
    await interaction.response.send_message(str)



# Echo command
@tree.command(name = "echo", description = "Echo.")
@app_commands.checks.has_permissions(administrator=True)
async def echo(interaction: discord.Interaction, string: str):
    await interaction.response.send_message(f"{string}")


@tree.command(
    name = "testtop",
    description="Get top message in guild channels"
)
@app_commands.checks.has_permissions(administrator=True)
async def testtop(interaction: discord.Interaction):
    await interaction.response.send_message("Testing now, check top channels")
    await doTopScans()
    await interaction.channel.send("Done.")


# Warn
@tree.command(
    name = "warn",
    description = "Warns a member.")
@app_commands.checks.has_permissions(mute_members=True)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str):
    if (member.top_role >= interaction.user.top_role):
        await interaction.response.send_message(":x: Cannot warn a member with higher rank than you.")
        return
    await interaction.response.send_message(f"{interaction.user.name} warned user {member.mention} for '{reason}' ({interaction.guild})")
    reason.replace("\"", "\\\"")
    command = f"""INSERT INTO Warns(guild, uid, mid, reason, timewarned) VALUES
        ({int(interaction.guild.id)}, {int(member.id)}, {int(interaction.user.id)}, "{reason}", DATETIME('now'))"""
    print(command)
    con.execute(command)
    con.commit()


# Time Out
@tree.command(
    name = "timeout",
    description = "times out a member and adds a warn")
@app_commands.checks.has_permissions(mute_members=True)
@app_commands.describe(times='times to choose from')
@app_commands.choices(times=[
    app_commands.Choice(name='second',  value=0),
    app_commands.Choice(name='minute',  value=1),
    app_commands.Choice(name='hour',    value=2),
    app_commands.Choice(name='day',     value=3),
    app_commands.Choice(name='month',   value=3),
])
async def timeout(interaction: discord.Interaction, member: discord.Member, time: int, times: app_commands.Choice[int], reason: str):
    if(member.top_role >= interaction.user.top_role):
        await interaction.response.send_message(":x: Cannot timeout a member with higher rank than you.")
        return
    inter = ""
    print(times.value)
    if times.value == 0:
        await member.timeout(datetime.timedelta(seconds=time), reason=reason)
    elif times.value == 1:
        await member.timeout(datetime.timedelta(minutes=time), reason=reason)
    elif times.value == 2:
        await member.timeout(datetime.timedelta(hours=time), reason=reason)
    elif times.value == 3:
        if time > 28:
            inter += ("I can only timeout up to 28 days, sorry. I'll do that.\n")
            await member.timeout(datetime.timedelta(days=28), reason=reason)
        else:
            await member.timeout(datetime.timedelta(days=time), reason=reason)
    elif times.value == 4:
        inter += ("I can only timeout up to 1 month, sorry. I'll do that.\n")
        await member.timeout(datetime.timedelta(days=28), reason=reason)
    msg = inter + f"{interaction.user.name} warned and timeouted user {member.mention} for '{reason}' ({interaction.guild})"
    await interaction.response.send_message(msg)
    await auditChannel(interaction, msg)
    reason.replace("\"", "\\\"")
    command = f"""INSERT INTO Warns(guild, uid, mid, reason, timewarned) VALUES
        ({int(interaction.guild.id)}, {int(member.id)}, {int(interaction.user.id)}, "{reason}", DATETIME('now'))"""
    print(command)
    con.execute(command)
    con.commit()


@tree.command(
    name="modstats",
    description="List stats for a moderator"
)
@app_commands.checks.has_permissions(mute_members=True)
async def modstats(interaction: discord.Interaction, member: discord.Member):
    query = pd.read_sql_query(
        f"""SELECT COUNT(*) FROM Warns WHERE mid = {member.id} AND guild = {interaction.guild.id}""", con)
    await interaction.response.send_message(f"User {member.mention} has {query['COUNT(*)'][0]} warns.")


@tree.command(
    name = "autotime",
    description = "Automatically timeout member."
)
@app_commands.checks.has_permissions(mute_members=True)
@app_commands.choices(reason=[
app_commands.Choice(name="Gore",                        value=1),
app_commands.Choice(name="CP",                          value=2),
app_commands.Choice(name="Illegal content",             value=3),
app_commands.Choice(name="Zoophilia",                   value=4),
app_commands.Choice(name="Severe Doxxing",              value=5),
app_commands.Choice(name="Repulsive Porn",              value=6),
app_commands.Choice(name="Pedophilia",                  value=7),
app_commands.Choice(name="ToS Name",                    value=21),
app_commands.Choice(name="Porn",                        value=22),
app_commands.Choice(name="Pedo Jokes",                  value=23),
app_commands.Choice(name="Cropped Porn",                value=31),
app_commands.Choice(name="Cartoon Porn",                value=32),
app_commands.Choice(name="Pedo Framing",                value=33),
app_commands.Choice(name="Banned Slurs",                value=41),
app_commands.Choice(name="Suicide Jokes",               value=43),
app_commands.Choice(name="Death Threats",               value=44),
app_commands.Choice(name="Advertising",                 value=45),
app_commands.Choice(name="Non-English",                 value=46),
app_commands.Choice(name="Spam",                        value=47),
app_commands.Choice(name="Spam Ping",                   value=48),
app_commands.Choice(name="Nazi",                        value=49),
app_commands.Choice(name="Sensitive Topics",            value=50),
app_commands.Choice(name="Disrespecting Religions",     value=51),
app_commands.Choice(name="Harassment",                  value=52),
app_commands.Choice(name="Racism",                      value=53),
])
async def autotime(interaction: discord.Interaction, member: discord.Member, reason: app_commands.Choice[int], consecutive: typing.Optional[bool], modnote: typing.Optional[str]):
    if (member.top_role >= interaction.user.top_role):
        await interaction.response.send_message(":x: Cannot timeout a member with higher rank than you.")
        return
    elif member.is_timed_out():
        await interaction.response.send_message(":x: Member is already timed out, another mod probably beat you to it!")
        return
    val = reason.value
    if consecutive:
        if val >= 50:
            val -=10
        val -= 10
    if modnote is None:
        reasoning = reason.name
    else:
        modnote.replace("\"", "\\\"")
        reasoning = reason.name + (", " + modnote)
    print(reasoning)
    if val >= 40:
        await member.timeout(datetime.timedelta(minutes=10), reason= reasoning)
    elif val >= 30:
        await member.timeout(datetime.timedelta(hours=1), reason= reasoning)
    elif val >= 20:
        await member.timeout(datetime.timedelta(days=1), reason= reasoning)
    elif val >= 10:
        await member.timeout(datetime.timedelta(days=7), reason= reasoning)
    else:
        await member.timeout(datetime.timedelta(days=28), reason="[BANNABLE] " + reasoning)
    command = f"""INSERT INTO Warns(guild, uid, mid, reason, timewarned) VALUES
        ({int(interaction.guild.id)}, {int(member.id)}, {int(interaction.user.id)}, "{reasoning}", DATETIME('now'))"""
    print(command)
    con.execute(command)
    con.commit()
    msg = f"{interaction.user.name} Timed out {member.mention} for {str(reasoning)}"
    await interaction.response.send_message(msg)
    await auditChannel(interaction, msg)



@tree.command(
    name = "unwarn",
    description = "Remove a warn from a member.")
async def unwarn(interaction: discord.Interaction, member: discord.Member, id: int):
    if (member.top_role >= interaction.user.top_role):
        await interaction.response.send_message(":x: Cannot remove a warn from a member with higher rank than you.")
        return
    cur.execute(f"""DELETE FROM Warns WHERE guild = {interaction.guild.id} AND uid = {member.id} AND id = {id}""")
    if cur.rowcount == 0:
        await interaction.response.send_message(f"Warn {id} for {member.mention} not found.")
    else:
        await interaction.response.send_message(f"Removed warn {id} from {member.mention}")


# List warns
@tree.command(
    name = "warns",
    description = "Lists a member's warns")
@app_commands.checks.has_permissions(mute_members=True)
async def warns(interaction: discord.Interaction, member: discord.Member):
    index = 0
    query = pd.read_sql_query(f"""SELECT * FROM Warns WHERE uid = {member.id} AND guild = {interaction.guild.id} ORDER BY timewarned DESC LIMIT 20""", con)
    embed = discord.Embed(title=f"Warns for {member.name} ({len(query.index)})\n", description="Range 1 - 10", color=discord.Color.blurple())
    if not query.empty:
        for ind in query.index:
            if(ind > 10):
                break
            embed.add_field(name="Date, ID", value=query['timewarned'][ind][0:10] + " ​ ​ ​ " + '{0: <10}'.format(query['id'][ind]), inline=True)
            embed.add_field(name="Mod responsible", value=await client.fetch_user(int(query['mid'][ind])), inline=True)
            embed.add_field(name="Reason", value='{0: <40}'\
                .format(('"' + query['reason'][ind][:34] + "..." if len(query['reason'][ind]) > 40 else '"' + query['reason'][ind]) + '"', inline=True))
        await interaction.response.send_message(embed = embed)
    else:
        await interaction.response.send_message("No warns found for this user.")


@tree.command(
    name = "updatemessagecount",
    description = "Updates message counts for users")
@app_commands.checks.has_permissions(administrator=True)
async def updatemessagecount(interaction: discord.Interaction, member: discord.Member, count: int):
    query = pd.read_sql_query(
        f"""SELECT id FROM Message_Counts WHERE guild = {interaction.guild.id} AND uid = {member.id}""", con)
    try:
        con.execute(f"""UPDATE Message_Counts 
                SET messagecount = {count}
                WHERE id = {query['id'][0]}""")
    except:
        print(f"adding user {member.id}")
        con.execute(
            f"""INSERT INTO Message_Counts (guild, uid, messagecount) VALUES ({interaction.guild.id}, {member.id}, {count})""")
    await interaction.response.send_message(f"Updated message count for {member.mention}")
    con.commit()

@tree.command(
    name = "votechannel",
    description = "Sets a channel to be a channel for voting in."
)
@app_commands.checks.has_permissions(mute_members=True)
@app_commands.describe(topchannel='Channel top votes are placed in')
async def votechannel(interaction: discord.Interaction, topchannel: discord.TextChannel):
    print(interaction.channel.id)
    con.execute(f"""
        INSERT OR IGNORE INTO Voting_Channels
        (guild, channel_id, top_channel)
        VALUES
        ({interaction.guild.id}, {interaction.channel.id}, {topchannel.id})
    """)
    con.execute(f"""
        INSERT OR IGNORE INTO Top_Vote_Channels
        (guild, channel_id)
        VALUES
        ({interaction.guild.id}, {topchannel.id})
        """)
    con.commit()
    await interaction.response.send_message("Voting channel created.")


@tree.command(
    name = "unvotechannel",
    description = "Removes a channel to be a channel for voting in."
)
@app_commands.checks.has_permissions(mute_members=True)
async def unvotechannel(interaction: discord.Interaction):
    con.execute(f"""DELETE FROM Voting_Channels 
        WHERE guild = {interaction.guild.id} AND 
        channel_id = {interaction.channel.id})""")
    con.commit()
    await interaction.response.send_message("Voting channel removed.")


# Give role
@tree.command(
    name = "give",
    description = "Give a member a role")
@app_commands.checks.has_permissions(mute_members=True)
@app_commands.describe(level='Role to give')
async def give(interaction: discord.Interaction, member: discord.Member, level: int):
    if level < 2 or level > 10:
        await interaction.response.send_message(":x: Role doesn't exist.")
        return
    roleid = ""
    for role in interaction.guild.roles:
        if role.name.startswith(rolesindex[level - 2]):
            roleid = role
    if roleid == "":
        await interaction.response.send_message(":x: Role doesn't exist.")
    else:
        await member.add_roles(roleid)
        await interaction.response.send_message("Done.")
        await roleChannel(interaction, f"{interaction.user.name} gave **\"{roleid.name}\"** to {member.mention}")


# Take role
@tree.command(
    name = "take",
    description = "Take a member's role")
@app_commands.checks.has_permissions(mute_members=True)
@app_commands.describe(level='Role to take')
async def take(interaction: discord.Interaction, member: discord.Member, level: int):
    if discord.utils.get(interaction.guild.roles, name="DO NOT PROMOTE") in member.roles:
        await interaction.response.send_message(":x: Member has \"DO NOT PROMOTE\".")
        return
    if level < 2 or level > 10:
        await interaction.response.send_message(":x: Role doesn't exist.")
        return
    roleid = ""
    for role in interaction.guild.roles:
        if role.name.startswith(rolesindex[level - 2]):
            roleid = role
    if roleid == "":
        await interaction.response.send_message(":x: Role doesn't exist.")
    else:
        await member.remove_roles(roleid)
        await interaction.response.send_message("Done.")
        await roleChannel(interaction, f"{interaction.user.name} took **\"{roleid.name}\"** from {member.mention}")


# DNP
@tree.command(
    name = "dnp",
    description = "Block member from promotions")
@app_commands.checks.has_permissions(mute_members=True)
async def dnp(interaction: discord.Interaction, member: discord.Member, reason: typing.Optional[str]):
    if (member.top_role >= interaction.user.top_role):
        await interaction.response.send_message("Cannot give dnp to a higher level user than you.")
    else:
        dnp = discord.utils.get(interaction.guild.roles, name="DO NOT PROMOTE")
        if dnp in member.roles:
            await member.remove_roles(dnp)
            await dnpChannel(interaction, f"{interaction.user.name} took **\"DO NOT PROMOTE\"** from {member.mention}{f' for the reason {reason}' if reason else ''}")
        else:
            await member.add_roles(dnp)
            await dnpChannel(interaction,
                             f"{interaction.user.name} gave **\"DO NOT PROMOTE\"** to {member.mention}{f' for the reason {reason}' if reason else ''}")
        await interaction.response.send_message("Done.")


@client.event
async def on_message(message: discord.Message):
    query = pd.read_sql_query(f"""SELECT id FROM Message_Counts WHERE guild = {message.guild.id} AND uid = {message.author.id}""", con)
    try:
        con.execute(f"""UPDATE Message_Counts 
            SET messagecount = messagecount + 1 
            WHERE id = {query['id'][0]}""")
    except:
        print(f"adding user {message.author.id}")
        con.execute(f"""INSERT INTO Message_Counts (guild, uid, messagecount) VALUES ({message.guild.id}, {message.author.id}, 1)""")
    con.commit()
    query = pd.read_sql_query(f"""SELECT * FROM Voting_Channels WHERE channel_id = {message.channel.id} AND guild = {message.guild.id}""", con)
    if not query.empty and (message.embeds or re.search("(?P<url>https?://[^\s]+)", message.content).group("url")):
        await message.add_reaction("👍")
        await message.add_reaction("👎")
    if message.content.startswith("!atime "):
        if message.guild.get_member(message.author.id).guild_permissions.mute_members:
            if message.reference is not None and not message.is_system():
                for reason in mutetimes.items():
                    reason_low = reason[0].lower()
                    if reason_low in message.content.lower():
                        await atime(message=message.reference.resolved, user=message.author, name=reason[0], value=reason[1])
                        return
    if message.content.startswith("!getmembers") and message.author.id == 841804705675739157:
        dump = open("dump.txt", "wt")
        for member in message.guild.members:
            dump.write(member.name + "\n")
        dump.close()
        dump = open("dump.txt", "rt")
        await message.channel.send(file=discord.File(fp="dump.txt", filename="dump.txt"))


async def atime(message: discord.Message, user:discord.Member, name: str, value: int):
    guild = message.guild
    auth = message.author.id
    auth = guild.get_member(auth)
    if (auth.top_role >= user.top_role):
        await message.channel.send(":x: Cannot timeout a member with higher rank than you.")
        return
    elif auth.is_timed_out():
        await message.channel.send(":x: Member is already timed out, another mod probably beat you to it!")
        return
    reason = ""
    if value == min_10:
        reason = "[10 mins] " + name
        await auth.timeout(datetime.timedelta(minutes=10), reason=reason)
    if value == hour:
        reason = "[1 hour] " + name
        await auth.timeout(datetime.timedelta(hours=1), reason=reason)
    if value == day:
        reason="[1 day] " + name
        await auth.timeout(datetime.timedelta(days=1), reason=reason)
    if value == week:
        reason = "[1 week] " + name
        await auth.timeout(datetime.timedelta(weeks=1), reason=reason)
    if value == ban:
        reason="[BAN] " + name
        await auth.timeout(datetime.timedelta(weeks=4), reason=reason)
    text = f"{user.name} muted user {auth.mention} for {reason}"
    await message.channel.send(text)
    await message.delete()
    command = f"""INSERT INTO Warns(guild, uid, mid, reason, timewarned) VALUES
            ({int(message.guild.id)}, {int(auth.id)}, {int(user.id)}, "{reason}", DATETIME('now'))"""
    print(command)
    con.execute(command)
    con.commit()
    for c in guild.text_channels:
        if c.name == "timeout-logs":
            await c.send(text)






@tree.command(
    name = "messages",
    description = "Gets a user's message count"
)
async def messagecount(interaction: discord.Interaction, member: discord.Member):
    try:
        query = pd.read_sql_query(f"""SELECT messagecount FROM Message_Counts WHERE guild = {interaction.guild.id} AND uid = {member.id}""", con)
        await interaction.response.send_message(f"User {member.mention} has sent {query['messagecount'][0]} messages.")
    except:
        await interaction.response.send_message(f":x: User {member.mention} has no messages.")


@tree.command(
    name = "lock",
    description = "Locks the channel you're in. Only use in raids."
)
@app_commands.checks.has_permissions(mute_members=True)
async def lock(interaction: discord.Interaction):
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
    await interaction.response.send_message("Channel locked.")


@tree.command(
    name = "unlock",
    description = "Unlocks the channel you're in."
)
@app_commands.checks.has_permissions(mute_members=True)
async def unlock(interaction: discord.Interaction):
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=True)
    await interaction.response.send_message("Channel unlocked.")


def check(message, member: discord.Member):
    return message.author.id == member.id

@tree.command(
    name="purge",
    description="Purges messages"
)
@app_commands.checks.has_permissions(mute_members=True)
async def purge(interaction: discord.Interaction, member: typing.Optional[discord.Member], count: int):
    # We will do this in groups of 100
    print(interaction.channel_id)
    countdown = count
    await interaction.response.send_message("Purging...")
    while(countdown > 100):
        if member:
            await interaction.channel.purge(limit=100, check=lambda message: message.author == member and not message.pinned)
        else:
            await interaction.channel.purge(limit=100, check=lambda message: not message.pinned)
        countdown -= 100
    else:
        if member:
            await interaction.channel.purge(limit=countdown, check=lambda message:message.author == member and not message.pinned)
        else:
            await interaction.channel.purge(limit=countdown, check=lambda message: not message.pinned)
    await interaction.channel.send(f"Purged {count} messages.")


@tree.command(
    name="beneral",
    description="Send a message as if you were Shapirone"
)
@app_commands.checks.has_permissions(mute_members=True)
async def beneral(interaction:discord.Interaction, text: str, channel: typing.Optional[discord.TextChannel]):
    await interaction.response.send_message(content="Sending message as Shapirone", ephemeral=True)
    if not channel:
        await interaction.channel.send(text)
    else:
        await channel.send(text)


async def auditChannel(interaction:discord.Interaction, text: str):
    guild = interaction.guild
    for c in guild.text_channels:
        if c.name == "timeout-logs":
            await c.send(text)


async def roleChannel(interaction:discord.Interaction, text: str):
    guild = interaction.guild
    for c in guild.text_channels:
        if c.name == "promotion-logs":
            await c.send(text)


async def dnpChannel(interaction:discord.Interaction, text: str):
    guild = interaction.guild
    for c in guild.text_channels:
        if c.name == "donotpromote-logs":
            await c.send(text)


# Start bot
client.run(open("secret.code").readline())



