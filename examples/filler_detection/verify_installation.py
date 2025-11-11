#!/usr/bin/env python3
"""
Installation verification script for Filler Detection Extension.

This script verifies that all components are properly installed and working.
Run this after setting up the extension to ensure everything is configured correctly.

Usage:
    python verify_installation.py
"""

import sys
import traceback
from typing import Tuple


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def print_result(test_name: str, passed: bool, details: str = "") -> None:
    """Print test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {test_name}")
    if details:
        print(f"       {details}")


def test_imports() -> Tuple[bool, str]:
    """Test that all modules can be imported."""
    try:
        from filler_detector import (
            FillerDetectionConfig,
            FillerDetectionResult,
            FillerDetector,
        )
        from integration import IntegratedFillerSession
        return True, "All modules imported successfully"
    except Exception as e:
        return False, f"Import error: {str(e)}"


def test_basic_detection() -> Tuple[bool, str]:
    """Test basic filler detection."""
    try:
        from filler_detector import FillerDetector, FillerDetectionConfig
        
        config = FillerDetectionConfig(ignored_words=["uh", "um"])
        detector = FillerDetector(config)
        
        # Test filler-only
        result = detector.analyze_transcript("uh um", agent_state="speaking")
        if not result.is_filler_only:
            return False, "Failed to detect filler-only utterance"
        
        if result.should_interrupt:
            return False, "Should not interrupt on filler when agent speaking"
        
        # Test real words
        result = detector.analyze_transcript("wait stop", agent_state="speaking")
        if result.is_filler_only:
            return False, "Incorrectly marked real words as filler"
        
        if not result.should_interrupt:
            return False, "Should interrupt on real words"
        
        return True, "Basic detection logic works correctly"
    except Exception as e:
        return False, f"Detection error: {str(e)}"


def test_agent_state_awareness() -> Tuple[bool, str]:
    """Test that filtering respects agent state."""
    try:
        from filler_detector import FillerDetector, FillerDetectionConfig
        
        detector = FillerDetector(FillerDetectionConfig(ignored_words=["uh"]))
        
        # Agent speaking - should ignore
        result = detector.analyze_transcript("uh", agent_state="speaking")
        if result.should_interrupt:
            return False, "Should not interrupt when agent speaking"
        
        # Agent listening - should register
        result = detector.analyze_transcript("uh", agent_state="listening")
        if not result.should_interrupt:
            return False, "Should register when agent listening"
        
        return True, "Agent state awareness works correctly"
    except Exception as e:
        return False, f"State awareness error: {str(e)}"


def test_dynamic_updates() -> Tuple[bool, str]:
    """Test dynamic word list updates."""
    try:
        from filler_detector import FillerDetector, FillerDetectionConfig
        
        detector = FillerDetector(FillerDetectionConfig(ignored_words=["uh"]))
        
        # Initially "okay" is not a filler
        result = detector.analyze_transcript("okay", agent_state="speaking")
        if result.is_filler_only:
            return False, "Incorrectly detected 'okay' as filler initially"
        
        # Add "okay" to filler list
        detector.add_ignored_words(["okay"])
        
        # Now "okay" should be a filler
        result = detector.analyze_transcript("okay", agent_state="speaking")
        if not result.is_filler_only:
            return False, "Failed to update filler list dynamically"
        
        return True, "Dynamic updates work correctly"
    except Exception as e:
        return False, f"Dynamic update error: {str(e)}"


def test_multilingual_support() -> Tuple[bool, str]:
    """Test multilingual filler detection."""
    try:
        from filler_detector import FillerDetector, FillerDetectionConfig
        
        config = FillerDetectionConfig(
            ignored_words=["uh", "haan", "嗯", "うん"]
        )
        detector = FillerDetector(config)
        
        test_cases = [
            ("uh", True),
            ("haan", True),
            ("嗯", True),
            ("うん", True),
        ]
        
        for text, should_be_filler in test_cases:
            result = detector.analyze_transcript(text, agent_state="speaking")
            if result.is_filler_only != should_be_filler:
                return False, f"Failed for '{text}'"
        
        return True, "Multilingual support works correctly"
    except Exception as e:
        return False, f"Multilingual error: {str(e)}"


def test_configuration() -> Tuple[bool, str]:
    """Test configuration options."""
    try:
        from filler_detector import FillerDetectionConfig
        
        # Test default config
        config = FillerDetectionConfig()
        if len(config.ignored_words) == 0:
            return False, "Default config has no ignored words"
        
        # Test custom config
        config = FillerDetectionConfig(
            ignored_words=["test"],
            confidence_threshold=0.7,
            case_sensitive=True,
        )
        
        if config.confidence_threshold != 0.7:
            return False, "Failed to set confidence_threshold"
        
        if not config.case_sensitive:
            return False, "Failed to set case_sensitive"
        
        return True, "Configuration works correctly"
    except Exception as e:
        return False, f"Configuration error: {str(e)}"


def test_statistics() -> Tuple[bool, str]:
    """Test statistics tracking."""
    try:
        from filler_detector import FillerDetector, FillerDetectionConfig
        
        detector = FillerDetector(FillerDetectionConfig(ignored_words=["uh"]))
        
        # Process some transcripts
        detector.analyze_transcript("uh", agent_state="speaking")
        detector.analyze_transcript("wait", agent_state="speaking")
        
        stats = detector.get_stats()
        
        if stats["total_transcripts"] != 2:
            return False, f"Expected 2 transcripts, got {stats['total_transcripts']}"
        
        if "filler_only_detections" not in stats:
            return False, "Missing filler_only_detections in stats"
        
        return True, "Statistics tracking works correctly"
    except Exception as e:
        return False, f"Statistics error: {str(e)}"


def check_optional_dependencies() -> Tuple[bool, str]:
    """Check if optional dependencies are available."""
    missing = []
    
    try:
        import pytest
    except ImportError:
        missing.append("pytest")
    
    if missing:
        return False, f"Optional dependencies missing: {', '.join(missing)}"
    return True, "All optional dependencies available"


def main():
    """Run all verification tests."""
    print_header("Filler Detection Extension - Installation Verification")
    
    tests = [
        ("Module Imports", test_imports),
        ("Basic Detection", test_basic_detection),
        ("Agent State Awareness", test_agent_state_awareness),
        ("Dynamic Updates", test_dynamic_updates),
        ("Multilingual Support", test_multilingual_support),
        ("Configuration", test_configuration),
        ("Statistics Tracking", test_statistics),
    ]
    
    optional_tests = [
        ("Optional Dependencies", check_optional_dependencies),
    ]
    
    # Run core tests
    print("Core Functionality Tests:")
    print("-" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            success, details = test_func()
            print_result(test_name, success, details)
            if success:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print_result(test_name, False, f"Unexpected error: {str(e)}")
            traceback.print_exc()
            failed += 1
    
    # Run optional tests
    print("\n\nOptional Features:")
    print("-" * 60)
    
    for test_name, test_func in optional_tests:
        try:
            success, details = test_func()
            print_result(test_name, success, details)
        except Exception as e:
            print_result(test_name, False, f"Error: {str(e)}")
    
    # Summary
    print_header("Verification Summary")
    
    total = passed + failed
    success_rate = (passed / total * 100) if total > 0 else 0
    
    print(f"Tests Passed: {passed}/{total} ({success_rate:.1f}%)")
    print(f"Tests Failed: {failed}/{total}")
    
    if failed == 0:
        print("\n✅ All tests passed! The extension is properly installed and working.")
        print("\nNext steps:")
        print("  1. Run the demo: python demo_scenarios.py")
        print("  2. Run unit tests: pytest test_filler_detector.py -v")
        print("  3. Try the example agent: python example_agent.py")
        return 0
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        print("\nTroubleshooting:")
        print("  1. Ensure you're in the correct directory")
        print("  2. Check that all files are present")
        print("  3. Review the error messages above")
        print("  4. See README.md for more help")
        return 1


if __name__ == "__main__":
    sys.exit(main())

