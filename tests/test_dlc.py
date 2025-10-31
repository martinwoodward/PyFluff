"""
Tests for PyFluff DLC module.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pyfluff.dlc import DLCManager
from pyfluff.protocol import FileTransferMode


@pytest.fixture
def mock_furby():
    """Create a mock FurbyConnect instance."""
    furby = MagicMock()
    furby._write_gp = AsyncMock()
    furby._write_file = AsyncMock()
    furby._gp_callbacks = []
    return furby


@pytest.fixture
def dlc_manager(mock_furby):
    """Create a DLCManager instance with mock furby."""
    return DLCManager(mock_furby)


def test_dlc_manager_initialization(mock_furby):
    """Test DLCManager initialization."""
    manager = DLCManager(mock_furby)
    assert manager.furby == mock_furby
    assert manager._transfer_ready.is_set() is False
    assert manager._transfer_complete.is_set() is False
    assert manager._transfer_error is None


def test_file_transfer_callback_ready(dlc_manager):
    """Test file transfer callback with READY_TO_RECEIVE."""
    data = bytes([0x24, FileTransferMode.READY_TO_RECEIVE.value])
    dlc_manager._file_transfer_callback(data)
    assert dlc_manager._transfer_ready.is_set()


def test_file_transfer_callback_complete(dlc_manager):
    """Test file transfer callback with FILE_RECEIVED_OK."""
    data = bytes([0x24, FileTransferMode.FILE_RECEIVED_OK.value])
    dlc_manager._file_transfer_callback(data)
    assert dlc_manager._transfer_complete.is_set()
    assert dlc_manager._transfer_error is None


def test_file_transfer_callback_error(dlc_manager):
    """Test file transfer callback with FILE_RECEIVED_ERROR."""
    data = bytes([0x24, FileTransferMode.FILE_RECEIVED_ERROR.value])
    dlc_manager._file_transfer_callback(data)
    assert dlc_manager._transfer_complete.is_set()
    assert dlc_manager._transfer_error == "File transfer failed"


def test_file_transfer_callback_timeout(dlc_manager):
    """Test file transfer callback with FILE_TRANSFER_TIMEOUT."""
    data = bytes([0x24, FileTransferMode.FILE_TRANSFER_TIMEOUT.value])
    dlc_manager._file_transfer_callback(data)
    assert dlc_manager._transfer_complete.is_set()
    assert dlc_manager._transfer_error == "File transfer timeout"


@pytest.mark.asyncio
async def test_upload_dlc_chunk_delay_parameter(dlc_manager, tmp_path):
    """Test that chunk_delay parameter is properly used during upload."""
    # Create a small test file
    test_file = tmp_path / "test.dlc"
    test_data = b"A" * 60  # 60 bytes = 3 chunks of 20 bytes
    test_file.write_bytes(test_data)

    # Mock the necessary methods
    dlc_manager.furby.enable_nordic_packet_ack = AsyncMock()

    # Track sleep calls to verify chunk_delay is used
    sleep_calls = []

    async def mock_sleep(duration):
        sleep_calls.append(duration)

    # Set up the callback to simulate Furby responses
    def simulate_furby_response(callback):
        # Simulate READY_TO_RECEIVE
        dlc_manager._transfer_ready.set()
        # Simulate FILE_RECEIVED_OK after all chunks
        asyncio.get_running_loop().call_later(0.1, dlc_manager._transfer_complete.set)

    dlc_manager.furby.add_gp_callback = MagicMock(side_effect=simulate_furby_response)

    # Test with custom chunk_delay
    custom_delay = 0.01
    with patch("asyncio.sleep", side_effect=mock_sleep):
        with patch.object(dlc_manager.furby, "_gp_callbacks", []):
            try:
                await dlc_manager.upload_dlc(
                    test_file, slot=2, chunk_delay=custom_delay, timeout=1.0
                )
            except (TimeoutError, RuntimeError):
                # Expected to timeout since we're mocking
                pass

    # Verify chunk_delay was used (should have 3 sleep calls for 3 chunks)
    chunk_sleep_calls = [call for call in sleep_calls if call == custom_delay]
    assert len(chunk_sleep_calls) == 3, f"Expected 3 chunk delays, got {len(chunk_sleep_calls)}"


@pytest.mark.asyncio
async def test_upload_dlc_default_chunk_delay(dlc_manager, tmp_path):
    """Test that default chunk_delay is 0.020 seconds."""
    # Create a small test file
    test_file = tmp_path / "test.dlc"
    test_data = b"B" * 40  # 40 bytes = 2 chunks of 20 bytes
    test_file.write_bytes(test_data)

    # Mock the necessary methods
    dlc_manager.furby.enable_nordic_packet_ack = AsyncMock()

    # Track sleep calls
    sleep_calls = []

    async def mock_sleep(duration):
        sleep_calls.append(duration)

    def simulate_furby_response(callback):
        dlc_manager._transfer_ready.set()
        asyncio.get_running_loop().call_later(0.1, dlc_manager._transfer_complete.set)

    dlc_manager.furby.add_gp_callback = MagicMock(side_effect=simulate_furby_response)

    # Test with default chunk_delay (should be 0.020)
    with patch("asyncio.sleep", side_effect=mock_sleep):
        with patch.object(dlc_manager.furby, "_gp_callbacks", []):
            try:
                await dlc_manager.upload_dlc(test_file, slot=2, timeout=1.0)
            except (TimeoutError, RuntimeError):
                # Expected to timeout since we're mocking
                pass

    # Verify default chunk_delay of 0.020 was used
    default_delay = 0.020
    chunk_sleep_calls = [call for call in sleep_calls if call == default_delay]
    assert len(chunk_sleep_calls) == 2, f"Expected 2 chunk delays, got {len(chunk_sleep_calls)}"


@pytest.mark.asyncio
async def test_flash_and_activate_passes_chunk_delay(dlc_manager, tmp_path):
    """Test that flash_and_activate passes chunk_delay to upload_dlc."""
    test_file = tmp_path / "test.dlc"
    test_file.write_bytes(b"C" * 20)

    # Mock all the methods
    dlc_manager.delete_dlc = AsyncMock()
    dlc_manager.upload_dlc = AsyncMock()
    dlc_manager.load_dlc = AsyncMock()
    dlc_manager.activate_dlc = AsyncMock()

    custom_delay = 0.015
    await dlc_manager.flash_and_activate(
        test_file, slot=2, delete_first=True, chunk_delay=custom_delay
    )

    # Verify upload_dlc was called with correct chunk_delay
    dlc_manager.upload_dlc.assert_called_once()
    call_kwargs = dlc_manager.upload_dlc.call_args.kwargs
    assert call_kwargs["chunk_delay"] == custom_delay
