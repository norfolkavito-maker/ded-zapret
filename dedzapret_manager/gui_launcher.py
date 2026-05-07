#!/usr/bin/env python3
"""
GUI Launcher for DedZapret Manager

Simple launcher for the graphical interface.
"""

import sys
import os
from pathlib import Path

# Add app directory to Python path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

try:
    from zapret_manager.ui.gui.main_window import main
    
    if __name__ == "__main__":
        print("🚀 Запуск DedZapret Manager GUI...")
        main()
        
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Убедитесь что все зависимости установлены:")
    print("  - tkinter (обычно включён в Python)")
    print(f"  - Модули в директории: {app_dir}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Ошибка запуска: {e}")
    sys.exit(1)
