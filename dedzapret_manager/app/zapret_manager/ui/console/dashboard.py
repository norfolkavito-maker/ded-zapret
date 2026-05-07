"""
Dashboard for DedZapret Manager Console UI

Provides main dashboard with system status and quick actions.
"""

from typing import Dict, Any
from dataclasses import dataclass

from ...core.paths import SafePaths
from ...core.state import get_state_manager
from ...core.config import get_config_manager
from ...core.logging import get_logger, LogComponent
from ...runtime.winws2.detector import Winws2Detector


@dataclass
class SystemStatus:
    """System status information"""
    overall_status: str = "disabled"
    runtime_status: str = "stopped"
    proxy_status: str = "disabled"
    active_strategy: str = ""
    active_profile: str = ""
    warnings_count: int = 0
    errors_count: int = 0
    health_score: int = 100
    internet_connected: bool = True
    dns_mode: str = "system"
    last_test_time: str = ""
    test_in_progress: bool = False


class Dashboard:
    """Main dashboard for console UI"""
    
    def __init__(self, safe_paths: SafePaths):
        self.safe_paths = safe_paths
        self.state_manager = get_state_manager()
        self.config_manager = get_config_manager()
        self.logger = get_logger("dashboard", LogComponent.UI)
        
        # Initialize components
        self.winws2_detector = Winws2Detector(safe_paths)
    
    def get_system_status(self) -> SystemStatus:
        """Get current system status"""
        try:
            # Get state
            state = self.state_manager.get_state()
            
            # Detect runtime
            winws2_info = self.winws2_detector.detect_winws2()
            
            # Get requirements status
            requirements = self.winws2_detector.check_runtime_requirements()
            
            # Build status
            status = SystemStatus()
            status.overall_status = state.overall_status.value
            status.runtime_status = state.runtime.status.value
            status.proxy_status = state.proxy.status.value
            status.active_strategy = state.runtime.active_strategy_id
            status.active_profile = state.runtime.active_profile_id
            status.warnings_count = len(state.warnings) + len(state.runtime.warnings) + len(state.proxy.warnings)
            status.errors_count = len(state.errors) + len(state.runtime.errors) + len(state.proxy.errors)
            status.health_score = state.health_score
            status.internet_connected = state.network.internet_connected
            status.dns_mode = state.network.dns_mode
            status.last_test_time = state.testing.last_test_time or ""
            status.test_in_progress = state.testing.test_in_progress
            
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get system status: {e}")
            return SystemStatus()
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get formatted status summary"""
        status = self.get_system_status()
        
        return {
            "overall_status": status.overall_status,
            "runtime_status": status.runtime_status,
            "proxy_status": status.proxy_status,
            "active_strategy": status.active_strategy,
            "active_profile": status.active_profile,
            "warnings_count": status.warnings_count,
            "errors_count": status.errors_count,
            "health_score": status.health_score,
            "internet_connected": status.internet_connected,
            "dns_mode": status.dns_mode,
            "last_test_time": status.last_test_time,
            "test_in_progress": status.test_in_progress
        }
    
    def format_status_display(self) -> str:
        """Format status for console display"""
        status = self.get_system_status()
        
        lines = [
            f"📊 {status.overall_status.upper()}",
            f"Runtime: {status.runtime_status}",
            f"Strategy: {status.active_strategy or 'None'}",
            f"Profile: {status.active_profile or 'None'}",
            f"Warnings: {status.warnings_count}",
            f"Errors: {status.errors_count}",
            f"Health: {status.health_score}/100"
        ]
        
        return " | ".join(lines)
    
    def check_system_health(self) -> Dict[str, Any]:
        """Perform system health check"""
        health_result = {
            "overall_health": "good",
            "issues": [],
            "recommendations": []
        }
        
        try:
            # Check runtime
            winws2_info = self.winws2_detector.detect_winws2()
            if not winws2_info.exists:
                health_result["issues"].append("winws2 executable not found")
                health_result["recommendations"].append("Download and install winws2 runtime")
                health_result["overall_health"] = "poor"
            
            # Check requirements
            requirements = self.winws2_detector.check_runtime_requirements()
            if not requirements.get("admin_rights", False):
                health_result["issues"].append("Administrator rights required")
                health_result["recommendations"].append("Run as administrator")
                health_result["overall_health"] = "poor"
            
            if not requirements.get("windivert", False):
                health_result["issues"].append("WinDivert not found")
                health_result["recommendations"].append("Install WinDivert driver")
                health_result["overall_health"] = "poor"
            
            # Check state consistency
            state = self.state_manager.get_state()
            if state.errors:
                health_result["issues"].append(f"State errors: {len(state.errors)}")
                health_result["overall_health"] = "fair"
            
            return health_result
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            health_result["overall_health"] = "error"
            health_result["issues"].append(f"Health check error: {e}")
            return health_result
