"""
UI messages for DedZapret Manager

Provides localized messages for different languages.
"""

from typing import Dict, Any


def get_russian_messages() -> Dict[str, str]:
    """Get Russian language messages"""
    return {
        # General
        "app_name": "DedZapret Manager",
        "version": "Версия",
        "status": "Статус",
        "error": "Ошибка",
        "warning": "Предупреждение",
        "info": "Информация",
        "success": "Успешно",
        "failed": "Не удалось",
        
        # Status messages
        "status_disabled": "Отключено",
        "status_enabled": "Включено",
        "status_running": "Работает",
        "status_stopped": "Остановлено",
        "status_error": "Ошибка",
        
        # Actions
        "action_start": "Запустить",
        "action_stop": "Остановить",
        "action_restart": "Перезапустить",
        "action_test": "Тестировать",
        "action_configure": "Настроить",
        "action_update": "Обновить",
        
        # Components
        "component_runtime": "Runtime",
        "component_proxy": "Прокси",
        "component_strategy": "Стратегия",
        "component_profile": "Профиль",
        
        # Messages
        "msg_runtime_started": "Runtime запущен",
        "msg_runtime_stopped": "Runtime остановлен",
        "msg_strategy_applied": "Стратегия применена",
        "msg_test_completed": "Тест завершён",
        "msg_no_errors": "Ошибок нет",
        "msg_check_logs": "Проверьте логи для деталей"
    }


def get_english_messages() -> Dict[str, str]:
    """Get English language messages"""
    return {
        # General
        "app_name": "DedZapret Manager",
        "version": "Version",
        "status": "Status",
        "error": "Error",
        "warning": "Warning",
        "info": "Information",
        "success": "Success",
        "failed": "Failed",
        
        # Status messages
        "status_disabled": "Disabled",
        "status_enabled": "Enabled",
        "status_running": "Running",
        "status_stopped": "Stopped",
        "status_error": "Error",
        
        # Actions
        "action_start": "Start",
        "action_stop": "Stop",
        "action_restart": "Restart",
        "action_test": "Test",
        "action_configure": "Configure",
        "action_update": "Update",
        
        # Components
        "component_runtime": "Runtime",
        "component_proxy": "Proxy",
        "component_strategy": "Strategy",
        "component_profile": "Profile",
        
        # Messages
        "msg_runtime_started": "Runtime started",
        "msg_runtime_stopped": "Runtime stopped",
        "msg_strategy_applied": "Strategy applied",
        "msg_test_completed": "Test completed",
        "msg_no_errors": "No errors",
        "msg_check_logs": "Check logs for details"
    }
