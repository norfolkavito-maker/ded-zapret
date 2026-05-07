#!/usr/bin/env python3
"""
DedZapret Manager - Quick Test Runner

Simple script to test core functionality without full UI.
Tests basic components and reports status.
"""

import sys
import os
from pathlib import Path

# Add app directory to Python path
app_path = Path(__file__).parent / "app"
sys.path.insert(0, str(app_path))

# Also add the zapret_manager directory directly
zapret_path = Path(__file__).parent / "app" / "zapret_manager"
sys.path.insert(0, str(zapret_path))

def test_core_components():
    """Test core components functionality"""
    print("🧪 Testing DedZapret Manager Core Components")
    print("=" * 50)
    
    try:
        # Test 1: Core initialization
        print("\n1. Testing Core Components...")
        from zapret_manager.core.paths import get_safe_paths, init_safe_paths
        from zapret_manager.core.config import get_config_manager, init_config_manager
        from zapret_manager.core.audit import get_audit_logger, init_audit_logger
        from zapret_manager.core.security import get_masker, init_masker
        from zapret_manager.core.backup import BackupManager
        
        # Initialize components in correct order
        safe_paths = init_safe_paths()
        
        # Initialize logging first
        from zapret_manager.core.logging import init_logging
        logging_manager = init_logging(safe_paths)
        
        config_manager = init_config_manager(safe_paths)
        audit_logger = init_audit_logger(safe_paths)
        masker = init_masker()
        backup_manager = BackupManager(safe_paths)
        
        print("✅ Core components initialized successfully")
        print(f"   - Safe paths: {safe_paths.get_app_data_dir()}")
        print(f"   - Config manager: Ready")
        print(f"   - Audit logger: Ready")
        print(f"   - Data masker: Ready")
        print(f"   - Backup manager: Ready")
        
        # Test 2: Strategy components
        print("\n2. Testing Strategy Components...")
        from zapret_manager.strategies.registry import get_strategy_registry, init_strategy_registry
        from zapret_manager.strategies.loader import StrategyLoader
        from zapret_manager.strategies.validator import StrategyValidator
        
        # Initialize strategy components
        strategy_registry = init_strategy_registry(safe_paths)
        strategy_loader = StrategyLoader(safe_paths)
        strategy_validator = StrategyValidator(safe_paths)
        
        # Initialize state manager for runtime components
        from zapret_manager.core.state import init_state_manager
        state_manager = init_state_manager(safe_paths)
        
        print("✅ Strategy components initialized successfully")
        
        # Load strategies
        strategies = strategy_loader.load_all_strategies()
        print(f"   - Loaded {len(strategies)} strategies")
        
        if strategies:
            print("   - Sample strategies:")
            for i, strategy in enumerate(strategies[:3], 1):
                print(f"     {i}. {strategy.name} ({strategy.source})")
        
        # Test 3: Runtime components
        print("\n3. Testing Runtime Components...")
        from zapret_manager.runtime.winws2.detector import Winws2Detector
        from zapret_manager.runtime.winws2.command_model import Winws2CommandBuilder
        from zapret_manager.runtime.winws2.process import Winws2ProcessManager
        
        winws2_detector = Winws2Detector(safe_paths)
        command_builder = Winws2CommandBuilder(safe_paths)
        process_manager = Winws2ProcessManager(safe_paths)
        
        # Pass state manager to runtime components
        from zapret_manager.runtime.winws2.process import Winws2ProcessManager as ProcessManager
        process_manager = ProcessManager(safe_paths)
        process_manager.state_manager = state_manager
        
        print("✅ Runtime components initialized successfully")
        
        # Detect winws2
        winws2_info = winws2_detector.detect_winws2()
        if winws2_info.exists:
            print(f"   - winws2 found: {winws2_info.path}")
            print(f"   - Version: {winws2_info.version}")
            print(f"   - Size: {winws2_info.size} bytes")
        else:
            print("   - winws2: NOT FOUND")
        
        # Check requirements
        requirements = winws2_detector.check_runtime_requirements()
        print(f"   - Admin rights: {'✅' if requirements['admin_rights'] else '❌'}")
        print(f"   - WinDivert: {'✅' if requirements['windivert'] else '❌'}")
        print(f"   - PowerShell: {'✅' if requirements['powershell'] else '❌'}")
        print(f"   - x64 Architecture: {'✅' if requirements['x64_architecture'] else '❌'}")
        
        # Test 4: UI Components
        print("\n4. Testing UI Components...")
        from zapret_manager.ui.messages import get_russian_messages
        from zapret_manager.ui.quick_actions import get_quick_actions
        from zapret_manager.ui.console.dashboard import Dashboard
        
        # Initialize UI components
        messages = get_russian_messages()
        quick_actions = get_quick_actions()
        dashboard = Dashboard(safe_paths)
        
        print("✅ UI components initialized successfully")
        print(f"   - Russian messages: Ready")
        print(f"   - Quick actions: Ready")
        print(f"   - Dashboard: Ready")
        
        # Test 5: Get system status
        print("\n5. Testing System Status...")
        system_status = dashboard.get_system_status()
        
        print("✅ System status retrieved successfully")
        print(f"   - Overall status: {system_status.overall_status}")
        print(f"   - Runtime status: {system_status.runtime_status}")
        print(f"   - Active strategy: {system_status.active_strategy}")
        print(f"   - Proxy status: {system_status.proxy_status}")
        print(f"   - Warnings: {system_status.warnings_count}")
        print(f"   - Errors: {system_status.errors_count}")
        
        # Test 6: Quick actions
        print("\n6. Testing Quick Actions...")
        from zapret_manager.ui.quick_actions import ActionType
        
        available_actions = quick_actions.get_available_actions()
        print("✅ Quick actions available:")
        for action in available_actions:
            status_icon = "✅" if action["available"] else "❌"
            print(f"   {status_icon} {action['icon']} {action['name']}: {action['description']}")
        
        print("\n" + "=" * 50)
        print("🎉 Core functionality test completed successfully!")
        print("💡 Ready for UI testing and further development")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Core functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_simple_strategy_management():
    """Test simple strategy management"""
    print("\n🎯 Testing Strategy Management...")
    print("-" * 30)
    
    try:
        from zapret_manager.strategies.registry import get_strategy_registry
        from zapret_manager.strategies.model import Strategy, StrategyStatus, RuntimeTarget, OriginalEngine
        
        registry = get_strategy_registry()
        
        # Create a test strategy
        test_strategy = Strategy(
            id="test.basic",
            name="Test Basic Strategy",
            description_ru="Тестовая базовая стратегия",
            source="test",
            kind="base",
            runtime_target=RuntimeTarget.WINWS2,
            original_engine=OriginalEngine.WINWS2,
            normalized_engine=RuntimeTarget.WINWS2,
            status=StrategyStatus.FLOWSEAL_WINWS2_READY,
            author="Test",
            version="1.0.0"
        )
        
        # Add to registry
        registry.add_strategy(test_strategy)
        print("✅ Test strategy added to registry")
        
        # Retrieve from registry
        retrieved = registry.get_strategy("test.basic")
        if retrieved:
            print(f"✅ Strategy retrieved: {retrieved.name}")
        else:
            print("❌ Failed to retrieve strategy")
        
        # List all strategies
        all_strategies = registry.get_all_strategies()
        print(f"✅ Total strategies in registry: {len(all_strategies)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Strategy management test failed: {e}")
        return False

def main():
    """Main test runner"""
    print("🚀 DedZapret Manager - Quick Test Runner")
    print("Testing core functionality without full UI...")
    print()
    
    # Test core components
    core_test_passed = test_core_components()
    
    # Test strategy management
    strategy_test_passed = test_simple_strategy_management()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    print(f"Core Components: {'✅ PASSED' if core_test_passed else '❌ FAILED'}")
    print(f"Strategy Management: {'✅ PASSED' if strategy_test_passed else '❌ FAILED'}")
    
    if core_test_passed and strategy_test_passed:
        print("\n🎉 ALL TESTS PASSED!")
        print("💡 DedZapret Manager core is ready for use!")
        print("🔗 Repository: https://github.com/norfolkavito-maker/ded-zapret")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED!")
        print("🔧 Check the error messages above for details")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
