"""
Tests for PyFluff DLC (DownLoadable Content) manager.

These tests use mocks for BLE operations since we can't test with real hardware.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, call

import pytest
from pyfluff.dlc import DLCManager
from pyfluff.furby import FurbyConnect
from pyfluff.protocol import FileTransferMode


class TestDLCManager:
    """Tests for DLCManager class."""

    @pytest.fixture
    def mock_furby(self) -> FurbyConnect:
        """Create a mocked FurbyConnect instance."""
        furby = MagicMock(spec=FurbyConnect)
        furby._write_gp = AsyncMock()
        furby._write_nordic = AsyncMock()
        furby._write_file = AsyncMock()
        furby.enable_nordic_packet_ack = AsyncMock()
        furby._gp_callbacks = []  # Add callback list
        furby.add_gp_callback = MagicMock(side_effect=lambda cb: furby._gp_callbacks.append(cb))
        furby.remove_gp_callback = MagicMock(side_effect=lambda cb: furby._gp_callbacks.remove(cb) if cb in furby._gp_callbacks else None)
        return furby

    @pytest.fixture
    def dlc_manager(self, mock_furby: FurbyConnect) -> DLCManager:
        """Create a DLCManager instance with mocked Furby."""
        return DLCManager(mock_furby)

    def test_initialization(self, mock_furby: FurbyConnect) -> None:
        """Test DLCManager initialization."""
        manager = DLCManager(mock_furby)
        assert manager.furby == mock_furby
        assert manager._transfer_ready.is_set() is False
        assert manager._transfer_complete.is_set() is False
        assert manager._transfer_error is None

    def test_file_transfer_callback_ready_to_receive(
        self, dlc_manager: DLCManager
    ) -> None:
        """Test callback handling for READY_TO_RECEIVE status."""
        dlc_manager._transfer_ready.clear()
        
        # Simulate READY_TO_RECEIVE response (0x24, 0x02)
        dlc_manager._file_transfer_callback(bytes([0x24, 0x02]))
        
        assert dlc_manager._transfer_ready.is_set()
        assert dlc_manager._transfer_error is None

    def test_file_transfer_callback_received_ok(
        self, dlc_manager: DLCManager
    ) -> None:
        """Test callback handling for FILE_RECEIVED_OK status."""
        dlc_manager._transfer_complete.clear()
        
        # Simulate FILE_RECEIVED_OK response (0x24, 0x05)
        dlc_manager._file_transfer_callback(bytes([0x24, 0x05]))
        
        assert dlc_manager._transfer_complete.is_set()
        assert dlc_manager._transfer_error is None

    def test_file_transfer_callback_received_error(
        self, dlc_manager: DLCManager
    ) -> None:
        """Test callback handling for FILE_RECEIVED_ERROR status."""
        dlc_manager._transfer_complete.clear()
        
        # Simulate FILE_RECEIVED_ERROR response (0x24, 0x06)
        dlc_manager._file_transfer_callback(bytes([0x24, 0x06]))
        
        assert dlc_manager._transfer_complete.is_set()
        assert dlc_manager._transfer_error == "File transfer failed"

    def test_file_transfer_callback_timeout(
        self, dlc_manager: DLCManager
    ) -> None:
        """Test callback handling for FILE_TRANSFER_TIMEOUT status."""
        dlc_manager._transfer_complete.clear()
        
        # Simulate FILE_TRANSFER_TIMEOUT response (0x24, 0x03)
        dlc_manager._file_transfer_callback(bytes([0x24, 0x03]))
        
        assert dlc_manager._transfer_complete.is_set()
        assert dlc_manager._transfer_error == "File transfer timeout"

    def test_file_transfer_callback_invalid_packet(
        self, dlc_manager: DLCManager
    ) -> None:
        """Test callback ignores invalid packets."""
        # Packet too short
        dlc_manager._file_transfer_callback(bytes([0x24]))
        assert dlc_manager._transfer_ready.is_set() is False
        
        # Wrong command ID
        dlc_manager._file_transfer_callback(bytes([0x23, 0x02]))
        assert dlc_manager._transfer_ready.is_set() is False

    def test_file_transfer_callback_unknown_mode(
        self, dlc_manager: DLCManager
    ) -> None:
        """Test callback handles unknown file transfer mode gracefully."""
        # Unknown mode value (0xFF)
        dlc_manager._file_transfer_callback(bytes([0x24, 0xFF]))
        # Should not crash, just log warning

    @pytest.mark.asyncio
    async def test_upload_dlc_file_not_found(
        self, dlc_manager: DLCManager, tmp_path: Path
    ) -> None:
        """Test upload raises error for non-existent file."""
        non_existent = tmp_path / "nonexistent.dlc"
        
        with pytest.raises(FileNotFoundError):
            await dlc_manager.upload_dlc(non_existent)

    @pytest.mark.asyncio
    async def test_load_dlc(self, dlc_manager: DLCManager, mock_furby: FurbyConnect) -> None:
        """Test loading a DLC from a slot."""
        await dlc_manager.load_dlc(2)
        
        # Should send load command (0x60, slot)
        mock_furby._write_gp.assert_called_once()
        call_args = mock_furby._write_gp.call_args[0][0]
        assert call_args[0] == 0x60  # Load DLC command
        assert call_args[1] == 2     # Slot number

    @pytest.mark.asyncio
    async def test_activate_dlc(
        self, dlc_manager: DLCManager, mock_furby: FurbyConnect
    ) -> None:
        """Test activating a loaded DLC."""
        await dlc_manager.activate_dlc()
        
        # Should send activate command (0x61)
        mock_furby._write_gp.assert_called_once()
        call_args = mock_furby._write_gp.call_args[0][0]
        assert call_args[0] == 0x61

    @pytest.mark.asyncio
    async def test_deactivate_dlc(
        self, dlc_manager: DLCManager, mock_furby: FurbyConnect
    ) -> None:
        """Test deactivating a DLC slot."""
        await dlc_manager.deactivate_dlc(1)
        
        # Should send deactivate command (0x62, slot)
        mock_furby._write_gp.assert_called_once()
        call_args = mock_furby._write_gp.call_args[0][0]
        assert call_args[0] == 0x62  # Deactivate DLC command
        assert call_args[1] == 1     # Slot number

    @pytest.mark.asyncio
    async def test_delete_dlc(
        self, dlc_manager: DLCManager, mock_furby: FurbyConnect
    ) -> None:
        """Test deleting a DLC slot."""
        await dlc_manager.delete_dlc(3)
        
        # Should send delete command (0x74, slot)
        mock_furby._write_gp.assert_called_once()
        call_args = mock_furby._write_gp.call_args[0][0]
        assert call_args[0] == 0x74  # Delete DLC command
        assert call_args[1] == 3     # Slot number

    @pytest.mark.asyncio
    async def test_upload_dlc_enables_nordic_ack(
        self, dlc_manager: DLCManager, mock_furby: FurbyConnect, tmp_path: Path
    ) -> None:
        """Test that upload enables Nordic packet ACK by default."""
        # Create a small test DLC file
        dlc_file = tmp_path / "test.dlc"
        dlc_file.write_bytes(b"TEST" * 10)  # 40 bytes
        
        # Create a task to set ready/complete after brief delay
        async def set_transfer_states() -> None:
            await asyncio.sleep(0.01)  # Let upload start
            dlc_manager._transfer_ready.set()
            await asyncio.sleep(0.01)
            dlc_manager._transfer_complete.set()
        
        asyncio.create_task(set_transfer_states())
        
        await dlc_manager.upload_dlc(dlc_file, slot=2)
        
        # Should enable Nordic packet ACK
        mock_furby.enable_nordic_packet_ack.assert_called_once_with(True)

    @pytest.mark.asyncio
    async def test_upload_dlc_can_skip_nordic_ack(
        self, dlc_manager: DLCManager, mock_furby: FurbyConnect, tmp_path: Path
    ) -> None:
        """Test that upload can skip enabling Nordic packet ACK."""
        # Create a small test DLC file
        dlc_file = tmp_path / "test.dlc"
        dlc_file.write_bytes(b"TEST" * 10)
        
        # Create a task to set ready/complete after brief delay
        async def set_transfer_states() -> None:
            await asyncio.sleep(0.01)
            dlc_manager._transfer_ready.set()
            await asyncio.sleep(0.01)
            dlc_manager._transfer_complete.set()
        
        asyncio.create_task(set_transfer_states())
        
        await dlc_manager.upload_dlc(dlc_file, slot=2, enable_nordic_ack=False)
        
        # Should not enable Nordic packet ACK
        mock_furby.enable_nordic_packet_ack.assert_not_called()

    @pytest.mark.asyncio
    async def test_upload_dlc_registers_callback(
        self, dlc_manager: DLCManager, mock_furby: FurbyConnect, tmp_path: Path
    ) -> None:
        """Test that upload registers and unregisters callback."""
        dlc_file = tmp_path / "test.dlc"
        dlc_file.write_bytes(b"TEST" * 10)
        
        # Create a task to set ready/complete after brief delay
        async def set_transfer_states() -> None:
            await asyncio.sleep(0.01)
            dlc_manager._transfer_ready.set()
            await asyncio.sleep(0.01)
            dlc_manager._transfer_complete.set()
        
        asyncio.create_task(set_transfer_states())
        
        await dlc_manager.upload_dlc(dlc_file, slot=2)
        
        # Callback should have been added and then removed
        assert dlc_manager._file_transfer_callback not in mock_furby._gp_callbacks

    @pytest.mark.asyncio
    async def test_upload_dlc_sends_announce_command(
        self, dlc_manager: DLCManager, mock_furby: FurbyConnect, tmp_path: Path
    ) -> None:
        """Test that upload sends DLC announce command."""
        dlc_file = tmp_path / "test.dlc"
        test_data = b"TEST" * 10
        dlc_file.write_bytes(test_data)
        
        # Create a task to set ready/complete after brief delay
        async def set_transfer_states() -> None:
            await asyncio.sleep(0.01)
            dlc_manager._transfer_ready.set()
            await asyncio.sleep(0.01)
            dlc_manager._transfer_complete.set()
        
        asyncio.create_task(set_transfer_states())
        
        await dlc_manager.upload_dlc(dlc_file, slot=2)
        
        # Should send announce command with file size, slot, and filename
        calls = mock_furby._write_gp.call_args_list
        assert len(calls) > 0
        
        # First call should be announce command
        announce_cmd = calls[0][0][0]
        assert announce_cmd[0] == 0x50  # Announce DLC upload command

    @pytest.mark.asyncio
    async def test_upload_dlc_sends_file_chunks(
        self, dlc_manager: DLCManager, mock_furby: FurbyConnect, tmp_path: Path
    ) -> None:
        """Test that upload sends file data in chunks."""
        dlc_file = tmp_path / "test.dlc"
        test_data = b"TEST" * 25  # 100 bytes = 5 chunks of 20 bytes
        dlc_file.write_bytes(test_data)
        
        # Create a task to set ready/complete after brief delay
        async def set_transfer_states() -> None:
            await asyncio.sleep(0.01)
            dlc_manager._transfer_ready.set()
            await asyncio.sleep(0.05)  # Wait for chunks to be sent
            dlc_manager._transfer_complete.set()
        
        asyncio.create_task(set_transfer_states())
        
        await dlc_manager.upload_dlc(dlc_file, slot=2)
        
        # Should have called _write_file multiple times (5 chunks)
        assert mock_furby._write_file.call_count == 5

    @pytest.mark.asyncio
    async def test_upload_dlc_handles_transfer_error(
        self, dlc_manager: DLCManager, mock_furby: FurbyConnect, tmp_path: Path
    ) -> None:
        """Test that upload raises error on transfer failure."""
        dlc_file = tmp_path / "test.dlc"
        dlc_file.write_bytes(b"TEST" * 10)
        
        # Create a task to set ready then error
        async def set_error_state() -> None:
            await asyncio.sleep(0.01)
            dlc_manager._transfer_ready.set()
            await asyncio.sleep(0.02)
            dlc_manager._transfer_error = "Test error"
            dlc_manager._transfer_complete.set()
        
        asyncio.create_task(set_error_state())
        
        with pytest.raises(RuntimeError, match="Test error"):
            await dlc_manager.upload_dlc(dlc_file, slot=2, timeout=1.0)

    @pytest.mark.asyncio
    async def test_upload_dlc_timeout_waiting_for_ready(
        self, dlc_manager: DLCManager, mock_furby: FurbyConnect, tmp_path: Path
    ) -> None:
        """Test that upload times out if Furby doesn't signal ready."""
        dlc_file = tmp_path / "test.dlc"
        dlc_file.write_bytes(b"TEST" * 10)
        
        # Don't set transfer_ready, so it will timeout
        with pytest.raises(RuntimeError, match="did not respond"):
            await dlc_manager.upload_dlc(dlc_file, slot=2, timeout=0.5)


