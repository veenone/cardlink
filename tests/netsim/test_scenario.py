"""Unit tests for scenario module.

Tests for Scenario, Step, ScenarioRunner, and related classes.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cardlink.netsim.scenario import (
    Condition,
    ConditionOperator,
    Scenario,
    ScenarioResult,
    ScenarioRunner,
    Step,
    StepResult,
    StepStatus,
)
from cardlink.netsim.exceptions import ConfigurationError


class TestCondition:
    """Tests for Condition class."""

    def test_from_dict_basic(self):
        """Test basic condition creation."""
        data = {
            "variable": "test_var",
            "operator": "equals",
            "value": "test_value",
        }
        condition = Condition.from_dict(data)

        assert condition.variable == "test_var"
        assert condition.operator == ConditionOperator.EQUALS
        assert condition.value == "test_value"

    def test_from_dict_default_operator(self):
        """Test condition with default operator."""
        data = {"variable": "test_var"}
        condition = Condition.from_dict(data)

        assert condition.operator == ConditionOperator.DEFINED

    def test_from_dict_missing_variable(self):
        """Test condition without variable raises error."""
        with pytest.raises(ConfigurationError):
            Condition.from_dict({"operator": "equals"})

    def test_from_dict_invalid_operator(self):
        """Test condition with invalid operator raises error."""
        with pytest.raises(ConfigurationError):
            Condition.from_dict({
                "variable": "test_var",
                "operator": "invalid_op",
            })


class TestStep:
    """Tests for Step class."""

    def test_from_dict_basic(self):
        """Test basic step creation."""
        data = {
            "name": "test_step",
            "action": "ue.list",
            "params": {"imsi": "001010123456789"},
        }
        step = Step.from_dict(data)

        assert step.name == "test_step"
        assert step.action == "ue.list"
        assert step.params == {"imsi": "001010123456789"}
        assert step.timeout == 30.0
        assert step.on_failure == "stop"

    def test_from_dict_with_condition(self):
        """Test step with condition."""
        data = {
            "action": "ue.list",
            "condition": {
                "variable": "ue_registered",
                "operator": "equals",
                "value": True,
            },
        }
        step = Step.from_dict(data)

        assert step.condition is not None
        assert step.condition.variable == "ue_registered"

    def test_from_dict_missing_action(self):
        """Test step without action raises error."""
        with pytest.raises(ConfigurationError):
            Step.from_dict({"name": "test"})

    def test_from_dict_default_name(self):
        """Test step with default name."""
        step = Step.from_dict({"action": "test.action"}, index=5)
        assert step.name == "step_5"

    def test_from_dict_custom_timeout(self):
        """Test step with custom timeout."""
        step = Step.from_dict({
            "action": "test.action",
            "timeout": 60.0,
        })
        assert step.timeout == 60.0

    def test_from_dict_save_as(self):
        """Test step with save_as."""
        step = Step.from_dict({
            "action": "ue.get",
            "save_as": "ue_result",
        })
        assert step.save_as == "ue_result"


class TestScenario:
    """Tests for Scenario class."""

    def test_from_yaml_basic(self):
        """Test basic YAML parsing."""
        yaml_content = """
name: test_scenario
description: A test scenario
steps:
  - name: step1
    action: ue.list
  - name: step2
    action: cell.status
"""
        scenario = Scenario.from_yaml(yaml_content)

        assert scenario.name == "test_scenario"
        assert scenario.description == "A test scenario"
        assert len(scenario.steps) == 2

    def test_from_yaml_with_variables(self):
        """Test YAML with variables."""
        yaml_content = """
name: test_scenario
variables:
  imsi: "001010123456789"
  timeout: 30
steps:
  - action: ue.get
    params:
      imsi: "${imsi}"
"""
        scenario = Scenario.from_yaml(yaml_content)

        assert scenario.variables["imsi"] == "001010123456789"
        assert scenario.variables["timeout"] == 30

    def test_from_yaml_with_setup_teardown(self):
        """Test YAML with setup and teardown."""
        yaml_content = """
name: test_scenario
setup:
  - action: cell.start
