"""SimulationWorker: generates synthetic profile data for offline development.

Mimics the DeviceWorker interface using simulated data — no hardware required.
"""

import logging
import random
import math
import time
from threading import Event

from PySide6.QtCore import QObject, Signal, Slot

logger = logging.getLogger(__name__)


class SimulationWorker(QObject):
    """Simulated measurement worker for offline development and testing."""

    point_acquired = Signal(int, float, float)
    measurement_finished = Signal()
    connection_established = Signal()
    connection_lost = Signal()
    error_occurred = Signal(str)
    log_message = Signal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stop_event = Event()
        self._session_id: int = 0
        self._target_count: int = 200
        self._extraction_config: dict = {}
        self._ethernet_config = None

    @Slot()
    def request_stop(self):
        self._stop_event.set()

    @Slot(int, int, dict, object)
    def run(self, session_id: int, target_count: int,
            extraction_config: dict, ethernet_config):
        """Simulated acquisition loop."""
        self._stop_event.clear()
        self._session_id = session_id
        self._target_count = target_count
        self._extraction_config = extraction_config

        try:
            self._do_simulation()
        except Exception as e:
            logger.exception(f"Simulation error: {e}")
            self.error_occurred.emit(f"Simulation error: {e}")

    def _do_simulation(self):
        """Generate synthetic measurement data."""

        # Simulate connection delay
        self.log_message.emit("Simulation: Connecting to device...", logging.INFO)
        time.sleep(0.3)
        self.connection_established.emit()

        self.log_message.emit("Simulation: Starting measurement...", logging.INFO)
        time.sleep(0.2)

        acquired_count = 0
        target = self._target_count

        # Parameters for synthetic data — simulates a resin bump profile
        # Values oscillate with slight noise around 5.0mm, with occasional peaks
        base_value = 5.0  # mm
        x_position = 12.34  # mm (simulated X position of max Z)

        self.log_message.emit(
            f"Simulation: Acquiring {target} points...", logging.INFO
        )

        while acquired_count < target and not self._stop_event.is_set():
            # Generate a measurement value with:
            # - Sine wave oscillation to simulate surface variation
            # - Random noise
            # - Occasional "defect" spike
            phase = acquired_count / target * 4 * math.pi
            sine_component = 0.15 * math.sin(phase)
            noise = random.gauss(0, 0.02)

            # 5% chance of a larger deviation (simulates measurement variation)
            if random.random() < 0.05:
                spike = random.uniform(-0.3, 0.5)
            else:
                spike = 0.0

            value = base_value + sine_component + noise + spike
            value = round(max(0.1, value), 6)

            acquired_count += 1
            self.point_acquired.emit(acquired_count, value, x_position)

            # Simulate measurement interval (~50ms = 20 Hz acquisition rate)
            time.sleep(0.05)

        self.log_message.emit(
            f"Simulation: Complete. Acquired {acquired_count} points.",
            logging.INFO
        )
        self.connection_lost.emit()
        self.measurement_finished.emit()
