import os
import whisper
from pydub import AudioSegment
from typing import Dict, List
import uuid


class AudioProcessor:
    """Handles audio processing and transcription."""

    def __init__(self, model_size: str = "small"):
        self.speech_model = whisper.load_model(model_size, device="cpu")

    def process_audio(self, audio_content: bytes, filename: str) -> Dict:
        """Transcribe audio content and return results."""
        temp_files = self._create_temp_files(audio_content, filename)
        try:
            transcription = self._perform_transcription(temp_files.process_path)
            return {
                "text": transcription["text"],
                "segments": self._extract_word_chunks(transcription),
                "wav_path": temp_files.process_path,  # Return the .wav path for storage
                "temp_input_path": temp_files.input_path  # Return input path for cleanup
            }
        except Exception as e:
            # Clean up in case of error
            self._remove_temp_files(temp_files)
            raise

    def _create_temp_files(self, audio_data: bytes, original_name: str):
        """Handle temporary file creation for processing."""

        class TempFiles:
            def __init__(self, input_path, process_path=None):
                self.input_path = input_path
                self.process_path = process_path

        # Save the original audio to a temporary file
        input_path = f"temp_{uuid.uuid4().hex}_{original_name}"
        with open(input_path, "wb") as f:
            f.write(audio_data)

        # Always convert to .wav for processing and storage
        process_path = f"temp_{uuid.uuid4().hex}.wav"
        audio = AudioSegment.from_file(input_path)
        audio.export(process_path, format="wav")

        return TempFiles(input_path, process_path)

    def _perform_transcription(self, audio_path: str) -> Dict:
        """Execute Whisper transcription."""
        return self.speech_model.transcribe(audio_path, word_timestamps=True, fp16=False)

    @staticmethod
    def _extract_word_chunks(transcription: Dict) -> List[Dict]:
        """Extract word-level timing information."""
        word_chunks = []
        for segment in transcription["segments"]:
            for word in segment.get("words", []):
                word_chunks.append({
                    "text": word["word"],
                    "start": word["start"],
                    "end": word["end"]
                })
        return word_chunks

    @staticmethod
    def _remove_temp_files(temp_files) -> None:
        """Clean up temporary files."""
        for path in [temp_files.input_path, temp_files.process_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    continue