teardown:
  - action: cell.stop
steps:
  - action: ue.list
"""
        scenario = Scenario.from_yaml(yaml_content)

        assert len(scenario.setup) == 1
        assert len(scenario.teardown) == 1
        assert scenario.setup[0].action == "cell.start"

    def test_from_yaml_with_tags(self):
        """Test YAML with tags."""
        yaml_content = """
name: test_scenario
tags:
  - smoke
  - regression
steps:
  - action: ue.list
"""
        scenario = Scenario.from_yaml(yaml_content)

        assert "smoke" in scenario.tags
        assert "regression" in scenario.tags

    def test_from_yaml_invalid_yaml(self):
        """Test invalid YAML raises error."""
        with pytest.raises(ConfigurationError):
            Scenario.from_yaml("invalid: yaml: content:")

    def test_from_yaml_missing_name(self):
        """Test YAML without name raises error."""
        with pytest.raises(ConfigurationError):
            Scenario.from_yaml("steps:\n  - action: test")


class TestStepResult:
    """Tests for StepResult class."""

    def test_to_dict(self):
        """Test StepResult serialization."""
        result = StepResult(
            step_name="test_step",
            status=StepStatus.PASSED,
            result={"data": "value"},
            duration_ms=100.5,
        )

        data = result.to_dict()
        assert data["step_name"] == "test_step"
        assert data["status"] == "passed"
        assert data["result"] == {"data": "value"}
        assert data["duration_ms"] == 100.5


class TestScenarioResult:
    """Tests for ScenarioResult class."""

    def test_to_dict(self):
        """Test ScenarioResult serialization."""
        result = ScenarioResult(
            scenario_name="test",
            passed=True,
            duration_ms=1000.0,
        )

        data = result.to_dict()
        assert data["scenario_name"] == "test"
        assert data["passed"] is True

    def test_counts(self):
        """Test result counting properties."""
        result = ScenarioResult(
            scenario_name="test",
            passed=False,
            step_results=[
                StepResult("s1", StepStatus.PASSED),
                StepResult("s2", StepStatus.PASSED),
                StepResult("s3", StepStatus.FAILED),
                StepResult("s4", StepStatus.SKIPPED),
            ],
        )

        assert result.passed_count == 2
        assert result.failed_count == 1
        assert result.skipped_count == 1


class TestScenarioRunner:
    """Tests for ScenarioRunner class."""

    @pytest.fixture
    def mock_manager(self):
        """Create mock simulator manager."""
        manager = MagicMock()

        # UE manager
        manager.ue = MagicMock()
        manager.ue.list_ues = AsyncMock(return_value=[])
        manager.ue.get_ue = AsyncMock(return_value={"imsi": "001010123456789"})
        manager.ue.wait_for_registration = AsyncMock(return_value={"imsi": "001010123456789"})
        manager.ue.detach_ue = AsyncMock(return_value=True)

        # Session manager
        manager.sessions = MagicMock()
        manager.sessions.list_sessions = AsyncMock(return_value=[])
        manager.sessions.get_session = AsyncMock(return_value=None)
        manager.sessions.release_session = AsyncMock(return_value=True)

        # SMS manager
        manager.sms = MagicMock()
        manager.sms.send_mt_sms = AsyncMock(return_value="msg_001")
        manager.sms.send_ota_trigger = AsyncMock(return_value="msg_002")

        # Cell manager
        manager.cell = MagicMock()
        manager.cell.start = AsyncMock(return_value=True)
        manager.cell.stop = AsyncMock(return_value=True)
        manager.cell.get_status = AsyncMock(return_value={"status": "active"})
        manager.cell.configure = AsyncMock(return_value=True)

        # Trigger manager
        manager.triggers = MagicMock()
        manager.triggers.trigger_paging = AsyncMock(return_value=True)
        manager.triggers.trigger_handover = AsyncMock(return_value=True)
        manager.triggers.trigger_detach = AsyncMock(return_value=True)

        return manager

    def test_init(self, mock_manager):
        """Test ScenarioRunner initialization."""
        runner = ScenarioRunner(mock_manager)
        assert runner._manager == mock_manager
        assert len(runner._action_map) > 0

    def test_get_available_actions(self, mock_manager):
        """Test getting available actions."""
        runner = ScenarioRunner(mock_manager)
        actions = runner.get_available_actions()

        assert "ue.list" in actions
        assert "cell.start" in actions
        assert "sms.send" in actions

    @pytest.mark.asyncio
    async def test_run_simple_scenario(self, mock_manager):
        """Test running a simple scenario."""
        runner = ScenarioRunner(mock_manager)

        scenario = Scenario(
            name="simple_test",
            steps=[
                Step(name="list_ues", action="ue.list"),
            ],
        )

        result = await runner.run(scenario)

        assert result.passed is True
        assert len(result.step_results) == 1
        assert result.step_results[0].status == StepStatus.PASSED

    @pytest.mark.asyncio
    async def test_run_with_variables(self, mock_manager):
        """Test running scenario with variables."""
        runner = ScenarioRunner(mock_manager)

        scenario = Scenario(
            name="var_test",
            variables={"imsi": "001010123456789"},
            steps=[
                Step(
                    name="get_ue",
                    action="ue.get",
                    params={"imsi": "${imsi}"},
                ),
            ],
        )

        result = await runner.run(scenario)

        assert result.passed is True
        mock_manager.ue.get_ue.assert_called_with("001010123456789")

    @pytest.mark.asyncio
    async def test_run_with_save_as(self, mock_manager):
        """Test running scenario with save_as."""
        runner = ScenarioRunner(mock_manager)

        mock_manager.ue.get_ue = AsyncMock(return_value={"imsi": "001010123456789", "status": "registered"})

        scenario = Scenario(
            name="save_test",
            steps=[
                Step(
                    name="get_ue",
                    action="ue.get",
                    params={"imsi": "001010123456789"},
                    save_as="ue_info",
                ),
            ],
        )

        result = await runner.run(scenario)

        assert result.passed is True
        assert "ue_info" in result.variables

    @pytest.mark.asyncio
    async def test_run_with_condition_skip(self, mock_manager):
        """Test step skipping with condition."""
        runner = ScenarioRunner(mock_manager)

        scenario = Scenario(
            name="condition_test",
            steps=[
                Step(
                    name="skip_step",
                    action="ue.list",
                    condition=Condition(
                        variable="nonexistent",
                        operator=ConditionOperator.DEFINED,
                    ),
                ),
            ],
        )

        result = await runner.run(scenario)

        assert result.passed is True
        assert result.step_results[0].status == StepStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_run_with_failure(self, mock_manager):
        """Test scenario with step failure."""
        runner = ScenarioRunner(mock_manager)

        mock_manager.ue.get_ue = AsyncMock(side_effect=Exception("UE not found"))

        scenario = Scenario(
            name="failure_test",
            steps=[
                Step(
                    name="get_ue",
                    action="ue.get",
                    params={"imsi": "001010123456789"},
                ),
            ],
        )

        result = await runner.run(scenario)

        assert result.passed is False
        assert result.step_results[0].status == StepStatus.FAILED
        assert "UE not found" in result.step_results[0].error

    @pytest.mark.asyncio
    async def test_run_failure_continue(self, mock_manager):
        """Test scenario continues on failure with on_failure=continue."""
        runner = ScenarioRunner(mock_manager)

        mock_manager.ue.get_ue = AsyncMock(side_effect=Exception("UE not found"))

        scenario = Scenario(
            name="continue_test",
            steps=[
                Step(
                    name="get_ue",
                    action="ue.get",
                    params={"imsi": "001010123456789"},
                    on_failure="continue",
                ),
                Step(name="list_ues", action="ue.list"),
            ],
        )

        result = await runner.run(scenario)

        assert result.passed is False
        assert len(result.step_results) == 2  # Both steps executed

    @pytest.mark.asyncio
    async def test_run_with_timeout(self, mock_manager):
        """Test step timeout."""
        runner = ScenarioRunner(mock_manager)

        async def slow_operation(*args, **kwargs):
            await asyncio.sleep(5)
            return True

        mock_manager.ue.list_ues = slow_operation

        scenario = Scenario(
            name="timeout_test",
            steps=[
                Step(
                    name="slow_step",
                    action="ue.list",
                    timeout=0.1,  # Very short timeout
                ),
            ],
        )

        result = await runner.run(scenario)

        assert result.passed is False
        assert "Timeout" in result.step_results[0].error

    @pytest.mark.asyncio
    async def test_run_setup_teardown(self, mock_manager):
        """Test setup and teardown execution."""
        runner = ScenarioRunner(mock_manager)

        scenario = Scenario(
            name="setup_teardown_test",
            setup=[Step(name="setup", action="cell.start")],
            teardown=[Step(name="teardown", action="cell.stop")],
            steps=[Step(name="main", action="ue.list")],
        )

        result = await runner.run(scenario)

        assert result.passed is True
        mock_manager.cell.start.assert_called_once()
        mock_manager.cell.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_teardown_runs_on_failure(self, mock_manager):
        """Test teardown runs even when main steps fail."""
        runner = ScenarioRunner(mock_manager)

        mock_manager.ue.list_ues = AsyncMock(side_effect=Exception("Error"))

        scenario = Scenario(
            name="teardown_test",
            teardown=[Step(name="teardown", action="cell.stop")],
            steps=[Step(name="main", action="ue.list")],
        )

        result = await runner.run(scenario)

        assert result.passed is False
        mock_manager.cell.stop.assert_called_once()  # Teardown still ran

    def test_register_custom_action(self, mock_manager):
        """Test registering custom action."""
        runner = ScenarioRunner(mock_manager)

        async def custom_handler(params):
            return {"custom": True}

        runner.register_action("custom.action", custom_handler)

        assert "custom.action" in runner._action_map

    @pytest.mark.asyncio
    async def test_variable_resolution(self, mock_manager):
        """Test variable resolution in params."""
        runner = ScenarioRunner(mock_manager)

        variables = {"name": "test", "count": 5}

        # Test simple substitution
        resolved = runner._resolve_variables(
            {"key": "${name}", "num": "${count}"},
            variables,
        )
        assert resolved["key"] == "test"
        assert resolved["num"] == 5

    @pytest.mark.asyncio
    async def test_variable_resolution_nested(self, mock_manager):
        """Test nested variable resolution."""
        runner = ScenarioRunner(mock_manager)

        variables = {"imsi": "001010123456789"}

        resolved = runner._resolve_variables(
            {"outer": {"inner": "${imsi}"}},
            variables,
        )
        assert resolved["outer"]["inner"] == "001010123456789"

    def test_condition_evaluation_defined(self, mock_manager):
        """Test condition evaluation - defined."""
        runner = ScenarioRunner(mock_manager)

        condition = Condition("var", ConditionOperator.DEFINED)
        assert runner._evaluate_condition(condition, {"var": "value"}) is True
        assert runner._evaluate_condition(condition, {}) is False

    def test_condition_evaluation_equals(self, mock_manager):
        """Test condition evaluation - equals."""
        runner = ScenarioRunner(mock_manager)

        condition = Condition("var", ConditionOperator.EQUALS, "expected")
        assert runner._evaluate_condition(condition, {"var": "expected"}) is True
        assert runner._evaluate_condition(condition, {"var": "other"}) is False

    def test_condition_evaluation_contains(self, mock_manager):
        """Test condition evaluation - contains."""
        runner = ScenarioRunner(mock_manager)

        condition = Condition("var", ConditionOperator.CONTAINS, "test")
        assert runner._evaluate_condition(condition, {"var": "this is a test"}) is True
        assert runner._evaluate_condition(condition, {"var": "no match"}) is False

    def test_condition_evaluation_greater_than(self, mock_manager):
        """Test condition evaluation - greater than."""
        runner = ScenarioRunner(mock_manager)

        condition = Condition("var", ConditionOperator.GREATER_THAN, 10)
        assert runner._evaluate_condition(condition, {"var": 15}) is True
        assert runner._evaluate_condition(condition, {"var": 5}) is False
