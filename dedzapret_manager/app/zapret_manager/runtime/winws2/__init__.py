"""
winws2 runtime module for DedZapret Manager

Provides winws2 detection, command building, and process
management functionality.
"""

from .detector import Winws2Detector, Winws2Info
from .command_model import Winws2CommandBuilder, CommandBuildResult
from .process import Winws2ProcessManager, ProcessInfo

__all__ = [
    'Winws2Detector', 'Winws2Info',
    'Winws2CommandBuilder', 'CommandBuildResult',
    'Winws2ProcessManager', 'ProcessInfo'
]
