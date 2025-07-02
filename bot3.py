import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import yt_dlp
import asyncio

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1309646863292432464
song_queues = {}  # Key: guild.id, Value: list of (audio_url, title)


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix = '!', intents = intents)

async def search_ytdlp_async(query, ydl_opts):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: _extract(query, ydl_opts))


def _extract(query, ydl_opts):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(query, download = False)


@bot.event
async def on_ready():
    print(f'{bot.user} is online!')


@bot.event
async def on_message(msg):
    if msg.guild.id:
        print(msg.guild.id)
        await bot.process_commands(msg)


@bot.command()
async def play(ctx, *args): 
    if len(args) < 1:
        await ctx.send('Type a song name to query after !play')

    song_query = ' '.join(args)
    print(f'Received command to play: {song_query}')

    voice_channel = ctx.author.voice.channel 
    voice_client = ctx.guild.voice_client
    guild_id = ctx.guild.id

    if not voice_client:
        voice_client = await voice_channel.connect()
    elif voice_channel != voice_client.channel:
        await voice_client.move_to(voice_channel)

    ydl_options = {
        #'format': 'bestaudio[abr<=96]/bestaudio',
        'format': 'bestaudio[ext=webm][acodec=opus]/bestaudio',
        'noplaylist': True,
    }

    query = 'ytsearch1: ' + song_query
    results = await search_ytdlp_async(query, ydl_options)
    tracks = results.get('entries', [])

    if not tracks:
        await ctx.send('No results found')
        return
    
    first_track = tracks[0]
    audio_url = first_track['url']
    title = first_track.get('title', 'Untitled')

	# Iniitialize queue if needed
    if guild_id not in song_queues:
	    song_queues[guild_id] = []
	
	# Add song to queue
    song_queues[guild_id].append((audio_url, title))
    await ctx.send(f'Queued: {title}')
	
    # Start playback if not already playing
    if not voice_client.is_playing():
        await play_next_in_queue(ctx.guild, voice_client)


async def play_next_in_queue(guild, voice_client):
    queue = song_queues.get(guild.id)
    if not queue or len(queue) == 0:
        await voice_client.disconnect()
        return

    audio_url, title = queue.pop(0)
    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }
    source = discord.FFmpegOpusAudio(audio_url, **ffmpeg_options, executable='/usr/bin/ffmpeg')

    def after_playing(error):
        fut = asyncio.run_coroutine_threadsafe(
            play_next_in_queue(guild, voice_client),
            bot.loop
        )
        try:
            fut.result()
        except Exception as e:
            print(f"Error in playback: {e}")

    voice_client.play(source, after=after_playing)
    voice_client.current_title = title

    channel = discord.utils.get(guild.text_channels, name="general")  # Or wherever you want to send now playing
    if channel:
        await channel.send(f"Now playing: {title}")

    
@bot.command()
async def stop(ctx):
    await ctx.guild.voice_client.disconnect()


@bot.command()
async def queue(ctx):
    queue = song_queues.get(ctx.guild.id, [])
    voice_client = ctx.guild.voice_client

    if not queue and not (voice_client and voice_client.is_playing()):
        await ctx.send("The queue is empty.")
        return

    lines = []

    # Show current playing
    if voice_client and voice_client.is_playing():
        current_track = getattr(voice_client, "current_title", None)
        if current_track:
            lines.append(f"🟢 **Playing:** `{current_track}`")

    # Show rest of queue
    for i, (_, title) in enumerate(queue):
        lines.append(f"{i + 1}. {title}")

    await ctx.send("\n".join(lines))


@bot.command()
async def skip(ctx):
    vc = ctx.guild.voice_client
    if vc and vc.is_playing():
        vc.stop()
        await ctx.send("Skipped current track.")


@bot.command()
async def h(ctx):
    msg = '**!play** Play a song or add it to the queue\n'
    msg += '**!queue** Show the list of songs that are queued to play\n'
    msg += '**!stop** Disconnect the bot\n'
    msg += '**!skip** Skip the current track\n'
    await ctx.send(f"🟢 **Commands:** 🟢\n{msg}")


def run():
    bot.run(TOKEN)
