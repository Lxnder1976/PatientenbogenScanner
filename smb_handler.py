"""SMB-Verzeichnis Handling für macOS."""
import subprocess
from pathlib import Path
from typing import Optional

import config


class SMBHandler:
    """Klasse zum Mounten und Verwalten von SMB-Verzeichnissen."""
    
    def __init__(self, smb_path: str = config.SMB_SERVER):
        """
        Initialisiert den SMB Handler.
        
        Args:
            smb_path: SMB-Pfad (z.B. smb://192.168.1.140/scans)
        """
        self.smb_path = smb_path
        self.mount_point = config.SMB_MOUNT_POINT
        
    def get_mount_point(self) -> Optional[Path]:
        """
        Versucht das SMB-Verzeichnis zu mounten und gibt den Mount-Point zurück.
        
        Returns:
            Path zum gemounteten Verzeichnis oder None bei Fehler
        """
        # Prüfe ob bereits gemountet
        if self.is_mounted():
            return self.get_volumes_path()
        
        # Versuche zu mounten
        if self.mount():
            return self.get_volumes_path()
        
        return None
    
    def is_mounted(self) -> bool:
        """
        Prüft ob das SMB-Verzeichnis bereits gemountet ist.
        
        Returns:
            True wenn gemountet, sonst False
        """
        # Extrahiere Share-Name aus SMB-Pfad
        share_name = self.smb_path.split('/')[-1]
        volumes_path = Path(f"/Volumes/{share_name}")
        
        return volumes_path.exists() and volumes_path.is_mount()
    
    def get_volumes_path(self) -> Optional[Path]:
        """
        Gibt den Pfad zum gemounteten Verzeichnis in /Volumes zurück.
        
        Returns:
            Path zum Mount-Point in /Volumes
        """
        share_name = self.smb_path.split('/')[-1]
        volumes_path = Path(f"/Volumes/{share_name}")
        
        if volumes_path.exists():
            return volumes_path
        
        return None
    
    def mount(self) -> bool:
        """
        Mountet das SMB-Verzeichnis.
        
        Returns:
            True bei Erfolg, False bei Fehler
        """
        try:
            # macOS mountet SMB automatisch in /Volumes wenn man mit open arbeitet
            # Verwende osascript für bessere Integration
            share_name = self.smb_path.split('/')[-1]
            
            # AppleScript zum Mounten
            script = f'''
            tell application "Finder"
                try
                    mount volume "{self.smb_path}"
                    return true
                on error
                    return false
                end try
            end tell
            '''
            
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and 'true' in result.stdout.lower():
                return True
            
            return False
            
        except Exception as e:
            print(f"Fehler beim Mounten von {self.smb_path}: {e}")
            return False
    
    def unmount(self) -> bool:
        """
        Unmountet das SMB-Verzeichnis.
        
        Returns:
            True bei Erfolg, False bei Fehler
        """
        try:
            volumes_path = self.get_volumes_path()
            if not volumes_path:
                return True  # Bereits unmounted
            
            subprocess.run(
                ['diskutil', 'unmount', str(volumes_path)],
                capture_output=True,
                timeout=5
            )
            
            return True
            
        except Exception as e:
            print(f"Fehler beim Unmounten: {e}")
            return False
