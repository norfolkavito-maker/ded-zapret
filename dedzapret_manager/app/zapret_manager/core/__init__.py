"""
Core module for DedZapret Manager

Provides core functionality including paths management, configuration,
state management, logging, audit, security, and backup operations.
"""

from .paths import SafePaths, get_safe_paths, init_safe_paths
from .config import ConfigManager, get_config_manager, init_config_manager
from .state import StateManager, get_state_manager, init_state_manager
from .logging import get_logger, init_logging
from .audit import AuditLogger, get_audit_logger, init_audit_logger
from .security import DataMasker, get_masker, init_masker
from .backup import BackupManager

__all__ = [
    'SafePaths', 'get_safe_paths', 'init_safe_paths',
    'ConfigManager', 'get_config_manager', 'init_config_manager',
    'StateManager', 'get_state_manager', 'init_state_manager',
    'get_logger', 'init_logging',
    'AuditLogger', 'get_audit_logger', 'init_audit_logger',
    'DataMasker', 'get_masker', 'init_masker',
    'BackupManager'
]
