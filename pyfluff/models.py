"""
Pydantic models for data validation and API schemas.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AntennaColor(BaseModel):
    """RGB color for antenna LED"""

    red: int = Field(ge=0, le=255, description="Red channel (0-255)")
    green: int = Field(ge=0, le=255, description="Green channel (0-255)")
    blue: int = Field(ge=0, le=255, description="Blue channel (0-255)")


class ActionSequence(BaseModel):
    """Furby action sequence parameters"""

    input: int = Field(ge=0, le=255, description="Action input value")
    index: int = Field(ge=0, le=255, description="Action index")
    subindex: int = Field(ge=0, le=255, description="Action subindex")
    specific: int = Field(ge=0, le=255, description="Specific action ID")


class ActionList(BaseModel):
    """List of actions to execute in sequence"""

    actions: list[ActionSequence] = Field(description="List of actions to execute")
    delay: float = Field(default=2.0, ge=0.1, le=30.0, description="Delay between actions in seconds (default: 2.0)")


class MoodUpdate(BaseModel):
    """Mood meter update parameters"""

    type: str = Field(
        description="Mood type: excitedness, displeasedness, tiredness, fullness, wellness"
    )
    action: str = Field(description="Action: set or increase")
    value: int = Field(ge=0, le=255, description="Value to set or increase by")


class DLCUpload(BaseModel):
    """DLC file upload parameters"""

    slot: int = Field(ge=0, le=255, description="DLC slot number")
    filename: str = Field(max_length=12, description="DLC filename (max 12 chars)")


class SensorData(BaseModel):
    """Sensor data from Furby"""

    model_config = ConfigDict(extra="allow")

    timestamp: float = Field(description="Unix timestamp")
    raw_data: str = Field(description="Hex-encoded raw sensor data")
    # Additional fields can be added as protocol is better understood


class ConnectRequest(BaseModel):
    """Request to connect to a Furby"""

    address: str | None = Field(None, description="MAC address to connect to directly (optional)")
    timeout: float = Field(15.0, ge=1.0, le=60.0, description="Connection timeout per attempt in seconds")
    retries: int = Field(3, ge=1, le=10, description="Number of connection attempts (useful for F2F mode)")


class FurbyStatus(BaseModel):
    """Current Furby connection status"""

    connected: bool
    device_name: str | None = None
    device_address: str | None = None
    firmware_version: str | None = None


class CommandResponse(BaseModel):
    """Generic command response"""

    success: bool
    message: str
    data: dict[str, Any] | None = None


class FurbyInfo(BaseModel):
    """Furby device information"""

    manufacturer: str | None = None
    model_number: str | None = None
    serial_number: str | None = None
    hardware_revision: str | None = None
    firmware_revision: str | None = None
    software_revision: str | None = None


class KnownFurby(BaseModel):
    """Known Furby device cache entry"""

    address: str = Field(description="MAC address of the Furby")
    name: str | None = Field(None, description="Last known Furby name")
    name_id: int | None = Field(None, description="Last known name ID (0-128)")
    device_name: str | None = Field(None, description="BLE device name")
    last_seen: float = Field(description="Unix timestamp of last connection")
    firmware_revision: str | None = Field(None, description="Firmware version if known")

    model_config = ConfigDict(extra="allow")


class KnownFurbiesConfig(BaseModel):
    """Configuration file for known Furbies"""

    furbies: dict[str, KnownFurby] = Field(default_factory=dict, description="Map of MAC address to KnownFurby")

    model_config = ConfigDict(extra="allow")
