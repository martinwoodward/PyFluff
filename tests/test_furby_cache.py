"""
Tests for PyFluff Furby cache functionality.
"""

import json
import tempfile
from pathlib import Path

from pyfluff.furby_cache import FurbyCache


class TestFurbyCache:
    """Tests for FurbyCache class."""

    def test_create_new_cache(self) -> None:
        """Test creating a new cache when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache.json"
            cache = FurbyCache(cache_path)

            assert cache.cache_file == cache_path
            assert len(cache.config.furbies) == 0
            assert not cache_path.exists()  # Not saved yet

    def test_add_furby(self) -> None:
        """Test adding a Furby to cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache.json"
            cache = FurbyCache(cache_path)

            furby = cache.add_or_update(address="AA:BB:CC:DD:EE:FF", device_name="Furby")

            assert furby.address == "AA:BB:CC:DD:EE:FF"
            assert furby.device_name == "Furby"
            assert furby.last_seen > 0
            assert len(cache.config.furbies) == 1

    def test_update_existing_furby(self) -> None:
        """Test updating an existing Furby in cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache.json"
            cache = FurbyCache(cache_path)

            # Add Furby
            furby1 = cache.add_or_update(address="AA:BB:CC:DD:EE:FF", device_name="Furby")
            first_timestamp = furby1.last_seen

            # Update same Furby
            furby2 = cache.add_or_update(address="AA:BB:CC:DD:EE:FF", name="Ah-Bay", name_id=0)

            # Should be same address but updated
            assert furby2.address == "AA:BB:CC:DD:EE:FF"
            assert furby2.name == "Ah-Bay"
            assert furby2.name_id == 0
            assert furby2.last_seen >= first_timestamp
            assert len(cache.config.furbies) == 1  # Still only one Furby

    def test_save_and_load_cache(self) -> None:
        """Test saving and loading cache from disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache.json"

            # Create and populate cache
            cache1 = FurbyCache(cache_path)
            cache1.add_or_update(
                address="AA:BB:CC:DD:EE:FF", device_name="Furby", name="Ah-Bay", name_id=0
            )
            # add_or_update auto-saves via _save()

            assert cache_path.exists()

            # Load cache in new instance
            cache2 = FurbyCache(cache_path)
            assert len(cache2.config.furbies) == 1
            assert "AA:BB:CC:DD:EE:FF" in cache2.config.furbies

            furby = cache2.config.furbies["AA:BB:CC:DD:EE:FF"]
            assert furby.name == "Ah-Bay"
            assert furby.name_id == 0

    def test_get_existing_furby(self) -> None:
        """Test retrieving an existing Furby from cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache.json"
            cache = FurbyCache(cache_path)

            cache.add_or_update(address="AA:BB:CC:DD:EE:FF", device_name="Furby")

            furby = cache.get("AA:BB:CC:DD:EE:FF")
            assert furby is not None
            assert furby.address == "AA:BB:CC:DD:EE:FF"

    def test_get_nonexistent_furby(self) -> None:
        """Test retrieving a non-existent Furby returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache.json"
            cache = FurbyCache(cache_path)

            furby = cache.get("AA:BB:CC:DD:EE:FF")
            assert furby is None

    def test_list_all_furbies(self) -> None:
        """Test listing all cached Furbies."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache.json"
            cache = FurbyCache(cache_path)

            cache.add_or_update(address="AA:BB:CC:DD:EE:FF", device_name="Furby1")
            cache.add_or_update(address="11:22:33:44:55:66", device_name="Furby2")
            cache.add_or_update(address="FF:EE:DD:CC:BB:AA", device_name="Furby3")

            furbies = cache.get_all()
            assert len(furbies) == 3

            addresses = [f.address for f in furbies]
            assert "AA:BB:CC:DD:EE:FF" in addresses
            assert "11:22:33:44:55:66" in addresses
            assert "FF:EE:DD:CC:BB:AA" in addresses

    def test_remove_furby(self) -> None:
        """Test removing a Furby from cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache.json"
            cache = FurbyCache(cache_path)

            cache.add_or_update(address="AA:BB:CC:DD:EE:FF", device_name="Furby1")
            cache.add_or_update(address="11:22:33:44:55:66", device_name="Furby2")

            assert len(cache.config.furbies) == 2

            result = cache.remove("AA:BB:CC:DD:EE:FF")
            assert result is True
            assert len(cache.config.furbies) == 1
            assert "AA:BB:CC:DD:EE:FF" not in cache.config.furbies
            assert "11:22:33:44:55:66" in cache.config.furbies

    def test_remove_nonexistent_furby(self) -> None:
        """Test removing a non-existent Furby returns False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache.json"
            cache = FurbyCache(cache_path)

            result = cache.remove("AA:BB:CC:DD:EE:FF")
            assert result is False

    def test_clear_cache(self) -> None:
        """Test clearing all Furbies from cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache.json"
            cache = FurbyCache(cache_path)

            cache.add_or_update(address="AA:BB:CC:DD:EE:FF", device_name="Furby1")
            cache.add_or_update(address="11:22:33:44:55:66", device_name="Furby2")

            assert len(cache.config.furbies) == 2

            cache.clear()
            assert len(cache.config.furbies) == 0

    def test_load_corrupted_cache(self) -> None:
        """Test loading a corrupted cache file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache.json"

            # Write corrupted JSON
            with open(cache_path, "w") as f:
                f.write("{ this is not valid json }")

            # Should handle gracefully and start with empty cache
            cache = FurbyCache(cache_path)
            assert len(cache.config.furbies) == 0

    def test_save_with_multiple_furbies(self) -> None:
        """Test saving cache with multiple Furbies."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache.json"
            cache = FurbyCache(cache_path)

            cache.add_or_update(
                address="AA:BB:CC:DD:EE:FF", device_name="Furby1", name="Ah-Bay", name_id=0
            )
            cache.add_or_update(
                address="11:22:33:44:55:66",
                device_name="Furby2",
                name="Bee-Boh",
                name_id=11,
                firmware_revision="1.2.3",
            )

            # add_or_update auto-saves via _save()

            # Verify file contents
            with open(cache_path) as f:
                data = json.load(f)

            assert "furbies" in data
            assert len(data["furbies"]) == 2
            assert "AA:BB:CC:DD:EE:FF" in data["furbies"]
            assert "11:22:33:44:55:66" in data["furbies"]
            assert data["furbies"]["11:22:33:44:55:66"]["firmware_revision"] == "1.2.3"

    def test_cache_file_in_subdirectory(self) -> None:
        """Test creating cache file in a subdirectory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "subdir" / "nested" / "cache.json"
            cache = FurbyCache(cache_path)

            cache.add_or_update(address="AA:BB:CC:DD:EE:FF", device_name="Furby")
            # add_or_update auto-saves via _save()

            # Should create parent directories
            assert cache_path.exists()
            assert cache_path.parent.exists()

    def test_list_sorted_by_last_seen(self) -> None:
        """Test listing Furbies sorted by last seen timestamp."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache.json"
            cache = FurbyCache(cache_path)

            # Add Furbies with slight delays to ensure different timestamps
            import time

            cache.add_or_update(address="AA:BB:CC:DD:EE:FF", device_name="Furby1")
            time.sleep(0.01)
            cache.add_or_update(address="11:22:33:44:55:66", device_name="Furby2")
            time.sleep(0.01)
            cache.add_or_update(address="FF:EE:DD:CC:BB:AA", device_name="Furby3")

            # get_all() returns sorted list (most recent first)
            furbies = cache.get_all()
            assert len(furbies) == 3

            # Should be in reverse chronological order
            assert furbies[0].address == "FF:EE:DD:CC:BB:AA"
            assert furbies[1].address == "11:22:33:44:55:66"
            assert furbies[2].address == "AA:BB:CC:DD:EE:FF"

    def test_update_firmware_version(self) -> None:
        """Test updating firmware version of cached Furby."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache.json"
            cache = FurbyCache(cache_path)

            cache.add_or_update(address="AA:BB:CC:DD:EE:FF", device_name="Furby")
            cache.add_or_update(address="AA:BB:CC:DD:EE:FF", firmware_revision="1.2.3")

            furby = cache.get("AA:BB:CC:DD:EE:FF")
            assert furby is not None
            assert furby.firmware_revision == "1.2.3"

    def test_get_addresses(self) -> None:
        """Test getting all MAC addresses from cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache.json"
            cache = FurbyCache(cache_path)

            cache.add_or_update(address="AA:BB:CC:DD:EE:FF", device_name="Furby1")
            cache.add_or_update(address="11:22:33:44:55:66", device_name="Furby2")

            addresses = cache.get_addresses()
            assert len(addresses) == 2
            assert "AA:BB:CC:DD:EE:FF" in addresses
            assert "11:22:33:44:55:66" in addresses

    def test_update_name(self) -> None:
        """Test updating name of a known Furby."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache.json"
            cache = FurbyCache(cache_path)

            cache.add_or_update(address="AA:BB:CC:DD:EE:FF", device_name="Furby")
            cache.update_name("AA:BB:CC:DD:EE:FF", "Ah-Bay", 0)

            furby = cache.get("AA:BB:CC:DD:EE:FF")
            assert furby is not None
            assert furby.name == "Ah-Bay"
            assert furby.name_id == 0

    def test_update_name_nonexistent_furby(self) -> None:
        """Test updating name of non-existent Furby does nothing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache.json"
            cache = FurbyCache(cache_path)

            # Should not raise error, just log warning
            cache.update_name("AA:BB:CC:DD:EE:FF", "Ah-Bay", 0)
            assert len(cache.config.furbies) == 0

    def test_get_most_recent(self) -> None:
        """Test getting the most recently seen Furby."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache.json"
            cache = FurbyCache(cache_path)

            import time

            cache.add_or_update(address="AA:BB:CC:DD:EE:FF", device_name="Furby1")
            time.sleep(0.01)
            cache.add_or_update(address="11:22:33:44:55:66", device_name="Furby2")

            most_recent = cache.get_most_recent()
            assert most_recent is not None
            assert most_recent.address == "11:22:33:44:55:66"

    def test_get_most_recent_empty_cache(self) -> None:
        """Test getting most recent from empty cache returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache.json"
            cache = FurbyCache(cache_path)

            most_recent = cache.get_most_recent()
            assert most_recent is None
