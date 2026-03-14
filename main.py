import os
import asyncio
from telethon import TelegramClient, events
from quart import Quart, Response
import yt_dlp

# Render se Environment Variables uthana
api_id = int(os.environ.get("API_ID"))
api_hash = os.environ.get("API_HASH")
bot_token = os.environ.get("BOT_TOKEN")
base_url = os.environ.get("BASE_URL")

app = Quart(__name__)
bot = TelegramClient('bot_session', api_id, api_hash)

# --- PRIVATE & CUSTOM VIDEO DOWNLOADER ---
def download_social_video(url):
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', # Best Quality
        'outtmpl': 'downloaded_video.mp4',
        'quiet': True,
        'noplaylist': True,
    }
    
    # Agar cookies.txt file GitHub par hai, toh bot use private video ke liye use karega
    if os.path.exists('cookies.txt'):
        ydl_opts['cookiefile'] = 'cookies.txt'
        
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.extract_info(url, download=True)
        return 'downloaded_video.mp4'

@bot.on(events.NewMessage(incoming=True))
async def handler(event):
    msg_text = event.raw_text
    
    if "youtube.com" in msg_text or "youtu.be" in msg_text or "facebook.com" in msg_text or "fb.watch" in msg_text:
        await event.reply("📥 Downloading high-quality/private video... thoda wait karo bhai!")
        try:
            loop = asyncio.get_event_loop()
            video_file = await loop.run_in_executor(None, download_social_video, msg_text)
            
            sent_msg = await bot.send_file(event.chat_id, video_file, caption="✅ Download Done!")
            direct_link = f"{base_url}/stream/{sent_msg.id}"
            await event.reply(f"🔗 **Streaming Link:**\n{direct_link}")
            
            if os.path.exists(video_file): os.remove(video_file)
        except Exception as e:
            await event.reply(f"❌ Error: {str(e)}\n\n(Agar private video hai toh shayad cookies expire ho gayi hain)")

    elif event.video or event.document:
        msg_id = event.message.id
        direct_link = f"{base_url}/stream/{msg_id}"
        await event.reply(f"✅ **File Link Ready:**\n{direct_link}")

@app.route('/')
async def index():
    return "✅ SUCCESS! Render Par Server Ekdum Sahi Chal Raha Hai."

@app.route('/stream/<int:msg_id>')
async def stream_video(msg_id):
    headers = {'Content-Type': 'video/mp4', 'Accept-Ranges': 'bytes'}
    async def generate():
        async for chunk in bot.iter_download(msg_id, chunk_size=1024*1024):
            yield chunk
    return Response(generate(), headers=headers)

async def main():
    await bot.start(bot_token=bot_token)
    print("🚀 Bot Started!")
    
    port = int(os.environ.get("PORT", 8080))
    loop = asyncio.get_event_loop()
    loop.create_task(app.run_task(host="0.0.0.0", port=port))
    print(f"🌐 Web Server is LIVE on port {port}!")
    
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
