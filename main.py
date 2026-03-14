import os, re, asyncio
from telethon import TelegramClient, events
from quart import Quart, Response, request
import yt_dlp

# Environment Variables
api_id = int(os.environ.get("API_ID"))
api_hash = os.environ.get("API_HASH")
bot_token = os.environ.get("BOT_TOKEN")
base_url = os.environ.get("BASE_URL")

app = Quart(__name__)
bot = TelegramClient('bot_session', api_id, api_hash)

# --- UNIVERSAL DOWNLOADER (No Format Errors) ---
def download_video(url):
    ydl_opts = {
        # 'b' ka matlab hai sabse basic video format uthao bina nakhre kiye
        'format': 'b/best', 
        'outtmpl': 'video.mp4',
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
    }
    
    # Agar aapne cookies.txt upload ki hogi, toh ye use karega
    if os.path.exists('cookies.txt'):
        ydl_opts['cookiefile'] = 'cookies.txt'
        
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.extract_info(url, download=True)
        return 'video.mp4'

@bot.on(events.NewMessage(incoming=True))
async def handler(event):
    if event.raw_text.startswith('http') or event.video or event.document:
        status_msg = await event.reply("⚙️ **Har Quality Support Active...**\nVideo process ho rahi hai, thoda wait karein!")
        
        try:
            if event.raw_text.startswith('http'):
                loop = asyncio.get_event_loop()
                file_path = await loop.run_in_executor(None, download_video, event.raw_text)
                
                # Check agar file download hui ya nahi
                if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                    raise Exception("Facebook ne block kiya hai. Cookies ki zaroorat pad sakti hai.")

                sent = await bot.send_file(event.chat_id, file_path, caption="✅ **Video Downloaded!**")
                msg_id = sent.id
                if os.path.exists(file_path): os.remove(file_path)
            else:
                msg_id = event.message.id

            # 1. Direct Streaming Link
            s_link = f"{base_url}/stream/{event.chat_id}/{msg_id}"
            
            # 2. Blogger HTML Code
            b_code = f"&lt;video width='100%' controls poster=''&gt;&lt;source src='{s_link}' type='video/mp4'&gt;&lt;/video&gt;"
            
            final_text = (
                f"✅ **Dono Links Taiyar Hain!**\n\n"
                f"🔗 **Streaming Link (Direct URL):**\n`{s_link}`\n\n"
                f"📝 **Blogger HTML Code:**\n`{b_code}`\n\n"
                f"💡 *Tip: HTML code ko Blogger ke HTML View mein paste karein.*"
            )
            await status_msg.edit(final_text)

        except Exception as e:
            await status_msg.edit(f"❌ **Error:**\n`{str(e)}` \n\n*Solution: Agar video private hai toh cookies.txt upload karein.*")

# --- MASTER STREAMING CONTROLLER ---
@app.route('/stream/<int:chat_id>/<int:msg_id>')
async def stream(chat_id, msg_id):
    try:
        message = await bot.get_messages(chat_id, ids=msg_id)
        file_size = message.file.size
        range_header = request.headers.get('Range', None)
        start, end = 0, file_size - 1

        if range_header:
            match = re.search(r'bytes=(\d+)-(\d*)', range_header)
            if match:
                start = int(match.group(1))
                if match.group(2): end = int(match.group(2))

        chunk_size = end - start + 1
        headers = {
            'Content-Type': 'video/mp4',
            'Accept-Ranges': 'bytes',
            'Content-Length': str(chunk_size),
            'Content-Range': f'bytes {start}-{end}/{file_size}',
        }

        async def generate():
            async for chunk in bot.iter_download(message.media, offset=start, limit=chunk_size, chunk_size=1024*1024):
                yield chunk
        return Response(generate(), status=206, headers=headers)
    except Exception as e: return str(e), 500

@app.route('/')
async def health(): return "✅ Bot is Online!"

async def main():
    await bot.start(bot_token=bot_token)
    port = int(os.environ.get("PORT", 8080))
    asyncio.create_task(app.run_task(host="0.0.0.0", port=port))
    await bot.run_until_disconnected()

if __name__ == '__main__': asyncio.run(main())
