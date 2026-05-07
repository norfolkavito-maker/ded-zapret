"""
Backup system for DedZapret Manager

Handles automatic and manual backups of configuration,
state, and important data files.
"""

import json
import shutil
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import tempfile

from .paths import SafePaths
from .logging import get_logger, LogComponent
from .security import get_masker


class BackupType:
    """Backup type constants"""
    FULL = "full"
    CONFIG = "config"
    STATE = "state"
    LOGS = "logs"
    CUSTOM = "custom"


class BackupInfo:
    """Information about a backup"""
    
    def __init__(self, backup_path: Path):
        self.path = backup_path
        self.info_file = backup_path / "backup_info.json"
        self._info = self._load_info()
    
    def _load_info(self) -> Dict[str, Any]:
        """Load backup information"""
        if self.info_file.exists():
            try:
                with open(self.info_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        
        # Fallback info from filename
        return {
            "backup_type": "unknown",
            "created_at": datetime.fromtimestamp(self.path.stat().st_mtime).isoformat(),
            "version": "1.0.0",
            "description": "Backup information not available"
        }
    
    @property
    def backup_type(self) -> str:
        return self._info.get("backup_type", "unknown")
    
    @property
    def created_at(self) -> str:
        return self._info.get("created_at", "")
    
    @property
    def version(self) -> str:
        return self._info.get("version", "1.0.0")
    
    @property
    def description(self) -> str:
        return self._info.get("description", "")
    
    @property
    def size_bytes(self) -> int:
        """Get backup size in bytes"""
        if self.path.is_dir():
            total_size = 0
            for file_path in self.path.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            return total_size
        elif self.path.is_file() and self.path.suffix == '.zip':
            return self.path.stat().st_size
        return 0
    
    @property
    def size_mb(self) -> float:
        """Get backup size in MB"""
        return round(self.size_bytes / 1024 / 1024, 2)


class BackupManager:
    """Manages backup creation and restoration"""
    
    def __init__(self, safe_paths: SafePaths):
        self.safe_paths = safe_paths
        self.backup_dir = safe_paths.get_backup_dir()
        self.logger = get_logger("backup", LogComponent.AUDIT)
        self.masker = get_masker()
    
    def create_backup(self, 
                     backup_type: str = BackupType.FULL,
                     description: str = "",
                     include_logs: bool = False,
                     compress: bool = True) -> Optional[Path]:
        """Create a backup"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{backup_type}_{timestamp}"
            
            if compress:
                backup_path = self.backup_dir / f"{backup_name}.zip"
                return self._create_compressed_backup(backup_path, backup_type, description, include_logs)
            else:
                backup_path = self.backup_dir / backup_name
                return self._create_directory_backup(backup_path, backup_type, description, include_logs)
                
        except Exception as e:
            self.logger.error("Failed to create backup", error=str(e), backup_type=backup_type)
            return None
    
    def _create_compressed_backup(self, 
                                 backup_path: Path, 
                                 backup_type: str, 
                                 description: str,
                                 include_logs: bool) -> Optional[Path]:
        """Create compressed backup"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / "backup_content"
            temp_path.mkdir()
            
            # Create backup content
            if not self._create_backup_content(temp_path, backup_type, include_logs):
                return None
            
            # Create backup info
            backup_info = self._create_backup_info(backup_type, description, compress=True)
            info_file = temp_path / "backup_info.json"
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(backup_info, f, indent=2, ensure_ascii=False)
            
            # Create ZIP archive
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in temp_path.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(temp_path)
                        zipf.write(file_path, arcname)
            
            self.logger.info("Compressed backup created", 
                           backup_path=str(backup_path),
                           backup_type=backup_type,
                           size_mb=round(backup_path.stat().st_size / 1024 / 1024, 2))
            
            return backup_path
    
    def _create_directory_backup(self, 
                               backup_path: Path, 
                               backup_type: str, 
                               description: str,
                               include_logs: bool) -> Optional[Path]:
        """Create directory backup"""
        backup_path.mkdir(parents=True, exist_ok=True)
        
        if not self._create_backup_content(backup_path, backup_type, include_logs):
            return None
        
        # Create backup info
        backup_info = self._create_backup_info(backup_type, description, compress=False)
        info_file = backup_path / "backup_info.json"
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(backup_info, f, indent=2, ensure_ascii=False)
        
        self.logger.info("Directory backup created", 
                       backup_path=str(backup_path),
                       backup_type=backup_type)
        
        return backup_path
    
    def _create_backup_content(self, 
                              backup_path: Path, 
                              backup_type: str, 
                              include_logs: bool) -> bool:
        """Create backup content based on type"""
        try:
            if backup_type == BackupType.FULL:
                return self._backup_full(backup_path, include_logs)
            elif backup_type == BackupType.CONFIG:
                return self._backup_config(backup_path)
            elif backup_type == BackupType.STATE:
                return self._backup_state(backup_path)
            elif backup_type == BackupType.LOGS:
                return self._backup_logs(backup_path)
            elif backup_type == BackupType.CUSTOM:
                return self._backup_custom(backup_path)
            else:
                self.logger.error("Unknown backup type", backup_type=backup_type)
                return False
        except Exception as e:
            self.logger.error("Failed to create backup content", error=str(e))
            return False
    
    def _backup_full(self, backup_path: Path, include_logs: bool) -> bool:
        """Create full backup"""
        # Backup configuration
        if not self._backup_config(backup_path):
            return False
        
        # Backup state
        if not self._backup_state(backup_path):
            return False
        
        # Backup strategies
        if not self._backup_strategies(backup_path):
            return False
        
        # Backup profiles
        if not self._backup_profiles(backup_path):
            return False
        
        # Backup telemetry
        if not self._backup_telemetry(backup_path):
            return False
        
        # Backup logs (optional)
        if include_logs and not self._backup_logs(backup_path):
            return False
        
        return True
    
    def _backup_config(self, backup_path: Path) -> bool:
        """Backup configuration files"""
        config_dir = backup_path / "config"
        config_dir.mkdir(exist_ok=True)
        
        source_config = self.safe_paths.get_config_file()
        if source_config.exists():
            shutil.copy2(source_config, config_dir / "config.yaml")
        
        return True
    
    def _backup_state(self, backup_path: Path) -> bool:
        """Backup state files"""
        state_dir = backup_path / "state"
        state_dir.mkdir(exist_ok=True)
        
        # Copy state files
        state_files = [
            self.safe_paths.get_state_file(),
            self.safe_paths.get_current_file()
        ]
        
        for state_file in state_files:
            if state_file.exists():
                shutil.copy2(state_file, state_dir / state_file.name)
        
        return True
    
    def _backup_strategies(self, backup_path: Path) -> bool:
        """Backup strategies"""
        strategies_dir = backup_path / "strategies"
        strategies_dir.mkdir(exist_ok=True)
        
        source_strategies = self.safe_paths.get_strategies_dir()
        if source_strategies.exists():
            shutil.copytree(source_strategies, strategies_dir / "data", dirs_exist_ok=True)
        
        return True
    
    def _backup_profiles(self, backup_path: Path) -> bool:
        """Backup profiles"""
        profiles_dir = backup_path / "profiles"
        profiles_dir.mkdir(exist_ok=True)
        
        source_profiles = self.safe_paths.get_profiles_file()
        if source_profiles.exists():
            shutil.copy2(source_profiles, profiles_dir / "profiles.json")
        
        return True
    
    def _backup_telemetry(self, backup_path: Path) -> bool:
        """Backup telemetry data"""
        telemetry_dir = backup_path / "telemetry"
        telemetry_dir.mkdir(exist_ok=True)
        
        source_telemetry = self.safe_paths.get_telemetry_dir()
        if source_telemetry.exists():
            # Copy important telemetry files
            telemetry_files = [
                "strategy_runs.jsonl",
                "latest_strategy_ranking.json",
                "problem_domains.json"
            ]
            
            for telemetry_file in telemetry_files:
                source_file = source_telemetry / telemetry_file
                if source_file.exists():
                    shutil.copy2(source_file, telemetry_dir / telemetry_file)
        
        return True
    
    def _backup_logs(self, backup_path: Path) -> bool:
        """Backup log files"""
        logs_dir = backup_path / "logs"
        logs_dir.mkdir(exist_ok=True)
        
        source_logs = self.safe_paths.get_logs_dir()
        if source_logs.exists():
            # Copy recent log files (last 7 days)
            cutoff_time = datetime.now() - timedelta(days=7)
            
            for log_file in source_logs.glob("*"):
                if log_file.is_file() and log_file.stat().st_mtime > cutoff_time.timestamp():
                    shutil.copy2(log_file, logs_dir / log_file.name)
        
        return True
    
    def _backup_custom(self, backup_path: Path) -> bool:
        """Backup custom data (implementation specific)"""
        # This can be extended for custom backup needs
        return True
    
    def _create_backup_info(self, backup_type: str, description: str, compress: bool) -> Dict[str, Any]:
        """Create backup information"""
        return {
            "backup_type": backup_type,
            "created_at": datetime.now().isoformat(),
            "version": "1.0.0",
            "description": description or f"{backup_type} backup created on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "compress": compress,
            "created_by": "DedZapret Manager",
            "system_info": {
                "platform": self.safe_paths.is_windows(),
                "portable": self.safe_paths.is_portable(),
                "base_dir": str(self.safe_paths.get_base_dir())
            }
        }
    
    def restore_backup(self, backup_path: Union[str, Path], 
                      restore_components: Optional[List[str]] = None) -> bool:
        """Restore from backup"""
        try:
            backup_path = Path(backup_path)
            
            if not backup_path.exists():
                self.logger.error("Backup file not found", backup_path=str(backup_path))
                return False
            
            # Get backup info
            backup_info = BackupInfo(backup_path)
            
            # Extract backup if compressed
            if backup_path.suffix == '.zip':
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)
                    with zipfile.ZipFile(backup_path, 'r') as zipf:
                        zipf.extractall(temp_path)
                    
                    return self._restore_from_directory(temp_path, backup_info, restore_components)
            else:
                return self._restore_from_directory(backup_path, backup_info, restore_components)
                
        except Exception as e:
            self.logger.error("Failed to restore backup", error=str(e))
            return False
    
    def _restore_from_directory(self, 
                              backup_dir: Path, 
                              backup_info: BackupInfo,
                              restore_components: Optional[List[str]]) -> bool:
        """Restore from extracted backup directory"""
        try:
            # Determine what to restore
            if restore_components is None:
                restore_components = ["config", "state", "strategies", "profiles", "telemetry", "logs"]
            
            # Create current backup before restore
            self.create_backup(BackupType.FULL, "Pre-restore backup")
            
            success = True
            
            # Restore each component
            for component in restore_components:
                component_dir = backup_dir / component
                if not component_dir.exists():
                    continue
                
                if component == "config":
                    success &= self._restore_config(component_dir)
                elif component == "state":
                    success &= self._restore_state(component_dir)
                elif component == "strategies":
                    success &= self._restore_strategies(component_dir)
                elif component == "profiles":
                    success &= self._restore_profiles(component_dir)
                elif component == "telemetry":
                    success &= self._restore_telemetry(component_dir)
                elif component == "logs":
                    success &= self._restore_logs(component_dir)
            
            self.logger.info("Backup restored", 
                           backup_info=backup_info.created_at,
                           components=restore_components,
                           success=success)
            
            return success
            
        except Exception as e:
            self.logger.error("Failed to restore from directory", error=str(e))
            return False
    
    def _restore_config(self, config_dir: Path) -> bool:
        """Restore configuration"""
        source_config = config_dir / "config.yaml"
        if source_config.exists():
            target_config = self.safe_paths.get_config_file()
            target_config.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_config, target_config)
        return True
    
    def _restore_state(self, state_dir: Path) -> bool:
        """Restore state"""
        target_state_dir = self.safe_paths.get_state_dir()
        target_state_dir.mkdir(parents=True, exist_ok=True)
        
        for state_file in state_dir.glob("*"):
            if state_file.is_file():
                shutil.copy2(state_file, target_state_dir / state_file.name)
        
        return True
    
    def _restore_strategies(self, strategies_dir: Path) -> bool:
        """Restore strategies"""
        source_data = strategies_dir / "data"
        if source_data.exists():
            target_strategies = self.safe_paths.get_strategies_dir()
            target_strategies.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source_data, target_strategies, dirs_exist_ok=True)
        return True
    
    def _restore_profiles(self, profiles_dir: Path) -> bool:
        """Restore profiles"""
        source_profiles = profiles_dir / "profiles.json"
        if source_profiles.exists():
            target_profiles = self.safe_paths.get_profiles_file()
            target_profiles.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_profiles, target_profiles)
        return True
    
    def _restore_telemetry(self, telemetry_dir: Path) -> bool:
        """Restore telemetry"""
        target_telemetry = self.safe_paths.get_telemetry_dir()
        target_telemetry.mkdir(parents=True, exist_ok=True)
        
        for telemetry_file in telemetry_dir.glob("*"):
            if telemetry_file.is_file():
                shutil.copy2(telemetry_file, target_telemetry / telemetry_file.name)
        
        return True
    
    def _restore_logs(self, logs_dir: Path) -> bool:
        """Restore logs"""
        target_logs = self.safe_paths.get_logs_dir()
        target_logs.mkdir(parents=True, exist_ok=True)
        
        for log_file in logs_dir.glob("*"):
            if log_file.is_file():
                shutil.copy2(log_file, target_logs / log_file.name)
        
        return True
    
    def list_backups(self, backup_type: Optional[str] = None) -> List[BackupInfo]:
        """List available backups"""
        backups = []
        
        # List directory backups
        for backup_dir in self.backup_dir.iterdir():
            if backup_dir.is_dir() and backup_dir.name.startswith("backup_"):
                if backup_type is None or backup_type in backup_dir.name:
                    backups.append(BackupInfo(backup_dir))
        
        # List compressed backups
        for backup_file in self.backup_dir.glob("backup_*.zip"):
            if backup_type is None or backup_type in backup_file.name:
                backups.append(BackupInfo(backup_file))
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda b: b.created_at, reverse=True)
        return backups
    
    def delete_backup(self, backup_path: Union[str, Path]) -> bool:
        """Delete a backup"""
        try:
            backup_path = Path(backup_path)
            
            if backup_path.is_dir():
                shutil.rmtree(backup_path)
            elif backup_path.is_file():
                backup_path.unlink()
            else:
                return False
            
            self.logger.info("Backup deleted", backup_path=str(backup_path))
            return True
            
        except Exception as e:
            self.logger.error("Failed to delete backup", error=str(e))
            return False
    
    def cleanup_old_backups(self, days_to_keep: int = 30, max_backups: int = 10) -> int:
        """Clean up old backups"""
        try:
            cutoff_time = datetime.now() - timedelta(days=days_to_keep)
            backups = self.list_backups()
            
            deleted_count = 0
            
            # Delete backups older than cutoff time
            for backup in backups:
                try:
                    backup_time = datetime.fromisoformat(backup.created_at)
                    if backup_time < cutoff_time:
                        if self.delete_backup(backup.path):
                            deleted_count += 1
                except Exception:
                    continue
            
            # If still too many backups, delete oldest
            remaining_backups = self.list_backups()
            if len(remaining_backups) > max_backups:
                excess_backups = remaining_backups[max_backups:]
                for backup in excess_backups:
                    if self.delete_backup(backup.path):
                        deleted_count += 1
            
            self.logger.info("Old backups cleaned", 
                           deleted_count=deleted_count,
                           days_to_keep=days_to_keep,
                           max_backups=max_backups)
            
            return deleted_count
            
        except Exception as e:
            self.logger.error("Failed to cleanup old backups", error=str(e))
            return 0
    
    def get_backup_summary(self) -> Dict[str, Any]:
        """Get backup summary"""
        backups = self.list_backups()
        
        total_size = sum(b.size_bytes for b in backups)
        backup_types = {}
        
        for backup in backups:
            backup_type = backup.backup_type
            backup_types[backup_type] = backup_types.get(backup_type, 0) + 1
        
        return {
            "total_backups": len(backups),
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "backup_types": backup_types,
            "newest_backup": backups[0].created_at if backups else None,
            "oldest_backup": backups[-1].created_at if backups else None
        }
