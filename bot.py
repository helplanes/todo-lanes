import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import os
import asyncio
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread

# Load token from Replit Secrets (not .env)
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='.', intents=intents)

# Task storage
todo_lists = {}
completed_tasks = {}
last_reset = {}

# Reset function
def reset_channel_tasks(channel_id):
    todo_lists[channel_id] = []
    completed_tasks[channel_id] = set()
    last_reset[channel_id] = datetime.now()

# Bot is ready
@bot.event
async def on_ready():
    print(f'{bot.user} is online.')
    reset_tasks.start()

# Every hour, check for 24-hour expiry
@tasks.loop(minutes=60)
async def reset_tasks():
    now = datetime.now()
    for channel_id in list(todo_lists.keys()):
        if now - last_reset[channel_id] >= timedelta(hours=24):
            reset_channel_tasks(channel_id)

# Add tasks
@bot.command()
async def todo(ctx, *, arg):
    channel_id = ctx.channel.id
    if channel_id not in todo_lists:
        reset_channel_tasks(channel_id)

    if arg.isdigit():
        index = int(arg) - 1
        if 0 <= index < len(todo_lists[channel_id]):
            completed_tasks[channel_id].add(index)
            await ctx.send(f"✅ Task {index+1} marked as completed.")
        else:
            await ctx.send("⚠️ Invalid task number.")
        return

    new_tasks = [task.strip() for task in arg.split(",")]
    todo_lists[channel_id].extend(new_tasks)
    await ctx.send("📝 Tasks added.")
    await list_tasks(ctx)

# List current tasks
@bot.command()
async def list(ctx):
    await list_tasks(ctx)

async def list_tasks(ctx):
    channel_id = ctx.channel.id
    if channel_id not in todo_lists or not todo_lists[channel_id]:
        await ctx.send("🎉 No tasks for today!")
        return

    msg = "**📋 To-Do List:**\n"
    for i, task in enumerate(todo_lists[channel_id]):
        if i in completed_tasks[channel_id]:
            msg += f"~~{i+1}. {task}~~ ✅\n"
        else:
            msg += f"{i+1}. {task}\n"
    await ctx.send(msg)

# Keep-alive Flask web server
app = Flask('')

@app.route('/')
def home():
    return "✅ Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run).start()

# Run the bot
bot.run(TOKEN)
