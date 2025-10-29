#!/usr/bin/env python3
"""GUI für DocScanner - Patientenbogen-Scanner mit PyQt6."""
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from threading import Thread
from typing import Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QTextEdit, QProgressBar,
    QFileDialog, QLineEdit, QGroupBox, QListWidgetItem, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QColor

from file_manager import FileManager
from name_extractor import NameExtractor
from pdf_processor import PDFProcessor
from pdf_splitter import PDFSplitter
from smb_handler import SMBHandler
import config


class WorkerSignals(QObject):
    """Signals für Background Worker."""
    progress = pyqtSignal(int, int)  # current, total
    status = pyqtSignal(str)  # status message
    log = pyqtSignal(str)  # log message
    finished = pyqtSignal()
    error = pyqtSignal(str)


class ProcessingWorker:
    """Background Worker für PDF-Verarbeitung."""
    
    def __init__(self, pdf_files: list, signals: WorkerSignals):
        self.pdf_files = pdf_files
        self.signals = signals
        self.should_stop = False
        self.is_paused = False
        
    def run(self):
        """Führt die Verarbeitung aus."""
        try:
            file_manager = FileManager()
            pdf_processor = PDFProcessor()
            name_extractor = NameExtractor()
            pdf_splitter = PDFSplitter()
            
            pdf_splitter.cleanup_temp()
            
            total_files = len(self.pdf_files)
            
            for idx, pdf_path in enumerate(self.pdf_files, 1):
                if self.should_stop:
                    self.signals.log.emit("⏹️ Verarbeitung abgebrochen")
                    break
                
                while self.is_paused:
                    if self.should_stop:
                        break
                    Thread(target=lambda: None).join(0.1)
                
                if self.should_stop:
                    break
                
                self.signals.progress.emit(idx - 1, total_files)
                self.signals.status.emit(f"Verarbeite {pdf_path.name} ({idx}/{total_files})")
                self.signals.log.emit(f"\n[{idx}/{total_files}] Verarbeite: {pdf_path.name}")
                
                # Prüfe ob PDF gesplittet werden muss
                needs_split, reason = pdf_splitter.needs_splitting(pdf_path)
                self.signals.log.emit(f"  → {reason}")
                
                pdfs_to_process = []
                is_multi_pdf = False
                
                if needs_split:
                    self.signals.log.emit("  → PDF wird gesplittet...")
                    split_files = pdf_splitter.split_pdf(pdf_path)
                    
                    if not split_files:
                        self.signals.log.emit("  ❌ Fehler beim Splitten")
                        file_manager.move_to_failed(pdf_path)
                        continue
                    
                    self.signals.log.emit(f"  ✓ In {len(split_files)} Teile gesplittet")
                    pdfs_to_process = split_files
                    is_multi_pdf = True
                elif "Ungültige Seitenzahl" in reason or "Fehler" in reason:
                    self.signals.log.emit(f"  ❌ {reason}")
                    file_manager.move_to_failed(pdf_path)
                    continue
                else:
                    pdfs_to_process = [pdf_path]
                
                # Verarbeite alle PDFs
                for process_idx, process_pdf in enumerate(pdfs_to_process, 1):
                    if self.should_stop:
                        break
                    
                    if is_multi_pdf:
                        self.signals.log.emit(f"\n  [{process_idx}/{len(pdfs_to_process)}] Verarbeite Teil: {process_pdf.name}")
                    
                    indent = "    " if is_multi_pdf else "  "
                    
                    # Konvertiere zu Bild
                    self.signals.log.emit(f"{indent}→ PDF zu Bild konvertieren...")
                    base64_image = pdf_processor.get_first_page_as_base64(process_pdf)
                    
                    if not base64_image:
                        self.signals.log.emit(f"{indent}❌ Fehler bei der Bildkonvertierung")
                        if not is_multi_pdf:
                            file_manager.move_to_failed(process_pdf)
                        continue
                    
                    # Extrahiere Name
                    self.signals.log.emit(f"{indent}→ Name mit OpenAI Vision extrahieren...")
                    patient_name = name_extractor.extract_name_from_image(base64_image)
                    
                    if not patient_name:
                        self.signals.log.emit(f"{indent}❌ Name konnte nicht extrahiert werden")
                        if not is_multi_pdf:
                            file_manager.move_to_failed(process_pdf)
                        else:
                            # Bei Multi-PDF: Fehlgeschlagene Teile auch speichern
                            file_manager.move_to_failed(process_pdf)
                        continue
                    
                    self.signals.log.emit(f"{indent}✓ Extrahierter Name: {patient_name}")
                    
                    # Umbenennen und verschieben
                    self.signals.log.emit(f"{indent}→ Datei umbenennen und verschieben...")
                    try:
                        new_path = file_manager.rename_and_move_file(process_pdf, patient_name)
                        self.signals.log.emit(f"{indent}✅ Erfolgreich: {new_path.name}")
                    except Exception as e:
                        self.signals.log.emit(f"{indent}❌ Fehler beim Umbenennen: {e}")
                
                if is_multi_pdf:
                    original_path = pdf_splitter.move_to_originals(pdf_path, file_manager.output_dir)
                    self.signals.log.emit(f"\n  → Original gespeichert: {original_path.name}")
            
            pdf_splitter.cleanup_temp()
            self.signals.progress.emit(total_files, total_files)
            self.signals.status.emit("Verarbeitung abgeschlossen")
            self.signals.log.emit("\n✅ Verarbeitung abgeschlossen")
            
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()


