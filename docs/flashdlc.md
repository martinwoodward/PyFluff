# How to flash your own DLCs

## Debugging the flashing process
Before starting, I recommend you to open the 6th debug menu on Furby's LCD eyes using the `0xdb` command or through PyFluff's CLI/API. This menu will give you an overview of Furby's DLC "Slots", the memory regions where DLC files get stored.

I would assume that the `2M`, `1M`, `.5M` might be the sizes of those memory slots (2 / 1 / 0.5 Megabytes respectively), but I have not tested that. What I know, however, is that the numbers behind the `M` provide useful information for debugging the flashing process. These numbers are:
* `0` if the slot is empty, i.e. after deleting the DLC file
* `1` if the DLC file is currently being flashed / has not completed flashing, so this will be displayed if the flashing process has failed somewhere in between for some reason
* `2` if the DLC file has been successfully downloaded, but not activated yet
* `3` if the DLC file is active

## Before you start

* **Making a DLC.** The [Context Furby tools](https://github.com/ctxis/Furby) parse, edit and rebuild DLC files (see [DLC Format](dlcformat.md)). A DLC only changes what Furby does for actions triggered over Bluetooth, like input `75`; its own reactions to petting, noise and so on come from built-in memory.
* **Size.** Uploads tend to time out above about 350 KB. Audio is the biggest part, at roughly 2 KB per second.
* **One Furby at a time.** Wake only the Furby you're flashing. Two Furby Connects near each other start singing together, and while they do, neither advertises, so neither can be found.
* **File names.** Furby stores DLCs under 8.3 names like `____PINK.DLC`. In testing, an upload sent without a `.DLC` extension was accepted but never stored. PyFluff converts the name for you: up to 8 letters and digits, padded with underscores, plus `.DLC`. Longer names are shortened (with a warning), so give files distinct names of 8 letters or fewer.

## Flashing process

### Delete the old DLC file
Delete the DLC files already on the Furby, so the new one has room. A slot's number is its position in the debug menu, and the number after its `M` is its status. Call `delete_dlc()` for each slot whose status isn't `0`, and if a slot's status is `3` (active), call `deactivate_dlc()` on it first. After this step, all debug numbers on Furby's LCD should be `0`.

```python
import asyncio

from pyfluff import FurbyConnect
from pyfluff.dlc import DLCManager

async def delete_dlc():
    async with FurbyConnect() as furby:
        dlc_manager = DLCManager(furby)
        await dlc_manager.deactivate_dlc(slot=2)  # only needed if it's active
        await dlc_manager.delete_dlc(slot=2)
        print("DLC deleted")

asyncio.run(delete_dlc())
```

### Flash the new DLC file
PyFluff sends the file in 20-byte packets, 15 ms apart. Before uploading, it turns on Nordic Packet ACKs, notifications in which Furby reports how many packets it has buffered. PyFluff pauses while Furby falls more than 10 packets behind. Furby seems to send ACKs only while packets keep arriving, so after 2 seconds PyFluff carries on anyway.

```python
import asyncio
from pathlib import Path

from pyfluff import FurbyConnect
from pyfluff.dlc import DLCManager

async def flash_dlc():
    async with FurbyConnect() as furby:
        dlc_manager = DLCManager(furby)
        await dlc_manager.upload_dlc(Path("path/to/your/pink.dlc"), slot=2)
        print("DLC uploaded successfully")

asyncio.run(flash_dlc())
```

Depending on the file's size, this takes **2–5 minutes** (a 300 KB file is 15,000 packets × 15 ms, so at least 3¾ minutes). Furby should show status `1` in the debug menu during the upload, then `2` when it's done. The file may not land in the slot you passed to `upload_dlc`, so check which slot shows `2`.

If Furby reports a problem, the upload stops right away and raises an error:
* **File transfer timeout** (`24:03`): Furby stopped receiving packets. Try again with a longer gap between packets, e.g. `upload_dlc(path, packet_delay=0.03)`, and keep Furby close.
* **File transfer failed** (`24:06`): Furby reported a receive error. Delete the DLCs on Furby and try again.

### Loading and activating
Load the DLC from the slot whose status is now `2`, then activate it. If another DLC is active (status `3`), deactivate it first. The example assumes it landed in slot 2.

```python
import asyncio

from pyfluff import FurbyConnect
from pyfluff.dlc import DLCManager

async def activate_dlc():
    async with FurbyConnect() as furby:
        dlc_manager = DLCManager(furby)
        await dlc_manager.load_dlc(slot=2)
        await dlc_manager.activate_dlc()
        print("DLC activated")

asyncio.run(activate_dlc())
```

After this, Furby's debug screen should show status `3` for that slot. The actions and songs in the DLC are now available through action input `75`, e.g. input 75, index 0, subindex 0 and specific 0. See [Action Sequences](actions.md) for how to trigger them.

## Using the CLI

PyFluff's CLI covers uploading, loading and activating:

```bash
pyfluff upload-dlc path/to/pink.dlc --slot 2
pyfluff load-dlc 2
pyfluff activate-dlc
```

To delete or deactivate a DLC, use `DLCManager.delete_dlc()` and `DLCManager.deactivate_dlc()` from Python as above, or the web server's `/dlc/delete/{slot}` and `/dlc/deactivate/{slot}` endpoints.

> [!NOTE]
> This documentation is derived from the [bluefluff project](https://github.com/Jeija/bluefluff) by Jeija. The original research and reverse engineering work was done by the bluefluff community. PyFluff is a modern Python implementation of the same protocols.