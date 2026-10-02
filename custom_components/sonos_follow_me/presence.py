"""Presence latch, independent of Home Assistant."""

from dataclasses import dataclass


@dataclass
class Presence:
    """Only a primary detection may arm primary mode; all sensors may hold it."""

    mode: str
    occupied: bool = False

    def update(self, primary: str, others: list[str]) -> str:
        """Return occupied, clear or idle. Unknown sensors never mean empty."""
        values = [primary, *others]
        if primary == "on" or (self.mode == "equal" and "on" in values):
            self.occupied = True
        if not self.occupied:
            return "idle"
        return "clear" if all(value == "off" for value in values) else "occupied"

    def expire(self) -> None:
        """Disarm after the uninterrupted clear delay."""
        self.occupied = False
