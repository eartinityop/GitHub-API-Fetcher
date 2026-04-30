import os, requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# ========== CONFIGURE THESE ==========
REPO = "eartinityop/compress"       # e.g. "johndoe/video-compressor"
WF_FILE = "compress.yml"               # workflow file name
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
# =====================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "I am Eartinity's personal video compressor bot👋👋.\nSend me a video to get started."
    )

async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Store original message_id and user_id (the user's private chat ID)
    context.user_data["msg_id"] = update.message.message_id
    context.user_data["user_id"] = update.message.chat_id   # e.g., 123456789 (positive number)

    keyboard = [
        [InlineKeyboardButton("Compress this video ✅", callback_data="compress")],
        [InlineKeyboardButton("Cancel the process ❌", callback_data="cancel")]
    ]
    await update.message.reply_text(
        "Video received. What would you like to do?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "cancel":
        await query.edit_message_text("❌ Process cancelled.")
        return

    if data == "compress":
        keyboard = [
            [InlineKeyboardButton("240p", callback_data="quality_240"),
             InlineKeyboardButton("360p", callback_data="quality_360")],
            [InlineKeyboardButton("480p", callback_data="quality_480"),
             InlineKeyboardButton("720p", callback_data="quality_720")],
            [InlineKeyboardButton("1080p", callback_data="quality_1080")],
            [InlineKeyboardButton("Cancel ❌", callback_data="cancel_q")]
        ]
        await query.edit_message_text(
            "Select the desired quality:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data.startswith("quality_"):
        quality = data.split("_")[1]
        msg_id = context.user_data.get("msg_id")
        user_id = context.user_data.get("user_id")

        if not msg_id or not user_id:
            await query.edit_message_text("Error: Missing video info.")
            return

        # Progress message
        sent_msg = await query.message.reply_text("⏳ Triggering workflow...")
        progress_msg_id = sent_msg.message_id

        # GitHub trigger
        url = f"https://api.github.com/repos/{REPO}/actions/workflows/{WF_FILE}/dispatches"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json"
        }
        payload = {
            "ref": "main",
            "inputs": {
                "original_message_id": str(msg_id),
                "user_id": str(user_id),
                "quality": quality,
                "message_id": str(progress_msg_id)
            }
        }
        resp = requests.post(url, json=payload, headers=headers)
        if resp.status_code != 204:
            await sent_msg.edit_text(f"❌ Workflow trigger failed: {resp.status_code} {resp.text}")

    elif data == "cancel_q":
        await query.edit_message_text("❌ Compression cancelled.")

def main():
    app = Application.builder().token(os.environ["TELEGRAM_BOT_TOKEN"]).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO, video_handler))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
