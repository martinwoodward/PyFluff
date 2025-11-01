"""
Tests for MCP server functionality.

These tests verify that the MCP server tools are properly defined
and can be imported without errors.
"""

import pytest


def test_mcp_server_import():
    """Test that MCP server can be imported."""
    from pyfluff.mcp_server import mcp

    assert mcp is not None
    assert mcp.name == "PyFluff Furby Controller"


def test_mcp_server_has_tools():
    """Test that all expected tools are registered."""
    from pyfluff.mcp_server import mcp

    # Get the list of registered tools
    tool_names = [tool.name for tool in mcp._tool_manager._tools.values()]

    expected_tools = [
        "discover_furbies",
        "connect_furby",
        "disconnect_furby",
        "get_connection_status",
        "set_antenna_color",
        "trigger_action",
        "set_mood",
        "set_lcd_backlight",
        "cycle_debug_menu",
        "list_common_actions",
    ]

    for tool in expected_tools:
        assert tool in tool_names, f"Tool '{tool}' not found in registered tools"


def test_list_common_actions():
    """Test that list_common_actions returns expected data."""
    from pyfluff.mcp_server import list_common_actions

    result = list_common_actions()

    assert result["success"] is True
    assert "actions" in result
    assert isinstance(result["actions"], dict)

    # Check that expected actions are present
    expected_actions = ["giggle", "puke", "sneeze", "yawn", "sing_note_c", "dance"]
    for action in expected_actions:
        assert action in result["actions"]
        assert "input" in result["actions"][action]
        assert "index" in result["actions"][action]
        assert "description" in result["actions"][action]


@pytest.mark.asyncio
async def test_get_connection_status():
    """Test get_connection_status returns proper structure."""
    from pyfluff.mcp_server import get_connection_status

    result = await get_connection_status()

    assert "connected" in result
    assert isinstance(result["connected"], bool)
    assert "address" in result
    assert "name" in result


def test_mcp_server_instructions():
    """Test that MCP server has proper instructions."""
    from pyfluff.mcp_server import mcp

    assert mcp.instructions is not None
    assert "Furby Connect" in mcp.instructions
    assert "Bluetooth" in mcp.instructions
