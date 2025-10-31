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

    # Check extra byte at index 1
    assert cmd[1] == 0x00

    # Check size bytes (big-endian) at indices 2-4
    assert cmd[2] == 0x00  # (12345 >> 16) & 0xFF
    assert cmd[3] == 0x30  # (12345 >> 8) & 0xFF
    assert cmd[4] == 0x39  # 12345 & 0xFF

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


def test_build_load_dlc_command() -> None:
    """Test DLC load command generation."""
    cmd = FurbyProtocol.build_load_dlc_command(2)
    assert cmd == bytes([0x60, 2])
    assert len(cmd) == 2


def test_build_activate_dlc_command() -> None:
    """Test DLC activate command generation."""
    cmd = FurbyProtocol.build_activate_dlc_command()
    assert cmd == bytes([0x61])
    assert len(cmd) == 1


def test_build_deactivate_dlc_command() -> None:
    """Test DLC deactivate command generation."""
    cmd = FurbyProtocol.build_deactivate_dlc_command(3)
    assert cmd == bytes([0x62, 3])
    assert len(cmd) == 2


def test_build_delete_dlc_command() -> None:
    """Test DLC delete command generation."""
    cmd = FurbyProtocol.build_delete_dlc_command(1)
    assert cmd == bytes([0x74, 1])
    assert len(cmd) == 2


def test_antenna_command_bounds() -> None:
    """Test antenna command with boundary values."""
    # Min values
    cmd = FurbyProtocol.build_antenna_command(0, 0, 0)
    assert cmd == bytes([0x14, 0, 0, 0])

    # Max values
    cmd = FurbyProtocol.build_antenna_command(255, 255, 255)
    assert cmd == bytes([0x14, 255, 255, 255])


def test_action_command_all_zeros() -> None:
    """Test action command with all zero values."""
    cmd = FurbyProtocol.build_action_command(0, 0, 0, 0)
    assert cmd == bytes([0x13, 0x00, 0, 0, 0, 0])


def test_action_command_max_values() -> None:
    """Test action command with maximum values."""
    cmd = FurbyProtocol.build_action_command(255, 255, 255, 255)
    assert cmd == bytes([0x13, 0x00, 255, 255, 255, 255])


def test_name_command_bounds() -> None:
    """Test name command with boundary values."""
    # Min name ID
    cmd = FurbyProtocol.build_name_command(0)
    assert cmd == bytes([0x21, 0])

    # Max name ID
    cmd = FurbyProtocol.build_name_command(128)
    assert cmd == bytes([0x21, 128])


def test_moodmeter_all_types() -> None:
    """Test mood meter commands for all mood types."""
    # Test all mood types
    for mood_type in MoodMeterType:
        cmd = FurbyProtocol.build_moodmeter_command(1, mood_type, 50)
        assert cmd[0] == 0x23  # Command ID
        assert cmd[1] == 1  # Action (set)
        assert cmd[2] == mood_type.value
        assert cmd[3] == 50  # Value


def test_dlc_announce_with_short_filename() -> None:
    """Test DLC announce with short filename."""
    cmd = FurbyProtocol.build_dlc_announce_command(1000, 0, "A.DLC")
    assert cmd[6:18] == b"A.DLC\x00\x00\x00\x00\x00\x00\x00"


def test_dlc_announce_with_max_filename() -> None:
    """Test DLC announce with 12-character filename."""
    cmd = FurbyProtocol.build_dlc_announce_command(1000, 0, "EXACTLY12CHR")
    assert cmd[6:18] == b"EXACTLY12CHR"


def test_dlc_announce_truncates_long_filename() -> None:
    """Test DLC announce truncates filenames longer than 12 chars."""
    cmd = FurbyProtocol.build_dlc_announce_command(1000, 0, "VERYLONGFILENAME.DLC")
    assert cmd[6:18] == b"VERYLONGFILE"  # Truncated to 12 chars


def test_parse_response_single_byte() -> None:
    """Test parsing single-byte response."""
    cmd_id, payload = FurbyProtocol.parse_response(bytes([0x20]))
    assert cmd_id == 0x20
    assert payload == bytes([])


def test_parse_response_multi_byte() -> None:
    """Test parsing multi-byte response."""
    data = bytes([0x23, 0x01, 0x02, 0x03, 0x04])
    cmd_id, payload = FurbyProtocol.parse_response(data)
    assert cmd_id == 0x23
    assert payload == bytes([0x01, 0x02, 0x03, 0x04])


def test_is_furby_message_false_cases() -> None:
    """Test FurbyMessage detection returns False for non-messages."""
    assert not FurbyProtocol.is_furby_message(bytes([]))
    assert not FurbyProtocol.is_furby_message(bytes([0x21]))
    assert not FurbyProtocol.is_furby_message(bytes([0x23, 0x00]))


def test_get_furby_message_type_all_messages() -> None:
    """Test extracting all valid FurbyMessage types."""
    # Test a few known message types
    msg = FurbyProtocol.get_furby_message_type(bytes([0x20, 0x01]))
    assert msg == FurbyMessage.ENTERED_NAMING_MODE

    msg = FurbyProtocol.get_furby_message_type(bytes([0x20, 0x04]))
    assert msg == FurbyMessage.ENTERED_APP_MODE

    msg = FurbyProtocol.get_furby_message_type(bytes([0x20, 0x0C]))
    assert msg == FurbyMessage.SEQUENCE_PLAYING


def test_get_furby_message_type_short_data() -> None:
    """Test get_furby_message_type with insufficient data."""
    msg = FurbyProtocol.get_furby_message_type(bytes([0x20]))
    assert msg is None


def test_furby_names_dict() -> None:
    """Test that FURBY_NAMES dictionary is properly populated."""
    from pyfluff.protocol import FURBY_NAMES

    # Should have 130 names (IDs 0-129)
    assert len(FURBY_NAMES) == 130

    # Check some known names
    assert FURBY_NAMES[0] == "Ah-Bay"
    assert FURBY_NAMES[11] == "Bee-Boh"
    assert FURBY_NAMES[55] == "Doo-Doo"
    assert FURBY_NAMES[108] == "Tay-Tah"  # This was the bug - was "Tay-Toh"
    assert FURBY_NAMES[109] == "Tay-Toh"
    assert FURBY_NAMES[129] == "Way-Toh"

    # All IDs from 0-129 should be present
    for i in range(130):
        assert i in FURBY_NAMES
