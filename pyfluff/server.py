"""
FastAPI web server for PyFluff.

Provides HTTP API and WebSocket support for controlling Furby Connect.
"""

import asyncio
import logging
import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from pyfluff.dlc import DLCManager
from pyfluff.furby import FurbyConnect
from pyfluff.furby_cache import FurbyCache
from pyfluff.models import (
    ActionList,
    ActionSequence,
    AntennaColor,
    CommandResponse,
    ConnectRequest,
    FurbyStatus,
    MoodUpdate,
)
from pyfluff.protocol import MoodMeterType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global Furby instance and cache
furby: FurbyConnect | None = None
furby_cache: FurbyCache | None = None
connection_logs: list[WebSocket] = []


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan context manager for FastAPI app."""
    global furby, furby_cache

    # Startup: Load cache and prepare for connections
    logger.info("PyFluff server starting up...")
    furby = None

    # Initialize Furby cache
    try:
        furby_cache = FurbyCache("known_furbies.json")
        known_count = len(furby_cache.get_all())
        logger.info(f"Loaded Furby cache with {known_count} known device(s)")
    except Exception as e:
        logger.error(f"Failed to initialize cache: {e}")
        furby_cache = FurbyCache()  # Start with empty cache

    logger.info("Server ready. Connect to Furby via the web interface.")

    yield

    # Shutdown: Disconnect from Furby
    logger.info("PyFluff server shutting down...")
    if furby and furby.connected:
        try:
            await furby.disconnect()
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")


# Create FastAPI app
app = FastAPI(
    title="PyFluff API",
    description="Modern Python controller for Furby Connect via Bluetooth LE",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
web_dir = Path(__file__).parent.parent / "web"
if web_dir.exists():
    app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")


# Helper function to check connection
def get_furby() -> FurbyConnect:
    """Get connected Furby instance or raise error."""
    if furby is None or not furby.connected:
        raise HTTPException(status_code=503, detail="Not connected to Furby")
    return furby


async def broadcast_log(message: str, log_type: str = "info") -> None:
    """Broadcast log message to all connected WebSocket clients."""
    if not connection_logs:
        return

    log_data = {"message": message, "type": log_type}

    # Send to all connected clients
    disconnected = []
    for ws in connection_logs:
        try:
            await ws.send_json(log_data)
        except Exception:
            disconnected.append(ws)

    # Remove disconnected clients
    for ws in disconnected:
        connection_logs.remove(ws)


# API Endpoints


@app.get("/")
async def root() -> HTMLResponse:
    """Serve web interface."""
    web_dir = Path(__file__).parent.parent / "web"
    index_file = web_dir / "index.html"

    if index_file.exists():
        return FileResponse(index_file)
    else:
        return HTMLResponse(
            """
            <html>
                <head><title>PyFluff</title></head>
                <body>
                    <h1>PyFluff API Server</h1>
                    <p>Web interface not found. API is available at <a href="/docs">/docs</a></p>
                </body>
            </html>
            """
        )


@app.get("/status", response_model=FurbyStatus)
async def get_status() -> FurbyStatus:
    """Get current Furby connection status."""
    if furby is None:
        return FurbyStatus(connected=False)

    status = FurbyStatus(
        connected=furby.connected,
        device_name=furby.device.name if furby.device else None,
        device_address=furby.device.address if furby.device else None,
    )

    if furby.connected:
        try:
            info = await furby.get_device_info()
            status.firmware_version = info.firmware_revision
        except Exception as e:
            logger.warning(f"Could not get device info: {e}")

    return status


@app.get("/known-furbies", response_model=dict)
async def get_known_furbies() -> dict:
    """Get list of all known Furby devices from cache."""
    if furby_cache is None:
        return {"furbies": [], "count": 0}

    furbies = furby_cache.get_all()
    return {"furbies": [f.model_dump() for f in furbies], "count": len(furbies)}


@app.delete("/known-furbies/{address}", response_model=CommandResponse)
async def remove_known_furby(address: str) -> CommandResponse:
    """Remove a Furby from the known devices cache."""
    if furby_cache is None:
        raise HTTPException(status_code=503, detail="Cache not initialized")

    if furby_cache.remove(address):
        return CommandResponse(success=True, message=f"Removed {address} from cache")
    else:
        raise HTTPException(status_code=404, detail="Furby not found in cache")


@app.delete("/known-furbies", response_model=CommandResponse)
async def clear_known_furbies() -> CommandResponse:
    """Clear all known Furby devices from cache."""
    if furby_cache is None:
        raise HTTPException(status_code=503, detail="Cache not initialized")

    furby_cache.clear()
    return CommandResponse(success=True, message="Cache cleared")


@app.post("/connect", response_model=CommandResponse)
async def connect(request: ConnectRequest | None = None) -> CommandResponse:
    """Connect to a Furby device. Optionally provide MAC address to connect directly."""
    global furby, furby_cache

    if furby and furby.connected:
        await broadcast_log("Already connected", "info")
        return CommandResponse(success=True, message="Already connected")

    try:
        # Extract connection parameters
        address = request.address if request else None
        timeout = request.timeout if request else 15.0
        retries = request.retries if request else 3

        # Send initial message
        if address:
            await broadcast_log(f"Connecting to Furby at {address}...", "info")
            if retries > 1:
                await broadcast_log(
                    f"Using {retries} connection attempts (F2F mode support)", "info"
                )
        else:
            await broadcast_log("Scanning for Furby devices...", "info")

        furby = FurbyConnect()

        # Create custom logging handler to broadcast to WebSocket
        class WebSocketHandler(logging.Handler):
            def emit(self, record):
                log_type = (
                    "error"
                    if record.levelno >= logging.ERROR
                    else "success" if "success" in record.getMessage().lower() else "info"
                )
                # Use asyncio to schedule the broadcast
                loop = asyncio.get_event_loop()
                loop.create_task(broadcast_log(record.getMessage(), log_type))

        # Add handler temporarily
        ws_handler = WebSocketHandler()
        ws_handler.setLevel(logging.INFO)
        furby_logger = logging.getLogger("pyfluff.furby")
        furby_logger.addHandler(ws_handler)

        try:
            await furby.connect(address=address, timeout=timeout, retries=retries)
            await broadcast_log("Connected to Furby", "success")

            # Update cache after successful connection
            if furby_cache and furby.device:
                try:
                    # Get device info for firmware version
                    info = await furby.get_device_info()
                    furby_cache.add_or_update(
                        address=furby.device.address,
                        device_name=furby.device.name,
                        firmware_revision=info.firmware_revision,
                    )
                    logger.info(f"Updated cache for {furby.device.address}")
                except Exception as e:
                    logger.warning(f"Could not update cache: {e}")

            # Short pause to let connection stabilize
            await asyncio.sleep(0.5)

            # Toggle debug menu
            try:
                await furby.cycle_debug_menu()
                await broadcast_log("Debug menu toggled", "success")
            except Exception as e:
                logger.warning(f"Could not toggle debug menu: {e}")

            # Flash antenna red twice
            try:
                for _i in range(2):
                    await furby.set_antenna_color(255, 0, 0)
                    await asyncio.sleep(0.3)
                    await furby.set_antenna_color(0, 0, 0)
                    await asyncio.sleep(0.3)
                await broadcast_log("Connection sequence complete", "success")
            except Exception as e:
                logger.warning(f"Could not flash antenna: {e}")

            return CommandResponse(success=True, message="Connected to Furby")
        finally:
            furby_logger.removeHandler(ws_handler)

    except Exception as e:
        logger.error(f"Connection failed: {e}")
        await broadcast_log(f"Connection failed: {e}", "error")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/disconnect", response_model=CommandResponse)
async def disconnect() -> CommandResponse:
    """Disconnect from Furby."""
    fb = get_furby()
    await fb.disconnect()
    return CommandResponse(success=True, message="Disconnected")


@app.post("/antenna", response_model=CommandResponse)
async def set_antenna(color: AntennaColor) -> CommandResponse:
    """Set antenna LED color."""
    logger.info(f"Setting antenna color: RGB({color.red}, {color.green}, {color.blue})")
    fb = get_furby()
    try:
        await fb.set_antenna_color(color.red, color.green, color.blue)
        logger.info("Antenna color set successfully")
        return CommandResponse(
            success=True,
            message=f"Antenna color set to RGB({color.red}, {color.green}, {color.blue})",
        )
    except Exception as e:
        logger.error(f"Failed to set antenna color: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/action", response_model=CommandResponse)
async def trigger_action(action: ActionSequence) -> CommandResponse:
    """Trigger a Furby action sequence."""
    logger.info(
        f"Triggering action: {action.input}/{action.index}/" f"{action.subindex}/{action.specific}"
    )
    fb = get_furby()
    try:
        await fb.trigger_action(action.input, action.index, action.subindex, action.specific)
        logger.info("Action triggered successfully")
        return CommandResponse(success=True, message="Action triggered")
    except Exception as e:
        logger.error(f"Failed to trigger action: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/actions/sequence", response_model=CommandResponse)
async def trigger_action_sequence(action_list: ActionList) -> CommandResponse:
    """
    Trigger a sequence of Furby actions with delays between them.

    This endpoint executes multiple actions one after another, waiting for the
    specified delay between each action to allow Furby to complete animations/sounds.
    """
    fb = get_furby()
    total_actions = len(action_list.actions)
    logger.info(
        f"Starting action sequence with {total_actions} actions " f"(delay: {action_list.delay}s)"
    )

    try:
        for i, action in enumerate(action_list.actions, 1):
            logger.info(
                f"Triggering action {i}/{total_actions}: "
                f"{action.input}/{action.index}/{action.subindex}/{action.specific}"
            )
            await fb.trigger_action(action.input, action.index, action.subindex, action.specific)

            # Wait before next action (except after the last one)
            if i < total_actions:
                logger.debug(f"Waiting {action_list.delay}s before next action")
                await asyncio.sleep(action_list.delay)

        logger.info(f"Action sequence completed successfully ({total_actions} actions)")
        return CommandResponse(
            success=True,
            message=f"Sequence completed: {total_actions} actions",
            data={"actions_executed": total_actions, "delay_used": action_list.delay},
        )
    except Exception as e:
        logger.error(f"Failed to execute action sequence: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/lcd/{state}", response_model=CommandResponse)
async def set_lcd(state: bool) -> CommandResponse:
    """Control LCD backlight."""
    logger.info(f"Setting LCD backlight: {'on' if state else 'off'}")
    fb = get_furby()
    try:
        await fb.set_lcd_backlight(state)
        logger.info("LCD state changed successfully")
        return CommandResponse(success=True, message=f"LCD backlight {'on' if state else 'off'}")
    except Exception as e:
        logger.error(f"Failed to set LCD: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/debug", response_model=CommandResponse)
async def cycle_debug_menu() -> CommandResponse:
    """Cycle through debug menus."""
    fb = get_furby()
    await fb.cycle_debug_menu()
    return CommandResponse(success=True, message="Debug menu cycled")


@app.post("/name/{name_id}", response_model=CommandResponse)
async def set_name(name_id: int) -> CommandResponse:
    """Set Furby name by ID (0-128)."""
    global furby_cache

    if not 0 <= name_id <= 128:
        raise HTTPException(status_code=400, detail="Name ID must be between 0 and 128")

    fb = get_furby()
    await fb.set_name(name_id)

    # Update cache with new name
    if furby_cache and fb.device:
        try:
            # Note: We store the name_id, but could also map to actual name string
            # from the names database if needed
            furby_cache.update_name(
                address=fb.device.address,
                name=f"Name ID {name_id}",  # Could be enhanced with actual name lookup
                name_id=name_id,
            )
            logger.info(f"Updated name in cache for {fb.device.address}")
        except Exception as e:
            logger.warning(f"Could not update name in cache: {e}")

    return CommandResponse(success=True, message=f"Name set to ID {name_id}")


@app.post("/mood", response_model=CommandResponse)
async def set_mood(mood: MoodUpdate) -> CommandResponse:
    """Update Furby mood meter."""
    fb = get_furby()

    # Map mood type string to enum
    mood_map = {
        "excitedness": MoodMeterType.EXCITEDNESS,
        "displeasedness": MoodMeterType.DISPLEASEDNESS,
        "tiredness": MoodMeterType.TIREDNESS,
        "fullness": MoodMeterType.FULLNESS,
        "wellness": MoodMeterType.WELLNESS,
    }

    mood_type = mood_map.get(mood.type.lower())
    if mood_type is None:
        raise HTTPException(status_code=400, detail=f"Invalid mood type: {mood.type}")

    set_absolute = mood.action.lower() == "set"
    await fb.set_mood(mood_type, mood.value, set_absolute)

    return CommandResponse(
        success=True,
        message=f"Mood {mood.type} {'set to' if set_absolute else 'increased by'} {mood.value}",
    )


@app.post("/dlc/upload", response_model=CommandResponse)
async def upload_dlc(
    file: UploadFile, slot: int = 2, chunk_delay: float = 0.020
) -> CommandResponse:
    """Upload a DLC file to Furby."""
    fb = get_furby()

    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dlc") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        dlc_manager = DLCManager(fb)
        await dlc_manager.upload_dlc(tmp_path, slot, chunk_delay=chunk_delay)
        return CommandResponse(
            success=True, message=f"DLC uploaded to slot {slot}"
        )
    except Exception as e:
        logger.error(f"DLC upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        tmp_path.unlink(missing_ok=True)


@app.post("/dlc/load/{slot}", response_model=CommandResponse)
async def load_dlc(slot: int) -> CommandResponse:
    """Load DLC from slot."""
    fb = get_furby()
    dlc_manager = DLCManager(fb)
    await dlc_manager.load_dlc(slot)
    return CommandResponse(success=True, message=f"DLC loaded from slot {slot}")


@app.post("/dlc/activate", response_model=CommandResponse)
async def activate_dlc() -> CommandResponse:
    """Activate loaded DLC."""
    fb = get_furby()
    dlc_manager = DLCManager(fb)
    await dlc_manager.activate_dlc()
    return CommandResponse(success=True, message="DLC activated")


@app.post("/dlc/deactivate/{slot}", response_model=CommandResponse)
async def deactivate_dlc(slot: int) -> CommandResponse:
    """Deactivate DLC slot."""
    fb = get_furby()
    dlc_manager = DLCManager(fb)
    await dlc_manager.deactivate_dlc(slot)
    return CommandResponse(success=True, message=f"DLC slot {slot} deactivated")


@app.post("/dlc/delete/{slot}", response_model=CommandResponse)
async def delete_dlc(slot: int) -> CommandResponse:
    """Delete DLC from slot."""
    fb = get_furby()
    dlc_manager = DLCManager(fb)
    await dlc_manager.delete_dlc(slot)
    return CommandResponse(success=True, message=f"DLC slot {slot} deleted")


@app.post("/dlc/flash-and-activate", response_model=CommandResponse)
async def flash_and_activate(
    file: UploadFile,
    slot: int = 2,
    delete_first: bool = True,
    chunk_delay: float = 0.020,
) -> CommandResponse:
    """
    Complete DLC workflow: Upload, load, and activate in one call.

    This endpoint performs all necessary steps to flash a DLC file:
    1. (Optional) Delete existing DLC in slot
    2. Upload the new DLC file
    3. Load the DLC from slot
    4. Activate the DLC

    Progress updates are sent via WebSocket to /ws/dlc endpoint.

    Args:
        file: UploadFile containing the DLC file to flash
        slot: DLC slot number (0-2, default: 2)
        delete_first: Whether to delete existing DLC in slot first (default: True)
        chunk_delay: Delay in seconds between chunks (default: 0.020 = 20ms).
                     Conservative default to prevent FILE_TRANSFER_TIMEOUT errors.
                     Can be decreased to 0.005-0.010 for faster uploads if reliable.

    Returns:
        CommandResponse with success status and message

    Raises:
        HTTPException: If not connected to Furby or upload fails
    """
    fb = get_furby()

    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dlc") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        dlc_manager = DLCManager(fb)

        # Create progress callback that broadcasts to WebSocket clients
        async def progress_callback(bytes_done: int, total_bytes: int, message: str):
            progress_data = {
                "bytes_done": bytes_done,
                "total_bytes": total_bytes,
                "message": message,
                "percentage": (bytes_done / total_bytes * 100) if total_bytes > 0 else 0,
            }
            # Broadcast to all connected DLC WebSocket clients
            await broadcast_dlc_progress(progress_data)

        await dlc_manager.flash_and_activate(
            tmp_path,
            slot=slot,
            delete_first=delete_first,
            progress_callback=progress_callback,
            chunk_delay=chunk_delay,
        )

        return CommandResponse(
            success=True, message=f"DLC successfully flashed and activated in slot {slot}"
        )
    except Exception as e:
        logger.error(f"DLC flash and activate failed: {e}")
        # Send error to WebSocket clients
        await broadcast_dlc_progress(
            {
                "bytes_done": 0,
                "total_bytes": 0,
                "message": f"Error: {str(e)}",
                "percentage": 0,
                "error": True,
            }
        )
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        tmp_path.unlink(missing_ok=True)


# Global list of DLC WebSocket connections
dlc_progress_clients: list[WebSocket] = []


async def broadcast_dlc_progress(progress_data: dict) -> None:
    """Broadcast DLC progress to all connected WebSocket clients."""
    if not dlc_progress_clients:
        return

    # Send to all connected clients
    disconnected = []
    for ws in dlc_progress_clients:
        try:
            await ws.send_json(progress_data)
        except Exception:
            disconnected.append(ws)

    # Remove disconnected clients
    for ws in disconnected:
        dlc_progress_clients.remove(ws)


@app.websocket("/ws/dlc")
async def websocket_dlc_progress(websocket: WebSocket) -> None:
    """WebSocket endpoint for DLC upload progress updates."""
    await websocket.accept()
    dlc_progress_clients.append(websocket)
    logger.info("DLC progress WebSocket client connected")

    try:
        # Keep connection alive by waiting for client messages or pings
        # This avoids unnecessary CPU wake-ups every second
        while True:
            try:
                # Wait for any message from client (including pings) with 60s timeout
                await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
            except TimeoutError:
                # Send a ping to check if connection is still alive
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        logger.info("DLC progress WebSocket client disconnected")
        if websocket in dlc_progress_clients:
            dlc_progress_clients.remove(websocket)
    except Exception as e:
        logger.error(f"DLC progress WebSocket error: {e}")
        if websocket in dlc_progress_clients:
            dlc_progress_clients.remove(websocket)
        await websocket.close()


@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket) -> None:
    """WebSocket endpoint for streaming connection logs."""
    await websocket.accept()
    connection_logs.append(websocket)
    logger.info("Log WebSocket client connected")

    try:
        # Keep connection alive
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        logger.info("Log WebSocket client disconnected")
        if websocket in connection_logs:
            connection_logs.remove(websocket)
    except Exception as e:
        logger.error(f"Log WebSocket error: {e}")
        if websocket in connection_logs:
            connection_logs.remove(websocket)
        await websocket.close()


@app.websocket("/ws/sensors")
async def websocket_sensors(websocket: WebSocket) -> None:
    """WebSocket endpoint for streaming sensor data."""
    await websocket.accept()
    logger.info("WebSocket client connected")

    try:
        fb = get_furby()

        async for sensor_data in fb.sensor_stream():
            await websocket.send_json(sensor_data.model_dump())

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "pyfluff.server:app",
        host="0.0.0.0",
        port=8080,
        log_level="info",
        reload=False,
    )
