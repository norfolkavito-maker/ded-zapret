"""
winws2 process manager for DedZapret Manager

Manages winws2 process lifecycle: start, stop, monitor,
and health checking with proper cleanup and error handling.
"""

import os
import subprocess
import signal
import time
import threading
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
import logging
import psutil

from ...core.paths import get_safe_paths
from ...core.config import get_config_manager
from ...core.audit import get_audit_logger
from ...core.security import DataMasker

logger = logging.getLogger(__name__)

@dataclass
class ProcessInfo:
    """Information about running winws2 process"""
    pid: int
    command: List[str]
    start_time: float
    strategy_id: str
    status: str = "running"
    exit_code: Optional[int] = None
    cpu_percent: float = 0.0
    memory_mb: float = 0.0

class Winws2ProcessManager:
    """Manages winws2 process lifecycle"""
    
    def __init__(self, safe_paths=None):
        """
        Initialize process manager
        
        Args:
            safe_paths: SafePaths instance. If None, uses default.
        """
        self.safe_paths = safe_paths or get_safe_paths()
        self.config_manager = get_config_manager()
        self.audit_logger = get_audit_logger()
        self.masker = DataMasker()
        
        # Process tracking
        self._current_process: Optional[subprocess.Popen] = None
        self._process_info: Optional[ProcessInfo] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_monitoring = threading.Event()
        
        # Callbacks
        self._status_callbacks: List[Callable[[ProcessInfo], None]] = []
        
        # Load current state
        self._load_current_state()
    
    def _load_current_state(self) -> None:
        """Load current process state from storage"""
        try:
            current = self.config_manager.get_current()
            runtime_info = current.get("runtime", {})
            
            if runtime_info.get("active") and runtime_info.get("pid"):
                # Try to find if process is still running
                try:
                    process = psutil.Process(runtime_info["pid"])
                    if process.is_running() and "winws2" in process.name().lower():
                        self._process_info = ProcessInfo(
                            pid=runtime_info["pid"],
                            command=runtime_info.get("command", []),
                            start_time=runtime_info.get("start_time", time.time()),
                            strategy_id=runtime_info.get("strategy_id", ""),
                            status="running"
                        )
                        logger.info(f"Found running winws2 process: PID {runtime_info['pid']}")
                        self._start_monitoring()
                        return
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    logger.info("Previous winws2 process no longer running")
                    self._clear_current_state()
        except Exception as e:
            logger.error(f"Failed to load current state: {e}")
    
    def _save_current_state(self) -> None:
        """Save current process state to storage"""
        try:
            current = self.config_manager.get_current()
            
            if self._process_info:
                current["runtime"] = {
                    "active": True,
                    "pid": self._process_info.pid,
                    "command": self._process_info.command,
                    "start_time": self._process_info.start_time,
                    "strategy_id": self._process_info.strategy_id,
                    "status": self._process_info.status
                }
            else:
                current["runtime"] = {
                    "active": False,
                    "pid": None,
                    "command": [],
                    "start_time": None,
                    "strategy_id": None,
                    "status": "stopped"
                }
            
            self.config_manager.set_current(current)
            
        except Exception as e:
            logger.error(f"Failed to save current state: {e}")
    
    def _clear_current_state(self) -> None:
        """Clear current process state"""
        try:
            current = self.config_manager.get_current()
            current["runtime"] = {
                "active": False,
                "pid": None,
                "command": [],
                "start_time": None,
                "strategy_id": None,
                "status": "stopped"
            }
            self.config_manager.set_current(current)
        except Exception as e:
            logger.error(f"Failed to clear current state: {e}")
    
    def start_process(self, command: List[str], strategy_id: str) -> bool:
        """
        Start winws2 process
        
        Args:
            command: Command to execute
            strategy_id: Strategy ID being used
            
        Returns:
            True if started successfully, False otherwise
        """
        try:
            # Stop existing process if running
            if self.is_running():
                logger.warning("winws2 is already running, stopping first")
                if not self.stop_process():
                    return False
            
            # Validate command
            if not command or len(command) < 2:
                logger.error("Invalid command provided")
                return False
            
            # Check if executable exists
            executable = Path(command[0])
            if not executable.exists():
                logger.error(f"winws2 executable not found: {executable}")
                return False
            
            # Start process
            logger.info(f"Starting winws2 with strategy: {strategy_id}")
            
            # Use CREATE_NO_WINDOW on Windows to hide console
            creation_flags = 0
            if os.name == 'nt':
                creation_flags = subprocess.CREATE_NO_WINDOW
            
            self._current_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                creationflags=creation_flags,
                text=False
            )
            
            # Create process info
            self._process_info = ProcessInfo(
                pid=self._current_process.pid,
                command=command,
                start_time=time.time(),
                strategy_id=strategy_id,
                status="starting"
            )
            
            # Save state
            self._save_current_state()
            
            # Start monitoring
            self._start_monitoring()
            
            # Wait a bit to check if process started successfully
            time.sleep(1.0)
            
            if self._current_process.poll() is None:
                self._process_info.status = "running"
                self._save_current_state()
                
                self.audit_logger.log_runtime_start(
                    strategy_id=strategy_id,
                    process_id=self._process_info.pid,
                    command=command
                )
                
                logger.info(f"winws2 started successfully: PID {self._process_info.pid}")
                return True
            else:
                # Process exited immediately
                exit_code = self._current_process.returncode
                self._process_info.status = "failed"
                self._process_info.exit_code = exit_code
                self._save_current_state()
                
                self.audit_logger.log_runtime_stop(
                    strategy_id=strategy_id,
                    process_id=self._process_info.pid,
                    exit_code=exit_code
                )
                
                logger.error(f"winws2 exited immediately with code: {exit_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start winws2 process: {e}")
            self.audit_logger.log_action(
                action="runtime_start_failed",
                component="runtime_winws2",
                success=False,
                message=f"Failed to start winws2: {e}",
                strategy_id=strategy_id,
                details={"error": str(e)}
            )
            return False
    
    def stop_process(self, timeout: int = 10) -> bool:
        """
        Stop winws2 process
        
        Args:
            timeout: Timeout in seconds for graceful shutdown
            
        Returns:
            True if stopped successfully, False otherwise
        """
        try:
            if not self.is_running():
                logger.info("winws2 is not running")
                return True
            
            if not self._process_info:
                logger.error("No process info available")
                return False
            
            logger.info(f"Stopping winws2 process: PID {self._process_info.pid}")
            
            # Try graceful shutdown first
            if self._current_process:
                try:
                    self._current_process.terminate()
                except psutil.NoSuchProcess:
                    logger.info("Process already terminated")
                except Exception as e:
                    logger.warning(f"Failed to terminate process gracefully: {e}")
            
            # Wait for graceful shutdown
            start_time = time.time()
            while time.time() - start_time < timeout:
                if self._current_process and self._current_process.poll() is not None:
                    break
                time.sleep(0.5)
            
            # Force kill if still running
            if self._current_process and self._current_process.poll() is None:
                logger.warning("Process did not terminate gracefully, force killing")
                try:
                    self._current_process.kill()
                except psutil.NoSuchProcess:
                    logger.info("Process already terminated")
                except Exception as e:
                    logger.warning(f"Failed to kill process: {e}")
            
            # Wait for process to actually die
            if self._current_process:
                try:
                    self._current_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning("Process did not terminate within timeout")
            
            # Update status
            if self._process_info:
                self._process_info.status = "stopped"
                self._process_info.exit_code = self._current_process.returncode if self._current_process else None
                self._save_current_state()
                
                self.audit_logger.log_runtime_stop(
                    strategy_id=self._process_info.strategy_id,
                    process_id=self._process_info.pid,
                    exit_code=self._process_info.exit_code
                )
            
            # Stop monitoring
            self._stop_monitoring.set()
            if self._monitor_thread and self._monitor_thread.is_alive():
                self._monitor_thread.join(timeout=5)
            
            # Clear process references
            self._current_process = None
            self._process_info = None
            
            # Clear state
            self._clear_current_state()
            
            logger.info("winws2 stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop winws2 process: {e}")
            self.audit_logger.log_action(
                action="runtime_stop_failed",
                component="runtime_winws2",
                success=False,
                message=f"Failed to stop winws2: {e}",
                strategy_id=self._process_info.strategy_id if self._process_info else "unknown",
                details={"error": str(e)}
            )
            return False
    
    def is_running(self) -> bool:
        """
        Check if winws2 process is running
        
        Returns:
            True if process is running, False otherwise
        """
        if not self._process_info:
            return False
        
        try:
            if self._current_process:
                return self._current_process.poll() is None
            else:
                # Check by PID
                process = psutil.Process(self._process_info.pid)
                return process.is_running() and "winws2" in process.name().lower()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    
    def get_process_info(self) -> Optional[ProcessInfo]:
        """
        Get current process information
        
        Returns:
            ProcessInfo or None if not running
        """
        return self._process_info
    
    def _start_monitoring(self) -> None:
        """Start process monitoring thread"""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        
        self._stop_monitoring.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_process,
            daemon=True
        )
        self._monitor_thread.start()
    
    def _stop_monitoring(self) -> None:
        """Stop process monitoring thread"""
        self._stop_monitoring.set()
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)
    
    def _monitor_process(self) -> None:
        """Monitor process health and resource usage"""
        while not self._stop_monitoring.wait(1.0):
            try:
                if not self._process_info or not self.is_running():
                    break
                
                # Update resource usage
                try:
                    process = psutil.Process(self._process_info.pid)
                    self._process_info.cpu_percent = process.cpu_percent()
                    self._process_info.memory_mb = process.memory_info().rss / 1024 / 1024
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    self._process_info.status = "terminated"
                    break
                
                # Notify callbacks
                for callback in self._status_callbacks:
                    try:
                        callback(self._process_info)
                    except Exception as e:
                        logger.error(f"Status callback failed: {e}")
                
            except Exception as e:
                logger.error(f"Process monitoring error: {e}")
        
        # Final update
        if self._process_info:
            self._save_current_state()
    
    def add_status_callback(self, callback: Callable[[ProcessInfo], None]) -> None:
        """
        Add callback for status updates
        
        Args:
            callback: Function to call with ProcessInfo updates
        """
        self._status_callbacks.append(callback)
    
    def remove_status_callback(self, callback: Callable[[ProcessInfo], None]) -> None:
        """
        Remove status callback
        
        Args:
            callback: Function to remove
        """
        if callback in self._status_callbacks:
            self._status_callbacks.remove(callback)
    
    def restart_process(self, new_command: Optional[List[str]] = None, 
                      new_strategy_id: Optional[str] = None) -> bool:
        """
        Restart winws2 process
        
        Args:
            new_command: New command to use (optional)
            new_strategy_id: New strategy ID (optional)
            
        Returns:
            True if restarted successfully, False otherwise
        """
        try:
            # Get current info if not provided
            if not new_command and self._process_info:
                new_command = self._process_info.command
            
            if not new_strategy_id and self._process_info:
                new_strategy_id = self._process_info.strategy_id
            
            if not new_command or not new_strategy_id:
                logger.error("Cannot restart without command and strategy ID")
                return False
            
            logger.info("Restarting winws2 process")
            
            # Stop current process
            if not self.stop_process():
                return False
            
            # Small delay before restart
            time.sleep(1.0)
            
            # Start new process
            return self.start_process(new_command, new_strategy_id)
            
        except Exception as e:
            logger.error(f"Failed to restart winws2 process: {e}")
            return False
    
    def get_process_logs(self, lines: int = 100) -> Dict[str, List[str]]:
        """
        Get recent process logs
        
        Args:
            lines: Number of lines to retrieve
            
        Returns:
            Dictionary with stdout and stderr logs
        """
        logs = {"stdout": [], "stderr": []}
        
        if not self._current_process:
            return logs
        
        try:
            # Read stdout
            if self._current_process.stdout:
                stdout_lines = []
                for line in self._current_process.stdout.readlines(lines):
                    stdout_lines.append(line.decode('utf-8', errors='ignore').strip())
                logs["stdout"] = stdout_lines[-lines:]
            
            # Read stderr
            if self._current_process.stderr:
                stderr_lines = []
                for line in self._current_process.stderr.readlines(lines):
                    stderr_lines.append(line.decode('utf-8', errors='ignore').strip())
                logs["stderr"] = stderr_lines[-lines:]
                
        except Exception as e:
            logger.error(f"Failed to get process logs: {e}")
        
        return logs
    
    def get_resource_usage(self) -> Dict[str, Any]:
        """
        Get current resource usage
        
        Returns:
            Dictionary with resource usage information
        """
        if not self._process_info:
            return {"status": "not_running"}
        
        try:
            process = psutil.Process(self._process_info.pid)
            
            return {
                "status": "running",
                "pid": self._process_info.pid,
                "cpu_percent": self._process_info.cpu_percent,
                "memory_mb": self._process_info.memory_mb,
                "memory_percent": process.memory_percent(),
                "num_threads": process.num_threads(),
                "create_time": process.create_time(),
                "running_time": time.time() - self._process_info.start_time,
                "strategy_id": self._process_info.strategy_id
            }
            
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.error(f"Failed to get resource usage: {e}")
            return {"status": "error", "error": str(e)}
    
    def cleanup(self) -> None:
        """Clean up resources and stop monitoring"""
        try:
            # Stop process if running
            if self.is_running():
                logger.info("Cleaning up: stopping winws2 process")
                self.stop_process()
            
            # Stop monitoring
            self._stop_monitoring()
            
            # Clear callbacks
            self._status_callbacks.clear()
            
            logger.info("Process manager cleanup completed")
            
        except Exception as e:
            logger.error(f"Failed to cleanup process manager: {e}")
