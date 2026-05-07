"""
Paths management for DedZapret Manager

Handles all path operations including data directory creation,
runtime paths, and safe path resolution.
"""

import os
import sys
import platform
from pathlib import Path
from typing import Optional, Dict, Any
import json


class SafePaths:
    """Manages all paths used by DedZapret Manager"""
    
    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize paths manager
        
        Args:
            base_dir: Base directory for portable mode. If None, uses APPDATA
        """
        self._is_windows = platform.system() == "Windows"
        self._is_portable = base_dir is not None
        
        if base_dir:
            self._base_dir = Path(base_dir).resolve()
        else:
            if self._is_windows:
                app_data = os.environ.get("APPDATA", "")
                self._base_dir = Path(app_data) / "DedZapretData"
            else:
                # For non-Windows development/testing
                home = Path.home()
                self._base_dir = home / ".dedzapret"
        
        self._setup_directories()
    
    def _setup_directories(self):
        """Create all necessary directories"""
        directories = [
            self.get_app_data_dir(),
            self.get_config_dir(),
            self.get_state_dir(),
            self.get_logs_dir(),
            self.get_runtime_dir(),
            self.get_strategies_dir(),
            self.get_reports_dir(),
            self.get_backup_dir(),
            self.get_telemetry_dir(),
            self.get_upstreams_dir(),
            self.get_runtime_bin_dir(),
            self.get_runtime_lists_dir(),
            self.get_runtime_utils_dir(),
            self.get_runtime_fake_dir(),
            self.get_connectivity_dir(),
            self.get_singbox_dir(),
            self.get_temp_dir()
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def is_windows(self) -> bool:
        """Check if running on Windows"""
        return self._is_windows
    
    def is_portable(self) -> bool:
        """Check if running in portable mode"""
        return self._is_portable
    
    def get_base_dir(self) -> Path:
        """Get base data directory"""
        return self._base_dir
    
    def get_app_data_dir(self) -> Path:
        """Get main application data directory"""
        return self._base_dir
    
    def get_config_dir(self) -> Path:
        """Get configuration directory"""
        return self._base_dir / "config"
    
    def get_state_dir(self) -> Path:
        """Get state directory"""
        return self._base_dir / "state"
    
    def get_logs_dir(self) -> Path:
        """Get logs directory"""
        return self._base_dir / "logs"
    
    def get_runtime_dir(self) -> Path:
        """Get runtime directory"""
        return self._base_dir / "runtime"
    
    def get_strategies_dir(self) -> Path:
        """Get strategies directory"""
        return self._base_dir / "strategies"
    
    def get_reports_dir(self) -> Path:
        """Get reports directory"""
        return self._base_dir / "reports"
    
    def get_backup_dir(self) -> Path:
        """Get backup directory"""
        return self._base_dir / "backup"
    
    def get_telemetry_dir(self) -> Path:
        """Get telemetry directory"""
        return self._base_dir / "telemetry"
    
    def get_upstreams_dir(self) -> Path:
        """Get upstream sources directory"""
        return self._base_dir / "upstreams"
    
    def get_runtime_bin_dir(self) -> Path:
        """Get runtime binaries directory"""
        return self.get_runtime_dir() / "zapret" / "bin"
    
    def get_runtime_lists_dir(self) -> Path:
        """Get runtime lists directory"""
        return self.get_runtime_dir() / "zapret" / "lists"
    
    def get_runtime_utils_dir(self) -> Path:
        """Get runtime utils directory"""
        return self.get_runtime_dir() / "zapret" / "utils"
    
    def get_runtime_fake_dir(self) -> Path:
        """Get runtime fake files directory"""
        return self.get_runtime_dir() / "zapret" / "files" / "fake"
    
    def get_connectivity_dir(self) -> Path:
        """Get connectivity directory"""
        return self._base_dir / "connectivity"
    
    def get_singbox_dir(self) -> Path:
        """Get sing-box directory"""
        return self.get_connectivity_dir() / "singbox"
    
    def get_temp_dir(self) -> Path:
        """Get temporary directory"""
        return self._base_dir / "temp"
    
    def get_config_file(self) -> Path:
        """Get main configuration file path"""
        return self.get_config_dir() / "config.yaml"
    
    def get_state_file(self) -> Path:
        """Get state file path"""
        return self.get_state_dir() / "state.json"
    
    def get_current_file(self) -> Path:
        """Get current state file path"""
        return self.get_state_dir() / "current.json"
    
    def get_audit_file(self) -> Path:
        """Get audit log file path"""
        return self.get_logs_dir() / "audit.jsonl"
    
    def get_app_log_file(self) -> Path:
        """Get application log file path"""
        return self.get_logs_dir() / "app.log"
    
    def get_runtime_log_file(self) -> Path:
        """Get runtime log file path"""
        return self.get_logs_dir() / "runtime.log"
    
    def get_winws2_path(self) -> Path:
        """Get winws2.exe path"""
        return self.get_runtime_bin_dir() / "winws2.exe"
    
    def get_windivert_dll_path(self) -> Path:
        """Get WinDivert.dll path"""
        return self.get_runtime_bin_dir() / "WinDivert.dll"
    
    def get_windivert_sys_path(self) -> Path:
        """Get WinDivert64.sys path"""
        return self.get_runtime_bin_dir() / "WinDivert64.sys"
    
    def get_singbox_path(self) -> Path:
        """Get sing-box.exe path"""
        return self.get_singbox_dir() / "sing-box.exe"
    
    def get_strategies_file(self) -> Path:
        """Get strategies registry file path"""
        return self.get_strategies_dir() / "strategies.json"
    
    def get_profiles_file(self) -> Path:
        """Get profiles file path"""
        return self.get_config_dir() / "profiles.json"
    
    def get_problem_domains_file(self) -> Path:
        """Get problem domains file path"""
        return self.get_telemetry_dir() / "problem_domains.json"
    
    def get_strategy_runs_file(self) -> Path:
        """Get strategy runs file path"""
        return self.get_telemetry_dir() / "strategy_runs.jsonl"
    
    def get_latest_ranking_file(self) -> Path:
        """Get latest strategy ranking file path"""
        return self.get_telemetry_dir() / "latest_strategy_ranking.json"
    
    def validate_paths(self) -> Dict[str, Any]:
        """Validate all critical paths exist and are accessible"""
        validation = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        critical_paths = [
            self.get_config_dir(),
            self.get_state_dir(),
            self.get_logs_dir(),
            self.get_runtime_dir()
        ]
        
        for path in critical_paths:
            if not path.exists():
                validation["errors"].append(f"Missing directory: {path}")
                validation["valid"] = False
            elif not os.access(path, os.W_OK):
                validation["errors"].append(f"No write access: {path}")
                validation["valid"] = False
        
        # Check for non-ASCII characters in path (Windows issue)
        if self._is_windows:
            try:
                self.get_base_dir().encode('ascii')
            except UnicodeEncodeError:
                validation["warnings"].append(
                    "Base directory contains non-ASCII characters, may cause issues"
                )
        
        return validation
    
    def get_path_summary(self) -> Dict[str, str]:
        """Get summary of all important paths"""
        return {
            "base_dir": str(self.get_base_dir()),
            "config_file": str(self.get_config_file()),
            "state_file": str(self.get_state_file()),
            "current_file": str(self.get_current_file()),
            "log_dir": str(self.get_logs_dir()),
            "runtime_dir": str(self.get_runtime_dir()),
            "winws2_path": str(self.get_winws2_path()),
            "strategies_dir": str(self.get_strategies_dir()),
            "is_portable": str(self.is_portable()),
            "is_windows": str(self.is_windows())
        }


# Global instance for singleton pattern
_safe_paths_instance: Optional[SafePaths] = None


def get_safe_paths() -> SafePaths:
    """Get global SafePaths instance"""
    global _safe_paths_instance
    if _safe_paths_instance is None:
        raise RuntimeError("SafePaths not initialized. Call init_safe_paths() first.")
    return _safe_paths_instance


def init_safe_paths(base_dir: Optional[Path] = None) -> SafePaths:
    """Initialize global SafePaths instance"""
    global _safe_paths_instance
    _safe_paths_instance = SafePaths(base_dir)
    return _safe_paths_instance
