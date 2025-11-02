"""
Basic tests for PyFluff protocol module.
"""

import pytest

from pyfluff.protocol import (
    FurbyMessage,
    FurbyProtocol,
    GeneralPlusCommand,
    MoodMeterType,
)


def test_build_antenna_command() -> None:
    """Test antenna color command generation."""
    cmd = FurbyProtocol.build_antenna_command(255, 128, 0)
    assert cmd == bytes([0x14, 255, 128, 0])
    assert len(cmd) == 4


def test_build_action_command() -> None:
    """Test action sequence command generation."""
    cmd = FurbyProtocol.build_action_command(55, 2, 14, 0)
    assert cmd == bytes([0x13, 0x00, 55, 2, 14, 0])
    assert len(cmd) == 6


def test_build_lcd_command() -> None:
    """Test LCD backlight command generation."""
    cmd_on = FurbyProtocol.build_lcd_command(True)
    assert cmd_on == bytes([0xCD, 0x01])

    cmd_off = FurbyProtocol.build_lcd_command(False)
    assert cmd_off == bytes([0xCD, 0x00])


def test_build_debug_menu_command() -> None:
    """Test debug menu command generation."""
    cmd = FurbyProtocol.build_debug_menu_command()
    assert cmd == bytes([0xDB])
    assert len(cmd) == 1


def test_build_name_command() -> None:
    """Test name setting command generation."""
    cmd = FurbyProtocol.build_name_command(42)
    assert cmd == bytes([0x21, 42])
    assert len(cmd) == 2


def test_build_moodmeter_command() -> None:
    """Test mood meter command generation."""
    cmd = FurbyProtocol.build_moodmeter_command(1, MoodMeterType.FULLNESS, 75)
    assert cmd == bytes([0x23, 1, 0x03, 75])
    assert len(cmd) == 4


def test_parse_response() -> None:
    """Test response packet parsing."""
    data = bytes([0x20, 0x06, 0x01, 0x02])
    cmd_id, payload = FurbyProtocol.parse_response(data)
    assert cmd_id == 0x20
    assert payload == bytes([0x06, 0x01, 0x02])


def test_parse_empty_response() -> None:
    """Test parsing empty response raises error."""
    with pytest.raises(ValueError):
        FurbyProtocol.parse_response(bytes([]))


def test_is_furby_message() -> None:
    """Test FurbyMessage detection."""
    assert FurbyProtocol.is_furby_message(bytes([0x20, 0x06]))
    assert not FurbyProtocol.is_furby_message(bytes([0x21, 0x00]))
    assert not FurbyProtocol.is_furby_message(bytes([]))


def test_get_furby_message_type() -> None:
    """Test FurbyMessage type extraction."""
    msg = FurbyProtocol.get_furby_message_type(bytes([0x20, 0x06]))
    assert msg == FurbyMessage.RESPONSE_PLAYED

    msg = FurbyProtocol.get_furby_message_type(bytes([0x20, 0x0E]))
    assert msg == FurbyMessage.SEQUENCE_ENDED

    # Invalid message
    msg = FurbyProtocol.get_furby_message_type(bytes([0x20, 0xFF]))
    assert msg is None

    # Not a FurbyMessage
    msg = FurbyProtocol.get_furby_message_type(bytes([0x21, 0x00]))
    assert msg is None


def test_build_dlc_announce_command() -> None:
    """Test DLC announcement command generation."""
    cmd = FurbyProtocol.build_dlc_announce_command(12345, 2, "TEST.DLC")

    # Check command ID
    assert cmd[0] == GeneralPlusCommand.ANNOUNCE_DLC_UPLOAD.value

    # Check size bytes (big-endian)
    assert cmd[1] == 0x00  # (12345 >> 16) & 0xFF
    assert cmd[2] == 0x30  # (12345 >> 8) & 0xFF
    assert cmd[3] == 0x39  # 12345 & 0xFF

    # Check slot
    assert cmd[5] == 2

    # Check filename (padded to 12 bytes)
    assert cmd[6:18] == b"TEST.DLC\x00\x00\x00\x00"


def test_build_nordic_packet_ack() -> None:
    """Test Nordic packet acknowledgment command."""
    cmd_on = FurbyProtocol.build_nordic_packet_ack(True)
    assert cmd_on == bytes([0x09, 0x01, 0x00])

    cmd_off = FurbyProtocol.build_nordic_packet_ack(False)
    assert cmd_off == bytes([0x09, 0x00, 0x00])
