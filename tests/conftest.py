#!/usr/bin/env python3
"""
conftest.py - Pytest configuration for auto-research tests

This file is executed before any test module is imported,
allowing us to set up the proper mock environment.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock

# Create mock quality_dashboard module BEFORE pytest imports anything
class MockQualityDashboard:
    class QualityDashboard:
        def __init__(self, *args, **kwargs):
            pass
        def run_evaluation(self):
            mock_result = Mock()
            mock_result.total_score = 75.0
            mock_result.dimensions = {
                "CLAUDE_CODE": Mock(score=75.0),
                "TEST_COVERAGE": Mock(score=70.0),
            }
            return mock_result

# Create the mock module structure
sys.modules['quality_dashboard'] = MockQualityDashboard()
sys.modules['quality_dashboard.dashboard'] = MockQualityDashboard()

# Now the package imports should work
sys.path.insert(0, str(Path(__file__).parent / 'agent'))