"""
Runtime module for DedZapret Manager

Provides runtime management functionality for winws2
and other DPI desynchronisation tools.
"""

from .winws2.detector import Winws2Detector, Winws2Info
from .winws2.command_model import Winws2CommandBuilder, CommandBuildResult
from .winws2.process import Winws2ProcessManager, ProcessInfo

__all__ = [
    'Winws2Detector', 'Winws2Info',
    'Winws2CommandBuilder', 'CommandBuildResult',
    'Winws2ProcessManager', 'ProcessInfo'
]
