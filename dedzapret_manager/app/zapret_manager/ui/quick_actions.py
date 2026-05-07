"""
Quick actions for DedZapret Manager

Provides quick action definitions and availability checks.
"""

from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum


class ActionType(Enum):
    """Action type enumeration"""
    START_RUNTIME = "start_runtime"
    STOP_RUNTIME = "stop_runtime"
    RESTART_RUNTIME = "restart_runtime"
    TEST_CURRENT = "test_current"
    TEST_ALL = "test_all"
    AUTO_PICK_BEST = "auto_pick_best"
    CREATE_REPORT = "create_report"
    OPEN_LOGS = "open_logs"
    SETTINGS = "settings"
    UPDATE_RUNTIME = "update_runtime"
    IMPORT_STRATEGIES = "import_strategies"


@dataclass
class QuickAction:
    """Quick action definition"""
    id: str
    name: str
    description: str
    icon: str
    available: bool = True
    requires_admin: bool = False
    requires_runtime: bool = False
    category: str = "general"


def get_quick_actions() -> List[QuickAction]:
    """Get available quick actions"""
    return [
        QuickAction(
            id="start_runtime",
            name="Запустить Runtime",
            description="Запустить winws2 с текущей стратегией",
            icon="▶️",
            available=True,
            category="runtime"
        ),
        QuickAction(
            id="stop_runtime", 
            name="Остановить Runtime",
            description="Остановить winws2",
            icon="⏹️",
            available=True,
            category="runtime"
        ),
        QuickAction(
            id="restart_runtime",
            name="Перезапустить Runtime", 
            description="Перезапустить winws2",
            icon="🔄",
            available=True,
            category="runtime"
        ),
        QuickAction(
            id="test_current",
            name="Тестировать текущую",
            description="Протестировать текущую стратегию",
            icon="🧪",
            available=True,
            category="testing"
        ),
        QuickAction(
            id="test_all",
            name="Тестировать все",
            description="Протестировать все стратегии",
            icon="🧪",
            available=True,
            category="testing"
        ),
        QuickAction(
            id="auto_pick_best",
            name="Выбрать лучшую",
            description="Автоматически выбрать лучшую стратегию",
            icon="⭐",
            available=True,
            category="strategy"
        ),
        QuickAction(
            id="create_report",
            name="Создать отчёт",
            description="Создать отчёт об ошибках",
            icon="📄",
            available=True,
            category="diagnostics"
        ),
        QuickAction(
            id="open_logs",
            name="Открыть логи",
            description="Открыть директорию с логами",
            icon="📂",
            available=True,
            category="diagnostics"
        ),
        QuickAction(
            id="settings",
            name="Настройки",
            description="Открыть настройки программы",
            icon="⚙️",
            available=True,
            category="settings"
        ),
        QuickAction(
            id="update_runtime",
            name="Обновить Runtime",
            description="Обновить winws2 и компоненты",
            icon="⬇️",
            available=True,
            category="updates"
        ),
        QuickAction(
            id="import_strategies",
            name="Импорт стратегий",
            description="Импортировать стратегии из upstream",
            icon="📥",
            available=True,
            category="strategy"
        )
    ]


def get_available_actions() -> List[Dict[str, Any]]:
    """Get list of available actions with status"""
    actions = get_quick_actions()
    
    return [
        {
            "id": action.id,
            "name": action.name,
            "description": action.description,
            "icon": action.icon,
            "available": action.available,
            "category": action.category,
            "requires_admin": action.requires_admin,
            "requires_runtime": action.requires_runtime
        }
        for action in actions
    ]


def get_actions_by_category(category: str) -> List[QuickAction]:
    """Get actions by category"""
    return [action for action in get_quick_actions() if action.category == category]


def get_action_by_id(action_id: str) -> QuickAction:
    """Get action by ID"""
    for action in get_quick_actions():
        if action.id == action_id:
            return action
    return None
