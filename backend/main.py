from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Optional
import shortuuid
import os
import shutil
from database_manager import DatabaseManager
from document_processor import DocumentProcessor
from audio_processor import AudioProcessor
from similarity_checker import SimilarityChecker

# Ensure audio recordings directory exists
AUDIO_STORAGE_PATH = "static/audiorecordings"
os.makedirs(AUDIO_STORAGE_PATH, exist_ok=True)

# Initialize service components
document_storage = DatabaseManager(
    credential_path="",
    database_url=""
)

doc_handler = DocumentProcessor()
audio_handler = AudioProcessor()
content_checker = SimilarityChecker()

# Initialize FastAPI app
app = FastAPI(title="Document Processing API", version="1.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Length", "Content-Range", "Content-Type", "Accept-Ranges"]
)

@app.post("/documents")
async def upload_document(
    file: Optional[UploadFile] = File(None),
    text_content: Optional[str] = Form(None),
    user_identifier: str = Form(...)
):
    """
    Handle document uploads either as PDF file or raw text.
    Stores the document in database and returns the document ID.
    """
    try:
        if not file and not text_content:
            raise HTTPException(status_code=400, detail="No document content provided")

        new_doc_id = shortuuid.uuid()

        if text_content:
            # Process text input
            pdf_data = doc_handler.create_pdf_from_text(text_content)
            extracted_text = text_content
        else:
            # Process file upload
            file_data = await file.read()
            extracted_text = doc_handler.get_text_from_pdf(file_data)
            pdf_data = file_data

        # Prepare document data for storage
        doc_data = {
            "pdf_content": doc_handler.convert_to_base64(pdf_data),
            "text_content": extracted_text,
            "user_id": user_identifier,
            "audio_recordings": {}
        }

        document_storage.store_document(doc_data, new_doc_id)
        return {"document_id": new_doc_id}

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Document processing failed: {str(error)}"
        )

@app.get("/documents")
async def list_documents(
    page_number: int = 1,
    items_per_page: int = 10,
    user_identifier: Optional[str] = None,
    user_only: bool = False
):
    """
    Retrieve paginated list of documents, optionally filtered by user.
    """
    try:
        all_documents = document_storage.document_ref.get() or {}
        document_list = []

        for doc_id, doc_data in all_documents.items():
            if user_only and user_identifier and doc_data.get("user_id") != user_identifier:
                continue
            doc_data["document_id"] = doc_id
            document_list.append(doc_data)

        total_documents = len(document_list)
        start_index = (page_number - 1) * items_per_page
        end_index = start_index + items_per_page

        return {
            "current_page": page_number,
            "page_size": items_per_page,
            "total_documents": total_documents,
            "documents": document_list[start_index:end_index]
        }
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve documents: {str(error)}"
        )

@app.post("/recordings/{document_id}")
async def upload_recording(
    document_id: str,
    audio_file: UploadFile = File(...),
    uploader_id: str = Form(...)
):
    """
    Process audio recordings for a specific document.
    Stores the recording as .wav locally and saves the file path in the database.
    Returns transcription data.
    """
    try:
        # Retrieve the original document
        document_data = document_storage.fetch_document(document_id)
        original_text = document_data.get("text_content", "")

        # Process the audio file
        audio_data = await audio_file.read()
        transcription_result = audio_handler.process_audio(audio_data, audio_file.filename)

        # Check content similarity
        is_semantically_valid = content_checker.check_content_similarity(
            original_text,
            transcription_result["text"]
        )

        # Save audio file as .wav
        audio_filename = f"{shortuuid.uuid()}.wav"
        audio_path = os.path.join(AUDIO_STORAGE_PATH, audio_filename)
        shutil.copy(transcription_result["wav_path"], audio_path)  # Copy the .wav file

        # Clean up temporary files
        for path in [transcription_result["temp_input_path"], transcription_result["wav_path"]]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    continue

        # Prepare recording data with file path
        recording_data = {
            "audio_path": audio_path,  # Accessible via /static/audiorecordings/
            "uploader_id": uploader_id,
            "transcribed_text": transcription_result["text"],
            "word_timings": transcription_result["segments"],
            "content_match": is_semantically_valid
        }

        # Store recording and return results
        recording_id = document_storage.add_audio_recording(document_id, recording_data)
        return {
            "document_id": document_id,
            "recording_id": recording_id,
            "content_match": is_semantically_valid
        }

    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Audio processing failed: {str(error)}"
        )

@app.get("/documents/{document_id}")
async def get_document_details(document_id: str):
    """
    Retrieve complete details for a specific document.
    """
    try:
        doc_data = document_storage.fetch_document(document_id)
        doc_data["document_id"] = document_id
        return doc_data
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve document: {str(error)}"
        )

@app.get("/recordings/{document_id}/{recording_id}")
async def get_recording_details(document_id: str, recording_id: str):
    """
    Retrieve specific recording details for a document.
    """
    try:
        doc_data = document_storage.fetch_document(document_id)
        recordings = doc_data.get("audio_recordings", {})

        if recording_id not in recordings:
            raise HTTPException(status_code=404, detail="Recording not found")

        return {
            "document_id": document_id,
            "recording_id": recording_id,
            "original_text": doc_data.get("text_content", ""),
            **recordings[recording_id]
        }
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve recording: {str(error)}"
        )

# Static files serving
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/telegram_miniapp.html")
async def serve_telegram_app():
    """
    Serve the Telegram mini-app interface.
    """
    return FileResponse("../outsiders/telegram_miniapp.html")