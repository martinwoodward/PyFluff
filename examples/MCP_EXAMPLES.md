# PyFluff MCP Server Examples

This directory contains examples of using the PyFluff MCP server with VS Code Copilot.

## Configuration Example

Copy `vscode-mcp-config.json` to your VS Code MCP configuration:

**macOS/Linux:**
```bash
mkdir -p ~/.vscode
cp vscode-mcp-config.json ~/.vscode/mcp-servers.json
```

**Windows:**
```powershell
$vscodePath = "$env:APPDATA\Code\User"
New-Item -ItemType Directory -Force -Path $vscodePath
Copy-Item vscode-mcp-config.json "$vscodePath\mcp-servers.json"
```

## Example Copilot Prompts

Once configured, you can use these prompts with GitHub Copilot in VS Code:

### Discovery and Connection

```
@workspace Discover nearby Furbies
```

```
@workspace Connect to my Furby at AA:BB:CC:DD:EE:FF
```

```
@workspace What's the connection status?
```

### Antenna Color Control

```
@workspace Set the antenna to red
```

```
@workspace Make the antenna purple (RGB 128, 0, 255)
```

```
@workspace Turn off the antenna light
```

```
@workspace Cycle through rainbow colors on the antenna
```

### Actions

```
@workspace Make my Furby giggle
```

```
@workspace List all common Furby actions
```

```
@workspace Make my Furby sneeze, then yawn
```

```
@workspace Trigger action input=55, index=2, subindex=14, specific=0
```

### Mood Control

```
@workspace Set my Furby's excitedness to 80
```

```
@workspace Make my Furby very happy and energetic
```

```
@workspace Set mood: excitedness=90, tiredness=10, fullness=50
```

### LCD and Debug

```
@workspace Turn on the LCD backlight
```

```
@workspace Cycle through the debug menu
```

### Complex Sequences

```
@workspace Discover my Furby, connect to it, set the antenna to blue, and make it giggle
```

```
@workspace Connect to my Furby and perform a light show with the antenna cycling through different colors
```

```
@workspace Make my Furby excited (excitedness=90), then make it laugh, then turn the antenna green
```

## Testing the MCP Server

You can test the MCP server directly from the command line:

```bash
# Start the server in stdio mode (for VS Code)
pyfluff mcp-server

# Start with HTTP SSE transport (for testing)
pyfluff mcp-server --transport sse

# Start with streamable HTTP transport
pyfluff mcp-server --transport streamable-http
```

## Troubleshooting

### Server Not Loading

1. Check that Python is in your PATH
2. Verify PyFluff is installed: `pip show pyfluff`
3. Test the server manually: `python -m pyfluff.cli mcp-server --help`
4. Check VS Code Output panel for MCP errors

### Connection Issues

1. Ensure Bluetooth is enabled
2. Make sure Furby is powered on and in range
3. Try discovering Furbies first before connecting
4. For Furbies in F2F mode, connect directly by MAC address

### Copilot Not Seeing Tools

1. Restart VS Code after changing MCP configuration
2. Check that the MCP server is listed in VS Code settings
3. Try disconnecting and reconnecting to reload the tools
4. Check the VS Code Output panel for MCP-related messages

## Advanced Usage

### Custom Python Environment

If you're using a virtual environment, specify the full path:

```json
{
  "mcpServers": {
    "pyfluff": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "pyfluff.cli", "mcp-server"],
      "env": {}
    }
  }
}
```

### Debug Logging

Enable debug logging by setting environment variables:

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

### Multiple Furbies

To control multiple Furbies, you can:

1. Connect to one, control it, then disconnect
2. Connect to another Furby
3. Repeat as needed

The MCP server maintains a single active connection at a time.

## See Also

- [MCP Documentation](../docs/MCP.md)
- [PyFluff README](../README.md)
- [Action List](../docs/actionlist.md)
- [Model Context Protocol](https://modelcontextprotocol.io/)
