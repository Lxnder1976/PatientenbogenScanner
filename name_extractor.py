"""Name Extraktion mit OpenAI Vision API."""
import re
from typing import Optional

from openai import OpenAI

import config


class NameExtractor:
    """Klasse zur Extraktion von Namen aus Bildern mit OpenAI Vision API."""
    
    def __init__(self):
        """Initialisiert den Name Extractor mit OpenAI Client."""
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.model = config.OPENAI_MODEL
        self.max_tokens = config.MAX_TOKENS
    
    def extract_name_from_image(self, base64_image: str) -> Optional[str]:
        """
        Extrahiert den Patientennamen aus einem Bild eines Patientenbogens.
        
        Args:
            base64_image: Base64-kodiertes Bild
            
        Returns:
            Extrahierter Name oder None bei Fehler
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """Dies ist ein handschriftlich ausgefüllter Patientenbogen.
Bitte extrahiere den vollständigen Namen des Patienten (Vor- und Nachname).
Gib NUR den Namen zurück, ohne zusätzliche Erklärungen oder Text.
Falls der Name nicht lesbar ist, antworte mit 'UNLESBAR'."""
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_completion_tokens=self.max_tokens  # GPT-5 verwendet max_completion_tokens
            )
            
            # Extrahiere die Antwort
            name = response.choices[0].message.content.strip()
            
            # Prüfe ob der Name lesbar war
            if name.upper() == "UNLESBAR":
                return None
            
            # Bereinige den Namen (entferne unerwünschte Zeichen)
            name = self._clean_name(name)
            
            return name if name else None
            
        except Exception as e:
            print(f"Fehler bei der Name-Extraktion: {e}")
            return None
    
    def _clean_name(self, name: str) -> str:
        """
        Bereinigt den extrahierten Namen.
        
        Args:
            name: Roher Name
            
        Returns:
            Bereinigter Name
        """
        # Entferne führende/nachfolgende Leerzeichen
        name = name.strip()
        
        # Erlaube nur Buchstaben, Leerzeichen, Bindestriche und Punkte
        name = re.sub(r'[^a-zA-ZäöüÄÖÜß\s\-\.]', '', name)
        
        # Entferne mehrfache Leerzeichen
        name = re.sub(r'\s+', ' ', name)
        
        return name
