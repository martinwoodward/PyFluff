"""
Tests for DLC uploads, against a stand-in for a connected Furby.
"""

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from pyfluff.dlc import DLCManager


class FakeFurby:
    """Answers a DLC upload the way Furby does: 24:02 when ready, 24:05 once it has it all."""

    def __init__(self, size: int, fail_after: int | None = None, unacked: int = 0) -> None:
        self.size = size
        self.fail_after = fail_after
        self.unacked = unacked
        self.announce = b""
        self.received = b""
        self.writes = 0
        self.acks: list[bool] = []
        self._gp_callbacks: list[Callable[[bytes], None]] = []
        self._nordic_callbacks: list[Callable[[bytes], None]] = []

    def add_gp_callback(self, callback: Callable[[bytes], None]) -> None:
        self._gp_callbacks.append(callback)

    def add_nordic_callback(self, callback: Callable[[bytes], None]) -> None:
        self._nordic_callbacks.append(callback)

    def notify(self, data: bytes) -> None:
        for callback in list(self._gp_callbacks):
            callback(data)

    async def enable_nordic_packet_ack(self, enabled: bool) -> None:
        self.acks.append(enabled)

    async def _write_gp(self, data: bytes) -> None:
        if data[0] == 0x50:
            self.announce = data
            self.notify(bytes([0x24, 0x02]))

    async def _write_file(self, data: bytes) -> None:
        self.received += data
        self.writes += 1
        for callback in list(self._nordic_callbacks):
            callback(bytes([0x09, self.unacked]))
        if self.fail_after is not None and self.writes == self.fail_after:
            self.notify(bytes([0x24, 0x06]))
        elif len(self.received) == self.size:
            self.notify(bytes([0x24, 0x05]))


def manager(furby: FakeFurby) -> DLCManager:
    fake: Any = furby
    return DLCManager(fake)


@pytest.fixture
def dlc_file(tmp_path: Path) -> Path:
    path = tmp_path / "spooky_pumpkin.dlc"
    path.write_bytes(bytes(range(256)) * 4)  # 1,024 bytes: 51 full packets and a short one
    return path


async def test_upload(dlc_file: Path) -> None:
    furby = FakeFurby(1024)
    await manager(furby).upload_dlc(dlc_file, packet_delay=0)

    assert furby.announce[6:18] == b"SPOOKYPU.DLC"
    assert furby.received == dlc_file.read_bytes()
    assert furby.acks == [True, False]
    assert furby._gp_callbacks == [] and furby._nordic_callbacks == []


async def test_upload_filename(dlc_file: Path) -> None:
    furby = FakeFurby(1024)
    await manager(furby).upload_dlc(dlc_file, filename="pink.dlc", packet_delay=0)

    assert furby.announce[6:18] == b"____PINK.DLC"


async def test_upload_stops_on_furby_error(dlc_file: Path) -> None:
    furby = FakeFurby(1024, fail_after=3)
    with pytest.raises(RuntimeError, match="File transfer failed"):
        await manager(furby).upload_dlc(dlc_file, packet_delay=0)

    assert furby.writes == 3
    assert furby._gp_callbacks == [] and furby._nordic_callbacks == []


async def test_upload_pauses_while_furby_is_behind(
    dlc_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("pyfluff.dlc.FILE_MAX_PAUSE", 0.01)
    furby = FakeFurby(1024, unacked=11)  # always behind, so every packet waits out the pause

    loop = asyncio.get_running_loop()
    started = loop.time()
    await manager(furby).upload_dlc(dlc_file, packet_delay=0)

    assert furby.received == dlc_file.read_bytes()
    assert loop.time() - started >= 51 * 0.01


async def test_upload_cleans_up_when_acks_fail(dlc_file: Path) -> None:
    furby = FakeFurby(1024)

    async def not_connected(enabled: bool) -> None:
        raise RuntimeError("Not connected to Furby")

    furby.enable_nordic_packet_ack = not_connected  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="Not connected"):
        await manager(furby).upload_dlc(dlc_file, packet_delay=0)

    assert furby._gp_callbacks == [] and furby._nordic_callbacks == []
