"""
State management for DedZapret Manager

Handles application state including runtime status, active strategies,
process information, and temporary state.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

from .paths import SafePaths


class OverallStatus(Enum):
    """Overall application status"""
    DISABLED = "disabled"
    STARTING = "starting"
    ACTIVE = "active"
    STOPPING = "stopping"
    ERROR = "error"


class RuntimeStatus(Enum):
    """Runtime status"""
    NOT_INSTALLED = "not_installed"
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    CRASHED = "crashed"
    ERROR = "error"


class ProxyStatus(Enum):
    """Proxy status"""
    DISABLED = "disabled"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"


@dataclass
class ProcessInfo:
    """Information about running process"""
    pid: int = 0
    name: str = ""
    command_line: str = ""
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    start_time: Optional[str] = None
    status: str = ""
    exit_code: Optional[int] = None


@dataclass
class RuntimeState:
    """Runtime state information"""
    status: RuntimeStatus = RuntimeStatus.STOPPED
    process_info: Optional[ProcessInfo] = None
    active_strategy_id: str = ""
    active_profile_id: str = ""
    last_start_time: Optional[str] = None
    last_stop_time: Optional[str] = None
    restart_count: int = 0
    total_uptime_minutes: int = 0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class ProxyState:
    """Proxy state information"""
    status: ProxyStatus = ProxyStatus.DISABLED
    process_info: Optional[ProcessInfo] = None
    active_node_id: str = ""
    active_node_name: str = ""
    local_socks_port: int = 2080
    local_mixed_port: int = 2081
    system_proxy_enabled: bool = False
    last_start_time: Optional[str] = None
    last_stop_time: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class NetworkState:
    """Network state information"""
    dns_mode: str = "system"
    dns_servers: List[str] = field(default_factory=list)
    hosts_modified: bool = False
    quic_blocked: bool = False
    tcp_timestamps_modified: bool = False
    internet_connected: bool = True
    last_connectivity_check: Optional[str] = None


@dataclass
class TestState:
    """Testing state information"""
    last_test_time: Optional[str] = None
    last_test_strategy: str = ""
    last_test_result: Dict[str, Any] = field(default_factory=dict)
    test_in_progress: bool = False
    test_progress: int = 0
    test_total: int = 0
    successful_tests: int = 0
    failed_tests: int = 0


@dataclass
class ApplicationState:
    """Main application state"""
    version: str = "1.0.0"
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Status information
    overall_status: OverallStatus = OverallStatus.DISABLED
    
    # Component states
    runtime: RuntimeState = field(default_factory=RuntimeState)
    proxy: ProxyState = field(default_factory=ProxyState)
    network: NetworkState = field(default_factory=NetworkState)
    testing: TestState = field(default_factory=TestState)
    
    # Statistics
    total_starts: int = 0
    total_stops: int = 0
    total_strategy_changes: int = 0
    total_tests_run: int = 0
    
    # Health and diagnostics
    health_score: int = 100  # 0-100
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    # Custom state
    custom_state: Dict[str, Any] = field(default_factory=dict)


class StateManager:
    """Manages application state persistence and updates"""
    
    def __init__(self, safe_paths: SafePaths):
        self.safe_paths = safe_paths
        self.state_file = safe_paths.get_state_file()
        self.current_file = safe_paths.get_current_file()
        self._state: Optional[ApplicationState] = None
    
    def load_state(self) -> ApplicationState:
        """Load state from file"""
        if not self.state_file.exists():
            return self._create_default_state()
        
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not data:
                return self._create_default_state()
            
            state = self._dict_to_state(data)
            self._state = state
            return state
            
        except Exception:
            # If state is corrupted, create backup and default
            self._backup_corrupted_state()
            return self._create_default_state()
    
    def save_state(self, state: ApplicationState) -> bool:
        """Save state to file"""
        try:
            state.updated_at = datetime.now().isoformat()
            
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self._state_to_dict(state), f, indent=2, ensure_ascii=False)
            
            self._state = state
            return True
            
        except Exception:
            return False
    
    def get_state(self) -> ApplicationState:
        """Get current state (cached)"""
        if self._state is None:
            self._state = self.load_state()
        return self._state
    
    def update_runtime_state(self, runtime_state: RuntimeState) -> bool:
        """Update runtime state"""
        state = self.get_state()
        state.runtime = runtime_state
        state.updated_at = datetime.now().isoformat()
        return self.save_state(state)
    
    def update_proxy_state(self, proxy_state: ProxyState) -> bool:
        """Update proxy state"""
        state = self.get_state()
        state.proxy = proxy_state
        state.updated_at = datetime.now().isoformat()
        return self.save_state(state)
    
    def update_network_state(self, network_state: NetworkState) -> bool:
        """Update network state"""
        state = self.get_state()
        state.network = network_state
        state.updated_at = datetime.now().isoformat()
        return self.save_state(state)
    
    def update_testing_state(self, testing_state: TestState) -> bool:
        """Update testing state"""
        state = self.get_state()
        state.testing = testing_state
        state.updated_at = datetime.now().isoformat()
        return self.save_state(state)
    
    def set_overall_status(self, status: OverallStatus) -> bool:
        """Set overall application status"""
        state = self.get_state()
        state.overall_status = status
        state.updated_at = datetime.now().isoformat()
        return self.save_state(state)
    
    def add_warning(self, warning: str) -> bool:
        """Add warning to state"""
        state = self.get_state()
        if warning not in state.warnings:
            state.warnings.append(warning)
        state.updated_at = datetime.now().isoformat()
        return self.save_state(state)
    
    def add_error(self, error: str) -> bool:
        """Add error to state"""
        state = self.get_state()
        if error not in state.errors:
            state.errors.append(error)
        state.updated_at = datetime.now().isoformat()
        return self.save_state(state)
    
    def clear_warnings(self) -> bool:
        """Clear all warnings"""
        state = self.get_state()
        state.warnings.clear()
        state.runtime.warnings.clear()
        state.proxy.warnings.clear()
        state.updated_at = datetime.now().isoformat()
        return self.save_state(state)
    
    def clear_errors(self) -> bool:
        """Clear all errors"""
        state = self.get_state()
        state.errors.clear()
        state.runtime.errors.clear()
        state.proxy.errors.clear()
        state.updated_at = datetime.now().isoformat()
        return self.save_state(state)
    
    def increment_statistic(self, stat_name: str) -> bool:
        """Increment a statistic counter"""
        state = self.get_state()
        if hasattr(state, stat_name):
            current_value = getattr(state, stat_name)
            setattr(state, stat_name, current_value + 1)
        state.updated_at = datetime.now().isoformat()
        return self.save_state(state)
    
    def update_process_info(self, pid: int) -> bool:
        """Update process information for running PID"""
        if pid <= 0:
            return False
        
        try:
            # Simplified process info without psutil
            process_info = ProcessInfo(
                pid=pid,
                name="unknown",
                command_line="",
                cpu_percent=0.0,
                memory_mb=0.0,
                start_time=datetime.now().isoformat(),
                status="running"
            )
            
            state = self.get_state()
            
            # Update runtime or proxy process info based on current state
            if state.runtime.status == RuntimeStatus.RUNNING and state.runtime.process_info and state.runtime.process_info.pid == pid:
                state.runtime.process_info = process_info
            elif state.proxy.status == ProxyStatus.RUNNING and state.proxy.process_info and state.proxy.process_info.pid == pid:
                state.proxy.process_info = process_info
            
            return self.save_state(state)
            
        except Exception:
            return False
    
    def get_current_runtime_info(self) -> Dict[str, Any]:
        """Get current runtime information for UI"""
        state = self.get_state()
        runtime = state.runtime
        
        return {
            "status": runtime.status.value,
            "active_strategy": runtime.active_strategy_id,
            "active_profile": runtime.active_profile_id,
            "process_info": asdict(runtime.process_info) if runtime.process_info else None,
            "last_start": runtime.last_start_time,
            "restart_count": runtime.restart_count,
            "uptime_minutes": runtime.total_uptime_minutes,
            "warnings": runtime.warnings,
            "errors": runtime.errors
        }
    
    def get_system_status_summary(self) -> Dict[str, Any]:
        """Get system status summary for dashboard"""
        state = self.get_state()
        
        return {
            "overall_status": state.overall_status.value,
            "runtime_status": state.runtime.status.value,
            "proxy_status": state.proxy.status.value,
            "active_strategy": state.runtime.active_strategy_id,
            "active_profile": state.runtime.active_profile_id,
            "warnings_count": len(state.warnings) + len(state.runtime.warnings) + len(state.proxy.warnings),
            "errors_count": len(state.errors) + len(state.runtime.errors) + len(state.proxy.errors),
            "health_score": state.health_score,
            "internet_connected": state.network.internet_connected,
            "dns_mode": state.network.dns_mode,
            "last_test_time": state.testing.last_test_time,
            "test_in_progress": state.testing.test_in_progress
        }
    
    def _create_default_state(self) -> ApplicationState:
        """Create default state"""
        state = ApplicationState()
        self.save_state(state)
        return state
    
    def _dict_to_state(self, data: Dict[str, Any]) -> ApplicationState:
        """Convert dictionary to state object"""
        # Extract nested states
        runtime_data = data.get('runtime', {})
        proxy_data = data.get('proxy', {})
        network_data = data.get('network', {})
        testing_data = data.get('testing', {})
        
        # Convert process info
        runtime_process = runtime_data.get('process_info')
        if runtime_process:
            runtime_process = ProcessInfo(**runtime_process)
        
        proxy_process = proxy_data.get('process_info')
        if proxy_process:
            proxy_process = ProcessInfo(**proxy_process)
        
        return ApplicationState(
            version=data.get('version', '1.0.0'),
            started_at=data.get('started_at', datetime.now().isoformat()),
            updated_at=data.get('updated_at', datetime.now().isoformat()),
            
            overall_status=OverallStatus(data.get('overall_status', OverallStatus.DISABLED.value)),
            
            runtime=RuntimeState(
                status=RuntimeStatus(runtime_data.get('status', RuntimeStatus.STOPPED.value)),
                process_info=runtime_process,
                active_strategy_id=runtime_data.get('active_strategy_id', ''),
                active_profile_id=runtime_data.get('active_profile_id', ''),
                last_start_time=runtime_data.get('last_start_time'),
                last_stop_time=runtime_data.get('last_stop_time'),
                restart_count=runtime_data.get('restart_count', 0),
                total_uptime_minutes=runtime_data.get('total_uptime_minutes', 0),
                warnings=runtime_data.get('warnings', []),
                errors=runtime_data.get('errors', [])
            ),
            
            proxy=ProxyState(
                status=ProxyStatus(proxy_data.get('status', ProxyStatus.DISABLED.value)),
                process_info=proxy_process,
                active_node_id=proxy_data.get('active_node_id', ''),
                active_node_name=proxy_data.get('active_node_name', ''),
                local_socks_port=proxy_data.get('local_socks_port', 2080),
                local_mixed_port=proxy_data.get('local_mixed_port', 2081),
                system_proxy_enabled=proxy_data.get('system_proxy_enabled', False),
                last_start_time=proxy_data.get('last_start_time'),
                last_stop_time=proxy_data.get('last_stop_time'),
                warnings=proxy_data.get('warnings', []),
                errors=proxy_data.get('errors', [])
            ),
            
            network=NetworkState(
                dns_mode=network_data.get('dns_mode', 'system'),
                dns_servers=network_data.get('dns_servers', []),
                hosts_modified=network_data.get('hosts_modified', False),
                quic_blocked=network_data.get('quic_blocked', False),
                tcp_timestamps_modified=network_data.get('tcp_timestamps_modified', False),
                internet_connected=network_data.get('internet_connected', True),
                last_connectivity_check=network_data.get('last_connectivity_check')
            ),
            
            testing=TestState(
                last_test_time=testing_data.get('last_test_time'),
                last_test_strategy=testing_data.get('last_test_strategy', ''),
                last_test_result=testing_data.get('last_test_result', {}),
                test_in_progress=testing_data.get('test_in_progress', False),
                test_progress=testing_data.get('test_progress', 0),
                test_total=testing_data.get('test_total', 0),
                successful_tests=testing_data.get('successful_tests', 0),
                failed_tests=testing_data.get('failed_tests', 0)
            ),
            
            total_starts=data.get('total_starts', 0),
            total_stops=data.get('total_stops', 0),
            total_strategy_changes=data.get('total_strategy_changes', 0),
            total_tests_run=data.get('total_tests_run', 0),
            
            health_score=data.get('health_score', 100),
            warnings=data.get('warnings', []),
        )

        state = self.get_state()

        # Update runtime or proxy process info based on current state
        if state.runtime.status == RuntimeStatus.RUNNING and state.runtime.process_info and state.runtime.process_info.pid == pid:
            state.runtime.process_info = process_info
        elif state.proxy.status == ProxyStatus.RUNNING and state.proxy.process_info and state.proxy.process_info.pid == pid:
            state.proxy.process_info = process_info

        try:
            return self.save_state(state)
        except Exception:
            return False

def get_current_runtime_info(self) -> Dict[str, Any]:
    """Get current runtime information for UI"""
    state = self.get_state()
    runtime = state.runtime

    return {
        "status": runtime.status.value,
        "active_strategy": runtime.active_strategy_id,
        "active_profile": runtime.active_profile_id,
        "process_info": asdict(runtime.process_info) if runtime.process_info else None,
        "last_start": runtime.last_start_time,
        "restart_count": runtime.restart_count,
        "uptime_minutes": runtime.total_uptime_minutes,
        "warnings": runtime.warnings,
        "errors": runtime.errors
    }

def get_system_status_summary(self) -> Dict[str, Any]:
    """Get system status summary for dashboard"""
    state = self.get_state()

    return {
        "overall_status": state.overall_status.value,
        "runtime_status": state.runtime.status.value,
        "proxy_status": state.proxy.status.value,
        "active_strategy": state.runtime.active_strategy_id,
        "active_profile": state.runtime.active_profile_id,
        "warnings_count": len(state.warnings) + len(state.runtime.warnings) + len(state.proxy.warnings),
        "errors_count": len(state.errors) + len(state.runtime.errors) + len(state.proxy.errors),
        "health_score": state.health_score,
        "internet_connected": state.network.internet_connected,
        "dns_mode": state.network.dns_mode,
        "last_test_time": state.testing.last_test_time,
        "test_in_progress": state.testing.test_in_progress
    }

def _create_default_state(self) -> ApplicationState:
    """Create default state"""
    state = ApplicationState(
        version='1.0.0',
        started_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
        
        overall_status=OverallStatus(OverallStatus.DISABLED.value),
        
        runtime=RuntimeState(
            status=RuntimeStatus(RuntimeStatus.STOPPED.value),
            process_info=None,
            active_strategy_id='',
            active_profile_id='',
            last_start_time=None,
            last_stop_time=None,
            restart_count=0,
            total_uptime_minutes=0,
            warnings=[],
            errors=[]
        ),
        
        proxy=ProxyState(
            status=ProxyStatus(ProxyStatus.DISABLED.value),
            process_info=None,
            active_node_id='',
            active_node_name='',
            local_socks_port=2080,
            local_mixed_port=2081,
            system_proxy_enabled=False,
            last_start_time=None,
            last_stop_time=None,
            warnings=[],
            errors=[]
        ),
        
        network=NetworkState(
            dns_mode='system',
            dns_servers=[],
            hosts_modified=False,
            quic_blocked=False,
            tcp_timestamps_modified=False,
            internet_connected=True,
            last_connectivity_check=None
        ),
        
        testing=TestState(
            last_test_time=None,
            last_test_strategy='',
            last_test_result={},
            test_in_progress=False,
            test_progress=0,
            test_total=0,
            successful_tests=0,
            failed_tests=0
        ),
        
        total_starts=0,
        total_stops=0,
        total_strategy_changes=0,
        total_tests_run=0,
        
        health_score=100,
        warnings=[],
        errors=[],
        
        custom_state={}
    )
    self.save_state(state)
    return state

@classmethod
def from_dict(cls, data: Dict[str, Any]) -> 'ApplicationState':
    """Create state from dictionary"""
    # Extract nested states
    runtime_data = data.get('runtime', {})
    proxy_data = data.get('proxy', {})
    network_data = data.get('network', {})
    testing_data = data.get('testing', {})
    
    return cls(
        version=data.get('version', '1.0.0'),
        started_at=data.get('started_at', datetime.now().isoformat()),
        updated_at=data.get('updated_at', datetime.now().isoformat()),
        
        overall_status=OverallStatus(data.get('overall_status', OverallStatus.DISABLED.value)),
        
        runtime=RuntimeState(
            status=RuntimeStatus(runtime_data.get('status', RuntimeStatus.STOPPED.value)),
            process_info=None,  # Will be set separately if needed
            active_strategy_id=runtime_data.get('active_strategy_id', ''),
            active_profile_id=runtime_data.get('active_profile_id', ''),
            last_start_time=runtime_data.get('last_start_time'),
            last_stop_time=runtime_data.get('last_stop_time'),
            restart_count=runtime_data.get('restart_count', 0),
            total_uptime_minutes=runtime_data.get('total_uptime_minutes', 0),
            warnings=runtime_data.get('warnings', []),
            errors=runtime_data.get('errors', [])
        ),
        
        proxy=ProxyState(
            status=ProxyStatus(proxy_data.get('status', ProxyStatus.DISABLED.value)),
            process_info=None,
            active_node_id=proxy_data.get('active_node_id', ''),
            active_node_name=proxy_data.get('active_node_name', ''),
            local_socks_port=proxy_data.get('local_socks_port', 2080),
            local_mixed_port=proxy_data.get('local_mixed_port', 2081),
            system_proxy_enabled=proxy_data.get('system_proxy_enabled', False),
            last_start_time=proxy_data.get('last_start_time'),
            last_stop_time=proxy_data.get('last_stop_time'),
            warnings=proxy_data.get('warnings', []),
            errors=proxy_data.get('errors', [])
        ),
        
        network=NetworkState(
            dns_mode=network_data.get('dns_mode', 'system'),
            dns_servers=network_data.get('dns_servers', []),
            hosts_modified=network_data.get('hosts_modified', False),
            quic_blocked=network_data.get('quic_blocked', False),
            tcp_timestamps_modified=network_data.get('tcp_timestamps_modified', False),
            internet_connected=network_data.get('internet_connected', True),
            last_connectivity_check=network_data.get('last_connectivity_check')
        ),
        
        testing=TestState(
            last_test_time=testing_data.get('last_test_time'),
            last_test_strategy=testing_data.get('last_test_strategy', ''),
            last_test_result=testing_data.get('last_test_result', {}),
            test_in_progress=testing_data.get('test_in_progress', False),
            test_progress=testing_data.get('test_progress', 0),
            test_total=testing_data.get('test_total', 0),
            successful_tests=testing_data.get('successful_tests', 0),
            failed_tests=testing_data.get('failed_tests', 0)
        ),
        
        total_starts=data.get('total_starts', 0),
        total_stops=data.get('total_stops', 0),
        total_strategy_changes=data.get('total_strategy_changes', 0),
        total_tests_run=data.get('total_tests_run', 0),
        
        health_score=data.get('health_score', 100),
        warnings=data.get('warnings', []),
        errors=data.get('errors', []),
        
        custom_state=data.get('custom_state', {})
    )

def _backup_corrupted_state(self):
    """Backup corrupted state file"""
    if self.state_file.exists():
        corrupted_file = self.safe_paths.get_backup_dir() / f"state_corrupted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        corrupted_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.rename(corrupted_file)


# Global instance for singleton pattern
_state_manager_instance: Optional[StateManager] = None


def get_state_manager() -> StateManager:
    """Get global StateManager instance"""
    global _state_manager_instance
    if _state_manager_instance is None:
        raise RuntimeError("StateManager not initialized. Call init_state_manager() first.")
    return _state_manager_instance


def init_state_manager(safe_paths: SafePaths) -> StateManager:
    """Initialize global StateManager instance"""
    global _state_manager_instance
    _state_manager_instance = StateManager(safe_paths)
    return _state_manager_instance
