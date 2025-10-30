"""
PyFluff - Modern Python Controller for Furby Connect

A complete rewrite of bluefluff in modern Python 3.11+ with async/await,
type hints, and maintained dependencies.
"""

__version__ = "1.0.0"
__author__ = "PyFluff Contributors"

from pyfluff.furby import FurbyConnect
from pyfluff.protocol import FurbyCharacteristic, FurbyProtocol, FurbyService

__all__ = ["FurbyConnect", "FurbyProtocol", "FurbyService", "FurbyCharacteristic"]
