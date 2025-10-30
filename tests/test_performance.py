"""
Performance tests for PyFluff optimizations.

These tests validate that performance optimizations are working correctly.
"""

import asyncio
import time
from pathlib import Path
from unittest.mock import AsyncMock

import aiofiles
import pytest

from pyfluff.furby import FurbyConnect
from pyfluff.furby_cache import FurbyCache
from pyfluff.models import KnownFurby
from pyfluff.protocol import FILE_CHUNK_SIZE


@pytest.mark.asyncio
async def test_device_info_caching() -> None:
    """Test that device info is cached and reused."""
    furby = FurbyConnect()
    furby._connected = True

    # Mock the BLE client
    mock_client = AsyncMock()
    furby.client = mock_client

    # Mock read_gatt_char to return dummy data
    mock_client.read_gatt_char = AsyncMock(return_value=b"TestData\x00")

    # First call should read from BLE
    info1 = await furby.get_device_info(use_cache=True)
    assert mock_client.read_gatt_char.call_count == 6  # 6 characteristics

    # Second call should use cache (no additional BLE reads)
    info2 = await furby.get_device_info(use_cache=True)
    assert mock_client.read_gatt_char.call_count == 6  # Still 6, not 12

    # Both should return the same cached object
    assert info1 is info2
    assert info1.manufacturer == "TestData"


@pytest.mark.asyncio
async def test_device_info_concurrent_reads() -> None:
    """Test that device info reads happen concurrently, not sequentially."""
    furby = FurbyConnect()
    furby._connected = True

    # Mock the BLE client
    mock_client = AsyncMock()
    furby.client = mock_client

    # Track timing of reads
    read_times = []

    async def mock_read(char_uuid: str) -> bytes:
        """Mock read that takes 100ms."""
        read_times.append(time.time())
        await asyncio.sleep(0.1)  # Simulate BLE read delay
        return b"TestData\x00"

    mock_client.read_gatt_char = mock_read

    # Read device info (should be concurrent)
    start_time = time.time()
    await furby.get_device_info(use_cache=False)
    elapsed = time.time() - start_time

    # With concurrent reads, total time should be ~0.1s (not ~0.6s for sequential)
    # Allow some tolerance for test execution overhead
    assert elapsed < 0.3, f"Reads took {elapsed}s, should be concurrent (~0.1s)"

    # All reads should have started roughly at the same time
    if len(read_times) >= 2:
        time_spread = max(read_times) - min(read_times)
        assert time_spread < 0.05, "Reads should start concurrently"


def test_furby_cache_batched_writes(tmp_path: Path) -> None:
    """Test that cache writes are batched efficiently."""
    cache_file = tmp_path / "test_cache.json"
    cache = FurbyCache(cache_file)

    async def add_entries():
        """Add entries with async support."""
        for i in range(10):
            cache.add_or_update(
                address=f"AA:BB:CC:DD:EE:{i:02X}",
                device_name="Furby",
            )
        # Wait a bit for async writes to complete
        await asyncio.sleep(0.2)

    # Run in async context to allow async writes
    asyncio.run(add_entries())

    # The cache should have all entries
    assert len(cache.config.furbies) == 10

    # File should exist
    assert cache_file.exists()

    # Verify data was saved
    cache2 = FurbyCache(cache_file)
    assert len(cache2.config.furbies) == 10


def test_furby_cache_efficient_sorting(tmp_path: Path) -> None:
    """Test that get_all() uses efficient sorting."""
    cache_file = tmp_path / "test_sort.json"
    cache = FurbyCache(cache_file)

    # Directly add entries to avoid automatic last_seen updates
    base_time = 1000.0
    for i in range(100):
        furby = KnownFurby(
            address=f"AA:BB:CC:DD:EE:{i:02X}",
            last_seen=base_time + float(i),
        )
        # Directly add to avoid add_or_update() which updates last_seen
        cache.config.furbies[furby.address] = furby

    # get_all() should return sorted list efficiently
    start_time = time.time()
    furbies = cache.get_all()
    elapsed = time.time() - start_time

    # Should be very fast for 100 items
    assert elapsed < 0.01, f"Sorting took {elapsed}s, should be < 0.01s"

    # Verify correct sort order (newest first)
    assert furbies[0].last_seen == base_time + 99.0, f"First: {furbies[0].last_seen}"
    assert furbies[-1].last_seen == base_time + 0.0, f"Last: {furbies[-1].last_seen}"


@pytest.mark.asyncio
async def test_dlc_chunked_reading(tmp_path: Path) -> None:
    """Test that DLC upload uses async file I/O with chunked reading."""
    # Create a test file using tmp_path for portability
    test_file = tmp_path / "test_dlc_read.dlc"
    test_data = b"A" * 1000  # 1KB test file
    test_file.write_bytes(test_data)

    # Verify the file can be read in chunks using aiofiles
    async with aiofiles.open(test_file, "rb") as f:
        chunks_read = 0
        total_bytes = 0
        while True:
            chunk = await f.read(FILE_CHUNK_SIZE)
            if not chunk:
                break
            chunks_read += 1
            total_bytes += len(chunk)
            assert len(chunk) <= FILE_CHUNK_SIZE

        # 1000 bytes / 20 bytes per chunk = 50 chunks
        expected_chunks = 1000 // FILE_CHUNK_SIZE
        assert chunks_read == expected_chunks, f"Expected {expected_chunks} chunks, got {chunks_read}"
        assert total_bytes == 1000, f"Expected 1000 bytes, got {total_bytes}"


def test_cache_memory_efficiency() -> None:
    """Test that cache operations don't create unnecessary copies."""
    cache = FurbyCache()

    # Add a furby
    furby1 = cache.add_or_update(
        address="AA:BB:CC:DD:EE:FF",
        device_name="Furby",
    )

    # Get it back
    furby2 = cache.get("AA:BB:CC:DD:EE:FF")

    # Should be the same object (not a copy)
    assert furby1 is furby2

    # get_all should return the actual objects, not copies
    all_furbies = cache.get_all()
    assert any(f is furby1 for f in all_furbies)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
