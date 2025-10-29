# PyFluff MCP Server Quick Reference

Quick reference for using the PyFluff MCP server with VS Code Copilot.

## Setup (One-time)

1. **Install PyFluff**
   ```bash
   pip install -e .
   ```

2. **Configure VS Code**
   
   Copy configuration to your VS Code settings:
   ```bash
   # macOS/Linux
   mkdir -p ~/.vscode
   cp examples/vscode-mcp-config.json ~/.vscode/mcp-servers.json
   
   # Windows PowerShell
   New-Item -ItemType Directory -Force -Path "$env:APPDATA\Code\User"
   Copy-Item examples/vscode-mcp-config.json "$env:APPDATA\Code\User\mcp-servers.json"
   ```

3. **Restart VS Code**

## Quick Commands

### Discovery & Connection
```
@workspace Discover Furbies
@workspace Connect to Furby at AA:BB:CC:DD:EE:FF
@workspace Connection status?
```

### Colors (RGB 0-255)
```
@workspace Set antenna to red (255,0,0)
@workspace Set antenna to purple (128,0,255)
@workspace Turn off antenna
```

### Common Actions
```
@workspace List common actions
@workspace Make Furby giggle
@workspace Make Furby sneeze
@workspace Make Furby yawn
```

### Mood Control (0-100)
```
@workspace Set excitedness to 80
@workspace Set tiredness to 20
@workspace Make Furby very happy
```

### Advanced
```
@workspace Turn on LCD backlight
@workspace Cycle debug menu
```

## Tool Reference

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `discover_furbies` | Scan for Furbies | timeout (default: 10.0s) |
| `connect_furby` | Connect to Furby | address (MAC), timeout |
| `disconnect_furby` | Disconnect | none |
| `get_connection_status` | Check status | none |
| `set_antenna_color` | Change LED | red, green, blue (0-255) |
| `trigger_action` | Perform action | input, index, subindex, specific |
| `set_mood` | Adjust mood | mood_type, value (0-100) |
| `set_lcd_backlight` | Control LCD | enabled (true/false) |
| `cycle_debug_menu` | Show debug | none |
| `list_common_actions` | Get actions | none |

## Common Actions Reference

| Action | Coordinates | Description |
|--------|-------------|-------------|
| Giggle | [55, 2, 14, 0] | Make Furby laugh |
| Puke | [55, 3, 10, 0] | Burp/puke sound |
| Sneeze | [55, 3, 1, 0] | Achoo! |
| Yawn | [55, 3, 3, 0] | Sleepy yawn |
| Sing C | [71, 0, 0, 0] | Musical note C |
| Dance | [30, 0, 0, 0] | Dance move |

## Mood Types

- `excitedness` - Energy level (0=calm, 100=hyper)
- `displeasedness` - Unhappiness (0=happy, 100=upset)
- `tiredness` - Fatigue (0=awake, 100=sleepy)
- `fullness` - Hunger (0=hungry, 100=full)
- `wellness` - Health (0=sick, 100=healthy)

## Troubleshooting

### "Not connected to Furby"
Run: `@workspace Connect to my Furby`

### "No Furbies found"
1. Ensure Bluetooth is on
2. Furby is powered on
3. Try: `@workspace Discover Furbies`
4. If in F2F mode, connect by MAC address

### "Connection failed"
1. Restart Furby (remove batteries 10s)
2. Move closer to computer
3. Check Bluetooth permissions
4. Try connecting by specific MAC address

### Server not loading
1. Check `~/.vscode/mcp-servers.json` exists
2. Verify Python path in config
3. Restart VS Code
4. Check Output panel for errors

## See Also

- [Full Documentation](../docs/MCP.md)
- [Usage Examples](MCP_EXAMPLES.md)
- [Action List](../docs/actionlist.md)
- [PyFluff README](../README.md)
