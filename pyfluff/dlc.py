"""
DLC (DownLoadable Content) file handling for Furby Connect.

DLC files contain audio, animations, and other content that can be
uploaded to Furby.
"""

import asyncio
import logging
from pathlib import Path

from pyfluff.furby import FurbyConnect
from pyfluff.protocol import FILE_CHUNK_SIZE, FileTransferMode, FurbyProtocol

logger = logging.getLogger(__name__)


class DLCManager:
    """Manager for DLC file operations."""

    def __init__(self, furby: FurbyConnect) -> None:
        """
        Initialize DLC manager.

        Args:
            furby: Connected FurbyConnect instance
        """
        self.furby = furby
        self._transfer_ready = asyncio.Event()
        self._transfer_complete = asyncio.Event()
        self._transfer_error: str | None = None

    def _file_transfer_callback(self, data: bytes) -> None:
        """Handle file transfer status notifications."""
        if len(data) < 2 or data[0] != 0x24:
            return

        try:
            mode = FileTransferMode(data[1])
            logger.info(f"File transfer status: {mode.name}")

            if mode == FileTransferMode.READY_TO_RECEIVE:
                self._transfer_ready.set()
            elif mode == FileTransferMode.FILE_RECEIVED_OK:
                self._transfer_complete.set()
            elif mode == FileTransferMode.FILE_RECEIVED_ERROR:
                self._transfer_error = "File transfer failed"
                self._transfer_complete.set()
            elif mode == FileTransferMode.FILE_TRANSFER_TIMEOUT:
                self._transfer_error = "File transfer timeout"
                self._transfer_complete.set()

        except ValueError:
            logger.warning(f"Unknown file transfer mode: {data[1]}")

    async def upload_dlc(
        self, dlc_path: Path, slot: int = 2, timeout: float = 60.0, enable_nordic_ack: bool = True
    ) -> None:
        """
        Upload a DLC file to Furby.

        Args:
            dlc_path: Path to DLC file
            slot: Slot number to upload to (default: 2)
            timeout: Upload timeout in seconds
            enable_nordic_ack: Enable Nordic packet ACK for monitoring (default: True)

        Raises:
            FileNotFoundError: If DLC file doesn't exist
            RuntimeError: If upload fails
        """
        if not dlc_path.exists():
            raise FileNotFoundError(f"DLC file not found: {dlc_path}")

        # Read DLC file
        dlc_data = dlc_path.read_bytes()
        file_size = len(dlc_data)
        filename = dlc_path.name

        logger.info(f"Uploading DLC: {filename} ({file_size} bytes) to slot {slot}")

        # Enable Nordic Packet ACK for monitoring
        if enable_nordic_ack:
            await self.furby.enable_nordic_packet_ack(True)

        # Reset transfer state
        self._transfer_ready.clear()
        self._transfer_complete.clear()
        self._transfer_error = None

        # Add transfer callback
        self.furby.add_gp_callback(self._file_transfer_callback)

        try:
            # Announce DLC upload
            cmd = FurbyProtocol.build_dlc_announce_command(file_size, slot, filename)
            await self.furby._write_gp(cmd)

            # Wait for ready signal
            try:
                await asyncio.wait_for(
                    self._transfer_ready.wait(), timeout=10.0
                )
            except TimeoutError:
                raise RuntimeError(
                    "Furby did not respond to DLC upload announcement"
                ) from None

            # Upload file in chunks
            logger.info("Furby ready, uploading data...")
            offset = 0
            chunk_count = 0

            while offset < file_size:
                chunk = dlc_data[offset : offset + FILE_CHUNK_SIZE]
                await self.furby._write_file(chunk)
                offset += len(chunk)
                chunk_count += 1

                # Small delay to prevent overwhelming Furby
                await asyncio.sleep(0.005)

                # Progress logging
                if chunk_count % 100 == 0:
                    progress = (offset / file_size) * 100
                    logger.info(f"Upload progress: {progress:.1f}%")

            logger.info(f"Uploaded {chunk_count} chunks, waiting for confirmation...")

            # Wait for transfer complete
            try:
                await asyncio.wait_for(
                    self._transfer_complete.wait(), timeout=timeout
                )
            except TimeoutError:
                raise RuntimeError("Timeout waiting for upload confirmation") from None

            # Check for errors
            if self._transfer_error:
                raise RuntimeError(self._transfer_error)

            logger.info("DLC upload complete!")

        finally:
            # Remove callback
            if self._file_transfer_callback in self.furby._gp_callbacks:
                self.furby._gp_callbacks.remove(self._file_transfer_callback)

    async def load_dlc(self, slot: int) -> None:
        """
        Load DLC from slot for activation.

        Args:
            slot: Slot number to load
        """
        cmd = FurbyProtocol.build_load_dlc_command(slot)
        await self.furby._write_gp(cmd)
        logger.info(f"Loaded DLC from slot {slot}")

    async def activate_dlc(self) -> None:
        """Activate the currently loaded DLC."""
        cmd = FurbyProtocol.build_activate_dlc_command()
        await self.furby._write_gp(cmd)
        logger.info("Activated DLC")

    async def deactivate_dlc(self, slot: int) -> None:
        """
        Deactivate DLC slot without deleting.

        Args:
            slot: Slot number to deactivate
        """
        cmd = FurbyProtocol.build_deactivate_dlc_command(slot)
        await self.furby._write_gp(cmd)
        logger.info(f"Deactivated DLC in slot {slot}")

    async def delete_dlc(self, slot: int) -> None:
        """
        Delete DLC from slot.

        Args:
            slot: Slot number to delete
        """
        cmd = FurbyProtocol.build_delete_dlc_command(slot)
        await self.furby._write_gp(cmd)
        logger.info(f"Deleted DLC from slot {slot}")
