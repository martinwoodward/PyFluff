"""
Furby cache management for persisting discovered Furby devices.

This module provides functionality to cache discovered Furbies, including
their MAC addresses, names, and last seen timestamps. This allows the
application to remember previously connected Furbies and provides quick
access to known devices even when they're in F2F mode.
"""

import asyncio
import json
import logging
import time
from pathlib import Path

import aiofiles

from pyfluff.models import KnownFurbiesConfig, KnownFurby

logger = logging.getLogger(__name__)


class FurbyCache:
    """
    Manages a persistent cache of known Furby devices.

    The cache is stored as a JSON file and tracks:
    - MAC addresses of discovered Furbies
    - Last known names and name IDs
    - Last seen timestamps
    - Firmware versions (when available)

    Uses async I/O for better performance and batches writes to reduce disk operations.
    """

    def __init__(self, cache_file: Path | str = "known_furbies.json") -> None:
        """
        Initialize the Furby cache.

        Args:
            cache_file: Path to the cache file (default: known_furbies.json)
        """
        self.cache_file = Path(cache_file)
        self.config = self._load()
        self._save_pending = False
        self._save_lock = asyncio.Lock()

    def _load(self) -> KnownFurbiesConfig:
        """Load cache from disk."""
        if not self.cache_file.exists():
            logger.info(f"Cache file not found, creating new cache: {self.cache_file}")
            return KnownFurbiesConfig(furbies={})

        try:
            with open(self.cache_file) as f:
                data = json.load(f)
                config = KnownFurbiesConfig(**data)
                logger.info(f"Loaded {len(config.furbies)} known Furbies from cache")
                return config
        except Exception as e:
            logger.error(f"Failed to load cache file: {e}")
            logger.warning("Starting with empty cache")
            return KnownFurbiesConfig(furbies={})

    async def _save_async(self) -> None:
        """Save cache to disk asynchronously."""
        async with self._save_lock:
            try:
                self.cache_file.parent.mkdir(parents=True, exist_ok=True)
                async with aiofiles.open(self.cache_file, "w") as f:
                    await f.write(json.dumps(self.config.model_dump(), indent=2))
                logger.debug(f"Saved cache with {len(self.config.furbies)} Furbies")
                self._save_pending = False
            except Exception as e:
                logger.error(f"Failed to save cache file: {e}")

    def _save(self) -> None:
        """Save cache to disk (synchronous fallback)."""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, "w") as f:
                json.dump(self.config.model_dump(), f, indent=2)
            logger.debug(f"Saved cache with {len(self.config.furbies)} Furbies")
            self._save_pending = False
        except Exception as e:
            logger.error(f"Failed to save cache file: {e}")

    def _schedule_save(self) -> None:
        """Schedule an async save operation."""
        if not self._save_pending:
            self._save_pending = True
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._save_async())
            except RuntimeError:
                # No event loop running, fall back to sync save
                self._save()

    def add_or_update(
        self,
        address: str,
        device_name: str | None = None,
        name: str | None = None,
        name_id: int | None = None,
        firmware_revision: str | None = None,
    ) -> KnownFurby:
        """
        Add or update a Furby in the cache.

        Args:
            address: MAC address of the Furby
            device_name: BLE device name (e.g., "Furby")
            name: Furby's name (if known)
            name_id: Furby's name ID (0-128)
            firmware_revision: Firmware version (if known)

        Returns:
            The updated KnownFurby entry
        """
        # Get existing entry or create new one
        if address in self.config.furbies:
            furby = self.config.furbies[address]
            logger.debug(f"Updating existing Furby: {address}")
        else:
            furby = KnownFurby(address=address, last_seen=time.time())
            logger.info(f"Adding new Furby to cache: {address}")

        # Update fields (only if new values provided)
        if device_name is not None:
            furby.device_name = device_name
        if name is not None:
            furby.name = name
        if name_id is not None:
            furby.name_id = name_id
        if firmware_revision is not None:
            furby.firmware_revision = firmware_revision

        # Always update last_seen
        furby.last_seen = time.time()

        # Save to cache
        self.config.furbies[address] = furby
        self._schedule_save()

        return furby

    def get(self, address: str) -> KnownFurby | None:
        """
        Get a Furby from the cache by MAC address.

        Args:
            address: MAC address of the Furby

        Returns:
            KnownFurby entry if found, None otherwise
        """
        return self.config.furbies.get(address)

    def get_all(self) -> list[KnownFurby]:
        """
        Get all known Furbies from the cache.

        Returns:
            List of all KnownFurby entries, sorted by last_seen (newest first)
        """
        return sorted(self.config.furbies.values(), key=lambda f: f.last_seen, reverse=True)

    def remove(self, address: str) -> bool:
        """
        Remove a Furby from the cache.

        Args:
            address: MAC address of the Furby to remove

        Returns:
            True if removed, False if not found
        """
        if address in self.config.furbies:
            del self.config.furbies[address]
            self._schedule_save()
            logger.info(f"Removed Furby from cache: {address}")
            return True
        return False

    def clear(self) -> None:
        """Clear all entries from the cache."""
        count = len(self.config.furbies)
        self.config.furbies.clear()
        self._schedule_save()
        logger.info(f"Cleared cache ({count} entries removed)")

    def get_addresses(self) -> list[str]:
        """
        Get all known MAC addresses.

        Returns:
            List of MAC addresses
        """
        return list(self.config.furbies.keys())

    def update_name(self, address: str, name: str, name_id: int) -> None:
        """
        Update the name of a known Furby.

        Args:
            address: MAC address of the Furby
            name: New name
            name_id: New name ID (0-128)
        """
        if address in self.config.furbies:
            self.config.furbies[address].name = name
            self.config.furbies[address].name_id = name_id
            self.config.furbies[address].last_seen = time.time()
            self._schedule_save()
            logger.info(f"Updated name for {address}: {name} (ID: {name_id})")
        else:
            logger.warning(f"Cannot update name for unknown Furby: {address}")

    def get_most_recent(self) -> KnownFurby | None:
        """
        Get the most recently seen Furby.

        Returns:
            Most recent KnownFurby entry, or None if cache is empty
        """
        furbies = self.get_all()
        return furbies[0] if furbies else None
