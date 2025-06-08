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

# Per-channel task tracking with timestamps
todo_lists = {}  # {channel_id: [task1, task2, ...]}
todo_timestamps = {}  # {channel_id: {task_index: created_timestamp}}
completed_tasks = {}  # {channel_id: set(indexes)}
completion_timestamps = {}  # {channel_id: {task_index: completed_timestamp}}

# Per-channel agenda tracking with timestamps
agenda_lists = {}  # {channel_id: [agenda_item1, agenda_item2, ...]}
agenda_timestamps = {}  # {channel_id: {item_index: created_timestamp}}
completed_agenda_items = {}  # {channel_id: set(indexes)}
agenda_completion_timestamps = {}  # {channel_id: {item_index: completed_timestamp}}


def reset_channel_tasks(channel_id):
    todo_lists[channel_id] = []
    todo_timestamps[channel_id] = {}
    completed_tasks[channel_id] = set()
    completion_timestamps[channel_id] = {}


def reset_channel_agenda(channel_id):
    agenda_lists[channel_id] = []
    agenda_timestamps[channel_id] = {}
    completed_agenda_items[channel_id] = set()
    agenda_completion_timestamps[channel_id] = {}


# Start message
@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user}')
    # Removed the auto-reset tasks


# Format time difference in a human-readable way
def format_time_taken(start_time, end_time):
    diff = end_time - start_time
    hours = diff.total_seconds() // 3600
    minutes = (diff.total_seconds() % 3600) // 60
    
    if hours > 0:
        return f"{int(hours)} hr {int(minutes)} min"
    else:
        return f"{int(minutes)} min"


