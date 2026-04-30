import os, requests, asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading


# ----- CONFIGURE THESE -----
REPO = "eartinityop/compress"                # e.g., "mohitkumar/video-compressor"
WF_FILE = "compress.yml"             # workflow file name inside .github/workflows/
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
# ---------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "I am Eartinity's personal video compressor bot👋👋.\nSend me a video to get started."
    )

async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video = update.message.video
    context.user_data["file_id"] = video.file_id
    context.user_data["chat_id"] = update.message.chat_id

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
        # Show quality options
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
        file_id = context.user_data.get("file_id")
        chat_id = context.user_data.get("chat_id")

        if not file_id or not chat_id:
            await query.edit_message_text("Error: Missing video info.")
            return

        # Send a new message that will be updated by the workflow
        sent_msg = await query.message.reply_text("⏳ Triggering workflow...")
        message_id = sent_msg.message_id

        # Trigger GitHub Actions
        url = f"https://api.github.com/repos/{REPO}/actions/workflows/{WF_FILE}/dispatches"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json"
        }
        payload = {
            "ref": "main",    # or your default branch
            "inputs": {
                "file_id": file_id,
                "chat_id": str(chat_id),
                "quality": quality,
                "message_id": str(message_id)
            }
        }
        resp = requests.post(url, json=payload, headers=headers)

        if resp.status_code == 204:
            # The workflow will now edit this message with progress
            pass
        else:
            await sent_msg.edit_text(f"❌ Workflow trigger failed: {resp.status_code} {resp.text}")

    elif data == "cancel_q":
        await query.edit_message_text("❌ Compression cancelled.")

def main():
    app = Application.builder().token(os.environ["TELEGRAM_BOT_TOKEN"]).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO, video_handler))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def start_health_server():
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

if __name__ == "__main__":
    start_health_server()
    main()
