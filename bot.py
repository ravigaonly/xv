import os
import subprocess
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from flask import Flask
from threading import Thread

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Get the bot token from environment variable

app = Flask(__name__)

# Heartbeat route to keep the instance alive
@app.route('/')
def home():
    return 'Bot is running!'

def run_flask():
    app.run(host='0.0.0.0', port=5000)

def clear_download_directory(directory):
    if os.path.exists(directory):
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                os.rmdir(file_path)

async def download_media(tweet_url, chat_id, context):
    try:
        output_dir = f"downloads/{chat_id}/media"
        clear_download_directory(output_dir)
        os.makedirs(output_dir, exist_ok=True)

        cookies_content = os.getenv("TWITTER_COOKIES")
        if not cookies_content:
            raise Exception("Cookies not found in environment variable.")
        
        cookies_path = "/tmp/cookies.txt"
        with open(cookies_path, "w") as f:
            f.write(cookies_content)
        
        command = ["gallery-dl", "--cookies", cookies_path, "--directory", output_dir, tweet_url]
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if result.returncode != 0:
            raise Exception(f"gallery-dl failed: {result.stderr.decode('utf-8')}")
        
        for file in os.listdir(output_dir):
            file_path = os.path.join(output_dir, file)
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                with open(file_path, "rb") as f:
                    await context.bot.send_photo(chat_id=chat_id, photo=f)
            elif file.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
                with open(file_path, "rb") as f:
                    await context.bot.send_video(chat_id=chat_id, video=f)
            os.remove(file_path)

    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"Error downloading media: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text

    if "twitter.com" in text or "x.com" in text:
        if "/status/" in text:
            await context.bot.send_message(chat_id=chat_id, text="Downloading media...")
            await download_media(text, chat_id, context)
        else:
            await context.bot.send_message(chat_id=chat_id, text="Please send a valid Twitter status link.")
    else:
        await context.bot.send_message(chat_id=chat_id, text="Send me a Twitter link with media.")

def main():
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN environment variable not set.")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start Flask app in a separate thread
    thread = Thread(target=run_flask)
    thread.daemon = True
    thread.start()

    # Run the bot
    application.run_polling()

if __name__ == "__main__":
    main()
