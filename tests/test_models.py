"""
Tests for PyFluff data models (Pydantic validation).
"""

import pytest
from pydantic import ValidationError
from pyfluff.models import (
    AntennaColor,
    ActionSequence,
    ActionList,
    MoodUpdate,
    DLCUpload,
    SensorData,
    ConnectRequest,
    FurbyStatus,
    CommandResponse,
    FurbyInfo,
    KnownFurby,
    KnownFurbiesConfig,
)


class TestAntennaColor:
    """Tests for AntennaColor model."""

    def test_valid_color(self) -> None:
        """Test valid RGB color."""
        color = AntennaColor(red=255, green=128, blue=0)
        assert color.red == 255
        assert color.green == 128
        assert color.blue == 0

    def test_min_values(self) -> None:
        """Test minimum RGB values (0)."""
        color = AntennaColor(red=0, green=0, blue=0)
        assert color.red == 0
        assert color.green == 0
        assert color.blue == 0

    def test_max_values(self) -> None:
        """Test maximum RGB values (255)."""
        color = AntennaColor(red=255, green=255, blue=255)
        assert color.red == 255
        assert color.green == 255
        assert color.blue == 255

    def test_negative_value_rejected(self) -> None:
        """Test that negative values are rejected."""
        with pytest.raises(ValidationError):
            AntennaColor(red=-1, green=0, blue=0)

    def test_too_large_value_rejected(self) -> None:
        """Test that values > 255 are rejected."""
        with pytest.raises(ValidationError):
            AntennaColor(red=256, green=0, blue=0)


class TestActionSequence:
    """Tests for ActionSequence model."""

    def test_valid_action(self) -> None:
        """Test valid action sequence."""
        action = ActionSequence(input=1, index=2, subindex=3, specific=4)
        assert action.input == 1
        assert action.index == 2
        assert action.subindex == 3
        assert action.specific == 4

    def test_zero_values(self) -> None:
        """Test zero values are valid."""
        action = ActionSequence(input=0, index=0, subindex=0, specific=0)
        assert action.input == 0

    def test_max_values(self) -> None:
        """Test maximum values (255)."""
        action = ActionSequence(input=255, index=255, subindex=255, specific=255)
        assert action.input == 255

    def test_negative_rejected(self) -> None:
        """Test that negative values are rejected."""
        with pytest.raises(ValidationError):
            ActionSequence(input=-1, index=0, subindex=0, specific=0)


class TestActionList:
    """Tests for ActionList model."""

    def test_valid_action_list(self) -> None:
        """Test valid action list with delay."""
        actions = [
            ActionSequence(input=1, index=0, subindex=0, specific=0),
            ActionSequence(input=2, index=0, subindex=0, specific=0),
        ]
        action_list = ActionList(actions=actions, delay=3.0)
        assert len(action_list.actions) == 2
        assert action_list.delay == 3.0

    def test_default_delay(self) -> None:
        """Test default delay value."""
        actions = [ActionSequence(input=1, index=0, subindex=0, specific=0)]
        action_list = ActionList(actions=actions)
        assert action_list.delay == 2.0

    def test_min_delay(self) -> None:
        """Test minimum delay value (0.1)."""
        actions = [ActionSequence(input=1, index=0, subindex=0, specific=0)]
        action_list = ActionList(actions=actions, delay=0.1)
        assert action_list.delay == 0.1

    def test_max_delay(self) -> None:
        """Test maximum delay value (30.0)."""
        actions = [ActionSequence(input=1, index=0, subindex=0, specific=0)]
        action_list = ActionList(actions=actions, delay=30.0)
        assert action_list.delay == 30.0

    def test_delay_too_small_rejected(self) -> None:
        """Test that delay < 0.1 is rejected."""
        actions = [ActionSequence(input=1, index=0, subindex=0, specific=0)]
        with pytest.raises(ValidationError):
            ActionList(actions=actions, delay=0.05)

    def test_delay_too_large_rejected(self) -> None:
        """Test that delay > 30.0 is rejected."""
        actions = [ActionSequence(input=1, index=0, subindex=0, specific=0)]
        with pytest.raises(ValidationError):
            ActionList(actions=actions, delay=31.0)