class ScannerWindow(QMainWindow):
    """Hauptfenster der Scanner-Anwendung."""
    
    def __init__(self):
        super().__init__()
        self.worker = None
        self.worker_thread = None
        self.is_processing = False
        self.smb_handler = SMBHandler()
        
        self.setWindowTitle("PatientenbogenScanner")
        self.setMinimumSize(1000, 700)
        
        self.init_ui()
        self.connect_smb()
        
        # Timer für Auto-Refresh
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_lists)
        self.refresh_timer.start(2000)  # Alle 2 Sekunden
        
        # Initial refresh
        self.refresh_lists()
    
    def init_ui(self):
        """Initialisiert die Benutzeroberfläche."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # SMB Pfad Auswahl
        smb_group = QGroupBox("Eingabeverzeichnis")
        smb_layout = QHBoxLayout()
        
        self.smb_status_label = QLabel("🔌 Verbinde mit SMB...")
        self.smb_status_label.setStyleSheet("color: orange;")
        
        self.smb_path_input = QLineEdit()
        self.smb_path_input.setText(config.SMB_SERVER)
        self.smb_path_input.setPlaceholderText("SMB-Pfad...")
        self.smb_path_input.setReadOnly(True)
        
        reconnect_btn = QPushButton("🔄 Neu verbinden")
        reconnect_btn.clicked.connect(self.connect_smb)
        
        browse_btn = QPushButton("📁 Lokal wählen")
        browse_btn.clicked.connect(self.browse_folder)
        
        smb_layout.addWidget(self.smb_status_label)
        smb_layout.addWidget(QLabel("SMB:"))
        smb_layout.addWidget(self.smb_path_input)
        smb_layout.addWidget(reconnect_btn)
        smb_layout.addWidget(browse_btn)
        smb_group.setLayout(smb_layout)
        layout.addWidget(smb_group)
        
        # Drei Listen nebeneinander
        lists_layout = QHBoxLayout()
        
        # Input-Liste
        input_group = QGroupBox("Neue Dateien (Heute)")
        input_layout = QVBoxLayout()
        self.input_list = QListWidget()
        input_layout.addWidget(self.input_list)
        input_group.setLayout(input_layout)
        lists_layout.addWidget(input_group)
        
        # Output-Liste
        output_group = QGroupBox("Verarbeitet (Output)")
        output_layout = QVBoxLayout()
        self.output_list = QListWidget()
        output_layout.addWidget(self.output_list)
        output_group.setLayout(output_layout)
        lists_layout.addWidget(output_group)
        
        # Failed-Liste
        failed_group = QGroupBox("Fehlgeschlagen")
        failed_layout = QVBoxLayout()
        self.failed_list = QListWidget()
        failed_layout.addWidget(self.failed_list)
        failed_group.setLayout(failed_layout)
        lists_layout.addWidget(failed_group)
        
        layout.addLayout(lists_layout)
        
        # Status und Progress
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("Bereit")
        self.status_label.setStyleSheet("font-weight: bold;")
        status_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        status_layout.addWidget(self.progress_bar)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Control Buttons
        buttons_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶️ Verarbeitung starten")
        self.start_btn.clicked.connect(self.start_processing)
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        
        self.pause_btn = QPushButton("⏸️ Pause")
        self.pause_btn.clicked.connect(self.pause_processing)
        self.pause_btn.setEnabled(False)
        
        self.stop_btn = QPushButton("⏹️ Stop")
        self.stop_btn.clicked.connect(self.stop_processing)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("background-color: #f44336; color: white;")
        
        self.show_output_btn = QPushButton("📂 Zeige Dateien")
        self.show_output_btn.clicked.connect(self.show_output_folder)
        self.show_output_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 10px;")
        
        buttons_layout.addWidget(self.start_btn)
        buttons_layout.addWidget(self.pause_btn)
        buttons_layout.addWidget(self.stop_btn)
        buttons_layout.addWidget(self.show_output_btn)
        buttons_layout.addStretch()
        
        layout.addLayout(buttons_layout)
        
        # Log-Fenster
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
    
    def connect_smb(self):
        """Verbindet mit dem SMB-Verzeichnis."""
        self.smb_status_label.setText("🔌 Verbinde...")
        self.smb_status_label.setStyleSheet("color: orange;")
        
        # Versuche SMB zu mounten
        mount_path = self.smb_handler.get_mount_point()
        
        if mount_path:
            self.smb_status_label.setText(f"✅ Verbunden: {mount_path}")
            self.smb_status_label.setStyleSheet("color: green; font-weight: bold;")
            self.current_input_dir = mount_path
            self.refresh_lists()
        else:
            self.smb_status_label.setText("❌ Verbindung fehlgeschlagen")
            self.smb_status_label.setStyleSheet("color: red;")
            QMessageBox.warning(
                self,
                "SMB-Verbindung fehlgeschlagen",
                f"Konnte nicht mit {config.SMB_SERVER} verbinden.\n\n"
                "Bitte prüfe:\n"
                "- Ist der Server erreichbar?\n"
                "- Sind die Zugangsdaten korrekt?\n"
                "- Ist das Netzwerk verbunden?\n\n"
                "Du kannst ein lokales Verzeichnis wählen."
            )
            self.current_input_dir = config.INPUT_DIR
    
    def browse_folder(self):
        """Öffnet Dialog zur Ordnerauswahl (für lokale Verzeichnisse)."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Lokales Eingabeverzeichnis auswählen",
            str(config.INPUT_DIR)
        )
        if folder:
            self.current_input_dir = Path(folder)
            self.smb_status_label.setText(f"📁 Lokal: {folder}")
            self.smb_status_label.setStyleSheet("color: blue;")
            self.refresh_lists()
    
    def refresh_lists(self):
        """Aktualisiert alle Listen."""
        if not hasattr(self, 'current_input_dir'):
            self.current_input_dir = config.INPUT_DIR
        
        input_dir = self.current_input_dir
        
        if not input_dir.exists():
            return
        
        # Input-Liste (nur heute's Dateien)
        self.input_list.clear()
        today = datetime.now().date()
        
        for pdf_file in sorted(input_dir.glob("*.pdf")):
            file_date = datetime.fromtimestamp(pdf_file.stat().st_mtime).date()
            if file_date == today:
                item = QListWidgetItem(f"📄 {pdf_file.name}")
                self.input_list.addItem(item)
        
        # Output-Liste
        self.output_list.clear()
        output_dir = config.OUTPUT_DIR
        if output_dir.exists():
            for pdf_file in sorted(output_dir.glob("*.pdf"), key=lambda x: x.stat().st_mtime, reverse=True):
                file_time = datetime.fromtimestamp(pdf_file.stat().st_mtime).strftime("%H:%M")
                item = QListWidgetItem(f"✅ {pdf_file.name} ({file_time})")
                item.setForeground(QColor(76, 175, 80))  # Grün
                self.output_list.addItem(item)
        
        # Failed-Liste
        self.failed_list.clear()
        failed_dir = config.OUTPUT_DIR / "failed"
        if failed_dir.exists():
            for pdf_file in sorted(failed_dir.glob("*.pdf"), key=lambda x: x.stat().st_mtime, reverse=True):
                file_time = datetime.fromtimestamp(pdf_file.stat().st_mtime).strftime("%H:%M")
                item = QListWidgetItem(f"❌ {pdf_file.name} ({file_time})")
                item.setForeground(QColor(244, 67, 54))  # Rot
                self.failed_list.addItem(item)
    
    def start_processing(self):
        """Startet die Verarbeitung."""
        if self.is_processing:
            return
        
        input_dir = self.current_input_dir
        
        if not input_dir.exists():
            QMessageBox.warning(self, "Fehler", "Eingabeverzeichnis existiert nicht!")
            return
        
        # Hole PDFs von heute
        today = datetime.now().date()
        pdf_files = []
        
        for pdf_file in sorted(input_dir.glob("*.pdf")):
            file_date = datetime.fromtimestamp(pdf_file.stat().st_mtime).date()
            if file_date == today:
                pdf_files.append(pdf_file)
        
        if not pdf_files:
            QMessageBox.information(self, "Info", "Keine neuen Dateien (von heute) gefunden!")
            return
        
        # Starte Worker
        self.is_processing = True
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        
        self.log_text.clear()
        self.log_text.append(f"🚀 Starte Verarbeitung von {len(pdf_files)} Datei(en)...\n")
        
        signals = WorkerSignals()
        signals.progress.connect(self.update_progress)
        signals.status.connect(self.update_status)
        signals.log.connect(self.append_log)
        signals.finished.connect(self.processing_finished)
        signals.error.connect(self.processing_error)
        
        self.worker = ProcessingWorker(pdf_files, signals)
        self.worker_thread = Thread(target=self.worker.run)
        self.worker_thread.start()
    
    def pause_processing(self):
        """Pausiert/Fortsetzt die Verarbeitung."""
        if self.worker:
            self.worker.is_paused = not self.worker.is_paused
            if self.worker.is_paused:
                self.pause_btn.setText("▶️ Fortsetzen")
                self.status_label.setText("⏸️ Pausiert")
            else:
                self.pause_btn.setText("⏸️ Pause")
    
    def stop_processing(self):
        """Stoppt die Verarbeitung."""
        if self.worker:
            self.worker.should_stop = True
            self.status_label.setText("Wird gestoppt...")
    
    def update_progress(self, current: int, total: int):
        """Aktualisiert den Fortschritt."""
        if total > 0:
            progress = int((current / total) * 100)
            self.progress_bar.setValue(progress)
    
    def update_status(self, status: str):
        """Aktualisiert den Status."""
        self.status_label.setText(status)
    
    def append_log(self, message: str):
        """Fügt Log-Nachricht hinzu."""
        self.log_text.append(message)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
        self.refresh_lists()
    
    def processing_finished(self):
        """Wird aufgerufen wenn Verarbeitung abgeschlossen ist."""
        self.is_processing = False
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setText("⏸️ Pause")
        self.progress_bar.setValue(100)
        self.refresh_lists()
    
    def processing_error(self, error: str):
        """Wird bei Fehler aufgerufen."""
        QMessageBox.critical(self, "Fehler", f"Fehler bei der Verarbeitung:\n{error}")
        self.processing_finished()
    
    def show_output_folder(self):
        """Öffnet den Finder mit dem Output-Verzeichnis."""
        output_dir = config.OUTPUT_DIR
        
        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)
        
        # Öffne Finder mit dem Output-Verzeichnis
        subprocess.run(['open', str(output_dir)])


def main():
    """Startet die GUI-Anwendung."""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Moderner Look
    
    window = ScannerWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
