"""
MCP Server for PyFluff - Control Furby Connect via VS Code Copilot.

This module provides an MCP (Model Context Protocol) server that exposes
Furby control functions as tools that can be used by VS Code Copilot and
other AI assistants supporting the MCP protocol.
"""

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from pyfluff.furby import FurbyConnect
from pyfluff.protocol import MoodMeterType

logger = logging.getLogger(__name__)

# Global Furby connection instance
_furby: FurbyConnect | None = None

# Create MCP server
mcp = FastMCP(
    name="PyFluff Furby Controller",
    instructions=(
        "Control Furby Connect toys via Bluetooth. "
        "First discover or connect to a Furby, then use the control tools. "
        "Available actions include changing antenna color, triggering actions, "
        "adjusting mood, and more."
    ),
)


def _get_furby() -> FurbyConnect:
    """Get the current Furby connection, creating one if needed."""
    global _furby
    if _furby is None:
        _furby = FurbyConnect()
    return _furby


@mcp.tool()
async def discover_furbies(timeout: float = 10.0) -> dict[str, Any]:
    """
    Discover nearby Furby Connect devices via Bluetooth.

    Args:
        timeout: Scan timeout in seconds (default: 10.0)

    Returns:
        Dictionary with list of discovered Furbies and their addresses
    """
    try:
        logger.info(f"Scanning for Furby devices (timeout: {timeout}s)...")
        devices = await FurbyConnect.discover(timeout=timeout, show_all=False)

        furbies = [
            {"address": d.address, "name": d.name or "Unknown", "rssi": d.rssi} for d in devices
        ]

        return {
            "success": True,
            "count": len(furbies),
            "devices": furbies,
            "message": f"Found {len(furbies)} Furby device(s)",
        }
    except Exception as e:
        logger.error(f"Discovery failed: {e}")
        return {
            "success": False,
            "count": 0,
            "devices": [],
            "error": str(e),
            "message": "Discovery failed. Ensure Bluetooth is enabled.",
        }


@mcp.tool()
async def connect_furby(address: str | None = None, timeout: float = 10.0) -> dict[str, Any]:
    """
    Connect to a Furby device.

    Args:
        address: MAC address of Furby (optional - will discover if not provided)
        timeout: Connection timeout in seconds (default: 10.0)

    Returns:
        Dictionary with connection status
    """
    global _furby
    furby = _get_furby()

    try:
        if furby.connected:
            return {
                "success": True,
                "message": "Already connected to Furby",
                "address": getattr(furby.device, "address", "unknown"),
            }

        logger.info(f"Connecting to Furby{' at ' + address if address else ''}...")
        await furby.connect(address=address, timeout=timeout)

        return {
            "success": True,
            "message": "Successfully connected to Furby",
            "address": getattr(furby.device, "address", "unknown"),
        }
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": (
                "Failed to connect to Furby. " "Try discovering devices first or check the address."
            ),
        }


@mcp.tool()
async def disconnect_furby() -> dict[str, Any]:
    """
    Disconnect from the current Furby.

    Returns:
        Dictionary with disconnection status
    """
    furby = _get_furby()

    try:
        if not furby.connected:
            return {"success": True, "message": "Not connected to any Furby"}

        await furby.disconnect()
        return {"success": True, "message": "Disconnected from Furby"}
    except Exception as e:
        logger.error(f"Disconnection failed: {e}")
        return {"success": False, "error": str(e), "message": "Failed to disconnect"}


@mcp.tool()
async def get_connection_status() -> dict[str, Any]:
    """
    Get current Furby connection status.

    Returns:
        Dictionary with connection status and device info
    """
    furby = _get_furby()

    return {
        "connected": furby.connected,
        "address": getattr(furby.device, "address", None) if furby.device else None,
        "name": getattr(furby.device, "name", None) if furby.device else None,
    }


@mcp.tool()
async def set_antenna_color(red: int, green: int, blue: int) -> dict[str, Any]:
    """
    Set the color of Furby's antenna LED.

    Args:
        red: Red channel value (0-255)
        green: Green channel value (0-255)
        blue: Blue channel value (0-255)

    Returns:
        Dictionary with operation status
    """
    furby = _get_furby()

    if not furby.connected:
        return {
            "success": False,
            "message": "Not connected to Furby. Use connect_furby first.",
        }

    # Validate RGB values
    if not all(0 <= v <= 255 for v in [red, green, blue]):
        return {
            "success": False,
            "message": "RGB values must be between 0 and 255",
        }

    try:
        await furby.set_antenna_color(red, green, blue)
        return {
            "success": True,
            "message": f"Antenna color set to RGB({red}, {green}, {blue})",
            "color": {"red": red, "green": green, "blue": blue},
        }
    except Exception as e:
        logger.error(f"Failed to set antenna color: {e}")
        return {"success": False, "error": str(e), "message": "Failed to set antenna color"}


@mcp.tool()
async def trigger_action(
    input_id: int, index: int = 0, subindex: int = 0, specific: int = 0
) -> dict[str, Any]:
    """
    Trigger a specific Furby action sequence.

    Furby actions are organized hierarchically:
    - input_id: Top-level action category (0-75)
    - index: Action index within input (default: 0)
    - subindex: Action subindex (default: 0)
    - specific: Specific variation (default: 0)

    Common examples:
    - Giggle: input=55, index=2, subindex=14, specific=0
    - Puke: input=55, index=3, subindex=10, specific=0

    Args:
        input_id: Top-level action category (0-75)
        index: Action index (default: 0)
        subindex: Action subindex (default: 0)
        specific: Specific variation (default: 0)

    Returns:
        Dictionary with operation status
    """
    furby = _get_furby()

    if not furby.connected:
        return {
            "success": False,
            "message": "Not connected to Furby. Use connect_furby first.",
        }

    try:
        await furby.trigger_action(input_id, index, subindex, specific)
        return {
            "success": True,
            "message": f"Triggered action [{input_id}, {index}, {subindex}, {specific}]",
            "action": {
                "input": input_id,
                "index": index,
                "subindex": subindex,
                "specific": specific,
            },
        }
    except Exception as e:
        logger.error(f"Failed to trigger action: {e}")
        return {"success": False, "error": str(e), "message": "Failed to trigger action"}


