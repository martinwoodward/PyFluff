# PyFluff Testing Guide

This document provides information about the PyFluff test suite.

## Test Coverage

### Overall Statistics
- **Total Tests**: 114 passing
- **Overall Coverage**: 37%
- **Test Files**: 4 files

### Coverage by Module

| Module | Coverage | Tests | Status |
|--------|----------|-------|--------|
| protocol.py | 100% | 30 | ✅ Complete |
| models.py | 100% | 44 | ✅ Complete |
| furby_cache.py | 98% | 20 | ✅ Complete |
| dlc.py | 95% | 20 | ✅ Complete |
| furby.py | 16% | - | ⚠️ Requires hardware |
| server.py | 0% | - | ⚠️ Integration testing |
| cli.py | 0% | - | ⚠️ CLI interface |

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run specific test file
pytest tests/test_protocol.py

# Run specific test
pytest tests/test_protocol.py::test_build_antenna_command
```

### Coverage Reports

```bash
# Terminal coverage report
pytest tests/ --cov=pyfluff --cov-report=term-missing

# HTML coverage report (detailed)
pytest tests/ --cov=pyfluff --cov-report=html
# Open htmlcov/index.html in your browser

# XML coverage report (for CI/CD)
pytest tests/ --cov=pyfluff --cov-report=xml
```

### Test Options

```bash
# Stop on first failure
pytest tests/ -x

# Show local variables on failure
pytest tests/ -l

# Disable output capture (see print statements)
pytest tests/ -s

# Run only failed tests from last run
pytest tests/ --lf

# Run tests in parallel (requires pytest-xdist)
pytest tests/ -n auto
```

## Test Files

### test_protocol.py (30 tests)
Tests for BLE protocol command generation and parsing.

**Coverage:**
- Command builders (antenna, action, mood, LCD, name, DLC)
- Response parsing and validation
- FurbyMessage type detection
- Edge cases and boundary conditions
- Furby name database

**Example:**
```python
def test_build_antenna_command() -> None:
    """Test antenna color command generation."""
    cmd = FurbyProtocol.build_antenna_command(255, 128, 0)
    assert cmd == bytes([0x14, 255, 128, 0])
```

### test_models.py (44 tests)
Tests for Pydantic data models and validation.

**Coverage:**
- All model classes (AntennaColor, ActionSequence, etc.)
- Field constraint validation
- Required vs optional fields
- Extra field handling
- Error cases (invalid inputs)

**Example:**
```python
def test_antenna_color_validation() -> None:
    """Test RGB color validation."""
    color = AntennaColor(red=255, green=128, blue=0)
    assert color.red == 255
    
    with pytest.raises(ValidationError):
        AntennaColor(red=-1, green=0, blue=0)  # Invalid
```

### test_furby_cache.py (20 tests)
Tests for Furby device cache management.

**Coverage:**
- Cache persistence (save/load)
- CRUD operations (add, update, remove, clear)
- Sorting by last seen timestamp
- Error handling (corrupted files)
- Directory creation

**Example:**
```python
def test_cache_persistence() -> None:
    """Test saving and loading cache."""
    cache = FurbyCache("test.json")
    cache.add_or_update(address="AA:BB:CC:DD:EE:FF")
    
    cache2 = FurbyCache("test.json")
    assert "AA:BB:CC:DD:EE:FF" in cache2.get_addresses()
```

### test_dlc.py (20 tests)
Tests for DLC (DownLoadable Content) file management.

**Coverage:**
- Upload workflow with async operations
- File transfer state machine
- Callback handling
- Nordic ACK enable/disable
- Chunking (20-byte packets)
- Error handling and timeouts

**Example:**
```python
@pytest.mark.asyncio
async def test_dlc_upload() -> None:
    """Test DLC file upload."""
    furby = MagicMock(spec=FurbyConnect)
    manager = DLCManager(furby)
    
    # Simulate successful upload
    manager._transfer_ready.set()
    manager._transfer_complete.set()
    
    await manager.upload_dlc("test.dlc", slot=2)
    assert furby.enable_nordic_packet_ack.called