class TestMoodUpdate:
    """Tests for MoodUpdate model."""

    def test_valid_mood_update(self) -> None:
        """Test valid mood update."""
        mood = MoodUpdate(type="excitedness", action="set", value=100)
        assert mood.type == "excitedness"
        assert mood.action == "set"
        assert mood.value == 100

    def test_min_value(self) -> None:
        """Test minimum mood value (0)."""
        mood = MoodUpdate(type="tiredness", action="set", value=0)
        assert mood.value == 0

    def test_max_value(self) -> None:
        """Test maximum mood value (255)."""
        mood = MoodUpdate(type="wellness", action="set", value=255)
        assert mood.value == 255

    def test_negative_value_rejected(self) -> None:
        """Test that negative values are rejected."""
        with pytest.raises(ValidationError):
            MoodUpdate(type="fullness", action="set", value=-1)


class TestDLCUpload:
    """Tests for DLCUpload model."""

    def test_valid_dlc_upload(self) -> None:
        """Test valid DLC upload parameters."""
        dlc = DLCUpload(slot=2, filename="TEST.DLC")
        assert dlc.slot == 2
        assert dlc.filename == "TEST.DLC"

    def test_max_slot(self) -> None:
        """Test maximum slot value (255)."""
        dlc = DLCUpload(slot=255, filename="TEST.DLC")
        assert dlc.slot == 255

    def test_filename_max_length(self) -> None:
        """Test maximum filename length (12 chars)."""
        dlc = DLCUpload(slot=0, filename="123456789012")
        assert dlc.filename == "123456789012"

    def test_filename_too_long_rejected(self) -> None:
        """Test that filenames > 12 chars are rejected."""
        with pytest.raises(ValidationError):
            DLCUpload(slot=0, filename="1234567890123")


class TestSensorData:
    """Tests for SensorData model."""

    def test_valid_sensor_data(self) -> None:
        """Test valid sensor data."""
        data = SensorData(timestamp=1234567890.0, raw_data="DEADBEEF")
        assert data.timestamp == 1234567890.0
        assert data.raw_data == "DEADBEEF"

    def test_extra_fields_allowed(self) -> None:
        """Test that extra fields are allowed."""
        data = SensorData(
            timestamp=1234567890.0,
            raw_data="DEADBEEF",
            custom_field="custom_value",
        )
        assert data.raw_data == "DEADBEEF"


class TestConnectRequest:
    """Tests for ConnectRequest model."""

    def test_default_values(self) -> None:
        """Test default connection parameters."""
        req = ConnectRequest()
        assert req.address is None
        assert req.timeout == 15.0
        assert req.retries == 3

    def test_with_address(self) -> None:
        """Test connection with specific address."""
        req = ConnectRequest(address="AA:BB:CC:DD:EE:FF")
        assert req.address == "AA:BB:CC:DD:EE:FF"

    def test_custom_timeout_and_retries(self) -> None:
        """Test custom timeout and retry values."""
        req = ConnectRequest(timeout=30.0, retries=5)
        assert req.timeout == 30.0
        assert req.retries == 5

    def test_min_timeout(self) -> None:
        """Test minimum timeout (1.0 seconds)."""
        req = ConnectRequest(timeout=1.0)
        assert req.timeout == 1.0

    def test_max_timeout(self) -> None:
        """Test maximum timeout (60.0 seconds)."""
        req = ConnectRequest(timeout=60.0)
        assert req.timeout == 60.0

    def test_timeout_too_small_rejected(self) -> None:
        """Test that timeout < 1.0 is rejected."""
        with pytest.raises(ValidationError):
            ConnectRequest(timeout=0.5)

    def test_timeout_too_large_rejected(self) -> None:
        """Test that timeout > 60.0 is rejected."""
        with pytest.raises(ValidationError):
            ConnectRequest(timeout=61.0)


