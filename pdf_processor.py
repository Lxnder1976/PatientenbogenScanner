"""PDF Verarbeitung und Bildkonvertierung."""
import base64
from io import BytesIO
from pathlib import Path
from typing import Optional

from pdf2image import convert_from_path
from PIL import Image

import config


class PDFProcessor:
    """Klasse zur Verarbeitung von PDF-Dateien."""
    
    def __init__(self, dpi: int = config.PDF_DPI):
        """
        Initialisiert den PDF Processor.
        
        Args:
            dpi: DPI für die PDF zu Bild Konvertierung
        """
        self.dpi = dpi
    
    def pdf_to_image(self, pdf_path: Path, page_number: int = 0) -> Optional[Image.Image]:
        """
        Konvertiert eine PDF-Seite in ein Bild.
        
        Args:
            pdf_path: Pfad zur PDF-Datei
            page_number: Seitennummer (0-basiert)
            
        Returns:
            PIL Image oder None bei Fehler
        """
        try:
            images = convert_from_path(
                pdf_path,
                dpi=self.dpi,
                first_page=page_number + 1,
                last_page=page_number + 1
            )
            return images[0] if images else None
        except Exception as e:
            print(f"Fehler beim Konvertieren von {pdf_path}: {e}")
            return None
    
    def image_to_base64(self, image: Image.Image, format: str = "PNG") -> str:
        """
        Konvertiert ein PIL Image zu base64.
        
        Args:
            image: PIL Image
            format: Bildformat (PNG, JPEG, etc.)
            
        Returns:
            Base64-kodierter String
        """
        buffered = BytesIO()
        image.save(buffered, format=format)
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    def get_first_page_as_base64(self, pdf_path: Path) -> Optional[str]:
        """
        Holt die erste Seite eines PDFs als base64-kodiertes Bild.
        
        Args:
            pdf_path: Pfad zur PDF-Datei
            
        Returns:
            Base64-kodierter String oder None bei Fehler
        """
        image = self.pdf_to_image(pdf_path, page_number=0)
        if image:
            return self.image_to_base64(image)
        return None
