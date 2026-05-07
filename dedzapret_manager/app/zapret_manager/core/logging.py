"""
Logging system for DedZapret Manager

Provides structured logging with multiple handlers, rotation,
and component-specific loggers.
"""

import logging
import logging.handlers
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum

from .paths import SafePaths


class LogLevel(Enum):
    """Log levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogComponent(Enum):
    """Log components"""
    APP = "app"
    RUNTIME = "runtime"
    STRATEGY = "strategy"
    PROXY = "proxy"
    NETWORK = "network"
    UI = "ui"
    AUDIT = "audit"
    TEST = "test"


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "component": getattr(record, 'component', 'app'),
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'strategy_id'):
            log_entry["strategy_id"] = record.strategy_id
        if hasattr(record, 'process_id'):
            log_entry["process_id"] = record.process_id
        if hasattr(record, 'user_action'):
            log_entry["user_action"] = record.user_action
        if hasattr(record, 'duration_ms'):
            log_entry["duration_ms"] = record.duration_ms
        if hasattr(record, 'error_code'):
            log_entry["error_code"] = record.error_code
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    """Text formatter for human-readable logs"""
    
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s [%(levelname)-8s] [%(component)-8s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def format(self, record: logging.LogRecord) -> str:
        # Add component to record
        if not hasattr(record, 'component'):
            record.component = getattr(record, 'component', 'app')
        return super().format(record)


class DedZapretLogger:
    """Enhanced logger with component support"""
    
    def __init__(self, name: str, component: LogComponent = LogComponent.APP):
        self.logger = logging.getLogger(f"dedzapret.{component.value}.{name}")
        self.component = component
        self.logger.setLevel(logging.DEBUG)
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self._log(logging.CRITICAL, message, **kwargs)
    
    def exception(self, message: str, **kwargs):
        """Log exception with traceback"""
        kwargs['exc_info'] = True
        self._log(logging.ERROR, message, **kwargs)
    
    def _log(self, level: int, message: str, **kwargs):
        """Internal logging method"""
        extra = {'component': self.component.value}
        
        # Add extra fields
        for key, value in kwargs.items():
            if key != 'exc_info':
                extra[key] = value
        
        self.logger.log(level, message, extra=extra, exc_info=kwargs.get('exc_info', False))


class LoggingManager:
    """Manages logging configuration and handlers"""
    
    def __init__(self, safe_paths: SafePaths):
        self.safe_paths = safe_paths
        self.logs_dir = safe_paths.get_logs_dir()
        self.app_log_file = safe_paths.get_app_log_file()
        self.runtime_log_file = safe_paths.get_runtime_log_file()
        self.session_log_file = self.logs_dir / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        
        self._configured = False
        self._loggers: Dict[str, DedZapretLogger] = {}
    
    def configure_logging(self, 
                         log_level: str = "INFO",
                         enable_console: bool = True,
                         enable_file: bool = True,
                         enable_json: bool = True,
                         max_file_size_mb: int = 10,
                         backup_count: int = 5) -> bool:
        """Configure logging system"""
        try:
            if self._configured:
                return True
            
            # Create logs directory
            self.logs_dir.mkdir(parents=True, exist_ok=True)
            
            # Configure root logger
            root_logger = logging.getLogger("dedzapret")
            root_logger.setLevel(getattr(logging, log_level.upper()))
            
            # Clear existing handlers
            root_logger.handlers.clear()
            
            # Console handler
            if enable_console:
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setLevel(getattr(logging, log_level.upper()))
                console_handler.setFormatter(TextFormatter())
                root_logger.addHandler(console_handler)
            
            # File handlers
            if enable_file:
                # Main app log (text format)
                app_handler = logging.handlers.RotatingFileHandler(
                    self.app_log_file,
                    maxBytes=max_file_size_mb * 1024 * 1024,
                    backupCount=backup_count,
                    encoding='utf-8'
                )
                app_handler.setLevel(getattr(logging, log_level.upper()))
                app_handler.setFormatter(TextFormatter())
                root_logger.addHandler(app_handler)
                
                # Runtime log (text format)
                runtime_handler = logging.handlers.RotatingFileHandler(
                    self.runtime_log_file,
                    maxBytes=max_file_size_mb * 1024 * 1024,
                    backupCount=backup_count,
                    encoding='utf-8'
                )
                runtime_handler.setLevel(logging.DEBUG)
                runtime_handler.setFormatter(TextFormatter())
                runtime_handler.addFilter(lambda record: getattr(record, 'component', '') == 'runtime')
                root_logger.addHandler(runtime_handler)
                
                # Session log (JSON format)
                if enable_json:
                    session_handler = logging.handlers.RotatingFileHandler(
                        self.session_log_file,
                        maxBytes=max_file_size_mb * 1024 * 1024,
                        backupCount=backup_count,
                        encoding='utf-8'
                    )
                    session_handler.setLevel(logging.DEBUG)
                    session_handler.setFormatter(JSONFormatter())
                    root_logger.addHandler(session_handler)
            
            self._configured = True
            self._get_logger(LogComponent.APP).info("Logging system initialized", 
                                                   log_level=log_level,
                                                   console=enable_console,
                                                   file=enable_file,
                                                   json=enable_json)
            return True
            
        except Exception as e:
            print(f"Failed to configure logging: {e}")
            return False
    
    def get_logger(self, name: str, component: LogComponent = LogComponent.APP) -> DedZapretLogger:
        """Get logger for specific component"""
        key = f"{component.value}.{name}"
        if key not in self._loggers:
            self._loggers[key] = DedZapretLogger(name, component)
        return self._loggers[key]
    
    def _get_logger(self, component: LogComponent) -> DedZapretLogger:
        """Get logger for logging manager itself"""
        return self.get_logger("logging_manager", component)
    
    def set_log_level(self, level: str) -> bool:
        """Change log level for all handlers"""
        try:
            log_level = getattr(logging, level.upper())
            root_logger = logging.getLogger("dedzapret")
            root_logger.setLevel(log_level)
            
            for handler in root_logger.handlers:
                handler.setLevel(log_level)
            
            self._get_logger(LogComponent.APP).info("Log level changed", new_level=level)
            return True
        except Exception:
            return False
    
    def rotate_logs(self) -> bool:
        """Manually rotate log files"""
        try:
            root_logger = logging.getLogger("dedzapret")
            for handler in root_logger.handlers:
                if isinstance(handler, logging.handlers.RotatingFileHandler):
                    handler.doRollover()
            
            self._get_logger(LogComponent.APP).info("Log files rotated")
            return True
        except Exception as e:
            self._get_logger(LogComponent.APP).error("Failed to rotate logs", error=str(e))
            return False
    
    def get_log_files_info(self) -> Dict[str, Any]:
        """Get information about log files"""
        log_files = {}
        
        log_file_paths = [
            ("app", self.app_log_file),
            ("runtime", self.runtime_log_file),
            ("session", self.session_log_file)
        ]
        
        for name, path in log_file_paths:
            if path.exists():
                stat = path.stat()
                log_files[name] = {
                    "path": str(path),
                    "size_bytes": stat.st_size,
                    "size_mb": round(stat.st_size / 1024 / 1024, 2),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                }
            else:
                log_files[name] = {
                    "path": str(path),
                    "exists": False
                }
        
        return log_files
    
    def cleanup_old_logs(self, days_to_keep: int = 30) -> bool:
        """Clean up old log files"""
        try:
            cutoff_time = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
            deleted_count = 0
            
            for log_file in self.logs_dir.glob("*.log*"):
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    deleted_count += 1
            
            for log_file in self.logs_dir.glob("*.jsonl*"):
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    deleted_count += 1
            
            self._get_logger(LogComponent.APP).info("Old log files cleaned", 
                                                   deleted_count=deleted_count,
                                                   days_to_keep=days_to_keep)
            return True
        except Exception as e:
            self._get_logger(LogComponent.APP).error("Failed to cleanup old logs", error=str(e))
            return False
    
    def export_logs(self, output_file: Optional[Path] = None) -> Optional[Path]:
        """Export all logs to a single file"""
        try:
            if output_file is None:
                output_file = self.logs_dir / f"exported_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"DedZapret Manager Log Export\n")
                f.write(f"Generated: {datetime.now().isoformat()}\n")
                f.write("=" * 80 + "\n\n")
                
                # Export main app log
                if self.app_log_file.exists():
                    f.write(f"APP LOG ({self.app_log_file}):\n")
                    f.write("-" * 40 + "\n")
                    f.write(self.app_log_file.read_text(encoding='utf-8'))
                    f.write("\n\n")
                
                # Export runtime log
                if self.runtime_log_file.exists():
                    f.write(f"RUNTIME LOG ({self.runtime_log_file}):\n")
                    f.write("-" * 40 + "\n")
                    f.write(self.runtime_log_file.read_text(encoding='utf-8'))
                    f.write("\n\n")
                
                # Export session log
                if self.session_log_file.exists():
                    f.write(f"SESSION LOG ({self.session_log_file}):\n")
                    f.write("-" * 40 + "\n")
                    f.write(self.session_log_file.read_text(encoding='utf-8'))
                    f.write("\n\n")
            
            self._get_logger(LogComponent.APP).info("Logs exported", output_file=str(output_file))
            return output_file
            
        except Exception as e:
            self._get_logger(LogComponent.APP).error("Failed to export logs", error=str(e))
            return None


# Global instance for singleton pattern
_logging_manager_instance: Optional[LoggingManager] = None


def get_logging_manager() -> LoggingManager:
    """Get global LoggingManager instance"""
    global _logging_manager_instance
    if _logging_manager_instance is None:
        raise RuntimeError("LoggingManager not initialized. Call init_logging() first.")
    return _logging_manager_instance


def get_logger(name: str = "default", component: LogComponent = LogComponent.APP) -> DedZapretLogger:
    """Get logger for specific component"""
    return get_logging_manager().get_logger(name, component)


def init_logging(safe_paths: SafePaths, 
                log_level: str = "INFO",
                enable_console: bool = True,
                enable_file: bool = True,
                enable_json: bool = True) -> LoggingManager:
    """Initialize global logging system"""
    global _logging_manager_instance
    _logging_manager_instance = LoggingManager(safe_paths)
    _logging_manager_instance.configure_logging(
        log_level=log_level,
        enable_console=enable_console,
        enable_file=enable_file,
        enable_json=enable_json
    )
    return _logging_manager_instance
