# MCP Server for PyFluff

PyFluff includes an MCP (Model Context Protocol) server that allows you to control your Furby Connect toy directly from VS Code using GitHub Copilot or other AI assistants that support the MCP protocol.

## What is MCP?

The [Model Context Protocol](https://modelcontextprotocol.io/) is an open standard that allows AI assistants to interact with external tools and services. Think of it like a USB-C port for AI - it provides a standardized way for AI models to access capabilities beyond their training data.

## Features

The PyFluff MCP server exposes the following tools:

- **discover_furbies** - Scan for nearby Furby Connect devices
- **connect_furby** - Connect to a specific Furby by MAC address
- **disconnect_furby** - Disconnect from current Furby
- **get_connection_status** - Check connection status
- **set_antenna_color** - Change the antenna LED color (RGB)
- **trigger_action** - Trigger specific Furby actions (giggle, puke, etc.)
- **set_mood** - Adjust Furby's mood meters (excitedness, tiredness, etc.)
- **set_lcd_backlight** - Control LCD eye backlight
- **cycle_debug_menu** - Cycle through debug menu screens
- **list_common_actions** - Get a list of common Furby actions

## Quick Start

### 1. Install PyFluff

```bash
pip install -e .
```

### 2. Configure VS Code

Create or edit your VS Code MCP settings file:

**macOS/Linux**: `~/.vscode/mcp-servers.json`
**Windows**: `%APPDATA%\Code\User\mcp-servers.json`

Add the following configuration:

```json
{
  "mcpServers": {
    "pyfluff": {
      "command": "python",
      "args": ["-m", "pyfluff.cli", "mcp-server"],
      "env": {}
    }
  }
}
```

Or use the CLI to start it directly:

```bash
pyfluff mcp-server
```

### 3. Restart VS Code

After adding the configuration, restart VS Code to load the MCP server.

### 4. Use Copilot to Control Your Furby

Open a file in VS Code and ask Copilot to control your Furby:

```
@workspace Discover nearby Furbies
@workspace Connect to my Furby
@workspace Change the antenna color to purple
@workspace Make my Furby giggle
@workspace Set my Furby's mood to excited
```

## Usage Examples

### Discovering and Connecting

```
Hey Copilot, can you discover my Furby and connect to it?
```

Copilot will:
1. Call `discover_furbies()` to scan for devices
2. Call `connect_furby()` with the discovered MAC address

### Changing Antenna Color

```
Make the antenna rainbow colors
```

Copilot will call `set_antenna_color()` multiple times with different RGB values.

### Triggering Actions

```
Make my Furby laugh
```

Copilot will use `list_common_actions()` to find the giggle action, then call `trigger_action()`.

### Adjusting Mood

```
Make my Furby very excited but also a bit tired
```

Copilot will call `set_mood()` multiple times:
- `set_mood("excitedness", 90)`
- `set_mood("tiredness", 30)`

## Advanced Configuration

### Custom Transport

By default, the MCP server uses `stdio` transport which works with VS Code. You can also use other transports:

```bash
# HTTP with Server-Sent Events
pyfluff mcp-server --transport sse

# Streamable HTTP
pyfluff mcp-server --transport streamable-http
```

### Environment Variables

You can set environment variables in the VS Code configuration:

```json
{
  "mcpServers": {
    "pyfluff": {
      "command": "python",
      "args": ["-m", "pyfluff.cli", "mcp-server"],
      "env": {
        "PYTHONPATH": "/path/to/PyFluff",
        "LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

### Using with Known MAC Address

If you know your Furby's MAC address, you can connect directly:

```
Connect to my Furby at AA:BB:CC:DD:EE:FF
```

This is useful when your Furby is in F2F (Furby-to-Furby) mode and not advertising.

## Troubleshooting

### Furby Not Found

If Copilot can't find your Furby:

1. Ensure Bluetooth is enabled on your computer
2. Make sure your Furby is powered on and in range
3. Try waking your Furby by touching its sensors
4. Your Furby might be in F2F mode - try connecting by MAC address

### Connection Fails

If connection fails:

1. Check that your Furby is not connected to another device
2. Try restarting your Furby (remove batteries for 10 seconds)
3. Ensure you have proper Bluetooth permissions
4. On Linux, you may need to run with appropriate permissions

### MCP Server Not Loading

If VS Code doesn't recognize the MCP server:

1. Check that the `mcp-servers.json` file is in the correct location
2. Verify the Python path is correct
3. Restart VS Code after making configuration changes
4. Check VS Code's Output panel for MCP-related errors

## Tool Reference

### discover_furbies

Scan for nearby Furby Connect devices.

**Parameters:**
- `timeout` (float, optional): Scan timeout in seconds (default: 10.0)

**Returns:**
- `success` (bool): Whether the scan was successful
- `count` (int): Number of Furbies found
- `devices` (list): List of discovered devices with address, name, and RSSI

### connect_furby

Connect to a Furby device.

**Parameters:**
- `address` (str, optional): MAC address of Furby to connect to
- `timeout` (float, optional): Connection timeout in seconds (default: 10.0)

**Returns:**
- `success` (bool): Whether connection was successful
- `message` (str): Status message
- `address` (str): MAC address of connected Furby

### set_antenna_color

Set the color of Furby's antenna LED.

**Parameters:**
- `red` (int): Red channel value (0-255)
- `green` (int): Green channel value (0-255)
- `blue` (int): Blue channel value (0-255)

**Returns:**
- `success` (bool): Whether the operation was successful
- `color` (dict): Applied color values

### trigger_action

Trigger a specific Furby action sequence.

**Parameters:**
- `input_id` (int): Top-level action category (0-75)
- `index` (int, optional): Action index (default: 0)
- `subindex` (int, optional): Action subindex (default: 0)
- `specific` (int, optional): Specific variation (default: 0)

**Returns:**
- `success` (bool): Whether the action was triggered
- `action` (dict): Action coordinates used

### set_mood

Set a specific mood meter value.

**Parameters:**
- `mood_type` (str): One of "excitedness", "displeasedness", "tiredness", "fullness", "wellness"
- `value` (int): New value (0-100)

**Returns:**
- `success` (bool): Whether the mood was set
- `mood` (dict): Applied mood type and value

### list_common_actions

Get a list of common Furby actions.

**Returns:**
- `success` (bool): Always true
- `actions` (dict): Dictionary of action names to coordinates
- `message` (str): Summary message

## Security Note

The MCP server runs with the same permissions as your VS Code instance. It can control any Furby that your computer can connect to via Bluetooth. Be cautious when using this in public spaces or with shared Bluetooth access.

## Further Reading

- [Model Context Protocol Documentation](https://modelcontextprotocol.io/)
- [PyFluff Documentation](../README.md)
- [Furby Connect Protocol](../docs/bluetooth.md)
- [Action List](../docs/actionlist.md)

## License

The MCP server is part of PyFluff and is licensed under the MIT License. See [LICENSE](../LICENSE) for details.
