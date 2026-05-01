import logging
import os
import subprocess
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, FSInputFile
from asyncio import run
import yt_dlp
import shutil



API_TOKEN = "8227650573:AAEKVFpakLCx_qeAXYIhvqfqoGmbykBomwY"
DOWNLOAD_MANZIL = 'downloads'
TEMP_MANZIL = 'temp'

logging.basicConfig(level=logging.INFO)

# Papkalarni yaratish
for folder in [DOWNLOAD_MANZIL, TEMP_MANZIL]:
    if not os.path.exists(folder):
        os.makedirs(folder)

async def convert_to_video_note(input_file: str, output_file: str) -> bool:
    """Videoni dumaloq (video note) formatiga o'tkazish (ovoz bilan)"""
    # OVOZ BILAN - an parametri olib tashlandi
    command = (
        f"ffmpeg -y -i {input_file} "
        f"-vf \"crop='min(iw,ih)':'min(iw,ih)',scale=360:360\" "
        f"-c:v libx264 -preset fast -crf 23 "
        f"-c:a aac -b:a 128k "  # Audio kodek qo'shildi
        f"{output_file}"
    )
    
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"FFmpeg xatoligi: {result.stderr}")
        return False
    
    return os.path.exists(output_file)

async def download_video(url: str, download_type: str = "video"):
    """YouTube yoki Instagram videolarini yuklab olish"""
    
    is_instagram = "instagram.com" in url or "instagr.am" in url
    is_youtube = "youtube.com" in url or "youtu.be" in url
    
    ydl_opts = {
        'outtmpl': os.path.join(DOWNLOAD_MANZIL, '%(title)s_%(id)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'no_check_certificate': True,
    }
    
    if is_instagram:
        ydl_opts.update({
            'extract_flat': False,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Sec-Fetch-Mode': 'navigate',
            }
        })
        
        if download_type == "audio":
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        else:
            ydl_opts.update({
                'format': 'best[ext=mp4]/best',
                'merge_output_format': 'mp4',
            })
    
    elif is_youtube:
        if download_type == "audio":
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        else:
            ydl_opts.update({
                'format': 'best[height<=720][ext=mp4]/best[ext=mp4]/best',
                'merge_output_format': 'mp4',
            })
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            if 'entries' in info:
                info = info['entries'][0]
            
            file_name = ydl.prepare_filename(info)
            
            if download_type == "audio":
                base_name = os.path.splitext(file_name)[0]
                file_name = base_name + '.mp3'
            
            if os.path.exists(file_name):
                return file_name, info.get('title', 'video'), None
            else:
                for ext in ['.mp4', '.webm', '.mkv']:
                    test_file = os.path.splitext(file_name)[0] + ext
                    if os.path.exists(test_file):
                        return test_file, info.get('title', 'video'), None
                
                return None, None, "Fayl yuklab olinmadi"
                
    except Exception as e:
        error_msg = str(e)
        if "Requested format is not available" in error_msg:
            try:
                ydl_opts_fallback = {
                    'outtmpl': os.path.join(DOWNLOAD_MANZIL, '%(title)s_%(id)s.%(ext)s'),
                    'quiet': True,
                    'no_warnings': True,
                    'format': 'best',
                }
                with yt_dlp.YoutubeDL(ydl_opts_fallback) as ydl:
                    info = ydl.extract_info(url, download=True)
                    if 'entries' in info:
                        info = info['entries'][0]
                    file_name = ydl.prepare_filename(info)
                    
                    if os.path.exists(file_name):
                        return file_name, info.get('title', 'video'), None
                    else:
                        return None, None, f"Yuklab olishning iloji bo'lmadi"
            except Exception as e2:
                return None, None, f"Xatolik: {str(e2)}"
        else:
            return None, None, f"Xatolik yuz berdi: {error_msg}"


bot = Bot(token=API_TOKEN)
dp = Dispatcher()


