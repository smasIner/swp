# Follow My Reading - Document Processing Bot

This project is a Telegram bot integrated with a FastAPI backend for document and audio processing. It allows users to upload text or PDF documents, store them in a Firebase Realtime Database, and process audio recordings with transcription and similarity checking.

## Prerequisites

Before deploying, ensure you have the following:

- **Python 3.9+** installed.
- **Firebase Account** with a Realtime Database set up.
- **Telegram Bot Token** obtained from BotFather.
- **Ngrok** (or another tunneling service) for exposing the local server to the internet (optional for development).

### System Dependencies
- **ffmpeg**: Required for audio processing (dependency for `pydub`).

## Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. **Install Dependencies**
   Create a virtual environment and install the required Python packages:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure Firebase**
   - Download your Firebase service account credentials JSON file from the Firebase Console.
   - Place the JSON file in a secure location and update the `credential_path` in `main.py` with the correct path:
     ```python
     document_storage = DatabaseManager(
         credential_path="/path/to/your/firebase_cred.json",
         database_url="https://your-database-name.firebaseio.com"
     )
     ```
   - Ensure your Firebase Realtime Database URL is correctly set in the `database_url` parameter.

4. **Set Up Telegram Bot**
   - Obtain a bot token from [BotFather](https://t.me/BotFather) on Telegram.
   - Update the bot token in `telegram_bot.py`:
     ```python
     application = Application.builder().token("YOUR_BOT_TOKEN").build()
     ```

5. **Install System Dependencies**
   Install `ffmpeg` for audio processing:
   - On macOS:
     ```bash
     brew install ffmpeg
     ```
   - On Ubuntu:
     ```bash
     sudo apt-get install ffmpeg
     ```
   - On Windows: Download and install from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH.

6. **Run the FastAPI Backend**
   Start the FastAPI server using `uvicorn`:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

7. **Expose the Server with Ngrok (Optional)**
   To make the local server accessible to Telegram, use `ngrok`:
   - Download and install `ngrok` from [ngrok.com](https://ngrok.com/).
   - Run ngrok to expose port 8000:
     ```bash
     ngrok http 8000
     ```
   - Copy the ngrok URL (e.g., `https://abc123.ngrok-free.app`) and update the `API_BASE_URL` in `telegram_bot.py`:
     ```python
     API_BASE_URL = "https://abc123.ngrok-free.app"
     ```

8. **Run the Telegram Bot**
   In a separate terminal, activate the virtual environment and start the bot:
   ```bash
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   python telegram_bot.py
   ```

## Usage
- Interact with the bot on Telegram using commands like `/start`, `/upload`, `/list`, and `/status`.
- Upload PDF or text files, and add audio recordings for transcription and similarity checking.
- Access the Telegram mini-app for an enhanced interface to view recordings and text.

## Notes
- Ensure `ffmpeg` is in your system PATH for audio processing to work.
- Ngrok is optional for local development but required for Telegram webhook integration in production.
- Keep your Firebase credentials and Telegram bot token secure and do not expose them publicly.