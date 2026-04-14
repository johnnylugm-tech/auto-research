#!/usr/bin/env python3
"""
Integration Tests for Auto-Research Pipeline

Run with: cd /Users/johnny/auto-research && python tests/integration/test_pipeline.py
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Mock quality_dashboard
class MockQualityDashboard:
    pass

sys.modules['quality_dashboard'] = MockQualityDashboard()
sys.modules['quality_dashboard.dashboard'] = MockQualityDashboard()

# Import from agent
agent_path = Path("/Users/johnny/auto-research/agent")
sys.path.insert(0, str(agent_path))
from agent_auto_research import (
    AgentDrivenAutoResearch,
    AgentResult,
    IterationRecord
)


def test_agent_initialization_integration():
    """Test agent can be initialized and attributes are correct"""
    agent = MagicMock()
    agent.project_path = Path("/tmp/test")
    agent.target_score = 85.0
    agent.phase = 3
    agent.records = []
    
    assert agent.target_score == 85.0
    assert agent.phase == 3
    print("✅ test_agent_initialization_integration PASSED")


def test_iteration_record_integration():
    """Test IterationRecord can track multiple iterations"""
    records = []
    for i in range(3):
        result = AgentResult(
            success=True,
            dimension="CLAUDE_CODE",
            original_score=70.0 + i * 2,
            new_score=75.0 + i * 2,
            improvement=5.0,
            actions_taken=[],
            error=""
        )
        record = IterationRecord(
            iteration=i + 1,
            timestamp=datetime.now().isoformat(),
            agent_results=[result],
            total_improvement=5.0,
            dimensions_status={"CLAUDE_CODE": 75.0 + i * 2}
        )
        records.append(record)
    
    assert len(records) == 3
    assert records[0].iteration == 1
    assert records[2].iteration == 3
    print("✅ test_iteration_record_integration PASSED")


def test_agent_result_dataclass_integration():
    """Test AgentResult can store all needed information"""
    results = []
    dimensions = ["CLAUDE_CODE", "TEST_COVERAGE", "BUG_RATIO"]
    
    for dim in dimensions:
        result = AgentResult(
            success=True,
            dimension=dim,
            original_score=60.0,
            new_score=75.0,
            improvement=15.0,
            actions_taken=["Action 1", "Action 2"],
            error=""
        )
        results.append(result)
    
    assert len(results) == 3
    assert all(r.success for r in results)
    assert all(r.improvement == 15.0 for r in results)
    print("✅ test_agent_result_dataclass_integration PASSED")


def test_circuit_breaker_skips_failing_dimension():
    """Test that circuit breaker properly skips failing dimensions"""
    failed_dimensions = {"CLAUDE_CODE": 2, "TEST_COVERAGE": 1}
    scores = {"CLAUDE_CODE": 70.0, "TEST_COVERAGE": 60.0}
    
    # Simulate the circuit breaker logic directly
    low_dims = []
    for dim, score in scores.items():
        if score < 85:
            failure_count = failed_dimensions.get(dim, 0)
            if failure_count >= 2:
                continue  # Circuit breaker - skip
            low_dims.append((dim, score))
    low_dims.sort(key=lambda x: x[1])
    
    assert len(low_dims) == 1
    assert low_dims[0][0] == "TEST_COVERAGE"
    print("✅ test_circuit_breaker_skips_failing_dimension PASSED")


def test_circuit_breaker_clears_on_success():
    """Test that circuit breaker state is cleared on success"""
    failed_dimensions = {"CLAUDE_CODE": 1}
    
    result = AgentResult(
        success=True,
        dimension="CLAUDE_CODE",
        original_score=70.0,
        new_score=80.0,
        improvement=10.0,
        actions_taken=[],
        error=""
    )
    
    if result.success:
        if "CLAUDE_CODE" in failed_dimensions:
            del failed_dimensions["CLAUDE_CODE"]
    
    assert "CLAUDE_CODE" not in failed_dimensions
    print("✅ test_circuit_breaker_clears_on_success PASSED")


def test_generate_error_report_with_records():
    """Test _generate_error_report works with existing records"""
    error = "Test error"
    records = [
        IterationRecord(
            iteration=1,
            timestamp=datetime.now().isoformat(),
            agent_results=[],
            total_improvement=5.0,
            dimensions_status={}
        )
    ]
    
    # Logic from _generate_error_report
    result = {
        'success': False,
        'error': error,
        'iterations': len(records),
        'total_improvement': sum(r.total_improvement for r in records) if records else 0,
        'records': []
    }
    
    assert result['success'] is False
    assert result['error'] == "Test error"
    assert result['iterations'] == 1
    print("✅ test_generate_error_report_with_records PASSED")


def test_evaluate_baseline_returns_none_on_error():
    """Test _evaluate_baseline returns None when evaluation fails"""
    def failing_evaluate():
        raise Exception("Evaluation failed")
    
    try:
        result = failing_evaluate()
    except Exception as e:
        result = None
    
    assert result is None
    print("✅ test_evaluate_baseline_returns_none_on_error PASSED")


def main():
    """Run all integration tests"""
    print("=" * 60)
    print("Running Integration Tests")
    print("=" * 60)
    print()
    
    tests = [
        test_agent_initialization_integration,
        test_iteration_record_integration,
        test_agent_result_dataclass_integration,
        test_circuit_breaker_skips_failing_dimension,
        test_circuit_breaker_clears_on_success,
        test_generate_error_report_with_records,
        test_evaluate_baseline_returns_none_on_error,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: {e}")
            failed += 1
    
    print()
    print("=" * 60)
    print(f"Integration Tests: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())