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

    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }

    source = discord.FFmpegOpusAudio(audio_url, **ffmpeg_options, executable = '/usr/bin/ffmpeg')

    if voice_client.is_playing():
        voice_client.stop()

    voice_client.play(source)
    await ctx.send(f'Now playing: {title}')

    
@bot.command()
async def stop(ctx):
    await ctx.guild.voice_client.disconnect()
bot.run(TOKEN)


