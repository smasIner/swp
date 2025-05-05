import os
import logging
import uuid
import requests
import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from typing import Dict, List

from telegram.request import HTTPXRequest

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Backend API configuration
API_BASE_URL = "http://localhost:8000"  # Update with your FastAPI server URL
AUDIO_STORAGE_PATH = "static/audiorecordings"

# User states to track voice message context
user_states: Dict[int, Dict] = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Hello, {user.first_name}!\n\n"
        "Welcome to the Document Processing Bot! 📚\n"
        "I help you upload and manage texts and audio recordings.\n\n"
        "Use these commands:\n"
        "📤 /upload - Upload a PDF/TXT file or send text\n"
        "📜 /list - Browse available texts\n"
        "📊 /status - Check processing status"
    )

async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /upload command."""
    await update.message.reply_text(
        "📤 Please upload a PDF file, or send the text directly."
    )

async def list_texts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /list command."""
    await fetch_and_display_texts(update, context, page=1)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command."""
    # Placeholder for background task count (not implemented in backend)
    await update.message.reply_text(
        "📊 Status: No ongoing audio processing tasks.\n"
        "All tasks run in the background."
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle document uploads (PDF/TXT)."""
    document = update.message.document
    user_id = str(update.effective_user.id)
    supported_mime_types = ["application/pdf", "text/plain"]

    if document.mime_type not in supported_mime_types:
        await update.message.reply_text(
            "❌ Unsupported file type. Please upload a PDF or TXT file."
        )
        return

    msg = await update.message.reply_text("⏳ Processing your file...")
    try:
        file = await document.get_file()
        file_data = await file.download_as_bytearray()

        files = {"file": (document.file_name, file_data, document.mime_type)}
        data = {"user_identifier": user_id}
        response = requests.post(f"{API_BASE_URL}/documents", files=files, data=data)

        if response.status_code == 200:
            doc_id = response.json()["document_id"]
            await msg.edit_text(
                f"✅ File uploaded successfully!\n"
                f"Title: {document.file_name}\n"
                f"Document ID: {doc_id}"
            )
        else:
            await msg.edit_text(f"❌ Failed to upload file: {response.json()['detail']}")
    except Exception as e:
        await msg.edit_text(f"❌ Failed to upload file. Please try again.\nError: {str(e)}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle plain text input."""
    if update.message.text.startswith("/"):
        return  # Ignore commands

    user_id = str(update.effective_user.id)
    text_content = update.message.text
    msg = await update.message.reply_text("⏳ Processing your text...")

    try:
        data = {"text_content": text_content, "user_identifier": user_id}
        response = requests.post(f"{API_BASE_URL}/documents", data=data)

        if response.status_code == 200:
            doc_id = response.json()["document_id"]
            await msg.edit_text(
                f"✅ Text uploaded successfully!\nDocument ID: {doc_id}"
            )
        else:
            await msg.edit_text(f"❌ Failed to upload text: {response.json()['detail']}")
    except Exception as e:
        await msg.edit_text(f"❌ Failed to upload text. Please try again.\nError: {str(e)}")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle voice messages."""
    user_id = update.effective_user.id
    state = user_states.get(user_id, {})

    if not state.get("expecting_voice") or not state.get("document_id"):
        await update.message.reply_text(
            "❌ Please select a text and use the '➕ Add New Recording' button first."
        )
        return

    document_id = state["document_id"]
    msg = await update.message.reply_text("⏳ Downloading...")

    try:
        voice = await update.message.voice.get_file()
        voice_data = await voice.download_as_bytearray()

        await msg.edit_text("⏳ Processing...")
        files = {"audio_file": (f"voice_{uuid.uuid4().hex}.wav", voice_data, "audio/wav")}
        data = {"uploader_id": str(user_id)}
        response = requests.post(
            f"{API_BASE_URL}/recordings/{document_id}", files=files, data=data
        )

        if response.status_code == 200:
            result = response.json()
            await msg.edit_text(
                f"✅ Recording processed successfully!\n"
                f"Document ID: {result['document_id']}\n"
                f"Recording ID: {result['recording_id']}"
            )
        else:
            await msg.edit_text(
                f"❌ Failed to process recording: {response.json()['detail']}"
            )
    except Exception as e:
        await msg.edit_text(
            f"❌ Failed to process recording. Please try again.\nError: {str(e)}"
        )
    finally:
        # Clear state
        if user_id in user_states:
            del user_states[user_id]

async def fetch_and_display_texts(
    update: Update, context: ContextTypes.DEFAULT_TYPE, page: int
) -> None:
    """Fetch and display paginated text list."""
    user_id = str(update.effective_user.id)
    msg = await update.effective_message.reply_text("⏳ Loading texts...")

    try:
        params = {
            "page_number": page,
            "items_per_page": 5,
            "user_identifier": user_id,
            "user_only": False,
        }
        response = requests.get(f"{API_BASE_URL}/documents", params=params)

        if response.status_code != 200:
            await msg.edit_text(f"❌ Failed to fetch texts: {response.json()['detail']}")
            return

        data = response.json()
        documents = data["documents"]
        total_pages = (data["total_documents"] + 4) // 5  # Ceiling division

        if not documents:
            await msg.edit_text(
                "📭 No texts available yet. Use /upload to add one!"
            )
            return

        keyboard = []
        for doc in documents:
            preview = (
                doc["text_content"][:30] + "..." if len(doc["text_content"]) > 30 else doc["text_content"]
            )
            recordings_count = len(doc.get("audio_recordings", {}))
            button_text = (
                f"📖 {preview} ({recordings_count} recording{'s' if recordings_count != 1 else ''})"
            )
            # Shortened callback to 'td'
            callback_data = f"td:{doc['document_id']}:{page}:1"
            if len(callback_data.encode('utf-8')) > 64:
                logger.warning(f"Callback data too long: {callback_data}")
                await msg.edit_text("❌ Error: Unable to display texts due to internal issue.")
                return
            keyboard.append(
                [
                    InlineKeyboardButton(
                        button_text,
                        callback_data=callback_data,
                    )
                ]
            )

        # Pagination buttons
        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"lt:{page-1}"))
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"lt:{page+1}"))
        if nav_buttons:
            keyboard.append(nav_buttons)

        reply_markup = InlineKeyboardMarkup(keyboard)
        await msg.edit_text("📜 Available Texts:", reply_markup=reply_markup)

    except Exception as e:
        await msg.edit_text(f"❌ Failed to fetch texts. Please try again.\nError: {str(e)}")

async def text_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display text detail view."""
    query = update.callback_query
    try:
        # Split callback data and validate
        data_parts = query.data.split(":")
        if len(data_parts) != 4:
            raise ValueError("Invalid callback data format")
        _, document_id, list_page, recordings_page = data_parts
        list_page, recordings_page = int(list_page), int(recordings_page)
    except ValueError as e:
        await query.message.edit_text(f"❌ Invalid button data. Please try again.\nError: {str(e)}")
        await query.answer()
        return

    try:
        response = requests.get(f"{API_BASE_URL}/documents/{document_id}")
        if response.status_code != 200:
            await query.message.edit_text(f"❌ Text not found: {response.json()['detail']}")
            return

        doc = response.json()
        preview = (
            doc["text_content"][:200] + "..." if len(doc["text_content"]) > 200 else doc["text_content"]
        )
        recordings = list(doc.get("audio_recordings", {}).items())
        total_recording_pages = (len(recordings) + 4) // 5  # Ceiling division

        text = (
            f"📝 Text Details\n\n"
            f"Uploader ID: {doc['user_id']}\n"
            f"Recordings: {len(recordings)} (Page {recordings_page}/{max(1, total_recording_pages)})\n"
            f"Preview: {preview}"
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    "📥 Download Text",
                    callback_data=f"dt:{document_id}",
                )
            ]
        ]

        # Add recording buttons (paginated)
        start_idx = (recordings_page - 1) * 5
        end_idx = start_idx + 5
        for idx, (rec_id, rec) in enumerate(recordings[start_idx:end_idx], start=start_idx + 1):
            callback_data = f"rd:{document_id}:{rec_id}:{list_page}:{recordings_page}"
            if len(callback_data.encode('utf-8')) > 64:
                logger.warning(f"Callback data too long for recording: {callback_data}")
                continue  # Skip this button to avoid errors
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"🎧 Recording {idx} by {rec['uploader_id']}",
                        callback_data=callback_data,
                    )
                ]
            )

        # Recording pagination buttons
        nav_buttons = []
        if recordings_page > 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    "⬅️ Prev",
                    callback_data=f"td:{document_id}:{list_page}:{recordings_page-1}",
                )
            )
        if recordings_page < total_recording_pages:
            nav_buttons.append(
                InlineKeyboardButton(
                    "Next ➡️",
                    callback_data=f"td:{document_id}:{list_page}:{recordings_page+1}",
                )
            )
        if nav_buttons:
            keyboard.append(nav_buttons)

        # Add new recording and back buttons
        keyboard.extend([
            [
                InlineKeyboardButton(
                    "➕ Add New Recording",
                    callback_data=f"ar:{document_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "🔙 Back to Texts",
                    callback_data=f"lt:{list_page}",
                )
            ],
        ])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(text, reply_markup=reply_markup)

    except Exception as e:
        await query.message.edit_text(f"❌ Failed to fetch text details.\nError: {str(e)}")

    await query.answer()

