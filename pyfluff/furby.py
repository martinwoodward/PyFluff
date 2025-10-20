"""
Core Furby Connect BLE communication class.

This module provides the main FurbyConnect class for connecting to and
controlling Furby Connect toys via Bluetooth Low Energy.
"""

import asyncio
import logging
from collections.abc import AsyncIterator, Callable

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice

from pyfluff.models import FurbyInfo, SensorData
from pyfluff.protocol import (
    FURBY_NAME,
    IDLE_INTERVAL,
    FurbyCharacteristic,
    FurbyProtocol,
    GeneralPlusResponse,
    MoodMeterType,
)

logger = logging.getLogger(__name__)


class FurbyConnect:
    """
    Main class for connecting to and controlling a Furby Connect device.

    This class handles BLE connection, command sending, and notification handling.
    It uses modern async/await patterns and the Bleak BLE library.
    """

    def __init__(self, device: BLEDevice | None = None) -> None:
        """
        Initialize FurbyConnect instance.

        Args:
            device: Optional BLEDevice to connect to. If None, will scan for Furby.
        """
        self.device = device
        self.client: BleakClient | None = None
        self._connected = False
        self._idle_task: asyncio.Task[None] | None = None
        self._gp_callbacks: list[Callable[[bytes], None]] = []
        self._nordic_callbacks: list[Callable[[bytes], None]] = []

    @property
    def connected(self) -> bool:
        """Check if currently connected to a Furby."""
        return self._connected and self.client is not None and self.client.is_connected

    @staticmethod
    async def discover(timeout: float = 10.0) -> list[BLEDevice]:
        """
        Discover nearby Furby Connect devices.

        Args:
            timeout: Scan timeout in seconds

        Returns:
            List of discovered Furby devices
        """
        logger.info(f"Scanning for Furby devices (timeout: {timeout}s)...")
        devices = await BleakScanner.discover(timeout=timeout)
        furbies = [d for d in devices if d.name and FURBY_NAME in d.name]
        logger.info(f"Found {len(furbies)} Furby device(s)")
        return furbies

    async def connect(self, timeout: float = 10.0) -> None:
        """
        Connect to a Furby device.

        If no device was provided during initialization, will scan for one.

        Args:
            timeout: Connection timeout in seconds

        Raises:
            RuntimeError: If no Furby found or connection fails
        """
        if self._connected:
            logger.warning("Already connected to Furby")
            return

        # Discover device if not provided
        if self.device is None:
            devices = await self.discover(timeout)
            if not devices:
                raise RuntimeError("No Furby devices found")
            self.device = devices[0]
            logger.info(f"Selected Furby: {self.device.address}")

        # Connect to device
        logger.info(f"Connecting to Furby at {self.device.address}...")
        self.client = BleakClient(self.device, timeout=timeout)

        try:
            await self.client.connect()
            self._connected = True
            logger.info("Connected successfully")

            # Subscribe to notifications
            await self._subscribe_notifications()

            # Start idle keepalive
            self._start_idle()

        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self._connected = False
            raise RuntimeError(f"Failed to connect to Furby: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from Furby device."""
        if not self.client:
            return

        logger.info("Disconnecting from Furby...")

        # Stop idle task
        self._stop_idle()

        # Disconnect
        if self.client.is_connected:
            await self.client.disconnect()

        self._connected = False
        logger.info("Disconnected")

    async def _subscribe_notifications(self) -> None:
        """Subscribe to BLE notification characteristics."""
        if not self.client:
            return

        # Subscribe to GeneralPlus notifications
        await self.client.start_notify(
            FurbyCharacteristic.GENERALPLUS_LISTEN, self._gp_notification_handler
        )
        logger.debug("Subscribed to GeneralPlus notifications")

        # Subscribe to Nordic notifications
        await self.client.start_notify(
            FurbyCharacteristic.NORDIC_LISTEN, self._nordic_notification_handler
        )
        logger.debug("Subscribed to Nordic notifications")

        # Subscribe to RSSI notifications (optional)
        try:
            await self.client.start_notify(
                FurbyCharacteristic.RSSI_LISTEN, self._rssi_notification_handler
            )
            logger.debug("Subscribed to RSSI notifications")
        except Exception as e:
            logger.warning(f"Could not subscribe to RSSI: {e}")

    def _gp_notification_handler(self, sender: int, data: bytes) -> None:
        """Handle notifications from GeneralPlus characteristic."""
        logger.debug(f"GP notification: {data.hex()}")
        for callback in self._gp_callbacks:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in GP callback: {e}")

    def _nordic_notification_handler(self, sender: int, data: bytes) -> None:
        """Handle notifications from Nordic characteristic."""
        logger.debug(f"Nordic notification: {data.hex()}")
        for callback in self._nordic_callbacks:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in Nordic callback: {e}")

    def _rssi_notification_handler(self, sender: int, data: bytes) -> None:
        """Handle RSSI notifications."""
        logger.debug(f"RSSI notification: {data.hex()}")

    def add_gp_callback(self, callback: Callable[[bytes], None]) -> None:
        """Add callback for GeneralPlus notifications."""
        self._gp_callbacks.append(callback)

    def add_nordic_callback(self, callback: Callable[[bytes], None]) -> None:
        """Add callback for Nordic notifications."""
        self._nordic_callbacks.append(callback)

    def _start_idle(self) -> None:
        """Start idle keepalive task to prevent Furby from talking."""
        if self._idle_task is None or self._idle_task.done():
            self._idle_task = asyncio.create_task(self._idle_loop())
            logger.debug("Started idle keepalive")

    def _stop_idle(self) -> None:
        """Stop idle keepalive task."""
        if self._idle_task and not self._idle_task.done():
            self._idle_task.cancel()
            logger.debug("Stopped idle keepalive")

    async def _idle_loop(self) -> None:
        """Idle loop that sends keepalive packets."""
        try:
            while True:
                await asyncio.sleep(IDLE_INTERVAL)
                if self.connected:
                    await self._write_gp(bytes([0x00]))
        except asyncio.CancelledError:
            logger.debug("Idle loop cancelled")

    async def _write_gp(self, data: bytes) -> None:
        """Write data to GeneralPlus characteristic."""
        if not self.client or not self.connected:
            raise RuntimeError("Not connected to Furby")

        await self.client.write_gatt_char(
            FurbyCharacteristic.GENERALPLUS_WRITE, data, response=False
        )
        logger.debug(f"GP write: {data.hex()}")

    async def _write_nordic(self, data: bytes) -> None:
        """Write data to Nordic characteristic."""
        if not self.client or not self.connected:
            raise RuntimeError("Not connected to Furby")

        await self.client.write_gatt_char(
            FurbyCharacteristic.NORDIC_WRITE, data, response=False
        )
        logger.debug(f"Nordic write: {data.hex()}")

    async def enable_nordic_packet_ack(self, enabled: bool = True) -> None:
        """
        Enable or disable Nordic packet acknowledgment.

        When enabled, Furby will send GotPacketAck (0x09) responses while
        writing to the FileWrite characteristic. This is useful for DLC uploads
        to monitor transfer progress.

        Args:
            enabled: True to enable, False to disable
        """
        cmd = FurbyProtocol.build_nordic_packet_ack(enabled)
        await self._write_nordic(cmd)
        logger.info(f"Nordic packet ACK {'enabled' if enabled else 'disabled'}")

    async def _write_file(self, data: bytes) -> None:
        """Write data to File characteristic."""
        if not self.client or not self.connected:
            raise RuntimeError("Not connected to Furby")

        await self.client.write_gatt_char(
            FurbyCharacteristic.FILE_WRITE, data, response=False
        )
        logger.debug(f"File write: {data.hex()}")

    # High-level command methods

    async def set_antenna_color(self, red: int, green: int, blue: int) -> None:
        """
        Set antenna LED color.

        Args:
            red: Red channel (0-255)
            green: Green channel (0-255)
            blue: Blue channel (0-255)
        """
        cmd = FurbyProtocol.build_antenna_command(red, green, blue)
        await self._write_gp(cmd)
        logger.info(f"Set antenna color to RGB({red}, {green}, {blue})")

    async def trigger_action(
        self, input: int, index: int, subindex: int, specific: int
    ) -> None:
        """
        Trigger a specific Furby action.

        Args:
            input: Action input value
            index: Action index
            subindex: Action subindex
            specific: Specific action ID
        """
        cmd = FurbyProtocol.build_action_command(input, index, subindex, specific)
        await self._write_gp(cmd)
        logger.info(f"Triggered action: {input}/{index}/{subindex}/{specific}")

    async def set_lcd_backlight(self, enabled: bool) -> None:
        """
        Control LCD backlight.

        Args:
            enabled: True to turn on, False to turn off
        """
        cmd = FurbyProtocol.build_lcd_command(enabled)
        await self._write_gp(cmd)
        logger.info(f"LCD backlight: {'on' if enabled else 'off'}")

    async def cycle_debug_menu(self) -> None:
        """Cycle through LCD debug menus."""
        cmd = FurbyProtocol.build_debug_menu_command()
        await self._write_gp(cmd)
        logger.info("Cycled debug menu")

    async def set_name(self, name_id: int) -> None:
        """
        Set Furby name.

        Args:
            name_id: Name ID (0-128)
        """
        cmd = FurbyProtocol.build_name_command(name_id)
        await self._write_gp(cmd)
        # Also trigger action to say the name
        await self.trigger_action(input=0x21, index=0, subindex=0, specific=name_id)
        logger.info(f"Set name to ID {name_id}")

    async def set_mood(
        self, mood_type: MoodMeterType, value: int, set_absolute: bool = True
    ) -> None:
        """
        Set Furby mood meter.

        Args:
            mood_type: Type of mood to set
            value: Value to set or delta
            set_absolute: True to set absolute value, False to increase
        """
        action = 1 if set_absolute else 0
        cmd = FurbyProtocol.build_moodmeter_command(action, mood_type, value)
        await self._write_gp(cmd)
        logger.info(f"Set mood {mood_type.name} to {value} (absolute={set_absolute})")

    async def get_device_info(self) -> FurbyInfo:
        """
        Get device information from Furby.

        Returns:
            FurbyInfo with device details
        """
        if not self.client or not self.connected:
            raise RuntimeError("Not connected to Furby")

        info = FurbyInfo()

        # Read device information characteristics
        try:
            data = await self.client.read_gatt_char(FurbyCharacteristic.MANUFACTURER_NAME)
            info.manufacturer = data.decode("utf-8").strip("\x00")
        except Exception as e:
            logger.warning(f"Could not read manufacturer: {e}")

        try:
            data = await self.client.read_gatt_char(FurbyCharacteristic.MODEL_NUMBER)
            info.model_number = data.decode("utf-8").strip("\x00")
        except Exception as e:
            logger.warning(f"Could not read model number: {e}")

        try:
            data = await self.client.read_gatt_char(FurbyCharacteristic.SERIAL_NUMBER)
            info.serial_number = data.decode("utf-8").strip("\x00")
        except Exception as e:
            logger.warning(f"Could not read serial number: {e}")

        try:
            data = await self.client.read_gatt_char(FurbyCharacteristic.HARDWARE_REVISION)
            info.hardware_revision = data.decode("utf-8").strip("\x00")
        except Exception as e:
            logger.warning(f"Could not read hardware revision: {e}")

        try:
            data = await self.client.read_gatt_char(FurbyCharacteristic.FIRMWARE_REVISION)
            info.firmware_revision = data.decode("utf-8").strip("\x00")
        except Exception as e:
            logger.warning(f"Could not read firmware revision: {e}")

        try:
            data = await self.client.read_gatt_char(FurbyCharacteristic.SOFTWARE_REVISION)
            info.software_revision = data.decode("utf-8").strip("\x00")
        except Exception as e:
            logger.warning(f"Could not read software revision: {e}")

        return info

    async def sensor_stream(self) -> AsyncIterator[SensorData]:
        """
        Stream sensor data from Furby.

        Yields:
            SensorData objects with sensor readings
        """
        import time

        queue: asyncio.Queue[bytes] = asyncio.Queue()

        def sensor_callback(data: bytes) -> None:
            if len(data) > 0 and data[0] == GeneralPlusResponse.SENSOR_STATUS.value:
                queue.put_nowait(data)

        self.add_gp_callback(sensor_callback)

        try:
            while True:
                data = await queue.get()
                yield SensorData(timestamp=time.time(), raw_data=data.hex())
        finally:
            self._gp_callbacks.remove(sensor_callback)

    async def __aenter__(self) -> "FurbyConnect":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: type, exc_val: Exception, exc_tb: object) -> None:
        """Async context manager exit."""
        await self.disconnect()
