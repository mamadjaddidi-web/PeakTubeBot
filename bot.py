
# PeakTubeBot - نسخه نهایی با ویدیو + زیرنویس چسبیده (HardSub)
import os
import asyncio
import logging
from datetime import timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import yt_dlp

# رفع مشکل ویندوز
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

TOKEN = "8462120028:AAGLjkcu3n0jj0Gi8BIfYwmPwplxWKqGN6o"
logging.basicConfig(level=logging.INFO)

if not os.path.exists("downloads"):
    os.makedirs("downloads")

# تبدیل عدد به K/M/B
def format_number(num):
    if num is None: return "نامشخص"
    if num >= 1_000_000_000: return f"{round(num / 1_000_000_000, 1)}B"
    elif num >= 1_000_000: return f"{round(num / 1_000_000, 1)}M"
    elif num >= 1_000: return f"{round(num / 1000, 1)}K"
    return str(num)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("کانال Peak", url="https://t.me/YourChannel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome = """
PeakTubeBot - بهترین دانلودر یوتیوب با زیرنویس چسبیده

سلام! به حرفه‌ای‌ترین ربات دانلود خوش اومدی

قابلیت‌ها:
• ویدیو با زیرنویس فارسی/انگلیسی چسبیده
• ویدیو بدون زیرنویس (1080p)
• فقط صدا (MP3 320kbps)

فقط لینک رو بفرست و لذت ببر

@PeakTubeBot - قلهٔ دانلود با زیرنویس
    """
    await update.message.reply_text(welcome, reply_markup=reply_markup, disable_web_page_preview=True)

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    user_id = update.effective_user.id

    if not any(x in url for x in ["youtube.com", "youtu.be", "y2u.be"]):
        await update.message.reply_text("لطفاً فقط لینک یوتیوب بفرستید!")
        return

    context.user_data['url'] = url
    context.user_data['user_id'] = user_id

    msg = await update.message.reply_text("در حال بررسی ویدیو و زیرنویس‌ها...")

    try:
        ydl_opts = {'quiet': True, 'skip_download': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            title = (info.get('title') or 'بدون عنوان')[:70]
            duration = info.get('duration', 0)
            duration_str = "نامشخص"
            if duration:
                td = timedelta(seconds=duration)
                duration_str = str(td)[2:] if td < timedelta(hours=1) else str(td)

            # چک کردن زیرنویس
            manual = info.get('subtitles', {})
            auto = info.get('automatic_captions', {})
            all_subs = {**manual, **auto}

            buttons = []

            # اولویت: فارسی → انگلیسی → بقیه
            if 'fa' in all_subs:
                buttons.append([InlineKeyboardButton("ویدیو + زیرنویس فارسی", callback_data="hardsub_fa")])
            if 'en' in all_subs:
                buttons.append([InlineKeyboardButton("ویدیو + زیرنویس انگلیسی", callback_data="hardsub_en")])

            # همیشه اینا باشن
            buttons.extend([
                [InlineKeyboardButton("ویدیو بدون زیرنویس (1080p)", callback_data="video")],
                [InlineKeyboardButton("فقط صدا (MP3 320kbps)", callback_data="audio")],
                [InlineKeyboardButton("لغو", callback_data="cancel")]
            ])

            reply_markup = InlineKeyboardMarkup(buttons)

            await msg.edit_text(
                f"**{title}**\n\n"
                f"مدت زمان: `{duration_str}`\n\n"
                f"لطفاً انتخاب کنید:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    except:
        await msg.edit_text("خطا در بررسی لینک. دوباره امتحان کنید.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    choice = query.data
    url = context.user_data.get('url')
    user_id = context.user_data.get('user_id')

    if not url:
        await query.edit_message_text("لینک منقضی شده.")
        return

    if choice == "cancel":
        await query.edit_message_text("لغو شد")
        return

    msg = await query.edit_message_text("در حال پردازش... لطفاً صبر کنید")

    if choice == "video":
        await download_video(url, user_id, msg, query.message, subtitle_lang=None)
    elif choice == "audio":
        await download_audio(url, user_id, msg, query.message)
    elif choice.startswith("hardsub_"):
        lang = choice.split("_", 1)[1]
        await download_video(url, user_id, msg, query.message, subtitle_lang=lang)

# دانلود ویدیو (با یا بدون زیرنویس چسبیده)
async def download_video(url, user_id, msg, message, subtitle_lang=None):
    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title') or 'ویدیو'
            uploader = info.get('uploader') or 'نامشخص'

        # تنظیمات دانلود
        opts = {
            'format': 'best[height<=1080]/best',
            'outtmpl': f'downloads/{user_id}_%(id)s.%(ext)s',
            'merge_output_format': 'mp4',
            'noplaylist': True,
        }

        # اگر زیرنویس خواست → هاردساب کن
        if subtitle_lang:
            await msg.edit_text(f"در حال دانلود ویدیو + زیرنویس {subtitle_lang.upper()}...")
            opts.update({
                'writessubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': [subtitle_lang],
                'subtitlesformat': 'srt',
                'embed_subs': True,  # این خط معجزه می‌کنه! زیرنویس رو تو ویدیو میچسبونه
            })
        else:
            await msg.edit_text(f"در حال دانلود ویدیو بدون زیرنویس...")

        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

        file_path = ydl.prepare_filename(info)
        if not os.path.exists(file_path):
            file_path = file_path.replace('.webm', '.mp4').replace('.mkv', '.mp4')

        file_size_mb = round(os.path.getsize(file_path) / (1024*1024), 2)
        quality = f"{info.get('height', 1080)}p"
        sub_text = f" + زیرنویس {subtitle_lang.upper()}" if subtitle_lang else ""

        caption = f"""
**{title}**

کانال: {uploader}
کیفیت: {quality}{sub_text}
حجم: {file_size_mb} مگابایت

@PeakTubeBot - قلهٔ دانلود با زیرنویس چسبیده
        """.strip()

        await msg.edit_text("در حال آپلود ویدیو...")
        with open(file_path, 'rb') as video:
            await message.reply_video(
                video=video,
                caption=caption,
                parse_mode='Markdown',
                supports_streaming=True
            )
        await msg.delete()
        os.remove(file_path)

    except Exception as e:
        await msg.edit_text(f"خطا در دانلود: {str(e)[:100]}")

# دانلود صدا
async def download_audio(url, user_id, msg, message):
    try:
        await msg.edit_text("در حال استخراج صدا...")
        opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'downloads/{user_id}_%(id)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title') or 'موزیک'
            ydl.download([url])

        base = ydl.prepare_filename(info).rsplit('.', 1)[0]
        file_path = base + '.mp3'
        file_size_mb = round(os.path.getsize(file_path) / (1024*1024), 2)

        caption = f"""
**{title}**

فرمت: MP3 320kbps
حجم: {file_size_mb} مگابایت

@PeakTubeBot
        """.strip()

        await msg.edit_text("در حال آپلود صدا...")
        with open(file_path, 'rb') as audio:
            await message.reply_audio(audio=audio, caption=caption, parse_mode='Markdown', title=title)
        await msg.delete()
        os.remove(file_path)

    except Exception as e:
        await msg.edit_text(f"خطا در دانلود صدا: {str(e)[:100]}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex(r"https?://(www\.)?(youtube\.com|youtu\.be|y2u\.be)"), handle_link))
    app.add_handler(CallbackQueryHandler(button_callback))
    print("PeakTubeBot با زیرنویس چسبیده (HardSub) فعال شد!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()