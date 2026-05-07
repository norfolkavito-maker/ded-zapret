"""
UI module for DedZapret Manager

Provides user interface components including console,
tray, messages, and quick actions.
"""

from .messages import get_russian_messages
from .quick_actions import get_quick_actions

__all__ = [
    'get_russian_messages',
    'get_quick_actions'
]
