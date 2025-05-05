from io import BytesIO
import base64
import PyPDF2
from reportlab.pdfgen import canvas


class DocumentProcessor:
    """Handles document processing operations."""

    @staticmethod
    def get_text_from_pdf(pdf_content: bytes) -> str:
        """Extract text content from PDF bytes."""
        text_content = []
        with BytesIO(pdf_content) as pdf_stream:
            pdf_reader = PyPDF2.PdfReader(pdf_stream)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_content.append(page_text)
        return "\n".join(text_content).strip()

    @staticmethod
    def create_pdf_from_text(text_content: str) -> bytes:
        """Generate PDF from text content."""
        output_buffer = BytesIO()
        pdf_canvas = canvas.Canvas(output_buffer)

        y_position = 800
        for line in text_content.splitlines():
            pdf_canvas.drawString(50, y_position, line)
            y_position -= 15
            if y_position < 50:
                pdf_canvas.showPage()
                y_position = 800

        pdf_canvas.save()
        return output_buffer.getvalue()

    @staticmethod
    def convert_to_base64(data: bytes) -> str:
        """Convert binary data to base64 string."""
        return base64.b64encode(data).decode("utf-8")