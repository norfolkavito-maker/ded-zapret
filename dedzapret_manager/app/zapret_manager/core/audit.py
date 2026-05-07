"""
Audit system for DedZapret Manager

Tracks all user actions, system events, and changes
for security and diagnostic purposes.
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
import uuid

from .paths import SafePaths
from .logging import get_logger, LogComponent


class AuditEventType(Enum):
    """Audit event types"""
    # User actions
    USER_ACTION = "user_action"
    STRATEGY_CHANGE = "strategy_change"
    PROFILE_CHANGE = "profile_change"
    CONFIG_CHANGE = "config_change"
    
    # System events
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    RUNTIME_START = "runtime_start"
    RUNTIME_STOP = "runtime_stop"
    RUNTIME_CRASH = "runtime_crash"
    
    # Network events
    PROXY_START = "proxy_start"
    PROXY_STOP = "proxy_stop"
    NETWORK_CHANGE = "network_change"
    DNS_CHANGE = "dns_change"
    HOSTS_CHANGE = "hosts_change"
    
    # Security events
    LOGIN_ATTEMPT = "login_attempt"
    PERMISSION_ERROR = "permission_error"
    SECURITY_VIOLATION = "security_violation"
    
    # Data events
    DATA_IMPORT = "data_import"
    DATA_EXPORT = "data_export"
    BACKUP_CREATE = "backup_create"
    BACKUP_RESTORE = "backup_restore"
    
    # Update events
    UPDATE_CHECK = "update_check"
    UPDATE_DOWNLOAD = "update_download"
    UPDATE_INSTALL = "update_install"
    
    # Error events
    ERROR_OCCURRED = "error_occurred"
    WARNING_ISSUED = "warning_issued"
    
    # Test events
    TEST_STARTED = "test_started"
    TEST_COMPLETED = "test_completed"
    TEST_FAILED = "test_failed"


class AuditEvent:
    """Single audit event"""
    
    def __init__(self, 
                 event_type: AuditEventType,
                 message: str,
                 details: Optional[Dict[str, Any]] = None,
                 user_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 severity: str = "info"):
        self.id = str(uuid.uuid4())
        self.timestamp = datetime.now().isoformat()
        self.event_type = event_type.value
        self.message = message
        self.details = details or {}
        self.user_id = user_id or "system"
        self.session_id = session_id or self._get_session_id()
        self.severity = severity  # info, warning, error, critical
        
        # Add system context
        self._add_system_context()
    
    def _get_session_id(self) -> str:
        """Get or create session ID"""
        # In a real implementation, this would be stored in session state
        return "session_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def _add_system_context(self):
        """Add system context to event"""
        import platform
        import os
        
        self.details.update({
            "platform": platform.system(),
            "platform_version": platform.version(),
            "python_version": platform.python_version(),
            "working_directory": os.getcwd(),
            "process_id": os.getpid()
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "message": self.message,
            "details": self.details,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "severity": self.severity
        }
    
    def to_json_line(self) -> str:
        """Convert event to JSON line for file storage"""
        return json.dumps(self.to_dict(), ensure_ascii=False, separators=(',', ':'))


class AuditLogger:
    """Manages audit logging and event tracking"""
    
    def __init__(self, safe_paths: SafePaths):
        self.safe_paths = safe_paths
        self.audit_file = safe_paths.get_audit_file()
        self.logger = get_logger("audit", LogComponent.AUDIT)
        self._session_id = self._generate_session_id()
        self._buffer: List[AuditEvent] = []
        self._buffer_size = 100
        self._auto_flush = True
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    def log_event(self, 
                  event_type: AuditEventType,
                  message: str,
                  details: Optional[Dict[str, Any]] = None,
                  severity: str = "info",
                  user_id: Optional[str] = None) -> bool:
        """Log an audit event"""
        try:
            event = AuditEvent(
                event_type=event_type,
                message=message,
                details=details,
                user_id=user_id,
                session_id=self._session_id,
                severity=severity
            )
            
            # Add to buffer
            self._buffer.append(event)
            
            # Log to application logger
            log_method = getattr(self.logger, severity, self.logger.info)
            log_method(f"Audit: {message}", 
                      event_type=event_type.value,
                      event_id=event.id,
                      details=details)
            
            # Auto-flush if enabled
            if self._auto_flush and len(self._buffer) >= self._buffer_size:
                self.flush()
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to log audit event", error=str(e))
            return False
    
    def log_user_action(self, action: str, details: Optional[Dict[str, Any]] = None) -> bool:
        """Log user action"""
        return self.log_event(
            AuditEventType.USER_ACTION,
            f"User action: {action}",
            details,
            user_id="user"
        )
    
    def log_strategy_change(self, 
                          old_strategy: str, 
                          new_strategy: str,
                          profile_id: Optional[str] = None) -> bool:
        """Log strategy change"""
        return self.log_event(
            AuditEventType.STRATEGY_CHANGE,
            f"Strategy changed from {old_strategy} to {new_strategy}",
            {
                "old_strategy": old_strategy,
                "new_strategy": new_strategy,
                "profile_id": profile_id
            }
        )
    
    def log_profile_change(self, 
                          old_profile: str, 
                          new_profile: str) -> bool:
        """Log profile change"""
        return self.log_event(
            AuditEventType.PROFILE_CHANGE,
            f"Profile changed from {old_profile} to {new_profile}",
            {
                "old_profile": old_profile,
                "new_profile": new_profile
            }
        )
    
    def log_runtime_start(self, 
                         strategy_id: str, 
                         process_id: int,
                         command_line: List[str]) -> bool:
        """Log runtime start"""
        return self.log_event(
            AuditEventType.RUNTIME_START,
            f"Runtime started with strategy {strategy_id}",
            {
                "strategy_id": strategy_id,
                "process_id": process_id,
                "command_line": command_line
            }
        )
    
    def log_runtime_stop(self, 
                        strategy_id: str, 
                        process_id: int,
                        exit_code: Optional[int] = None) -> bool:
        """Log runtime stop"""
        return self.log_event(
            AuditEventType.RUNTIME_STOP,
            f"Runtime stopped for strategy {strategy_id}",
            {
                "strategy_id": strategy_id,
                "process_id": process_id,
                "exit_code": exit_code
            }
        )
    
    def log_runtime_crash(self, 
                         strategy_id: str, 
                         process_id: int,
                         error_message: str) -> bool:
        """Log runtime crash"""
        return self.log_event(
            AuditEventType.RUNTIME_CRASH,
            f"Runtime crashed for strategy {strategy_id}",
            {
                "strategy_id": strategy_id,
                "process_id": process_id,
                "error_message": error_message
            },
            severity="error"
        )
    
    def log_proxy_start(self, 
                       node_id: str, 
                       process_id: int) -> bool:
        """Log proxy start"""
        return self.log_event(
            AuditEventType.PROXY_START,
            f"Proxy started with node {node_id}",
            {
                "node_id": node_id,
                "process_id": process_id
            }
        )
    
    def log_proxy_stop(self, 
                      node_id: str, 
                      process_id: int) -> bool:
        """Log proxy stop"""
        return self.log_event(
            AuditEventType.PROXY_STOP,
            f"Proxy stopped for node {node_id}",
            {
                "node_id": node_id,
                "process_id": process_id
            }
        )
    
    def log_config_change(self, 
                         section: str, 
                         old_value: Any, 
                         new_value: Any) -> bool:
        """Log configuration change"""
        return self.log_event(
            AuditEventType.CONFIG_CHANGE,
            f"Configuration changed in {section}",
            {
                "section": section,
                "old_value": old_value,
                "new_value": new_value
            }
        )
    
    def log_security_violation(self, 
                              violation_type: str, 
                              details: Dict[str, Any]) -> bool:
        """Log security violation"""
        return self.log_event(
            AuditEventType.SECURITY_VIOLATION,
            f"Security violation: {violation_type}",
            {
                "violation_type": violation_type,
                **details
            },
            severity="critical"
        )
    
    def log_test_started(self, 
                        test_type: str, 
                        strategy_id: Optional[str] = None) -> bool:
        """Log test started"""
        return self.log_event(
            AuditEventType.TEST_STARTED,
            f"Test started: {test_type}",
            {
                "test_type": test_type,
                "strategy_id": strategy_id
            }
        )
    
    def log_test_completed(self, 
                          test_type: str, 
                          result: Dict[str, Any]) -> bool:
        """Log test completed"""
        return self.log_event(
            AuditEventType.TEST_COMPLETED,
            f"Test completed: {test_type}",
            {
                "test_type": test_type,
                "result": result
            }
        )
    
    def log_error(self, 
                 error_type: str, 
                 error_message: str,
                 details: Optional[Dict[str, Any]] = None) -> bool:
        """Log error event"""
        return self.log_event(
            AuditEventType.ERROR_OCCURRED,
            f"Error: {error_type} - {error_message}",
            {
                "error_type": error_type,
                "error_message": error_message,
                **(details or {})
            },
            severity="error"
        )
    
    def flush(self) -> bool:
        """Flush buffered events to file"""
        try:
            # Ensure audit directory exists
            self.audit_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Append buffered events to file
            with open(self.audit_file, 'a', encoding='utf-8') as f:
                for event in self._buffer:
                    f.write(event.to_json_line() + '\n')
            
            # Clear buffer
            self._buffer.clear()
            return True
            
        except Exception as e:
            self.logger.error("Failed to flush audit events", error=str(e))
            return False
    
    def get_events(self, 
                   limit: int = 100,
                   event_type: Optional[AuditEventType] = None,
                   session_id: Optional[str] = None,
                   severity: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get audit events with filtering"""
        try:
            events = []
            
            if not self.audit_file.exists():
                return events
            
            with open(self.audit_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        event_data = json.loads(line)
                        
                        # Apply filters
                        if event_type and event_data.get('event_type') != event_type.value:
                            continue
                        if session_id and event_data.get('session_id') != session_id:
                            continue
                        if severity and event_data.get('severity') != severity:
                            continue
                        
                        events.append(event_data)
                        
                        if len(events) >= limit:
                            break
                            
                    except json.JSONDecodeError:
                        continue
            
            # Return in reverse order (newest first)
            return list(reversed(events[-limit:]))
            
        except Exception as e:
            self.logger.error("Failed to get audit events", error=str(e))
            return []
    
    def get_session_events(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get events for current or specific session"""
        target_session = session_id or self._session_id
        return self.get_events(limit=1000, session_id=target_session)
    
    def get_event_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary of events in last N hours"""
        try:
            cutoff_time = datetime.now().timestamp() - (hours * 3600)
            
            events_by_type = {}
            events_by_severity = {}
            total_events = 0
            
            if not self.audit_file.exists():
                return {
                    "total_events": 0,
                    "events_by_type": {},
                    "events_by_severity": {},
                    "time_range_hours": hours
                }
            
            with open(self.audit_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        event_data = json.loads(line)
                        event_time = datetime.fromisoformat(event_data['timestamp']).timestamp()
                        
                        if event_time < cutoff_time:
                            continue
                        
                        total_events += 1
                        
                        # Count by type
                        event_type = event_data.get('event_type', 'unknown')
                        events_by_type[event_type] = events_by_type.get(event_type, 0) + 1
                        
                        # Count by severity
                        severity = event_data.get('severity', 'info')
                        events_by_severity[severity] = events_by_severity.get(severity, 0) + 1
                        
                    except (json.JSONDecodeError, ValueError, KeyError):
                        continue
            
            return {
                "total_events": total_events,
                "events_by_type": events_by_type,
                "events_by_severity": events_by_severity,
                "time_range_hours": hours
            }
            
        except Exception as e:
            self.logger.error("Failed to get event summary", error=str(e))
            return {
                "total_events": 0,
                "events_by_type": {},
                "events_by_severity": {},
                "time_range_hours": hours,
                "error": str(e)
            }
    
    def export_events(self, 
                     output_file: Optional[Path] = None,
                     hours: int = 24) -> Optional[Path]:
        """Export events to file"""
        try:
            if output_file is None:
                output_file = self.safe_paths.get_reports_dir() / f"audit_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            events = self.get_events(limit=10000)
            
            # Filter by time range
            cutoff_time = datetime.now().timestamp() - (hours * 3600)
            filtered_events = []
            
            for event in events:
                try:
                    event_time = datetime.fromisoformat(event['timestamp']).timestamp()
                    if event_time >= cutoff_time:
                        filtered_events.append(event)
                except (ValueError, KeyError):
                    continue
            
            export_data = {
                "export_time": datetime.now().isoformat(),
                "time_range_hours": hours,
                "total_events": len(filtered_events),
                "events": filtered_events
            }
            
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info("Audit events exported", 
                           output_file=str(output_file),
                           event_count=len(filtered_events))
            
            return output_file
            
        except Exception as e:
            self.logger.error("Failed to export audit events", error=str(e))
            return None
    
    def clear_old_events(self, days_to_keep: int = 30) -> bool:
        """Clear old audit events"""
        try:
            cutoff_time = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
            
            if not self.audit_file.exists():
                return True
            
            # Read current events
            current_events = []
            with open(self.audit_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        event_data = json.loads(line)
                        event_time = datetime.fromisoformat(event_data['timestamp']).timestamp()
                        
                        if event_time >= cutoff_time:
                            current_events.append(line)
                            
                    except (json.JSONDecodeError, ValueError, KeyError):
                        continue
            
            # Write back filtered events
            with open(self.audit_file, 'w', encoding='utf-8') as f:
                for event_line in current_events:
                    f.write(event_line + '\n')
            
            self.logger.info("Old audit events cleared", 
                           days_kept=days_to_keep,
                           events_remaining=len(current_events))
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to clear old audit events", error=str(e))
            return False


# Global instance for singleton pattern
_audit_logger_instance: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get global AuditLogger instance"""
    global _audit_logger_instance
    if _audit_logger_instance is None:
        raise RuntimeError("AuditLogger not initialized. Call init_audit_logger() first.")
    return _audit_logger_instance


def init_audit_logger(safe_paths: SafePaths) -> AuditLogger:
    """Initialize global AuditLogger instance"""
    global _audit_logger_instance
    _audit_logger_instance = AuditLogger(safe_paths)
    return _audit_logger_instance
