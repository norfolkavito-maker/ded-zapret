"""
winws2 detector for DedZapret Manager

Detects winws2 executable, validates its presence,
checks version, and verifies runtime requirements.
"""

import os
import subprocess
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
import logging
import re

from ...core.paths import get_safe_paths
from ...core.security import DataMasker
from ...core.audit import get_audit_logger

logger = logging.getLogger(__name__)

@dataclass
class Winws2Info:
    """Information about detected winws2"""
    path: Path
    exists: bool
    version: str = "unknown"
    size: int = 0
    checksum: str = ""
    is_executable: bool = False
    last_modified: Optional[str] = None
    warnings: list = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []

class Winws2Detector:
    """Detects and validates winws2 runtime"""
    
    def __init__(self, safe_paths=None):
        """
        Initialize winws2 detector
        
        Args:
            safe_paths: SafePaths instance. If None, uses default.
        """
        self.safe_paths = safe_paths or get_safe_paths()
        self.audit_logger = get_audit_logger()
        self.masker = DataMasker()
        
        # Search paths in order of preference
        self.search_paths = [
            self.safe_paths.get_zapret_runtime_path("bin"),
            self.safe_paths.get_zapret_runtime_path(),  # Direct in zapret
            self.safe_paths.get_runtime_path("flowseal", "bin"),
            self.safe_paths.get_runtime_path("flowseal"),
            self.safe_paths.get_runtime_path(),  # General runtime
            Path.cwd() / "bin",  # Current directory
            Path.cwd(),  # Current directory
        ]
        
        # Expected winws2 executable names
        self.executable_names = ["winws2.exe", "winws2"]
    
    def detect_winws2(self) -> Winws2Info:
        """
        Detect winws2 executable
        
        Returns:
            Winws2Info with detection results
        """
        for search_path in self.search_paths:
            if not search_path.exists():
                continue
            
            for exe_name in self.executable_names:
                exe_path = search_path / exe_name
                
                if exe_path.exists() and exe_path.is_file():
                    info = self._analyze_executable(exe_path)
                    if info.exists and info.is_executable:
                        logger.info(f"Found winws2: {exe_path}")
                        self.audit_logger.log_action(
                            action="winws2_detected",
                            component="runtime_winws2",
                            success=True,
                            message=f"winws2 detected: {exe_path.name}",
                            details={
                                "path": str(exe_path),
                                "version": info.version,
                                "size": info.size
                            }
                        )
                        return info
        
        # Not found
        logger.warning("winws2 executable not found")
        return Winws2Info(
            path=Path("winws2.exe"),
            exists=False,
            warnings=["winws2 executable not found in any search path"]
        )
    
    def _analyze_executable(self, exe_path: Path) -> Winws2Info:
        """
        Analyze executable file
        
        Args:
            exe_path: Path to executable
            
        Returns:
            Winws2Info with analysis results
        """
        try:
            stat = exe_path.stat()
            
            # Basic info
            info = Winws2Info(
                path=exe_path,
                exists=True,
                size=stat.st_size,
                last_modified=str(stat.st_mtime),
                is_executable=os.access(exe_path, os.X_OK) if os.name != 'nt' else True
            )
            
            # Calculate checksum
            info.checksum = self._calculate_checksum(exe_path)
            
            # Try to get version
            info.version = self._get_version(exe_path)
            
            # Validate executable
            self._validate_executable(info)
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to analyze executable {exe_path}: {e}")
            return Winws2Info(
                path=exe_path,
                exists=True,
                warnings=[f"Failed to analyze: {e}"]
            )
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate checksum for {file_path}: {e}")
            return ""
    
    def _get_version(self, exe_path: Path) -> str:
        """Extract version from executable"""
        try:
            # Try to run with --version flag
            result = subprocess.run(
                [str(exe_path), "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            if result.returncode == 0:
                version_output = result.stdout.strip()
                
                # Parse version from output
                version_match = re.search(r'(\d+\.\d+\.\d+)', version_output)
                if version_match:
                    return version_match.group(1)
                
                # Look for version-like patterns
                version_patterns = [
                    r'v?(\d+\.\d+\.\d+)',
                    r'Version[:\s]+(\d+\.\d+\.\d+)',
                    r'winws2[:\s]+(\d+\.\d+\.\d+)'
                ]
                
                for pattern in version_patterns:
                    match = re.search(pattern, version_output, re.IGNORECASE)
                    if match:
                        return match.group(1)
                
                # Return first line if version parsing fails
                if version_output:
                    return version_output.split('\n')[0].strip()
            
            # Try file properties (Windows only)
            if os.name == 'nt':
                try:
                    import win32api
                    import win32con
                    import win32file
                    
                    # Get file version info
                    info = win32api.GetFileVersionInfo(str(exe_path), "\\")
                    if info and 'FileVersionString' in info:
                        return info['FileVersionString']
                except ImportError:
                    pass
                except Exception as e:
                    logger.debug(f"Failed to get file version: {e}")
            
        except subprocess.TimeoutExpired:
            logger.warning(f"Version check timed out for {exe_path}")
        except Exception as e:
            logger.debug(f"Failed to get version from {exe_path}: {e}")
        
        return "unknown"
    
    def _validate_executable(self, info: Winws2Info) -> None:
        """Validate executable for potential issues"""
        # Check file size
        if info.size < 1024:  # Less than 1KB
            info.warnings.append("Executable size is very small, may be incomplete")
        
        if info.size > 100 * 1024 * 1024:  # More than 100MB
            info.warnings.append("Executable size is very large")
        
        # Check if file is in use
        if os.name == 'nt':
            try:
                # Try to open file exclusively
                with open(info.path, 'rb') as f:
                    pass
            except PermissionError:
                info.warnings.append("Executable may be in use")
            except Exception:
                pass
        
        # Check path for problematic characters
        path_str = str(info.path)
        if self._has_problematic_chars(path_str):
            info.warnings.append("Path contains problematic characters")
    
    def _has_problematic_chars(self, text: str) -> bool:
        """Check for problematic characters in path"""
        problematic = ['<', '>', ':', '"', '|', '?', '*', '\x00']
        return any(char in text for char in problematic)
    
    def check_runtime_requirements(self) -> Dict[str, Any]:
        """
        Check all runtime requirements
        
        Returns:
            Dictionary with requirement status
        """
        requirements = {
            "winws2": False,
            "windivert": False,
            "admin_rights": False,
            "powershell": False,
            "x64_architecture": False,
            "runtime_directory": False,
            "required_files": {}
        }
        
        # Check winws2
        winws2_info = self.detect_winws2()
        requirements["winws2"] = winws2_info.exists
        requirements["winws2_info"] = winws2_info
        
        # Check WinDivert
        requirements["windivert"] = self._check_windivert()
        
        # Check admin rights
        requirements["admin_rights"] = self._check_admin_rights()
        
        # Check PowerShell
        requirements["powershell"] = self._check_powershell()
        
        # Check architecture
        requirements["x64_architecture"] = self._check_x64_architecture()
        
        # Check runtime directory
        requirements["runtime_directory"] = self._check_runtime_directory()
        
        # Check required files
        requirements["required_files"] = self._check_required_files()
        
        return requirements
    
    def _check_windivert(self) -> bool:
        """Check WinDivert driver availability"""
        try:
            # Check for WinDivert files
            windivert_paths = [
                self.safe_paths.get_zapret_runtime_path("WinDivert.dll"),
                self.safe_paths.get_zapret_runtime_path("WinDivert64.sys"),
                self.safe_paths.get_zapret_runtime_path("bin", "WinDivert.dll"),
                self.safe_paths.get_zapret_runtime_path("bin", "WinDivert64.sys")
            ]
            
            windivert_found = all(path.exists() for path in windivert_paths)
            
            if not windivert_found:
                logger.warning("WinDivert components not found")
                return False
            
            # Try to load WinDivert (basic check)
            try:
                import ctypes
                windivert_dll = windivert_paths[0]
                if windivert_dll.exists():
                    ctypes.WinDLL(str(windivert_dll))
                    logger.debug("WinDivert DLL loaded successfully")
                    return True
            except Exception as e:
                logger.warning(f"Failed to load WinDivert: {e}")
            
            return windivert_found
            
        except Exception as e:
            logger.error(f"Failed to check WinDivert: {e}")
            return False
    
    def _check_admin_rights(self) -> bool:
        """Check if running with administrator rights"""
        try:
            if os.name == 'nt':
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            else:
                return os.geteuid() == 0
        except Exception as e:
            logger.error(f"Failed to check admin rights: {e}")
            return False
    
    def _check_powershell(self) -> bool:
        """Check PowerShell availability"""
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Get-Host"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to check PowerShell: {e}")
            return False
    
    def _check_x64_architecture(self) -> bool:
        """Check if running on x64 architecture"""
        try:
            if os.name == 'nt':
                import platform
                return platform.machine().endswith('64')
            else:
                return platform.machine().endswith('64')
        except Exception as e:
            logger.error(f"Failed to check architecture: {e}")
            return False
    
    def _check_runtime_directory(self) -> bool:
        """Check if runtime directory structure exists"""
        try:
            runtime_dir = self.safe_paths.get_zapret_runtime_path()
            
            if not runtime_dir.exists():
                return False
            
            # Check for subdirectories
            required_dirs = ["bin", "lists", "fake", "utils"]
            for dir_name in required_dirs:
                dir_path = runtime_dir / dir_name
                if not dir_path.exists():
                    logger.warning(f"Missing runtime directory: {dir_path}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to check runtime directory: {e}")
            return False
    
    def _check_required_files(self) -> Dict[str, bool]:
        """Check for required runtime files"""
        required_files = {}
        
        # Common required files
        file_checks = {
            "hostlist": self.safe_paths.get_zapret_runtime_path("lists", "hostlist.txt"),
            "ipset": self.safe_paths.get_zapret_runtime_path("lists", "ipset.txt"),
            "fake_tls": self.safe_paths.get_zapret_runtime_path("fake", "tls_clienthello_www_google_com.bin"),
            "fake_quic": self.safe_paths.get_zapret_runtime_path("fake", "quic_initial_www_google_com.bin")
        }
        
        for file_name, file_path in file_checks.items():
            required_files[file_name] = file_path.exists()
            if not file_path.exists():
                logger.warning(f"Missing required file: {file_name}")
        
        return required_files
    
    def get_detection_summary(self) -> Dict[str, Any]:
        """
        Get complete detection summary
        
        Returns:
            Dictionary with detection summary
        """
        winws2_info = self.detect_winws2()
        requirements = self.check_runtime_requirements()
        
        return {
            "winws2": {
                "found": winws2_info.exists,
                "path": str(winws2_info.path),
                "version": winws2_info.version,
                "size": winws2_info.size,
                "checksum": winws2_info.checksum,
                "warnings": winws2_info.warnings
            },
            "requirements": requirements,
            "overall_status": self._calculate_overall_status(winws2_info, requirements),
            "recommendations": self._get_recommendations(winws2_info, requirements)
        }
    
    def _calculate_overall_status(self, winws2_info: Winws2Info, 
                                requirements: Dict[str, Any]) -> str:
        """Calculate overall runtime status"""
        if not winws2_info.exists:
            return "missing"
        
        if not requirements["admin_rights"]:
            return "no_admin"
        
        if not requirements["windivert"]:
            return "no_windivert"
        
        if not requirements["runtime_directory"]:
            return "no_runtime_dir"
        
        missing_files = sum(1 for exists in requirements["required_files"].values() if not exists)
        if missing_files > 2:
            return "missing_files"
        
        if winws2_info.warnings:
            return "warnings"
        
        return "ready"
    
    def _get_recommendations(self, winws2_info: Winws2Info, 
                           requirements: Dict[str, Any]) -> List[str]:
        """Get recommendations based on detection results"""
        recommendations = []
        
        if not winws2_info.exists:
            recommendations.append("Download and install Flowseal runtime")
        
        if not requirements["admin_rights"]:
            recommendations.append("Run as administrator")
        
        if not requirements["windivert"]:
            recommendations.append("Install WinDivert driver")
        
        if not requirements["runtime_directory"]:
            recommendations.append("Create runtime directory structure")
        
        missing_files = [name for name, exists in requirements["required_files"].items() if not exists]
        if missing_files:
            recommendations.append(f"Download missing files: {', '.join(missing_files)}")
        
        if winws2_info.warnings:
            recommendations.extend([f"Warning: {warning}" for warning in winws2_info.warnings])
        
        return recommendations
