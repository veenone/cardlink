"""Scenario Runner for network simulator integration.

This module provides declarative test scenario definition and execution
using YAML configuration files.

Classes:
    Step: Single test step with action, parameters, and conditions
    Scenario: Complete test scenario with multiple steps
    ScenarioResult: Result of scenario execution
    ScenarioRunner: Execution engine for scenarios
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

import yaml

from cardlink.netsim.exceptions import ConfigurationError
from cardlink.netsim.types import NetworkEventType

log = logging.getLogger(__name__)


class StepStatus(Enum):
    """Step execution status."""

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ConditionOperator(Enum):
    """Condition evaluation operators."""

    DEFINED = "defined"
    NOT_DEFINED = "not_defined"
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"


@dataclass
class Condition:
    """Condition for conditional step execution.

    Attributes:
        variable: Variable name to evaluate.
        operator: Comparison operator.
        value: Expected value for comparison operators.
    """

    variable: str
    operator: ConditionOperator
    value: Optional[Any] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Condition":
        """Create Condition from dictionary.

        Args:
            data: Dictionary with variable, operator, and optional value.

        Returns:
            Condition instance.

        Raises:
            ConfigurationError: If condition is invalid.
        """
        if "variable" not in data:
            raise ConfigurationError("Condition missing 'variable' field")

        operator_str = data.get("operator", "defined")
        try:
            operator = ConditionOperator(operator_str)
        except ValueError:
            valid = [op.value for op in ConditionOperator]
            raise ConfigurationError(
                f"Invalid condition operator '{operator_str}'. "
                f"Valid operators: {valid}"
            )

        return cls(
            variable=data["variable"],
            operator=operator,
            value=data.get("value"),
        )


@dataclass
class Step:
    """Single test step in a scenario.

    Attributes:
        name: Step name for identification.
        action: Action to execute (e.g., "ue.wait_for_registration").
        params: Parameters for the action.
        timeout: Timeout in seconds for step execution.
        condition: Optional condition for step execution.
        on_failure: Action to take on failure ("continue", "stop", "skip").
        save_as: Variable name to save step result.
    """

    name: str
    action: str
    params: dict[str, Any] = field(default_factory=dict)
    timeout: float = 30.0
    condition: Optional[Condition] = None
    on_failure: str = "stop"
    save_as: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], index: int = 0) -> "Step":
        """Create Step from dictionary.

        Args:
            data: Dictionary with step configuration.
            index: Step index for default naming.

        Returns:
            Step instance.

        Raises:
            ConfigurationError: If step is invalid.
        """
        if "action" not in data:
            raise ConfigurationError(f"Step {index} missing 'action' field")

        condition = None
        if "condition" in data:
            condition = Condition.from_dict(data["condition"])

        return cls(
            name=data.get("name", f"step_{index}"),
            action=data["action"],
            params=data.get("params", {}),
            timeout=float(data.get("timeout", 30.0)),
            condition=condition,
            on_failure=data.get("on_failure", "stop"),
            save_as=data.get("save_as"),
        )


@dataclass
class StepResult:
    """Result of a single step execution.

    Attributes:
        step_name: Name of the step.
        status: Execution status.
        result: Result data from the action.
        error: Error message if failed.
        duration_ms: Execution duration in milliseconds.
        timestamp: When the step was executed.
    """

    step_name: str
    status: StepStatus
    result: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "step_name": self.step_name,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class Scenario:
    """Complete test scenario with multiple steps.

    Attributes:
        name: Scenario name.
        description: Scenario description.
        steps: List of steps to execute.
        variables: Initial variables for the scenario.
        tags: Tags for categorization.
        setup: Optional setup steps to run before main steps.
        teardown: Optional teardown steps to run after main steps.
    """

    name: str
    description: str = ""
    steps: list[Step] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    setup: list[Step] = field(default_factory=list)
    teardown: list[Step] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, yaml_content: str) -> "Scenario":
        """Create Scenario from YAML content.

        Args:
            yaml_content: YAML string defining the scenario.

        Returns:
            Scenario instance.

        Raises:
            ConfigurationError: If YAML is invalid.
        """
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML: {e}")

        if not isinstance(data, dict):
            raise ConfigurationError("Scenario must be a YAML dictionary")

        return cls._from_dict(data)

    @classmethod
    def from_file(cls, file_path: str) -> "Scenario":
        """Load Scenario from YAML file.

        Args:
            file_path: Path to YAML file.

        Returns:
            Scenario instance.

        Raises:
            ConfigurationError: If file not found or invalid.
        """
        path = Path(file_path)
        if not path.exists():
            raise ConfigurationError(f"Scenario file not found: {file_path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                return cls.from_yaml(f.read())
        except IOError as e:
            raise ConfigurationError(f"Cannot read scenario file: {e}")

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> "Scenario":
        """Create Scenario from dictionary."""
        if "name" not in data:
            raise ConfigurationError("Scenario missing 'name' field")

        # Parse steps
        steps = []
        for i, step_data in enumerate(data.get("steps", [])):
            steps.append(Step.from_dict(step_data, i))

        # Parse setup steps
        setup = []
        for i, step_data in enumerate(data.get("setup", [])):
            setup.append(Step.from_dict(step_data, i))

        # Parse teardown steps
        teardown = []
        for i, step_data in enumerate(data.get("teardown", [])):
            teardown.append(Step.from_dict(step_data, i))

        return cls(
            name=data["name"],
            description=data.get("description", ""),
            steps=steps,
            variables=data.get("variables", {}),
            tags=data.get("tags", []),
            setup=setup,
            teardown=teardown,
        )


@dataclass
class ScenarioResult:
    """Result of scenario execution.

    Attributes:
        scenario_name: Name of the executed scenario.
        passed: Whether scenario passed.
        step_results: Results of each step.
        variables: Final variable values.
        duration_ms: Total execution duration.
        started_at: When execution started.
        ended_at: When execution ended.
    """

    scenario_name: str
    passed: bool
    step_results: list[StepResult] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "scenario_name": self.scenario_name,
            "passed": self.passed,
            "step_results": [r.to_dict() for r in self.step_results],
            "variables": self.variables,
            "duration_ms": self.duration_ms,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
        }

    @property
    def passed_count(self) -> int:
        """Count of passed steps."""
        return sum(1 for r in self.step_results if r.status == StepStatus.PASSED)

    @property
    def failed_count(self) -> int:
        """Count of failed steps."""
        return sum(1 for r in self.step_results if r.status == StepStatus.FAILED)

    @property
    def skipped_count(self) -> int:
        """Count of skipped steps."""
        return sum(1 for r in self.step_results if r.status == StepStatus.SKIPPED)


class ScenarioRunner:
    """Execution engine for test scenarios.

    Provides step-by-step scenario execution with:
    - Action mapping to simulator manager operations
    - Variable substitution in parameters
    - Condition evaluation for conditional steps
    - Result collection and reporting

    Attributes:
        manager: The simulator manager for executing actions.

    Example:
        >>> runner = ScenarioRunner(simulator_manager)
        >>> scenario = Scenario.from_file("test.yaml")
        >>> result = await runner.run(scenario)
        >>> print(f"Passed: {result.passed}")
    """

    # Variable pattern: ${variable_name}
    VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")

    def __init__(self, manager: Any) -> None:
        """Initialize Scenario Runner.

        Args:
            manager: SimulatorManager instance for action execution.
        """
        self._manager = manager
        self._action_map: dict[str, Callable] = {}
        self._setup_action_map()

    def _setup_action_map(self) -> None:
        """Setup mapping from action strings to manager methods."""
        # UE actions
        self._action_map["ue.list"] = self._action_ue_list
        self._action_map["ue.get"] = self._action_ue_get
        self._action_map["ue.wait_for_registration"] = self._action_ue_wait
        self._action_map["ue.detach"] = self._action_ue_detach

        # Session actions
        self._action_map["session.list"] = self._action_session_list
        self._action_map["session.get"] = self._action_session_get
        self._action_map["session.release"] = self._action_session_release

        # SMS actions
        self._action_map["sms.send"] = self._action_sms_send
        self._action_map["sms.send_trigger"] = self._action_sms_trigger

        # Cell actions
        self._action_map["cell.start"] = self._action_cell_start
        self._action_map["cell.stop"] = self._action_cell_stop
        self._action_map["cell.status"] = self._action_cell_status
        self._action_map["cell.configure"] = self._action_cell_configure

        # Trigger actions
        self._action_map["trigger.paging"] = self._action_trigger_paging
        self._action_map["trigger.handover"] = self._action_trigger_handover
        self._action_map["trigger.detach"] = self._action_trigger_detach

        # Utility actions
        self._action_map["wait"] = self._action_wait
        self._action_map["log"] = self._action_log
        self._action_map["assert"] = self._action_assert

    # =========================================================================
    # Scenario Execution
    # =========================================================================

    async def run(
        self,
        scenario: Scenario,
        variables: Optional[dict[str, Any]] = None,
    ) -> ScenarioResult:
        """Execute a scenario.

        Args:
            scenario: The scenario to execute.
            variables: Additional variables to merge with scenario variables.

        Returns:
            ScenarioResult with execution details.
        """
        started_at = datetime.utcnow()

        # Initialize variables
        current_vars = dict(scenario.variables)
        if variables:
            current_vars.update(variables)

        step_results: list[StepResult] = []
        passed = True

        log.info(f"Starting scenario: {scenario.name}")

        # Run setup steps
        for step in scenario.setup:
            result = await self._execute_step(step, current_vars)
            step_results.append(result)

            if result.status == StepStatus.FAILED:
                log.error(f"Setup step failed: {step.name}")
                passed = False
                break

            if step.save_as and result.result is not None:
                current_vars[step.save_as] = result.result

        # Run main steps (only if setup passed)
        if passed:
            for step in scenario.steps:
                result = await self._execute_step(step, current_vars)
                step_results.append(result)

                if result.status == StepStatus.FAILED:
                    passed = False
                    if step.on_failure == "stop":
                        log.error(f"Step failed, stopping: {step.name}")
                        break
                    elif step.on_failure == "skip":
                        log.warning(f"Step failed, skipping remaining: {step.name}")
                        break
                    # "continue" - keep going

                if step.save_as and result.result is not None:
                    current_vars[step.save_as] = result.result

        # Run teardown steps (always run)
        for step in scenario.teardown:
            result = await self._execute_step(step, current_vars)
            step_results.append(result)

            if step.save_as and result.result is not None:
                current_vars[step.save_as] = result.result

        ended_at = datetime.utcnow()
        duration_ms = (ended_at - started_at).total_seconds() * 1000

        log.info(
            f"Scenario {scenario.name} completed: "
            f"{'PASSED' if passed else 'FAILED'} in {duration_ms:.1f}ms"
        )

        return ScenarioResult(
            scenario_name=scenario.name,
            passed=passed,
            step_results=step_results,
            variables=current_vars,
            duration_ms=duration_ms,
            started_at=started_at,
            ended_at=ended_at,
        )

    async def _execute_step(
        self,
        step: Step,
        variables: dict[str, Any],
    ) -> StepResult:
        """Execute a single step.

        Args:
            step: The step to execute.
            variables: Current variable values.

        Returns:
            StepResult with execution details.
        """
        started = datetime.utcnow()

        # Check condition
        if step.condition:
            if not self._evaluate_condition(step.condition, variables):
                log.debug(f"Step skipped (condition not met): {step.name}")
                return StepResult(
                    step_name=step.name,
                    status=StepStatus.SKIPPED,
                    timestamp=started,
                )

        # Resolve variables in params
        resolved_params = self._resolve_variables(step.params, variables)

        log.debug(f"Executing step: {step.name} ({step.action})")

        try:
            # Get action handler
            if step.action not in self._action_map:
                raise ConfigurationError(f"Unknown action: {step.action}")

            handler = self._action_map[step.action]

            # Execute with timeout
            import asyncio

            result = await asyncio.wait_for(
                handler(resolved_params),
                timeout=step.timeout,
            )

            duration_ms = (datetime.utcnow() - started).total_seconds() * 1000

            return StepResult(
                step_name=step.name,
                status=StepStatus.PASSED,
                result=result,
                duration_ms=duration_ms,
                timestamp=started,
            )

        except asyncio.TimeoutError:
            duration_ms = (datetime.utcnow() - started).total_seconds() * 1000
            log.error(f"Step timed out after {step.timeout}s: {step.name}")

            return StepResult(
                step_name=step.name,
                status=StepStatus.FAILED,
                error=f"Timeout after {step.timeout}s",
                duration_ms=duration_ms,
                timestamp=started,
            )

        except Exception as e:
            duration_ms = (datetime.utcnow() - started).total_seconds() * 1000
            log.error(f"Step failed: {step.name} - {e}")

            return StepResult(
                step_name=step.name,
                status=StepStatus.FAILED,
                error=str(e),
                duration_ms=duration_ms,
                timestamp=started,
            )

    # =========================================================================
    # Condition Evaluation
    # =========================================================================

    def _evaluate_condition(
        self,
        condition: Condition,
        variables: dict[str, Any],
    ) -> bool:
        """Evaluate a condition.

        Args:
            condition: The condition to evaluate.
            variables: Current variable values.

        Returns:
            True if condition is met, False otherwise.
        """
        var_value = variables.get(condition.variable)

        if condition.operator == ConditionOperator.DEFINED:
            return condition.variable in variables

        if condition.operator == ConditionOperator.NOT_DEFINED:
            return condition.variable not in variables

        if condition.operator == ConditionOperator.EQUALS:
            return var_value == condition.value

        if condition.operator == ConditionOperator.NOT_EQUALS:
            return var_value != condition.value

        if condition.operator == ConditionOperator.CONTAINS:
            if isinstance(var_value, (str, list, dict)):
                return condition.value in var_value
            return False

        if condition.operator == ConditionOperator.NOT_CONTAINS:
            if isinstance(var_value, (str, list, dict)):
                return condition.value not in var_value
            return True

        if condition.operator == ConditionOperator.GREATER_THAN:
            try:
                return float(var_value) > float(condition.value)
            except (ValueError, TypeError):
                return False

        if condition.operator == ConditionOperator.LESS_THAN:
            try:
                return float(var_value) < float(condition.value)
            except (ValueError, TypeError):
                return False

        return False

    # =========================================================================
    # Variable Resolution
    # =========================================================================

    def _resolve_variables(
        self,
        params: dict[str, Any],
        variables: dict[str, Any],
    ) -> dict[str, Any]:
        """Resolve variables in parameters.

        Substitutes ${var_name} patterns with variable values.

        Args:
            params: Parameters with possible variable references.
            variables: Current variable values.

        Returns:
            Parameters with variables resolved.
        """
        resolved: dict[str, Any] = {}

        for key, value in params.items():
            resolved[key] = self._resolve_value(value, variables)

        return resolved

    def _resolve_value(self, value: Any, variables: dict[str, Any]) -> Any:
        """Resolve variables in a single value.

        Args:
            value: Value to resolve.
            variables: Current variable values.

        Returns:
            Resolved value.
        """
        if isinstance(value, str):
            # Check for full variable replacement (${var})
            if value.startswith("${") and value.endswith("}"):
                var_name = value[2:-1]
                if var_name in variables:
                    return variables[var_name]
                log.warning(f"Undefined variable: {var_name}")
                return value

            # Check for embedded variables
            def replacer(match: re.Match) -> str:
                var_name = match.group(1)
                if var_name in variables:
                    return str(variables[var_name])
                log.warning(f"Undefined variable: {var_name}")
                return match.group(0)

            return self.VAR_PATTERN.sub(replacer, value)

        elif isinstance(value, dict):
            return {k: self._resolve_value(v, variables) for k, v in value.items()}

        elif isinstance(value, list):
            return [self._resolve_value(item, variables) for item in value]

        return value

    # =========================================================================
    # Action Handlers
    # =========================================================================

    async def _action_ue_list(self, params: dict[str, Any]) -> list:
        """List UEs."""
        return await self._manager.ue.list_ues()

    async def _action_ue_get(self, params: dict[str, Any]) -> Any:
        """Get UE by IMSI."""
        imsi = params.get("imsi")
        if not imsi:
            raise ValueError("Missing 'imsi' parameter")
        return await self._manager.ue.get_ue(imsi)

    async def _action_ue_wait(self, params: dict[str, Any]) -> Any:
        """Wait for UE registration."""
        imsi = params.get("imsi")
        timeout = params.get("timeout", 30)
        if not imsi:
            raise ValueError("Missing 'imsi' parameter")
        return await self._manager.ue.wait_for_registration(imsi, timeout=timeout)

    async def _action_ue_detach(self, params: dict[str, Any]) -> bool:
        """Detach UE."""
        imsi = params.get("imsi")
        if not imsi:
            raise ValueError("Missing 'imsi' parameter")
        return await self._manager.ue.detach_ue(imsi)

    async def _action_session_list(self, params: dict[str, Any]) -> list:
        """List sessions."""
        imsi = params.get("imsi")
        return await self._manager.sessions.list_sessions(imsi=imsi)

    async def _action_session_get(self, params: dict[str, Any]) -> Any:
        """Get session by ID."""
        session_id = params.get("session_id")
        if not session_id:
            raise ValueError("Missing 'session_id' parameter")
        return await self._manager.sessions.get_session(session_id)

    async def _action_session_release(self, params: dict[str, Any]) -> bool:
        """Release session."""
        session_id = params.get("session_id")
        if not session_id:
            raise ValueError("Missing 'session_id' parameter")
        return await self._manager.sessions.release_session(session_id)

    async def _action_sms_send(self, params: dict[str, Any]) -> str:
        """Send SMS."""
        imsi = params.get("imsi")
        pdu = params.get("pdu")
        if not imsi or not pdu:
            raise ValueError("Missing 'imsi' or 'pdu' parameter")

        # Convert hex string to bytes if needed
        if isinstance(pdu, str):
            pdu = bytes.fromhex(pdu)

        return await self._manager.sms.send_mt_sms(imsi, pdu)

    async def _action_sms_trigger(self, params: dict[str, Any]) -> str:
        """Send OTA trigger SMS."""
        imsi = params.get("imsi")
        tar = params.get("tar")
        if not imsi or not tar:
            raise ValueError("Missing 'imsi' or 'tar' parameter")

        # Convert hex string to bytes if needed
        if isinstance(tar, str):
            tar = bytes.fromhex(tar)

        return await self._manager.sms.send_ota_trigger(imsi, tar)

    async def _action_cell_start(self, params: dict[str, Any]) -> bool:
        """Start cell."""
        return await self._manager.cell.start()

    async def _action_cell_stop(self, params: dict[str, Any]) -> bool:
        """Stop cell."""
        return await self._manager.cell.stop()

    async def _action_cell_status(self, params: dict[str, Any]) -> Any:
        """Get cell status."""
        return await self._manager.cell.get_status()

    async def _action_cell_configure(self, params: dict[str, Any]) -> bool:
        """Configure cell."""
        return await self._manager.cell.configure(params)

    async def _action_trigger_paging(self, params: dict[str, Any]) -> bool:
        """Trigger paging."""
        imsi = params.get("imsi")
        if not imsi:
            raise ValueError("Missing 'imsi' parameter")
        paging_type = params.get("paging_type", "ps")
        return await self._manager.triggers.trigger_paging(imsi, paging_type)

    async def _action_trigger_handover(self, params: dict[str, Any]) -> bool:
        """Trigger handover."""
        imsi = params.get("imsi")
        target_cell = params.get("target_cell")
        if not imsi or target_cell is None:
            raise ValueError("Missing 'imsi' or 'target_cell' parameter")
        return await self._manager.triggers.trigger_handover(imsi, target_cell)

    async def _action_trigger_detach(self, params: dict[str, Any]) -> bool:
        """Trigger detach."""
        imsi = params.get("imsi")
        if not imsi:
            raise ValueError("Missing 'imsi' parameter")
        cause = params.get("cause", "reattach_required")
        return await self._manager.triggers.trigger_detach(imsi, cause)

    async def _action_wait(self, params: dict[str, Any]) -> None:
        """Wait for specified duration."""
        import asyncio

        seconds = params.get("seconds", 1)
        await asyncio.sleep(seconds)

    async def _action_log(self, params: dict[str, Any]) -> None:
        """Log a message."""
        message = params.get("message", "")
        level = params.get("level", "info").lower()

        if level == "debug":
            log.debug(message)
        elif level == "warning":
            log.warning(message)
        elif level == "error":
            log.error(message)
        else:
            log.info(message)

    async def _action_assert(self, params: dict[str, Any]) -> bool:
        """Assert a condition."""
        condition = params.get("condition")
        message = params.get("message", "Assertion failed")

        if not condition:
            raise AssertionError(message)
        return True

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def register_action(
        self,
        action_name: str,
        handler: Callable[[dict[str, Any]], Any],
    ) -> None:
        """Register a custom action handler.

        Args:
            action_name: Name for the action (e.g., "custom.my_action").
            handler: Async handler function taking params dict.
        """
        self._action_map[action_name] = handler

    def get_available_actions(self) -> list[str]:
        """Get list of available actions.

        Returns:
            List of action names.
        """
        return sorted(self._action_map.keys())
