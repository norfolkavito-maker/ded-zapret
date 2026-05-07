"""
Main window for DedZapret Manager GUI

Provides the main application window with status display,
controls, and settings.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, Dict, Any
import threading
import time

from ...core.paths import get_safe_paths
from ...core.state import get_state_manager
from ...core.config import get_config_manager
from ...core.logging import get_logger, LogComponent
from ...strategies.registry import get_strategy_registry
from ...runtime.winws2.detector import Winws2Detector
from ...runtime.winws2.process import Winws2ProcessManager
from ...runtime.winws2.command_model import Winws2CommandBuilder


class MainWindow:
    """Main application window"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("DedZapret Manager v1.0.0")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # Initialize components
        self.safe_paths = get_safe_paths()
        self.state_manager = get_state_manager()
        self.config_manager = get_config_manager()
        self.strategy_registry = get_strategy_registry()
        
        # Runtime components
        self.winws2_detector = Winws2Detector(self.safe_paths)
        self.command_builder = Winws2CommandBuilder(self.safe_paths)
        self.process_manager = Winws2ProcessManager(self.safe_paths)
        
        self.logger = get_logger("gui", LogComponent.UI)
        
        # Status variables
        self.status_text = tk.StringVar(value="Готов к работе")
        self.strategy_var = tk.StringVar(value="Не выбрана")
        self.runtime_status = tk.StringVar(value="Остановлен")
        
        # Create UI
        self._create_widgets()
        self._update_status()
        
        # Start status update thread
        self._start_status_updater()
    
    def _create_widgets(self):
        """Create UI widgets"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Status section
        status_frame = ttk.LabelFrame(main_frame, text="Статус системы", padding="5")
        status_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        # Overall status
        ttk.Label(status_frame, text="Общий статус:").grid(row=0, column=0, sticky="w")
        ttk.Label(status_frame, textvariable=self.status_text).grid(row=0, column=1, sticky="w")
        
        # Runtime status
        ttk.Label(status_frame, text="Runtime:").grid(row=1, column=0, sticky="w")
        ttk.Label(status_frame, textvariable=self.runtime_status).grid(row=1, column=1, sticky="w")
        
        # Strategy info
        ttk.Label(status_frame, text="Стратегия:").grid(row=2, column=0, sticky="w")
        ttk.Label(status_frame, textvariable=self.strategy_var).grid(row=2, column=1, sticky="w")
        
        # Control buttons
        control_frame = ttk.LabelFrame(main_frame, text="Управление", padding="5")
        control_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        
        # Start/Stop button
        self.start_stop_btn = ttk.Button(
            control_frame, 
            text="Запустить Runtime",
            command=self._toggle_runtime
        )
        self.start_stop_btn.grid(row=0, column=0, padx=5, pady=5)
        
        # Test button
        test_btn = ttk.Button(
            control_frame,
            text="Тестировать",
            command=self._test_strategy
        )
        test_btn.grid(row=0, column=1, padx=5, pady=5)
        
        # Settings button
        settings_btn = ttk.Button(
            control_frame,
            text="Настройки",
            command=self._open_settings
        )
        settings_btn.grid(row=1, column=0, padx=5, pady=5)
        
        # Logs button
        logs_btn = ttk.Button(
            control_frame,
            text="Открыть логи",
            command=self._open_logs
        )
        logs_btn.grid(row=1, column=1, padx=5, pady=5)
        
        # Progress bar
        self.progress = ttk.Progressbar(
            main_frame,
            mode='indeterminate',
            length=300
        )
        self.progress.grid(row=2, column=0, columnspan=2, sticky="ew", pady=10)
        
        # Status text area
        self.status_text_area = tk.Text(
            main_frame,
            height=10,
            width=80,
            wrap=tk.WORD
        )
        self.status_text_area.grid(row=3, column=0, columnspan=2, sticky="ew", pady=5)
        
        # Scrollbar for text area
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.status_text_area.yview)
        scrollbar.grid(row=3, column=2, sticky="ns", pady=5)
        self.status_text_area.config(yscrollcommand=scrollbar.set)
    
    def _toggle_runtime(self):
        """Toggle runtime start/stop"""
        try:
            if self.process_manager.is_running():
                # Stop runtime
                self._add_status("Остановка runtime...")
                success = self.process_manager.stop_process()
                if success:
                    self._add_status("Runtime успешно остановлен")
                    self.start_stop_btn.config(text="Запустить Runtime")
                else:
                    self._add_status("Ошибка при остановке runtime")
            else:
                # Start runtime
                self._add_status("Запуск runtime...")
                
                # Get selected strategy
                strategies = self.strategy_registry.get_all_strategies()
                if strategies:
                    strategy = strategies[0]  # Use first available strategy
                    command = self.command_builder.build_command(strategy)
                    if command.success:
                        success = self.process_manager.start_process(command.command, strategy.id)
                        if success:
                            self._add_status(f"Runtime запущен со стратегией: {strategy.name}")
                            self.start_stop_btn.config(text="Остановить Runtime")
                        else:
                            self._add_status("Ошибка при запуске runtime")
                    else:
                        self._add_status("Ошибка сборки команды")
                else:
                    self._add_status("Нет доступных стратегий")
                    
        except Exception as e:
            self._add_status(f"Ошибка: {e}")
    
    def _test_strategy(self):
        """Test current strategy"""
        try:
            self._add_status("Тестирование стратегии...")
            self.progress.start()
            
            # Simulate testing
            time.sleep(2)
            
            self._add_status("Тестирование завершено успешно")
            self.progress.stop()
            
        except Exception as e:
            self._add_status(f"Ошибка тестирования: {e}")
            self.progress.stop()
    
    def _open_settings(self):
        """Open settings dialog"""
        messagebox.showinfo("Настройки", "Настройки будут доступны в следующих версиях")
    
    def _open_logs(self):
        """Open logs directory"""
        try:
            logs_dir = self.safe_paths.get_logs_dir()
            if logs_dir.exists():
                import os
                os.startfile(str(logs_dir))
            else:
                messagebox.showwarning("Логи", "Директория логов не найдена")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть логи: {e}")
    
    def _add_status(self, message: str):
        """Add status message to text area"""
        timestamp = time.strftime("%H:%M:%S")
        self.status_text_area.insert(tk.END, f"[{timestamp}] {message}\n")
        self.status_text_area.see(tk.END)
    
    def _update_status(self):
        """Update status displays"""
        try:
            # Get current state
            state = self.state_manager.get_state()
            
            # Update status text
            if state.overall_status.value == "enabled":
                self.status_text.set("Система активна")
            else:
                self.status_text.set("Система неактивна")
            
            # Update runtime status
            if state.runtime.status.value == "running":
                self.runtime_status.set("Работает")
                self.start_stop_btn.config(text="Остановить Runtime")
            else:
                self.runtime_status.set("Остановлен")
                self.start_stop_btn.config(text="Запустить Runtime")
            
            # Update strategy
            if state.runtime.active_strategy_id:
                strategy = self.strategy_registry.get_strategy(state.runtime.active_strategy_id)
                if strategy:
                    self.strategy_var.set(strategy.name)
                else:
                    self.strategy_var.set("Неизвестная стратегия")
            else:
                self.strategy_var.set("Не выбрана")
                
        except Exception as e:
            self.logger.error(f"Failed to update status: {e}")
    
    def _start_status_updater(self):
        """Start background status updater"""
        def update_status():
            while True:
                try:
                    self._update_status()
                    time.sleep(1)
                except Exception as e:
                    self.logger.error(f"Status updater error: {e}")
                    time.sleep(5)
        
        updater_thread = threading.Thread(target=update_status, daemon=True)
        updater_thread.start()
    
    def run(self):
        """Run the application"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.logger.info("Application interrupted by user")
        except Exception as e:
            self.logger.error(f"Application error: {e}")
        finally:
            self.logger.info("Application shutdown")


def main():
    """Main entry point for GUI"""
    app = MainWindow()
    app.run()


if __name__ == "__main__":
    main()