@dp.message(lambda message: message.text and (
    "youtube.com" in message.text or 
    "youtu.be" in message.text or 
    "instagram.com" in message.text or
    "instagr.am" in message.text
))
async def handle_link(message: Message):
    url = message.text.strip()
    
    status_msg = await message.answer("⏳ Video yuklab olinmoqda va tayyorlanmoqda...")
    
    file_path, title, error = await download_video(url, download_type="video")
    
    if error:
        await status_msg.edit_text(f"❌ {error}")
        return
    
    if not file_path or not os.path.exists(file_path):
        await status_msg.edit_text("❌ Yuklab olishda xatolik yuz berdi")
        return
    
    temp_input = os.path.join(TEMP_MANZIL, f"temp_input_{message.message_id}.mp4")
    temp_output = os.path.join(TEMP_MANZIL, f"temp_output_{message.message_id}.mp4")
    
    try:
        shutil.copy2(file_path, temp_input)
        
        await status_msg.edit_text("⏳ Video dumaloq formatga o'tkazilmoqda (ovoz bilan)...")
        
        if await convert_to_video_note(temp_input, temp_output):
            video_note_file = FSInputFile(temp_output)
            await bot.send_video_note(
                chat_id=message.chat.id,
                video_note=video_note_file
            )
            await status_msg.delete()
        else:
            video_file = FSInputFile(file_path)
            await bot.send_video(
                chat_id=message.chat.id,
                video=video_file,
                caption=f"🎬 *{title[:100]}*\n\n❌ Dumaloq formatga o'tkazib bo'lmadi",
                parse_mode="Markdown"
            )
            await status_msg.edit_text("⚠️ Video dumaloq formatga o'tkazilmadi, oddiy video sifatida yuborildi")
        
    except Exception as e:
        await status_msg.edit_text(f"❌ Xatolik: {str(e)[:200]}")
    
    finally:
        for f in [file_path, temp_input, temp_output]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass


@dp.message(F.video)
async def handle_video(message: types.Message):
    msg = await message.reply("⏳ Video dumaloq formatga o'tkazilmoqda (ovoz bilan)...")

    file = await bot.get_file(message.video.file_id)
    file_path = file.file_path

    input_file = os.path.join(TEMP_MANZIL, f"input_{message.message_id}.mp4")
    output_file = os.path.join(TEMP_MANZIL, f"output_{message.message_id}.mp4")

    await bot.download_file(file_path, input_file)

    # OVOZ BILAN - an parametri olib tashlandi
    command = (
        f"ffmpeg -y -i {input_file} "
        f"-vf \"crop='min(iw,ih)':'min(iw,ih)',scale=360:360\" "
        f"-c:v libx264 -preset fast -crf 23 "
        f"-c:a aac -b:a 128k "  # Audio qo'shildi
        f"{output_file}"
    )

    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        error_msg = f"❌ FFmpeg xatoligi:\n{result.stderr[-200:]}"
        await message.reply(error_msg)
        
        if os.path.exists(input_file):
            os.remove(input_file)
        await msg.delete()
        return

    if not os.path.exists(output_file):
        await message.reply("❌ Video qayta ishlashda xatolik yuz berdi")
        if os.path.exists(input_file):
            os.remove(input_file)
        await msg.delete()
        return

    try:
        video_note_file = FSInputFile(output_file)
        await bot.send_video_note(
            chat_id=message.chat.id,
            video_note=video_note_file
        )
        
    except Exception as e:
        await message.reply(f"❌ Xatolik: {e}")

    for f in [input_file, output_file]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except:
                pass

    await msg.delete()


async def main():
    try:
        subprocess.run(["pip", "install", "--upgrade", "yt-dlp"], capture_output=True)
    except:
        pass
    
    print("✅ Bot ishga tushdi!")
    print("📹 YouTube va Instagram havolalarini yuboring - ular dumaloq video (ovoz bilan) qaytariladi")
    print("🎬 Oddiy videolarni yuboring - ular ham dumaloq formatga (ovoz bilan) o'tkaziladi")
    
    await dp.start_polling(bot)


if __name__ == "__main__":
    run(main())