@mcp.tool()
async def set_mood(mood_type: str, value: int) -> dict[str, Any]:
    """
    Set a specific mood meter value for Furby.

    Available mood types:
    - "excitedness": How excited Furby is (0-100)
    - "displeasedness": How displeased Furby is (0-100)
    - "tiredness": How tired Furby is (0-100)
    - "fullness": How full/hungry Furby is (0-100)
    - "wellness": How well Furby feels (0-100)

    Args:
        mood_type: Type of mood meter to adjust
        value: New value for the mood meter (0-100)

    Returns:
        Dictionary with operation status
    """
    furby = _get_furby()

    if not furby.connected:
        return {
            "success": False,
            "message": "Not connected to Furby. Use connect_furby first.",
        }

    # Validate value
    if not 0 <= value <= 100:
        return {
            "success": False,
            "message": "Mood value must be between 0 and 100",
        }

    # Map mood type string to enum
    mood_map = {
        "excitedness": MoodMeterType.EXCITEDNESS,
        "displeasedness": MoodMeterType.DISPLEASEDNESS,
        "tiredness": MoodMeterType.TIREDNESS,
        "fullness": MoodMeterType.FULLNESS,
        "wellness": MoodMeterType.WELLNESS,
    }

    mood_enum = mood_map.get(mood_type.lower())
    if mood_enum is None:
        return {
            "success": False,
            "message": f"Invalid mood type. Must be one of: {', '.join(mood_map.keys())}",
        }

    try:
        await furby.set_moodmeter(mood_enum, value)
        return {
            "success": True,
            "message": f"Set {mood_type} to {value}",
            "mood": {"type": mood_type, "value": value},
        }
    except Exception as e:
        logger.error(f"Failed to set mood: {e}")
        return {"success": False, "error": str(e), "message": "Failed to set mood"}


@mcp.tool()
async def set_lcd_backlight(enabled: bool) -> dict[str, Any]:
    """
    Control Furby's LCD eye backlight.

    Args:
        enabled: True to turn on backlight, False to turn off

    Returns:
        Dictionary with operation status
    """
    furby = _get_furby()

    if not furby.connected:
        return {
            "success": False,
            "message": "Not connected to Furby. Use connect_furby first.",
        }

    try:
        await furby.set_lcd(enabled)
        return {
            "success": True,
            "message": f"LCD backlight {'enabled' if enabled else 'disabled'}",
            "enabled": enabled,
        }
    except Exception as e:
        logger.error(f"Failed to set LCD backlight: {e}")
        return {"success": False, "error": str(e), "message": "Failed to set LCD backlight"}


@mcp.tool()
async def cycle_debug_menu() -> dict[str, Any]:
    """
    Cycle through Furby's debug menu screens.

    This displays diagnostic information on Furby's LCD eyes.

    Returns:
        Dictionary with operation status
    """
    furby = _get_furby()

    if not furby.connected:
        return {
            "success": False,
            "message": "Not connected to Furby. Use connect_furby first.",
        }

    try:
        await furby.cycle_debug_menu()
        return {
            "success": True,
            "message": "Cycled debug menu",
        }
    except Exception as e:
        logger.error(f"Failed to cycle debug menu: {e}")
        return {"success": False, "error": str(e), "message": "Failed to cycle debug menu"}


@mcp.tool()
def list_common_actions() -> dict[str, Any]:
    """
    List common Furby actions with their coordinates.

    Returns a dictionary of common actions that can be triggered.

    Returns:
        Dictionary with common action definitions
    """
    actions = {
        "giggle": {
            "input": 55,
            "index": 2,
            "subindex": 14,
            "specific": 0,
            "description": "Make Furby giggle",
        },
        "puke": {
            "input": 55,
            "index": 3,
            "subindex": 10,
            "specific": 0,
            "description": "Make Furby puke (burp)",
        },
        "sneeze": {
            "input": 55,
            "index": 3,
            "subindex": 1,
            "specific": 0,
            "description": "Make Furby sneeze",
        },
        "yawn": {
            "input": 55,
            "index": 3,
            "subindex": 3,
            "specific": 0,
            "description": "Make Furby yawn",
        },
        "sing_note_c": {
            "input": 71,
            "index": 0,
            "subindex": 0,
            "specific": 0,
            "description": "Sing musical note C",
        },
        "dance": {
            "input": 30,
            "index": 0,
            "subindex": 0,
            "specific": 0,
            "description": "Make Furby dance",
        },
    }

    return {
        "success": True,
        "actions": actions,
        "message": (
            f"Found {len(actions)} common actions. " "Use trigger_action with these coordinates."
        ),
    }


def run_server(transport: str = "stdio") -> None:
    """
    Run the MCP server with the specified transport.

    Args:
        transport: Transport type - "stdio", "sse", or "streamable-http"
    """
    logger.info(f"Starting PyFluff MCP server with {transport} transport...")
    mcp.run(transport=transport)


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run with stdio transport (default for VS Code)
    run_server(transport="stdio")
