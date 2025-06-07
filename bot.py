import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask

# Load token from .env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Set up bot with message content intent
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='.', intents=intents,
                   help_command=None)  # Disable default help

# Per-channel task tracking
todo_lists = {}  # {channel_id: [task1, task2, ...]}
completed_tasks = {}  # {channel_id: set(indexes)}
last_reset = {}  # {channel_id: datetime}

# Per-channel agenda tracking
agenda_lists = {}  # {channel_id: [agenda_item1, agenda_item2, ...]}
completed_agenda_items = {}  # {channel_id: set(indexes)}
agenda_last_reset = {}  # {channel_id: datetime}


def reset_channel_tasks(channel_id):
    todo_lists[channel_id] = []
    completed_tasks[channel_id] = set()
    last_reset[channel_id] = datetime.now()


def reset_channel_agenda(channel_id):
    agenda_lists[channel_id] = []
    completed_agenda_items[channel_id] = set()
    agenda_last_reset[channel_id] = datetime.now()


# Start message
@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user}')
    reset_tasks.start()
    reset_agendas.start()


# Task: auto-reset tasks every 24 hours
@tasks.loop(minutes=60)
async def reset_tasks():
    now = datetime.now()
    for channel_id in list(todo_lists.keys()):
        if (now - last_reset[channel_id]) >= timedelta(hours=24):
            reset_channel_tasks(channel_id)
            print(f'🕓 Auto-reset tasks for channel: {channel_id}')


# Task: auto-reset agendas every 24 hours
@tasks.loop(minutes=60)
async def reset_agendas():
    now = datetime.now()
    for channel_id in list(agenda_lists.keys()):
        if (now - agenda_last_reset.get(channel_id, datetime.min)) >= timedelta(hours=24):
            reset_channel_agenda(channel_id)
            print(f'🕓 Auto-reset agenda for channel: {channel_id}')


# Command: .todo [tasks]
@bot.command()
async def todo(ctx, *, arg):
    channel_id = ctx.channel.id
    if channel_id not in todo_lists:
        reset_channel_tasks(channel_id)

    # Treat as task input
    new_tasks = [task.strip() for task in arg.split(",") if task.strip()]
    todo_lists[channel_id].extend(new_tasks)
    await ctx.send("📝 Added tasks!")
    await show_list(ctx)


# Command: .agenda [items]
@bot.command()
async def agenda(ctx, *, arg):
    channel_id = ctx.channel.id
    if channel_id not in agenda_lists:
        reset_channel_agenda(channel_id)

    # Add agenda items
    new_items = [item.strip() for item in arg.split(",") if item.strip()]
    agenda_lists[channel_id].extend(new_items)
    await ctx.send("📝 Added agenda items!")
    await show_agenda(ctx)


# Command: .done [task number or "all"]
@bot.command()
async def done(ctx, *, arg):
    channel_id = ctx.channel.id
    if channel_id not in todo_lists or not todo_lists[channel_id]:
        await ctx.send("📭 No tasks to mark as completed.")
        return

    # Check if "all" is specified
    if arg.strip().lower() == "all":
        # Mark all tasks as completed
        completed_tasks[channel_id] = set(range(len(todo_lists[channel_id])))
        await ctx.send("✅ All tasks marked as completed!")
        await show_list(ctx)
        return

    # Otherwise, try to mark a specific task as completed
    if arg.strip().isdigit():
        index = int(arg.strip()) - 1
        if 0 <= index < len(todo_lists[channel_id]):
            completed_tasks[channel_id].add(index)
            await ctx.send(
                f"✅ Task {index+1} marked complete: **{todo_lists[channel_id][index]}**"
            )
        else:
            await ctx.send("⚠️ Invalid task number.")
    else:
        await ctx.send("⚠️ Please specify a task number or 'all'.")

    await show_list(ctx)


# Command: .adone [agenda item number or "all"]
@bot.command()
async def adone(ctx, *, arg):
    channel_id = ctx.channel.id
    if channel_id not in agenda_lists or not agenda_lists[channel_id]:
        await ctx.send("📭 No agenda items to mark as completed.")
        return

    # Check if "all" is specified
    if arg.strip().lower() == "all":
        # Mark all agenda items as completed
        completed_agenda_items[channel_id] = set(range(len(agenda_lists[channel_id])))
        await ctx.send("✅ All agenda items marked as completed!")
        await show_agenda(ctx)
        return

    # Otherwise, try to mark a specific agenda item as completed
    if arg.strip().isdigit():
        index = int(arg.strip()) - 1
        if 0 <= index < len(agenda_lists[channel_id]):
            completed_agenda_items[channel_id].add(index)
            await ctx.send(
                f"✅ Agenda item {index+1} marked complete: **{agenda_lists[channel_id][index]}**"
            )
        else:
            await ctx.send("⚠️ Invalid agenda item number.")
    else:
        await ctx.send("⚠️ Please specify an agenda item number or 'all'.")

    await show_agenda(ctx)


# Command: .list
@bot.command(name='list')
async def show_list(ctx):
    channel_id = ctx.channel.id
    if channel_id not in todo_lists or not todo_lists[channel_id]:
        await ctx.send("📭 No tasks for today. Add some using `.todo`!")
        return

    msg = "**🗒️ Today's To-Do List:**\n"
    for i, task in enumerate(todo_lists[channel_id]):
        status = "✅" if i in completed_tasks.get(channel_id, set()) else "🔲"
        msg += f"{i+1}. {status} {task}\n"
    await ctx.send(msg)


# Command: .alist
@bot.command(name='alist')
async def show_agenda(ctx):
    channel_id = ctx.channel.id
    if channel_id not in agenda_lists or not agenda_lists[channel_id]:
        await ctx.send("📭 No agenda items for today. Add some using `.agenda`!")
        return

    msg = "**📋 Today's Meeting Agenda:**\n"
    for i, item in enumerate(agenda_lists[channel_id]):
        status = "✅" if i in completed_agenda_items.get(channel_id, set()) else "🔲"
        msg += f"{i+1}. {status} {item}\n"
    await ctx.send(msg)


# Custom help command
@bot.command()
async def help(ctx):
    help_embed = discord.Embed(
        title="📋 Todo Lanes - Task & Agenda Manager",
        description=
        "A simple manager for your Discord channel tasks and meeting agendas. Everything auto-resets every 24 hours.",
        color=0x3498db)

    help_embed.add_field(name="📝 Task Management",
                         value="`.todo [tasks]` - Add new tasks (comma-separated)\n"
                         "`.list` - Display all your current tasks\n"
                         "`.done [number]` - Mark a specific task as completed\n"
                         "`.done all` - Mark all tasks as completed",
                         inline=False)

    help_embed.add_field(name="📋 Agenda Management",
                         value="`.agenda [items]` - Add meeting agenda items (comma-separated)\n"
                         "`.alist` - Display all current agenda items\n"
                         "`.adone [number]` - Mark a specific agenda item as completed\n"
                         "`.adone all` - Mark all agenda items as completed",
                         inline=False)

    help_embed.add_field(name="Examples",
                        value="`.todo Buy milk, Call mom, Fix bug`\n"
                        "`.agenda Project status update, Budget review, New hiring plans`",
                        inline=False)

    await ctx.send(embed=help_embed)


app = Flask('')


@app.route('/')
def home():
    return "Bot is alive!"


def run():
    app.run(host='0.0.0.0', port=8080)


Thread(target=run).start()

bot.run(TOKEN)