# Command: .todo [tasks]
@bot.command()
async def todo(ctx, *, arg):
    channel_id = ctx.channel.id
    if channel_id not in todo_lists:
        reset_channel_tasks(channel_id)

    # Treat as task input
    new_tasks = [task.strip() for task in arg.split(",") if task.strip()]
    
    # Store timestamp for each new task
    now = datetime.now()
    for i in range(len(todo_lists[channel_id]), len(todo_lists[channel_id]) + len(new_tasks)):
        todo_timestamps[channel_id][i] = now
    
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
    
    # Store timestamp for each new agenda item
    now = datetime.now()
    for i in range(len(agenda_lists[channel_id]), len(agenda_lists[channel_id]) + len(new_items)):
        agenda_timestamps[channel_id][i] = now
        
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

    now = datetime.now()
    
    # Check if "all" is specified
    if arg.strip().lower() == "all":
        # Mark all tasks as completed
        newly_completed = [i for i in range(len(todo_lists[channel_id])) if i not in completed_tasks[channel_id]]
        completed_tasks[channel_id] = set(range(len(todo_lists[channel_id])))
        
        # Record completion timestamps for newly completed tasks
        for i in newly_completed:
            completion_timestamps[channel_id][i] = now
            
        await ctx.send("✅ All tasks marked as completed!")
        
        # Generate task summary
        summary = "**🕒 Task Completion Summary:**\n"
        total_time = timedelta(0)
        for i in range(len(todo_lists[channel_id])):
            if i in completion_timestamps[channel_id]:
                time_taken = format_time_taken(todo_timestamps[channel_id][i], completion_timestamps[channel_id][i])
                summary += f"{i+1}. ✅ {todo_lists[channel_id][i]} - {time_taken}\n"
                total_time += (completion_timestamps[channel_id][i] - todo_timestamps[channel_id][i])
        
        # Calculate average time
        if newly_completed:
            avg_seconds = total_time.total_seconds() / len(newly_completed)
            avg_hours = avg_seconds // 3600
            avg_minutes = (avg_seconds % 3600) // 60
            
            if avg_hours > 0:
                summary += f"\nAverage completion time: {int(avg_hours)} hr {int(avg_minutes)} min"
            else:
                summary += f"\nAverage completion time: {int(avg_minutes)} min"
                
        await ctx.send(summary)
        await show_list(ctx)
        return

    # Otherwise, try to mark a specific task as completed
    if arg.strip().isdigit():
        index = int(arg.strip()) - 1
        if 0 <= index < len(todo_lists[channel_id]):
            if index not in completed_tasks[channel_id]:
                completed_tasks[channel_id].add(index)
                completion_timestamps[channel_id][index] = now
                
                # Calculate time taken
                time_taken = format_time_taken(todo_timestamps[channel_id][index], now)
                await ctx.send(
                    f"✅ Task {index+1} marked complete: **{todo_lists[channel_id][index]}**\n"
                    f"⏱️ Time taken: {time_taken}"
                )
            else:
                await ctx.send("⚠️ Task already completed.")
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

    now = datetime.now()
    
    # Check if "all" is specified
    if arg.strip().lower() == "all":
        # Mark all agenda items as completed
        newly_completed = [i for i in range(len(agenda_lists[channel_id])) if i not in completed_agenda_items[channel_id]]
        completed_agenda_items[channel_id] = set(range(len(agenda_lists[channel_id])))
        
        # Record completion timestamps for newly completed items
        for i in newly_completed:
            agenda_completion_timestamps[channel_id][i] = now
            
        await ctx.send("✅ All agenda items marked as completed!")
        
        # Skip the summary and only show the detailed agenda list
        # This removes the duplicate information
        await show_agenda(ctx)
        return

    # Otherwise, try to mark a specific agenda item as completed
    if arg.strip().isdigit():
        index = int(arg.strip()) - 1
        if 0 <= index < len(agenda_lists[channel_id]):
            if index not in completed_agenda_items[channel_id]:
                completed_agenda_items[channel_id].add(index)
                agenda_completion_timestamps[channel_id][index] = now
                
                # Calculate time taken
                time_taken = format_time_taken(agenda_timestamps[channel_id][index], now)
                await ctx.send(
                    f"✅ Agenda item {index+1} marked complete: **{agenda_lists[channel_id][index]}**\n"
                    f"⏱️ Time taken: {time_taken}"
                )
            else:
                await ctx.send("⚠️ Item already completed.")
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
        await ctx.send("📭 No tasks yet. Add some using `.todo`!")
        return

    msg = "**🗒️ To-Do List:**\n"
    for i, task in enumerate(todo_lists[channel_id]):
        status = "✅" if i in completed_tasks.get(channel_id, set()) else "🔲"
        time_added = todo_timestamps[channel_id][i].strftime("%m/%d %H:%M")
        
        if i in completed_tasks.get(channel_id, set()) and i in completion_timestamps.get(channel_id, {}):
            time_completed = completion_timestamps[channel_id][i].strftime("%m/%d %H:%M")
            time_taken = format_time_taken(todo_timestamps[channel_id][i], completion_timestamps[channel_id][i])
            msg += f"{i+1}. {status} {task} (Added: {time_added}, Completed: {time_completed}, Took: {time_taken})\n"
        else:
            msg += f"{i+1}. {status} {task} (Added: {time_added})\n"
            
    await ctx.send(msg)


# Command: .alist
@bot.command(name='alist')
async def show_agenda(ctx):
    channel_id = ctx.channel.id
    if channel_id not in agenda_lists or not agenda_lists[channel_id]:
        await ctx.send("📭 No agenda items yet. Add some using `.agenda`!")
        return

    msg = "**📋 Meeting Agenda:**\n"
    for i, item in enumerate(agenda_lists[channel_id]):
        status = "✅" if i in completed_agenda_items.get(channel_id, set()) else "🔲"
        time_added = agenda_timestamps[channel_id][i].strftime("%m/%d %H:%M")
        
        if i in completed_agenda_items.get(channel_id, set()) and i in agenda_completion_timestamps.get(channel_id, {}):
            time_completed = agenda_completion_timestamps[channel_id][i].strftime("%m/%d %H:%M")
            time_taken = format_time_taken(agenda_timestamps[channel_id][i], agenda_completion_timestamps[channel_id][i])
            msg += f"{i+1}. {status} {item} (Added: {time_added}, Completed: {time_completed}, Took: {time_taken})\n"
        else:
            msg += f"{i+1}. {status} {item} (Added: {time_added})\n"
            
    await ctx.send(msg)