async def recording_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display recording detail view."""
    query = update.callback_query
    try:
        _, document_id, recording_id, list_page, recordings_page = query.data.split(":")
    except ValueError as e:
        await query.message.edit_text(f"❌ Invalid button data. Please try again.\nError: {str(e)}")
        await query.answer()
        return

    try:
        response = requests.get(f"{API_BASE_URL}/recordings/{document_id}/{recording_id}")
        if response.status_code != 200:
            await query.message.edit_text(f"❌ Recording not found: {response.json()['detail']}")
            return

        rec = response.json()
        preview = (
            rec["transcribed_text"][:150] + "..." if len(rec["transcribed_text"]) > 150 else rec["transcribed_text"]
        )
        match_status = "✅ Good" if rec["content_match"] else "❌ Poor"

        text = (
            f"🎤 Recording Details\n\n"
            f"Uploader ID: {rec['uploader_id']}\n"
            f"Semantic Match: {match_status}\n"
            f"Segments: {len(rec['word_timings'])}\n"
            f"Preview: {preview}"
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    "🔙 Back to Text",
                    callback_data=f"td:{document_id}:{list_page}:{recordings_page}",
                )
            ],
            [
                InlineKeyboardButton(
                    "🎤 Open in Mini App",
                    web_app={"url": f"#ngrok here#/static/telegram_miniapp.html?document_id={document_id}&recording_id={recording_id}"},
                )
            ],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(text, reply_markup=reply_markup)

    except Exception as e:
        await query.message.edit_text(f"❌ Failed to fetch recording details.\nError: {str(e)}")

    await query.answer()

async def add_recording(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Prepare to receive a voice message for a specific document."""
    query = update.callback_query
    try:
        _, document_id = query.data.split(":")
    except ValueError as e:
        await query.message.edit_text(f"❌ Invalid button data. Please try again.\nError: {str(e)}")
        await query.answer()
        return

    user_id = update.effective_user.id
    user_states[user_id] = {"expecting_voice": True, "document_id": document_id}
    await query.answer("Please send a voice message to add a new recording.")

