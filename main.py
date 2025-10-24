#!/usr/bin/env python3
"""Hauptprogramm für DocScanner - Automatische Patientenbogen-Umbenennung."""
from pathlib import Path

from file_manager import FileManager
from name_extractor import NameExtractor
from pdf_processor import PDFProcessor
from pdf_splitter import PDFSplitter


def process_patient_forms():
    """Verarbeitet alle Patientenbögen im Input-Verzeichnis."""
    print("=" * 60)
    print("DocScanner - Patientenbögen Verarbeitung")
    print("=" * 60)
    print()
    
    # Initialisiere Komponenten
    file_manager = FileManager()
    pdf_processor = PDFProcessor()
    name_extractor = NameExtractor()
    pdf_splitter = PDFSplitter()
    
    # Cleanup temp-Verzeichnis von vorherigen Läufen
    pdf_splitter.cleanup_temp()
    
    # Hole alle PDFs
    pdf_files = file_manager.get_pdf_files()
    
    if not pdf_files:
        print("ℹ️  Keine PDF-Dateien im Input-Verzeichnis gefunden.")
        print(f"   Verzeichnis: {file_manager.input_dir}")
        return
    
    print(f"📄 {len(pdf_files)} PDF-Datei(en) gefunden")
    print()
    
    success_count = 0
    failed_count = 0
    
    # Verarbeite jede PDF
    for idx, pdf_path in enumerate(pdf_files, 1):
        print(f"[{idx}/{len(pdf_files)}] Verarbeite: {pdf_path.name}")
        
        # Prüfe ob PDF gesplittet werden muss
        needs_split, reason = pdf_splitter.needs_splitting(pdf_path)
        print(f"  → {reason}")
        
        # Liste der zu verarbeitenden PDFs (entweder Original oder gesplittete)
        pdfs_to_process = []
        is_multi_pdf = False
        
        if needs_split:
            # Multi-Patientenbogen PDF splitten
            print(f"  → PDF wird gesplittet...")
            split_files = pdf_splitter.split_pdf(pdf_path)
            
            if not split_files:
                print("  ❌ Fehler beim Splitten")
                file_manager.move_to_failed(pdf_path)
                failed_count += 1
                print()
                continue
            
            print(f"  ✓ In {len(split_files)} Teile gesplittet")
            pdfs_to_process = split_files
            is_multi_pdf = True
        elif "Ungültige Seitenzahl" in reason:
            # PDF hat ungültige Seitenzahl
            print(f"  ❌ {reason}")
            file_manager.move_to_failed(pdf_path)
            failed_count += 1
            print()
            continue
        elif "Fehler" in reason:
            # Fehler beim Lesen
            print(f"  ❌ {reason}")
            file_manager.move_to_failed(pdf_path)
            failed_count += 1
            print()
            continue
        else:
            # Einzelner Bogen, normal verarbeiten
            pdfs_to_process = [pdf_path]
        
        # Verarbeite alle PDFs (entweder 1 Original oder mehrere gesplittete)
        for process_idx, process_pdf in enumerate(pdfs_to_process, 1):
            if is_multi_pdf:
                print(f"\n  [{process_idx}/{len(pdfs_to_process)}] Verarbeite Teil: {process_pdf.name}")
            
            # Konvertiere erste Seite zu Bild
            print("    → PDF zu Bild konvertieren..." if is_multi_pdf else "  → PDF zu Bild konvertieren...")
            base64_image = pdf_processor.get_first_page_as_base64(process_pdf)
            
            if not base64_image:
                indent = "    " if is_multi_pdf else "  "
                print(f"{indent}❌ Fehler bei der Bildkonvertierung")
                if not is_multi_pdf:
                    file_manager.move_to_failed(process_pdf)
                failed_count += 1
                continue
            
            # Extrahiere Name mit OpenAI Vision
            print("    → Name mit OpenAI Vision extrahieren..." if is_multi_pdf else "  → Name mit OpenAI Vision extrahieren...")
            patient_name = name_extractor.extract_name_from_image(base64_image)
            
            if not patient_name:
                indent = "    " if is_multi_pdf else "  "
                print(f"{indent}❌ Name konnte nicht extrahiert werden")
                if not is_multi_pdf:
                    file_manager.move_to_failed(process_pdf)
                failed_count += 1
                continue
            
            indent = "    " if is_multi_pdf else "  "
            print(f"{indent}✓ Extrahierter Name: {patient_name}")
            
            # Benenne Datei um und verschiebe
            print(f"{indent}→ Datei umbenennen und verschieben...")
            try:
                new_path = file_manager.rename_and_move_file(process_pdf, patient_name)
                print(f"{indent}✅ Erfolgreich: {new_path.name}")
                success_count += 1
            except Exception as e:
                print(f"{indent}❌ Fehler beim Umbenennen: {e}")
                failed_count += 1
        
        # Bei Multi-PDF: Original ins originals/ Verzeichnis verschieben
        if is_multi_pdf:
            original_path = pdf_splitter.move_to_originals(pdf_path, file_manager.output_dir)
            print(f"\n  → Original gespeichert: {original_path.name}")
        
        print()
    
    # Cleanup temp-Verzeichnis
    pdf_splitter.cleanup_temp()
    
    # Zusammenfassung
    print("=" * 60)
    print("Verarbeitung abgeschlossen")
    print("=" * 60)
    print(f"✅ Erfolgreich: {success_count}")
    print(f"❌ Fehlgeschlagen: {failed_count}")
    print()


if __name__ == "__main__":
    try:
        process_patient_forms()
    except KeyboardInterrupt:
        print("\n\n⚠️  Abbruch durch Benutzer")
    except Exception as e:
        print(f"\n\n❌ Unerwarteter Fehler: {e}")
