"""
DLC (DownLoadable Content) file handling for Furby Connect.

DLC files contain audio, animations, and other content that can be
uploaded to Furby.
"""

import asyncio
import logging
from pathlib import Path

from pyfluff.furby import FurbyConnect
from pyfluff.protocol import (
    FILE_CHUNK_SIZE,
    FILE_MAX_PAUSE,
    FILE_MAX_UNACKED,
    FILE_PACKET_DELAY,
    FileTransferMode,
    FurbyProtocol,
    NordicCommand,
)

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
        self._unacked = 0
        self._caught_up = asyncio.Event()

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
                self._caught_up.set()  # stop pausing; the upload is over
            elif mode == FileTransferMode.FILE_TRANSFER_TIMEOUT:
                self._transfer_error = "File transfer timeout"
                self._transfer_complete.set()
                self._caught_up.set()  # stop pausing; the upload is over

        except ValueError:
            logger.warning(f"Unknown file transfer mode: {data[1]}")

    def _nordic_callback(self, data: bytes) -> None:
        """Track how many packets Furby has buffered, from its packet ACKs."""
        if len(data) >= 2 and data[0] == NordicCommand.PACKET_ACK.value:
            self._unacked = data[1]
            if self._unacked <= FILE_MAX_UNACKED:
                self._caught_up.set()

    async def upload_dlc(
        self,
        dlc_path: Path,
        slot: int = 2,
        timeout: float = 60.0,
        enable_nordic_ack: bool = True,
        filename: str | None = None,
        packet_delay: float = FILE_PACKET_DELAY,
    ) -> None:
        """
        Upload a DLC file to Furby.

        Args:
            dlc_path: Path to DLC file
            slot: Slot number to upload to (default: 2)
            timeout: Seconds to wait for Furby to confirm the upload once it's all sent
            enable_nordic_ack: Enable Nordic packet ACK, used to pace the upload (default: True)
            filename: Name to store it under, if not dlc_path's (e.g. an uploaded file's
                original name). Either way it's sent as an 8.3 name like ____PINK.DLC.
            packet_delay: Seconds between 20-byte packets (default: 0.015). Raise it if
                uploads time out.

        Raises:
            FileNotFoundError: If DLC file doesn't exist
            RuntimeError: If upload fails
        """
        if not dlc_path.exists():
            raise FileNotFoundError(f"DLC file not found: {dlc_path}")

        # Read DLC file
        dlc_data = dlc_path.read_bytes()
        file_size = len(dlc_data)
        name = filename or dlc_path.name
        furby_filename = FurbyProtocol.dlc_filename(name)
        if furby_filename.lstrip("_").lower() != name.replace("\\", "/").rsplit("/", 1)[-1].lower():
            logger.warning(f"Furby keeps 8.3 names, so sending {name} as {furby_filename}")

        logger.info(f"Uploading DLC: {furby_filename} ({file_size} bytes) to slot {slot}")

        # Reset transfer state
        self._transfer_ready.clear()
        self._transfer_complete.clear()
        self._transfer_error = None
        self._unacked = 0

        # Add transfer callbacks
        self.furby.add_gp_callback(self._file_transfer_callback)
        self.furby.add_nordic_callback(self._nordic_callback)

        acks_on = False
        try:
            # Enable Nordic Packet ACK, which reports how many packets Furby has buffered
            if enable_nordic_ack:
                await self.furby.enable_nordic_packet_ack(True)
                acks_on = True

            # Announce DLC upload
            cmd = FurbyProtocol.build_dlc_announce_command(file_size, slot, furby_filename)
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
                # Furby reported a timeout or receive error: stop sending
                if self._transfer_complete.is_set():
                    break

                # Hold back while Furby is behind. It seems to ACK only while packets
                # keep arriving, so carry on after a while regardless.
                if self._unacked > FILE_MAX_UNACKED:
                    self._caught_up.clear()
                    try:
                        await asyncio.wait_for(self._caught_up.wait(), FILE_MAX_PAUSE)
                    except TimeoutError:
                        self._unacked = 0

                chunk = dlc_data[offset : offset + FILE_CHUNK_SIZE]
                await self.furby._write_file(chunk)
                offset += len(chunk)
                chunk_count += 1

                # Writes don't wait for a response, so sending faster drops packets
                await asyncio.sleep(packet_delay)

                # Progress logging
                if chunk_count % 100 == 0:
                    progress = (offset / file_size) * 100
                    logger.info(f"Upload progress: {progress:.1f}%")

            if not self._transfer_complete.is_set():
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
            # Remove callbacks
            if self._file_transfer_callback in self.furby._gp_callbacks:
                self.furby._gp_callbacks.remove(self._file_transfer_callback)
            if self._nordic_callback in self.furby._nordic_callbacks:
                self.furby._nordic_callbacks.remove(self._nordic_callback)
            if acks_on:
                try:
                    await self.furby.enable_nordic_packet_ack(False)
                except Exception as e:  # e.g. Furby disconnected; keep the original error
                    logger.warning(f"Could not turn off Nordic packet ACK: {e}")

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
