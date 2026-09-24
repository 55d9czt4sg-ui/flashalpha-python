# FlashAlpha Python SDK — Development Guide

## Quick Start

### 1. Activate the Virtual Environment
```bash
cd <your-local-checkout>
source venv/bin/activate
```

### 2. Verify Setup
```bash
pytest tests/ -q                    # Run all tests
pytest tests/ -m "not integration"  # Skip API-dependent tests
```

## Development Tools

All commands available via Makefile:

```bash
make help              # Show all available commands
make test              # Run full test suite
make test-unit         # Run unit tests only
make coverage          # Generate coverage report
make clean             # Clean build artifacts
```

## Environment Details

- **Python Version:** 3.14.5
- **Virtual Environment:** `./venv`
- **Package:** flashalpha 1.3.0 (editable mode)
- **Test Framework:** pytest 9.1.1
- **Coverage Tool:** pytest-cov 7.1.0
- **Mock HTTP:** responses 0.26.3

## Project Structure

```
src/flashalpha/          # Main SDK code
├── client.py            # FlashAlpha client
├── types.py             # TypedDict response models
└── ...                  # API endpoints and utilities

tests/                   # Test suite
├── test_client.py       # Client tests
├── test_integration.py  # Live API tests (requires API key)
├── test_response_envelope.py
└── ...

examples/                # Usage examples
docs/                    # Documentation
```

## Running Tests

### All Tests (Unit + Integration)
```bash
pytest tests/ -v
```

### Unit Tests Only (recommended for development)
```bash
pytest tests/ -m "not integration"
```

### With Coverage Report
```bash
make coverage
# Report saved to htmlcov/index.html
```

### Specific Test File
```bash
pytest tests/test_client.py -v
```

### Single Test
```bash
pytest tests/test_client.py::test_401_raises_authentication_error -v
```

## Integration Tests

Integration tests require `FLASHALPHA_API_KEY` environment variable:

```bash
export FLASHALPHA_API_KEY="your-api-key-here"
pytest tests/ -m "integration"
```

## Common Workflows

### Testing a Code Change
```bash
source venv/bin/activate
pytest tests/ -m "not integration" -v
```

### Checking Coverage
```bash
source venv/bin/activate
make coverage
open htmlcov/index.html
```

### Cleaning Up
```bash
source venv/bin/activate
make clean
```

## SDK Usage

### Quick Test
```python
from flashalpha import FlashAlpha

client = FlashAlpha('your-api-key')

# Get stock summary
summary = client.stock_summary('SPY')
print(summary)
```

### Available Endpoints

All endpoints and types are documented in:
- `src/flashalpha/client.py` — Client methods
- `src/flashalpha/types.py` — Response type definitions
- `README.md` — Full API reference
- `examples/` — Example scripts

## Troubleshooting

### Import Errors
```bash
# Reinstall in editable mode
pip install -e ".[dev]"
```

### Tests Not Running
```bash
# Verify pytest is installed
pip list | grep pytest

# Reinstall dev dependencies
pip install -e ".[dev]"
```

### Cache Issues
```bash
# Clean pytest cache
make clean
pytest tests/
```

## Next Steps

- Review `README.md` for full API documentation
- Check `examples/` for usage patterns
- Explore `AGENTS.md` for recommended use cases
- Read through `src/flashalpha/` to understand the SDK structure
