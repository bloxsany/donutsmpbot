import discord
from discord import app_commands
import json
import asyncio
import time
import io

CONFIG_FILE = 'config.json'
with open(CONFIG_FILE) as f:
    config = json.load(f)

TOKEN = config['token']
FARMS = config['farms']
BOT_OWNER_ID = 1244689320946831394  # Replace with your Discord ID

ROLE_IDS = {
    "giveaway": 1398070710211182602,
    "botupdate": 1398070660844228669,
    "video": 1398070755698413698,
    "announcement": 1398070616694853842,
    "quickdrop": 1399107782216646757
}

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

ping_cooldowns = {}

@bot.event
async def on_ready():
    await tree.sync()
    activity = discord.Activity(type=discord.ActivityType.watching, name="itz6b basement discord.gg/GD7uY9mub2 🎁")
    await bot.change_presence(status=discord.Status.online, activity=activity)
    print(f"✅ Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.content.strip().lower() == "!calculator":
        await handle_calculation_flow(message.channel, message.author)

async def handle_calculation_flow(channel, author):
    categories = list(FARMS.keys()) + ["bones"]
    category_list = "Choose a category by number:\n"
    for i, cat in enumerate(categories, start=1):
        label = f"{cat} farms" if cat != "bones" else "Bones per Min/hour"
        category_list += f"{i}: {label}\n"
    await channel.send(category_list)

    def check(m):
        return m.author == author and m.channel == channel

    try:
        cat_msg = await bot.wait_for('message', timeout=30.0, check=check)
        cat_index = int(cat_msg.content.strip()) - 1
        if not (0 <= cat_index < len(categories)):
            raise ValueError()
        selected_cat = categories[cat_index]

        if selected_cat == "bones":
            await channel.send("🦴 How many Skeleton spawners do you have?")
            spawner_msg = await bot.wait_for('message', timeout=30.0, check=check)
            spawners = int(spawner_msg.content.strip())
            bones_per_min = spawners * 2
            await channel.send(f"🦴 You will make **{bones_per_min:,} bones/minute**. Do you want to calculate per hour? (yes/no)")
            confirm_msg = await bot.wait_for('message', timeout=30.0, check=check)
            if confirm_msg.content.strip().lower() in ["yes", "y"]:
                bones_per_hour = bones_per_min * 60
                await channel.send(f"🕒 You will make **{bones_per_hour:,} bones/hour**.")
            return

        farms = FARMS[selected_cat]
        farm_list = f"Choose a farm from '{selected_cat}' category:\n"
        for fid, farm in farms.items():
            farm_list += f"{fid}: {farm['name']} (${farm['income']}M/hr)\n"
        await channel.send(farm_list)

        farm_msg = await bot.wait_for('message', timeout=30.0, check=check)
        farm_choice = farm_msg.content.strip()
        if farm_choice not in farms:
            return await channel.send("❌ Invalid farm ID.")

        await channel.send("How many modules do you have?")
        modules_msg = await bot.wait_for('message', timeout=30.0, check=check)
        modules = float(modules_msg.content.strip())

        await channel.send("What is your sell multiplier? (1.0 to 3.0)")
        multiplier_msg = await bot.wait_for('message', timeout=30.0, check=check)
        multiplier = float(multiplier_msg.content.strip())

        income = farms[farm_choice]['income']
        total = modules * income * multiplier
        if total >= 1:
            income_str = f"${total:.2f}M/hour"
        else:
            income_str = f"${int(total * 1000):,}K/hour"
        await channel.send(f"💰 Your farm will make **{income_str}**.")

    except (asyncio.TimeoutError, ValueError):
        await channel.send("❌ Invalid input or timeout.")

@tree.command(name="calculate", description="Calculate farm income interactively")
async def calculate(interaction: discord.Interaction):
    await interaction.response.send_message("Starting calculator in DMs!", ephemeral=True)
    await handle_calculation_flow(await interaction.user.create_dm(), interaction.user)

@tree.command(name="addfarm", description="Add a new farm")
@app_commands.describe(category="Farm category", fid="Farm ID", name="Farm name", income="Income per hour (millions)")
async def addfarm(interaction: discord.Interaction, category: str, fid: str, name: str, income: float):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You must be an admin to use this command.", ephemeral=True)
        return

    if category not in FARMS:
        FARMS[category] = {}
    FARMS[category][fid] = {"name": name, "income": income}
    with open(CONFIG_FILE, 'w') as f:
        config['farms'] = FARMS
        json.dump(config, f, indent=2)
    await interaction.response.send_message(f"✅ Added farm '{name}' to category '{category}' with ID '{fid}'.")

@tree.command(name="listfarms", description="List all farms by category")
async def listfarms(interaction: discord.Interaction):
    msg = "**Farms:**\n"
    for cat, farms in FARMS.items():
        msg += f"\n__{cat}__:\n"
        for fid, farm in farms.items():
            msg += f"{fid}: {farm['name']} (${farm['income']}M/hr)\n"
    await interaction.response.send_message(msg)

@tree.command(name="ping", description="Ping a specific role")
@app_commands.describe(type="Which type of ping?")
@app_commands.choices(type=[
    app_commands.Choice(name="Giveaway ping", value="giveaway"),
    app_commands.Choice(name="Bot update ping", value="botupdate"),
    app_commands.Choice(name="Video ping", value="video"),
    app_commands.Choice(name="Announcements ping", value="announcement"),
    app_commands.Choice(name="Quickdrop ping", value="quickdrop"),
])
async def ping(interaction: discord.Interaction, type: app_commands.Choice[str]):
    perms = interaction.channel.permissions_for(interaction.user)
    if not perms.mention_everyone:
        await interaction.response.send_message("❌ You need `Mention Everyone` permission in this channel.", ephemeral=True)
        return

    now = time.time()
    user_id = interaction.user.id
    last_used = ping_cooldowns.get(user_id, 0)
    if now - last_used < 60:
        remaining = int(60 - (now - last_used))
        await interaction.response.send_message(f"⏳ You must wait {remaining}s before using this command again.", ephemeral=True)
        return
    ping_cooldowns[user_id] = now

    role_id = ROLE_IDS.get(type.value)
    if not role_id:
        await interaction.response.send_message("❌ Role not found.", ephemeral=True)
        return

    mention = f"<@&{role_id}>"
    await interaction.response.send_message(f"🔔 {mention}")

@tree.command(name="message", description="Send a message to a channel (Admin only)")
@app_commands.describe(
    channel="Channel to send the message to",
    message="The message you want to send",
    file="Optional file to include"
)
async def message(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    message: str,
    file: discord.Attachment = None
):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You must be an admin to use this command.", ephemeral=True)
        return

    files = []
    if file:
        data = await file.read()
        files.append(discord.File(io.BytesIO(data), filename=file.filename))

    await channel.send(message, files=files)
    await interaction.response.send_message("✅ Message sent.", ephemeral=True)

@tree.command(name="help", description="Show all available commands and their descriptions")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📘 Bot Help Menu",
        description="Here's a list of all commands you can use:",
        color=discord.Color.green()
    )

    embed.add_field(
        name="🧮 Calculation",
        value="`!calculator` – Start calculator in channel\n`/calculate` – Start calculator in DMs",
        inline=False
    )
    embed.add_field(
        name="📊 Farm Management (Admin only)",
        value="`/addfarm` – Add a farm to a category\n`/listfarms` – Show all farms by category",
        inline=False
    )
    embed.add_field(
        name="🔔 Role Pings",
        value="`/ping` – Ping roles like Giveaway, Update, etc.",
        inline=False
    )
    embed.add_field(
        name="📨 Message Sender (Admin only)",
        value="`/message` – Send a message and optional file to a channel",
        inline=False
    )
    embed.add_field(
        name="🆘 Help",
        value="`/help` – Show this help menu",
        inline=False
    )

    embed.set_footer(text="Farm Bot by You ❤️")
    await interaction.response.send_message(embed=embed, ephemeral=True)

import psutil
import platform
from datetime import timedelta

start_time = time.time()  # Put this at the top with your imports

@tree.command(name="raminfo", description="Shows system RAM and CPU usage (Admin only)")
async def raminfo(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You must be an admin to use this command.", ephemeral=True)
        return

    # Get system info
    cpu_percent = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    ram_used = mem.used // (1024 ** 2)
    ram_total = mem.total // (1024 ** 2)
    ram_percent = mem.percent
    uptime_seconds = int(time.time() - start_time)
    uptime = str(timedelta(seconds=uptime_seconds))

    # Create the embed
    embed = discord.Embed(title="📊 System Resource Info", color=discord.Color.purple())
    embed.add_field(name="🧠 CPU Usage", value=f"{cpu_percent}%", inline=True)
    embed.add_field(name="💾 RAM Usage", value=f"{ram_used}MB / {ram_total}MB ({ram_percent}%)", inline=True)
    embed.add_field(name="⏱️ Uptime", value=uptime, inline=False)
    embed.set_footer(text=platform.system() + " " + platform.release())

    await interaction.response.send_message(embed=embed, ephemeral=True)


bot.run(TOKEN)