```

## Testing Approach

### Unit Testing
- Pure unit tests for all testable modules
- No hardware dependencies
- Comprehensive edge case coverage

### Mocking Strategy
- `AsyncMock` for BLE operations
- Proper callback simulation
- State management for workflows
- Timeout simulation for errors

### Test Organization
- Test classes group related functionality
- Descriptive test names
- Fixtures for reusable setup
- Parametrized tests where appropriate

## Modules Not Tested

### Furby (16% coverage)
**Reason:** Requires actual BLE hardware
- Most code involves real BLE communication
- Protocol building tested via protocol module
- Connection logic difficult to mock accurately

### Server (0% coverage)
**Reason:** Requires running server
- Would need integration tests with TestClient
- WebSocket connections complex to test
- Core business logic covered by other tests

### CLI (0% coverage)
**Reason:** Command-line interface
- Would require subprocess testing
- Less critical than library API
- Manual testing during development

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
      
      - name: Run tests with coverage
        run: |
          pytest tests/ --cov=pyfluff --cov-report=xml --cov-report=term-missing
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

## Writing New Tests

### Test Naming Convention
```python
# Good test names are descriptive
def test_antenna_command_with_max_values() -> None:
    """Test antenna command with RGB values at maximum (255)."""
    pass

def test_cache_handles_corrupted_file() -> None:
    """Test that cache gracefully handles corrupted JSON files."""
    pass
```

### Using Fixtures
```python
import pytest
from pyfluff.furby_cache import FurbyCache

@pytest.fixture
def temp_cache(tmp_path):
    """Create a temporary cache for testing."""
    cache_file = tmp_path / "test_cache.json"
    return FurbyCache(cache_file)

def test_with_fixture(temp_cache):
    """Test using the fixture."""
    temp_cache.add_or_update(address="AA:BB:CC:DD:EE:FF")
    assert len(temp_cache.get_all()) == 1
```

### Async Testing
```python
import pytest

@pytest.mark.asyncio
async def test_async_operation() -> None:
    """Test an async operation."""
    result = await some_async_function()
    assert result == expected_value
```

### Mocking BLE Operations
```python
from unittest.mock import AsyncMock, MagicMock

def test_with_mocked_furby():
    """Test with mocked Furby connection."""
    furby = MagicMock(spec=FurbyConnect)
    furby._write_gp = AsyncMock()
    furby._gp_callbacks = []
    
    # Your test code here
    await furby._write_gp(command)
    furby._write_gp.assert_called_once()
```

## Troubleshooting

### Tests Hang
- Check for missing `@pytest.mark.asyncio` decorator
- Ensure all async operations use `await`
- Set shorter timeouts for timeout tests

### Import Errors
```bash
# Install package in development mode
pip install -e ".[dev]"
```

### Coverage Not Updated
```bash
# Clear pytest cache
rm -rf .pytest_cache
rm -rf htmlcov
pytest tests/ --cov=pyfluff --cov-report=html
```

### Async Warnings
```bash
# Ensure pytest-asyncio is installed
pip install pytest-asyncio>=0.21.0
```

## Code Quality Tools

### Linting
```bash
# Run ruff linter
ruff check pyfluff/ tests/

# Auto-fix issues
ruff check --fix pyfluff/ tests/
```

### Formatting
```bash
# Format with black
black pyfluff/ tests/

# Check formatting without changes
black --check pyfluff/ tests/
```

### Type Checking
```bash
# Run mypy type checker
mypy pyfluff/
```

## Best Practices

1. **Write tests first** (TDD approach when possible)
2. **Keep tests simple** - one assertion per test ideally
3. **Use descriptive names** - explain what and why
4. **Test edge cases** - not just happy paths
5. **Mock external dependencies** - BLE, file I/O, network
6. **Use fixtures** - for common setup
7. **Document complex tests** - add docstrings
8. **Run tests frequently** - before committing

## Contributing Tests

When adding new features:

1. Add tests for new functionality
2. Ensure existing tests pass
3. Maintain or improve coverage
4. Follow existing patterns
5. Document complex test scenarios

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [Pydantic testing](https://docs.pydantic.dev/latest/concepts/testing/)
