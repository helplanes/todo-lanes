import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import os
import asyncio
from datetime import datetime, timedelta

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='.', intents=intents)

# Data structure to store tasks per channel
todo_lists = {}
completed_tasks = {}
last_reset = {}

def reset_channel_tasks(channel_id):
    todo_lists[channel_id] = []
    completed_tasks[channel_id] = set()
    last_reset[channel_id] = datetime.now()

@bot.event
async def on_ready():
    print(f'{bot.user} is online.')
    reset_tasks.start()

@tasks.loop(minutes=60)
async def reset_tasks():
    now = datetime.now()
    for channel_id in list(todo_lists.keys()):
        if (now - last_reset[channel_id]) >= timedelta(hours=24):
            reset_channel_tasks(channel_id)

@bot.command()
async def todo(ctx, *, arg):
    channel_id = ctx.channel.id
    if channel_id not in todo_lists:
        reset_channel_tasks(channel_id)

    if arg.strip().isdigit():
        index = int(arg.strip()) - 1
        if 0 <= index < len(todo_lists[channel_id]):
            completed_tasks[channel_id].add(index)
            await ctx.send(f"✅ Marked task {index+1} as complete: **{todo_lists[channel_id][index]}**")
        else:
            await ctx.send("Invalid task number.")
    else:
        new_tasks = [task.strip() for task in arg.split(",") if task.strip()]
        todo_lists[channel_id].extend(new_tasks)
        await ctx.send("📝 Added tasks!")
        await list(ctx)

@bot.command()
async def list(ctx):
    channel_id = ctx.channel.id
    if channel_id not in todo_lists or not todo_lists[channel_id]:
        await ctx.send("📭 No tasks for today. Use `.todo` to add some!")
        return

    msg = "**Today's To-Do List:**\n"
    for i, task in enumerate(todo_lists[channel_id]):
        status = "✅" if i in completed_tasks[channel_id] else "❌"
        msg += f"{i+1}. {status} {task}\n"
    await ctx.send(msg)

bot.run(TOKEN)
