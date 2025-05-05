import firebase_admin
from firebase_admin import credentials, db
from typing import Dict
import shortuuid  # Updated import

class DatabaseManager:
    """Handles all Firebase database operations."""

    def __init__(self, credential_path: str, database_url: str):
        self._setup_firebase(credential_path, database_url)
        self.document_ref = db.reference("document_files")

    @staticmethod
    def _setup_firebase(cred_path: str, db_url: str) -> None:
        """Initialize Firebase connection."""
        if not firebase_admin._apps:
            firebase_cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(firebase_cred, {"databaseURL": db_url})

    def store_document(self, document_data: Dict, doc_id: str) -> None:
        """Save document data to Firebase."""
        try:
            self.document_ref.child(doc_id).set(document_data)
        except Exception as error:
            raise RuntimeError("Document storage failed") from error

    def add_audio_recording(self, doc_id: str, audio_info: Dict) -> str:
        """Store audio recording metadata with file path and return generated ID."""
        try:
            recording_id = shortuuid.uuid()
            self.document_ref.child(doc_id).child("audio_recordings").child(recording_id).set(audio_info)
            return recording_id
        except Exception as error:
            raise RuntimeError("Audio storage failed") from error

    def fetch_document(self, doc_id: str) -> Dict:
        """Retrieve document data from Firebase."""
        doc_data = self.document_ref.child(doc_id).get()
        if not doc_data:
            raise ValueError("Document not found")
        return doc_data