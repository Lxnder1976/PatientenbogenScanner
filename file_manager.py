"""Datei-Management für PDF-Verarbeitung."""
import shutil
from pathlib import Path
from typing import List

import config


class FileManager:
    """Klasse zum Verwalten von PDF-Dateien."""
    
    def __init__(self, input_dir: Path = config.INPUT_DIR, output_dir: Path = config.OUTPUT_DIR):
        """
        Initialisiert den File Manager.
        
        Args:
            input_dir: Verzeichnis mit Input-PDFs
            output_dir: Verzeichnis für umbenannte PDFs
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        
        # Erstelle Verzeichnisse falls nicht vorhanden
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def get_pdf_files(self) -> List[Path]:
        """
        Holt alle PDF-Dateien aus dem Input-Verzeichnis.
        
        Returns:
            Liste von PDF-Dateipfaden
        """
        return list(self.input_dir.glob("*.pdf"))
    
    def rename_and_move_file(self, source_path: Path, patient_name: str) -> Path:
        """
        Benennt eine PDF-Datei um und verschiebt sie ins Output-Verzeichnis.
        
        Args:
            source_path: Pfad zur Originaldatei
            patient_name: Name des Patienten
            
        Returns:
            Pfad zur umbenannten Datei
        """
        # Erstelle neuen Dateinamen
        new_filename = f"Patientenbogen - {patient_name}.pdf"
        target_path = self.output_dir / new_filename
        
        # Prüfe ob Datei bereits existiert
        if target_path.exists():
            # Füge Nummer hinzu
            counter = 1
            while target_path.exists():
                new_filename = f"Patientenbogen - {patient_name} ({counter}).pdf"
                target_path = self.output_dir / new_filename
                counter += 1
        
        # Verschiebe Datei
        shutil.move(str(source_path), str(target_path))
        
        return target_path
    
    def move_to_failed(self, source_path: Path) -> Path:
        """
        Verschiebt eine fehlgeschlagene Datei in einen Failed-Ordner.
        
        Args:
            source_path: Pfad zur Datei
            
        Returns:
            Pfad zur verschobenen Datei
        """
        failed_dir = self.output_dir / "failed"
        failed_dir.mkdir(exist_ok=True)
        
        target_path = failed_dir / source_path.name
        
        # Prüfe ob Datei bereits existiert
        if target_path.exists():
            counter = 1
            while target_path.exists():
                target_path = failed_dir / f"{source_path.stem}_{counter}{source_path.suffix}"
                counter += 1
        
        shutil.move(str(source_path), str(target_path))
        
        return target_path
