"""Workshop lifecycle phase constants shared across operator handlers."""

from enum import StrEnum


class WorkshopPhase(StrEnum):
    PENDING = "Pending"
    CREATING = "Creating"
    STARTING = "Starting"
    READY = "Ready"
    RUNNING = "Running"
    TERMINATING = "Terminating"
    FAILED = "Failed"
