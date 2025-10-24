"""PDF Splitting für Multi-Patientenbogen PDFs."""
from pathlib import Path
from typing import List, Optional
import shutil

from PyPDF2 import PdfReader, PdfWriter

import config


class PDFSplitter:
    """Klasse zum Splitten von Multi-Patientenbogen PDFs."""
    
    def __init__(self, pages_per_patient: int = config.PAGES_PER_PATIENT):
        """
        Initialisiert den PDF Splitter.
        
        Args:
            pages_per_patient: Anzahl der Seiten pro Patientenbogen
        """
        self.pages_per_patient = pages_per_patient
        self.temp_dir = config.TEMP_DIR
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def get_page_count(self, pdf_path: Path) -> int:
        """
        Ermittelt die Anzahl der Seiten in einem PDF.
        
        Args:
            pdf_path: Pfad zur PDF-Datei
            
        Returns:
            Anzahl der Seiten
        """
        try:
            reader = PdfReader(pdf_path)
            return len(reader.pages)
        except Exception as e:
            print(f"Fehler beim Lesen von {pdf_path}: {e}")
            return 0
    
    def needs_splitting(self, pdf_path: Path) -> tuple[bool, str]:
        """
        Prüft ob ein PDF gesplittet werden muss.
        
        Args:
            pdf_path: Pfad zur PDF-Datei
            
        Returns:
            (needs_split, reason)
            - needs_split: True wenn Splitting nötig ist
            - reason: Erklärung
        """
        page_count = self.get_page_count(pdf_path)
        
        if page_count == 0:
            return False, "Fehler beim Lesen der Seitenzahl"
        
        if page_count == self.pages_per_patient:
            return False, f"Einzelner Bogen ({page_count} Seiten)"
        
        if page_count % self.pages_per_patient != 0:
            return False, f"Ungültige Seitenzahl ({page_count} Seiten, nicht durch {self.pages_per_patient} teilbar)"
        
        num_patients = page_count // self.pages_per_patient
        return True, f"Multi-Bogen ({page_count} Seiten = {num_patients} Patienten)"
    
    def split_pdf(self, pdf_path: Path) -> Optional[List[Path]]:
        """
        Splittet ein Multi-Patientenbogen PDF in einzelne PDFs.
        
        Args:
            pdf_path: Pfad zur PDF-Datei
            
        Returns:
            Liste von Pfaden zu den gesplitteten PDFs oder None bei Fehler
        """
        try:
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
            num_patients = total_pages // self.pages_per_patient
            
            split_files = []
            base_name = pdf_path.stem
            
            for patient_idx in range(num_patients):
                # Erstelle neuen PDF Writer
                writer = PdfWriter()
                
                # Füge die entsprechenden Seiten hinzu
                start_page = patient_idx * self.pages_per_patient
                end_page = start_page + self.pages_per_patient
                
                for page_num in range(start_page, end_page):
                    writer.add_page(reader.pages[page_num])
                
                # Speichere gesplittetes PDF
                output_filename = f"{base_name}_patient_{patient_idx + 1}.pdf"
                output_path = self.temp_dir / output_filename
                
                with open(output_path, 'wb') as output_file:
                    writer.write(output_file)
                
                split_files.append(output_path)
            
            return split_files
            
        except Exception as e:
            print(f"Fehler beim Splitten von {pdf_path}: {e}")
            return None
    
    def cleanup_temp(self):
        """Löscht alle temporären Dateien."""
        if self.temp_dir.exists():
            for file in self.temp_dir.glob("*.pdf"):
                try:
                    file.unlink()
                except Exception as e:
                    print(f"Warnung: Konnte {file} nicht löschen: {e}")
    
    def move_to_originals(self, pdf_path: Path, output_dir: Path) -> Path:
        """
        Verschiebt ein Original-Multi-PDF ins originals/ Verzeichnis.
        
        Args:
            pdf_path: Pfad zur Original-PDF
            output_dir: Output-Verzeichnis
            
        Returns:
            Neuer Pfad
        """
        originals_dir = output_dir / "originals"
        originals_dir.mkdir(exist_ok=True)
        
        target_path = originals_dir / pdf_path.name
        
        # Prüfe ob Datei bereits existiert
        if target_path.exists():
            counter = 1
            while target_path.exists():
                target_path = originals_dir / f"{pdf_path.stem}_{counter}{pdf_path.suffix}"
                counter += 1
        
        shutil.move(str(pdf_path), str(target_path))
        return target_path