# Custom help command
@bot.command()
async def help(ctx):
    help_embed = discord.Embed(
        title="📋 Todo Lanes - Task & Agenda Manager",
        description=
        "A simple manager for your Discord channel tasks and meeting agendas with time tracking.",
        color=0x3498db)

    help_embed.add_field(name="📝 Task Management",
                         value="`.todo [tasks]` - Add new tasks (comma-separated)\n"
                         "`.list` - Display all your current tasks\n"
                         "`.done [number]` - Mark a specific task as completed\n"
                         "`.done all` - Mark all tasks as completed with summary",
                         inline=False)

    help_embed.add_field(name="📋 Agenda Management",
                         value="`.agenda [items]` - Add meeting agenda items (comma-separated)\n"
                         "`.alist` - Display all current agenda items\n"
                         "`.adone [number]` - Mark a specific agenda item as completed\n"
                         "`.adone all` - Mark all agenda items as completed with summary",
                         inline=False)

    help_embed.add_field(name="🧹 Clearing Data",
                         value="`.clear tasks` - Remove completed tasks, keep incomplete ones\n"
                         "`.clear agenda` - Remove completed agenda items, keep incomplete ones\n"
                         "`.clear all` - Clear all tasks and agenda items completely",
                         inline=False)

    help_embed.add_field(name="⏱️ Time Tracking",
                         value="Tasks and agenda items now track:\n"
                         "- When they were created\n"
                         "- When they were completed\n"
                         "- How long they took to complete",
                         inline=False)

    help_embed.add_field(name="Examples",
                        value="`.todo Buy milk, Call mom, Fix bug`\n"
                        "`.agenda Project status update, Budget review, New hiring plans`",
                        inline=False)

    await ctx.send(embed=help_embed)


# Command: .clear [type]
@bot.command()
async def clear(ctx, arg=None):
    channel_id = ctx.channel.id
    
    if arg and arg.lower() == "tasks":
        # Clear completed tasks only
        if channel_id in todo_lists:
            # Get only incomplete tasks
            incomplete_tasks = [task for i, task in enumerate(todo_lists[channel_id]) 
                               if i not in completed_tasks[channel_id]]
            
            # Get timestamps for incomplete tasks
            incomplete_timestamps = {}
            for new_idx, old_idx in enumerate([i for i in range(len(todo_lists[channel_id])) 
                                              if i not in completed_tasks[channel_id]]):
                if old_idx in todo_timestamps.get(channel_id, {}):
                    incomplete_timestamps[new_idx] = todo_timestamps[channel_id][old_idx]
            
            # Reset the data structures
            reset_channel_tasks(channel_id)
            
            # Add back only incomplete tasks with their original timestamps
            todo_lists[channel_id] = incomplete_tasks
            todo_timestamps[channel_id] = incomplete_timestamps
                
            await ctx.send("🧹 Cleared all completed tasks!")
            await show_list(ctx)
            
    elif arg and arg.lower() == "agenda":
        # Clear completed agenda items only
        if channel_id in agenda_lists:
            # Get only incomplete agenda items
            incomplete_items = [item for i, item in enumerate(agenda_lists[channel_id]) 
                               if i not in completed_agenda_items[channel_id]]
            
            # Get timestamps for incomplete items
            incomplete_timestamps = {}
            for new_idx, old_idx in enumerate([i for i in range(len(agenda_lists[channel_id])) 
                                              if i not in completed_agenda_items[channel_id]]):
                if old_idx in agenda_timestamps.get(channel_id, {}):
                    incomplete_timestamps[new_idx] = agenda_timestamps[channel_id][old_idx]
            
            # Reset the data structures
            reset_channel_agenda(channel_id)
            
            # Add back only incomplete items with their original timestamps
            agenda_lists[channel_id] = incomplete_items
            agenda_timestamps[channel_id] = incomplete_timestamps
                
            await ctx.send("🧹 Cleared all completed agenda items!")
            await show_agenda(ctx)
            
    elif arg and arg.lower() == "all":
        # Reset everything for this channel
        reset_channel_tasks(channel_id)
        reset_channel_agenda(channel_id)
        await ctx.send("🧹 Cleared all tasks and agenda items for this channel!")
        
    else:
        # Show help if no valid argument was provided
        await ctx.send("Please specify what to clear: `.clear tasks`, `.clear agenda`, or `.clear all`")

app = Flask('')


@app.route('/')
def home():
    return "Bot is alive!"


def run():
    app.run(host='0.0.0.0', port=8080)


Thread(target=run).start()

bot.run(TOKEN)