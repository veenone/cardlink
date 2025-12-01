"""Network Event Triggers for network simulator integration.

This module provides programmatic triggering of network events
such as paging, handover, and cell outages.

Classes:
    TriggerManager: Manager for triggering network events
"""

import logging
from datetime import datetime
from typing import Any, Optional

from cardlink.netsim.interface import SimulatorInterface
from cardlink.netsim.types import NetworkEventType

log = logging.getLogger(__name__)


class TriggerManager:
    """Manager for triggering network events.

    Provides programmatic network event triggering with:
    - UE triggers (paging, detach)
    - Cell triggers (handover, outage)
    - Custom event triggers
    - Trigger validation and logging

    Attributes:
        adapter: The underlying simulator adapter.

    Example:
        >>> trigger_manager = TriggerManager(adapter, event_emitter)
        >>> # Trigger paging
        >>> await trigger_manager.trigger_paging("001010123456789")
        >>> # Trigger handover
        >>> await trigger_manager.trigger_handover("001010123456789", target_cell=2)
    """

    def __init__(self, adapter: SimulatorInterface, event_emitter: Any) -> None:
        """Initialize Trigger Manager.

        Args:
            adapter: The simulator adapter for trigger operations.
            event_emitter: Event emitter for broadcasting trigger events.
        """
        self._adapter = adapter
        self._events = event_emitter

        # Trigger history
        self._trigger_history: list[dict[str, Any]] = []
        self._max_history = 1000

    # =========================================================================
    # UE Triggers
    # =========================================================================

    async def trigger_paging(
        self,
        imsi: str,
        paging_type: str = "ps",
        timeout: float = 30.0,
    ) -> bool:
        """Trigger paging for a UE.

        Sends a paging request to the specified UE.

        Args:
            imsi: IMSI of the target UE.
            paging_type: Type of paging ("ps" for PS paging, "cs" for CS paging).
            timeout: Timeout in seconds.

        Returns:
            True if paging was triggered successfully.
        """
        self._validate_imsi(imsi)
        log.info(f"Triggering {paging_type} paging for IMSI: {imsi}")

        try:
            result = await self._adapter.trigger_event(
                event_type="paging",
                params={
                    "imsi": imsi,
                    "paging_type": paging_type,
                    "timeout": timeout,
                },
            )

            self._record_trigger("paging", imsi, {"paging_type": paging_type}, result)

            if result:
                await self._events.emit("trigger_executed", {
                    "trigger_type": "paging",
                    "imsi": imsi,
                    "paging_type": paging_type,
                })

            return result

        except Exception as e:
            log.error(f"Paging trigger failed: {e}")
            self._record_trigger("paging", imsi, {"paging_type": paging_type}, False, str(e))
            raise

    async def trigger_detach(
        self,
        imsi: str,
        cause: str = "reattach_required",
    ) -> bool:
        """Trigger network-initiated detach for a UE.

        Forces the network to detach the specified UE.

        Args:
            imsi: IMSI of the target UE.
            cause: Detach cause (e.g., "reattach_required", "eps_detach").

        Returns:
            True if detach was triggered successfully.
        """
        self._validate_imsi(imsi)
        log.info(f"Triggering detach for IMSI: {imsi}, cause: {cause}")

        try:
            result = await self._adapter.trigger_event(
                event_type="detach",
                params={
                    "imsi": imsi,
                    "cause": cause,
                },
            )

            self._record_trigger("detach", imsi, {"cause": cause}, result)

            if result:
                await self._events.emit("trigger_executed", {
                    "trigger_type": "detach",
                    "imsi": imsi,
                    "cause": cause,
                })

            return result

        except Exception as e:
            log.error(f"Detach trigger failed: {e}")
            self._record_trigger("detach", imsi, {"cause": cause}, False, str(e))
            raise

    async def trigger_service_request(
        self,
        imsi: str,
        service_type: str = "data",
    ) -> bool:
        """Trigger a service request for a UE.

        Forces the UE to perform a service request procedure.

        Args:
            imsi: IMSI of the target UE.
            service_type: Type of service ("data", "signaling").

        Returns:
            True if service request was triggered.
        """
        self._validate_imsi(imsi)
        log.info(f"Triggering service request for IMSI: {imsi}")

        try:
            result = await self._adapter.trigger_event(
                event_type="service_request",
                params={
                    "imsi": imsi,
                    "service_type": service_type,
                },
            )

            self._record_trigger("service_request", imsi, {"service_type": service_type}, result)

            if result:
                await self._events.emit("trigger_executed", {
                    "trigger_type": "service_request",
                    "imsi": imsi,
                    "service_type": service_type,
                })

            return result

        except Exception as e:
            log.error(f"Service request trigger failed: {e}")
            raise

    # =========================================================================
    # Cell Triggers
    # =========================================================================

    async def trigger_handover(
        self,
        imsi: str,
        target_cell: int,
        handover_type: str = "intra",
    ) -> bool:
        """Trigger handover for a UE.

        Forces a handover to the specified target cell.

        Args:
            imsi: IMSI of the target UE.
            target_cell: Target cell ID.
            handover_type: Type of handover ("intra", "inter", "x2", "s1").

        Returns:
            True if handover was triggered successfully.
        """
        self._validate_imsi(imsi)
        log.info(f"Triggering {handover_type} handover for IMSI: {imsi} to cell {target_cell}")

        try:
            result = await self._adapter.trigger_event(
                event_type="handover",
                params={
                    "imsi": imsi,
                    "target_cell": target_cell,
                    "handover_type": handover_type,
                },
            )

            self._record_trigger(
                "handover", imsi,
                {"target_cell": target_cell, "handover_type": handover_type},
                result
            )

            if result:
                await self._events.emit("trigger_executed", {
                    "trigger_type": "handover",
                    "imsi": imsi,
                    "target_cell": target_cell,
                    "handover_type": handover_type,
                })

            return result

        except Exception as e:
            log.error(f"Handover trigger failed: {e}")
            raise

    async def trigger_cell_outage(
        self,
        duration: float = 10.0,
        cell_id: Optional[int] = None,
    ) -> bool:
        """Trigger a cell outage.

        Simulates a cell outage for the specified duration.

        Args:
            duration: Outage duration in seconds.
            cell_id: Target cell ID (None for primary cell).

        Returns:
            True if outage was triggered successfully.
        """
        log.info(f"Triggering cell outage for {duration}s" + (f" on cell {cell_id}" if cell_id else ""))

        try:
            result = await self._adapter.trigger_event(
                event_type="cell_outage",
                params={
                    "duration": duration,
                    "cell_id": cell_id,
                },
            )

            self._record_trigger(
                "cell_outage", None,
                {"duration": duration, "cell_id": cell_id},
                result
            )

            if result:
                await self._events.emit("trigger_executed", {
                    "trigger_type": "cell_outage",
                    "duration": duration,
                    "cell_id": cell_id,
                })

            return result

        except Exception as e:
            log.error(f"Cell outage trigger failed: {e}")
            raise

    async def trigger_rlf(
        self,
        imsi: str,
    ) -> bool:
        """Trigger Radio Link Failure for a UE.

        Simulates a radio link failure causing connection re-establishment.

        Args:
            imsi: IMSI of the target UE.

        Returns:
            True if RLF was triggered successfully.
        """
        self._validate_imsi(imsi)
        log.info(f"Triggering RLF for IMSI: {imsi}")

        try:
            result = await self._adapter.trigger_event(
                event_type="rlf",
                params={"imsi": imsi},
            )

            self._record_trigger("rlf", imsi, {}, result)

            if result:
                await self._events.emit("trigger_executed", {
                    "trigger_type": "rlf",
                    "imsi": imsi,
                })

            return result

        except Exception as e:
            log.error(f"RLF trigger failed: {e}")
            raise

    async def trigger_tau(
        self,
        imsi: str,
        tau_type: str = "periodic",
    ) -> bool:
        """Trigger Tracking Area Update for a UE.

        Forces a TAU procedure.

        Args:
            imsi: IMSI of the target UE.
            tau_type: Type of TAU ("periodic", "normal").

        Returns:
            True if TAU was triggered.
        """
        self._validate_imsi(imsi)
        log.info(f"Triggering {tau_type} TAU for IMSI: {imsi}")

        try:
            result = await self._adapter.trigger_event(
                event_type="tau",
                params={
                    "imsi": imsi,
                    "tau_type": tau_type,
                },
            )

            self._record_trigger("tau", imsi, {"tau_type": tau_type}, result)

            if result:
                await self._events.emit("trigger_executed", {
                    "trigger_type": "tau",
                    "imsi": imsi,
                    "tau_type": tau_type,
                })

            return result

        except Exception as e:
            log.error(f"TAU trigger failed: {e}")
            raise

    # =========================================================================
    # Custom Triggers
    # =========================================================================

    async def trigger_custom(
        self,
        event_type: str,
        params: dict[str, Any],
    ) -> bool:
        """Trigger a custom network event.

        Args:
            event_type: Type of event to trigger.
            params: Event parameters.

        Returns:
            True if event was triggered successfully.
        """
        log.info(f"Triggering custom event: {event_type}")

        try:
            result = await self._adapter.trigger_event(
                event_type=event_type,
                params=params,
            )

            self._record_trigger(
                event_type,
                params.get("imsi"),
                params,
                result
            )

            if result:
                await self._events.emit("trigger_executed", {
                    "trigger_type": event_type,
                    **params,
                })

            return result

        except Exception as e:
            log.error(f"Custom trigger failed: {e}")
            raise

    # =========================================================================
    # Validation and History
    # =========================================================================

    def _validate_imsi(self, imsi: str) -> None:
        """Validate IMSI format.

        Args:
            imsi: IMSI to validate.

        Raises:
            ValueError: If IMSI is invalid.
        """
        if not imsi:
            raise ValueError("IMSI cannot be empty")

        if not imsi.isdigit():
            raise ValueError("IMSI must contain only digits")

        if len(imsi) < 14 or len(imsi) > 15:
            raise ValueError("IMSI must be 14-15 digits")

    def _record_trigger(
        self,
        trigger_type: str,
        imsi: Optional[str],
        params: dict[str, Any],
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """Record a trigger in history."""
        record = {
            "trigger_type": trigger_type,
            "imsi": imsi,
            "params": params,
            "success": success,
            "error": error,
            "timestamp": datetime.utcnow().isoformat(),
        }

        self._trigger_history.append(record)

        # Trim history
        if len(self._trigger_history) > self._max_history:
            self._trigger_history = self._trigger_history[-self._max_history:]

    def get_trigger_history(
        self,
        limit: int = 100,
        trigger_type: Optional[str] = None,
        imsi: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Get trigger history.

        Args:
            limit: Maximum number of records to return.
            trigger_type: Filter by trigger type.
            imsi: Filter by IMSI.

        Returns:
            List of trigger records.
        """
        history = self._trigger_history.copy()

        if trigger_type:
            history = [h for h in history if h["trigger_type"] == trigger_type]

        if imsi:
            history = [h for h in history if h["imsi"] == imsi]

        return history[-limit:]

    def clear_history(self) -> int:
        """Clear trigger history.

        Returns:
            Number of records cleared.
        """
        count = len(self._trigger_history)
        self._trigger_history.clear()
        return count

    @property
    def supported_triggers(self) -> list[str]:
        """Get list of supported trigger types."""
        return [
            "paging",
            "detach",
            "service_request",
            "handover",
            "cell_outage",
            "rlf",
            "tau",
            "custom",
        ]