class TestDLCManagerIntegration:
    """Integration-style tests for DLC workflow."""

    @pytest.mark.asyncio
    async def test_full_dlc_workflow(self, tmp_path: Path) -> None:
        """Test complete DLC workflow: upload, load, activate."""
        # Create mock Furby
        furby = MagicMock(spec=FurbyConnect)
        furby._write_gp = AsyncMock()
        furby._write_nordic = AsyncMock()
        furby._write_file = AsyncMock()
        furby.enable_nordic_packet_ack = AsyncMock()
        furby._gp_callbacks = []  # Add callback list
        furby.add_gp_callback = MagicMock(side_effect=lambda cb: furby._gp_callbacks.append(cb))
        furby.remove_gp_callback = MagicMock(side_effect=lambda cb: furby._gp_callbacks.remove(cb) if cb in furby._gp_callbacks else None)
        
        manager = DLCManager(furby)
        
        # Create test DLC file
        dlc_file = tmp_path / "custom.dlc"
        dlc_file.write_bytes(b"DLC_CONTENT" * 5)
        
        # Create a task to set ready/complete after brief delay
        async def set_transfer_states() -> None:
            await asyncio.sleep(0.01)
            manager._transfer_ready.set()
            await asyncio.sleep(0.02)
            manager._transfer_complete.set()
        
        asyncio.create_task(set_transfer_states())
        
        # Upload
        await manager.upload_dlc(dlc_file, slot=2)
        
        # Load
        await manager.load_dlc(2)
        
        # Activate
        await manager.activate_dlc()
        
        # Verify sequence of commands
        gp_calls = furby._write_gp.call_args_list
        assert len(gp_calls) >= 3  # Announce, Load, Activate
