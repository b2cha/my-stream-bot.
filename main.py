import os, re, asyncio
from telethon import TelegramClient, events
from quart import Quart, Response, request
import yt_dlp

api_id = int(os.environ.get("API_ID"))
api_hash = os.environ.get("API_HASH")
bot_token = os.environ.get("BOT_TOKEN")
base_url = os.environ.get("BASE_URL")

app = Quart(__name__)
bot = TelegramClient('bot_session', api_id, api_hash)

def download_video(url):
    ydl_opts = {
        'format': 'best[height<=480]', # Fast download ke liye
        'outtmpl': 'video.mp4',
        'quiet': True,
    }
    if os.path.exists('cookies.txt'): ydl_opts['cookiefile'] = 'cookies.txt'
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.extract_info(url, download=True)
        return 'video.mp4'

@bot.on(events.NewMessage(incoming=True))
async def handler(event):
    if "facebook.com" in event.raw_text or "fb.watch" in event.raw_text:
        msg = await event.reply("🚀 Processing... Please wait!")
        try:
            loop = asyncio.get_event_loop()
            file_path = await loop.run_in_executor(None, download_video, event.raw_text)
            sent = await bot.send_file(event.chat_id, file_path)
            if os.path.exists(file_path): os.remove(file_path)
            
            # Sahi link format
            s_link = f"{base_url}/stream/{event.chat_id}/{sent.id}"
            await msg.edit(f"✅ **Done!**\n\n🔗 Link: `{s_link}`")
        except Exception as e:
            await event.reply(f"❌ Error: {str(e)}")

@app.route('/stream/<int:chat_id>/<int:msg_id>')
async def stream(chat_id, msg_id):
    try:
        message = await bot.get_messages(chat_id, ids=msg_id)
        file_size = message.file.size
        
        # Simple Range handling
        range_header = request.headers.get('Range', None)
        start = 0
        if range_header:
            match = re.search(r'bytes=(\d+)-', range_header)
            if match:
                start = int(match.group(1))

        headers = {
            'Content-Type': 'video/mp4',
            'Accept-Ranges': 'bytes',
            'Content-Length': str(file_size - start),
            'Content-Range': f'bytes {start}-{file_size-1}/{file_size}',
        }

        async def generate():
            # Chunk size badha kar 2MB kar diya taaki video na ruke
            async for chunk in bot.iter_download(message.media, offset=start, chunk_size=2*1024*1024):
                yield chunk

        return Response(generate(), status=206, headers=headers)
    except Exception as e:
        return str(e), 500

async def main():
    await bot.start(bot_token=bot_token)
    await app.run_task(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

if __name__ == '__main__':
    asyncio.run(main())