async def download_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text download."""
    query = update.callback_query
    try:
        _, document_id = query.data.split(":")
    except ValueError as e:
        await query.message.edit_text(f"❌ Invalid button data. Please try again.\nError: {str(e)}")
        await query.answer()
        return

    try:
        response = requests.get(f"{API_BASE_URL}/documents/{document_id}")
        if response.status_code != 200:
            await query.message.edit_text(f"❌ Text not found: {response.json()['detail']}")
            return

        doc = response.json()
        text_content = doc["text_content"]
        file_name = f"text_{document_id}.txt"

        # Save text to a temporary file
        temp_file = f"/tmp/{file_name}"
        with open(temp_file, "w") as f:
            f.write(text_content)

        await query.message.reply_document(
            document=open(temp_file, "rb"),
            filename=file_name,
        )
        os.remove(temp_file)

    except Exception as e:
        await query.message.edit_text(f"❌ Failed to download text.\nError: {str(e)}")

    await query.answer()

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all button callbacks."""
    query = update.callback_query
    data = query.data

    if data.startswith("lt:"):
        page = int(data.split(":")[1])
        await fetch_and_display_texts(update, context, page)
    elif data.startswith("td:"):
        await text_detail(update, context)
    elif data.startswith("rd:"):
        await recording_detail(update, context)
    elif data.startswith("ar:"):
        await add_recording(update, context)
    elif data.startswith("dt:"):
        await download_text(update, context)

    await query.answer()

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors and log them."""
    logger.error(f"Update {update} caused error: {context.error}")
    if isinstance(context.error, telegram.error.TimedOut):
        if update and update.message:
            await update.message.reply_text(
                "⏳ The bot timed out while processing your request. Please try again."
            )

def main() -> None:
    request = HTTPXRequest(connect_timeout=0.01, read_timeout=0.01)
    """Run the bot."""
    application = Application.builder().token("").build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("upload", upload))
    application.add_handler(CommandHandler("list", list_texts))
    application.add_handler(CommandHandler("status", status))

    # Message handlers
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))

    # Callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))

    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()