class TestFurbyStatus:
    """Tests for FurbyStatus model."""

    def test_disconnected_status(self) -> None:
        """Test disconnected Furby status."""
        status = FurbyStatus(connected=False)
        assert status.connected is False
        assert status.device_name is None
        assert status.device_address is None

    def test_connected_status(self) -> None:
        """Test connected Furby status with details."""
        status = FurbyStatus(
            connected=True,
            device_name="Furby",
            device_address="AA:BB:CC:DD:EE:FF",
            firmware_version="1.0.0",
        )
        assert status.connected is True
        assert status.device_name == "Furby"
        assert status.device_address == "AA:BB:CC:DD:EE:FF"
        assert status.firmware_version == "1.0.0"


class TestCommandResponse:
    """Tests for CommandResponse model."""

    def test_success_response(self) -> None:
        """Test successful command response."""
        resp = CommandResponse(success=True, message="Command executed")
        assert resp.success is True
        assert resp.message == "Command executed"
        assert resp.data is None

    def test_failure_response(self) -> None:
        """Test failed command response."""
        resp = CommandResponse(success=False, message="Command failed")
        assert resp.success is False
        assert resp.message == "Command failed"

    def test_response_with_data(self) -> None:
        """Test command response with additional data."""
        resp = CommandResponse(
            success=True,
            message="Success",
            data={"result": 42, "status": "ok"},
        )
        assert resp.data is not None
        assert resp.data["result"] == 42


class TestFurbyInfo:
    """Tests for FurbyInfo model."""

    def test_empty_info(self) -> None:
        """Test Furby info with no data."""
        info = FurbyInfo()
        assert info.manufacturer is None
        assert info.model_number is None
        assert info.serial_number is None

    def test_complete_info(self) -> None:
        """Test Furby info with all fields."""
        info = FurbyInfo(
            manufacturer="Hasbro",
            model_number="FC-001",
            serial_number="12345678",
            hardware_revision="1.0",
            firmware_revision="1.2.3",
            software_revision="2.0",
        )
        assert info.manufacturer == "Hasbro"
        assert info.model_number == "FC-001"
        assert info.serial_number == "12345678"
        assert info.hardware_revision == "1.0"
        assert info.firmware_revision == "1.2.3"
        assert info.software_revision == "2.0"


class TestKnownFurby:
    """Tests for KnownFurby model."""

    def test_minimal_known_furby(self) -> None:
        """Test known Furby with minimal data."""
        furby = KnownFurby(address="AA:BB:CC:DD:EE:FF", last_seen=1234567890.0)
        assert furby.address == "AA:BB:CC:DD:EE:FF"
        assert furby.last_seen == 1234567890.0
        assert furby.name is None
        assert furby.name_id is None

    def test_complete_known_furby(self) -> None:
        """Test known Furby with all fields."""
        furby = KnownFurby(
            address="AA:BB:CC:DD:EE:FF",
            name="Ah-Bay",
            name_id=0,
            device_name="Furby",
            last_seen=1234567890.0,
            firmware_revision="1.2.3",
        )
        assert furby.address == "AA:BB:CC:DD:EE:FF"
        assert furby.name == "Ah-Bay"
        assert furby.name_id == 0
        assert furby.device_name == "Furby"
        assert furby.firmware_revision == "1.2.3"

    def test_extra_fields_allowed(self) -> None:
        """Test that extra fields are allowed."""
        furby = KnownFurby(
            address="AA:BB:CC:DD:EE:FF",
            last_seen=1234567890.0,
            custom_field="custom_value",
        )
        assert furby.address == "AA:BB:CC:DD:EE:FF"


class TestKnownFurbiesConfig:
    """Tests for KnownFurbiesConfig model."""

    def test_empty_config(self) -> None:
        """Test empty Furbies configuration."""
        config = KnownFurbiesConfig()
        assert config.furbies == {}

    def test_config_with_furbies(self) -> None:
        """Test configuration with multiple Furbies."""
        furby1 = KnownFurby(address="AA:BB:CC:DD:EE:FF", last_seen=1234567890.0)
        furby2 = KnownFurby(address="11:22:33:44:55:66", last_seen=1234567891.0)
        config = KnownFurbiesConfig(
            furbies={
                "AA:BB:CC:DD:EE:FF": furby1,
                "11:22:33:44:55:66": furby2,
            }
        )
        assert len(config.furbies) == 2
        assert "AA:BB:CC:DD:EE:FF" in config.furbies
        assert "11:22:33:44:55:66" in config.furbies
