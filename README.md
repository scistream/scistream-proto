# Scistream 

Please refer to our Full User documentation at [Read the Docs](https://scistream.readthedocs.io)

## Build & Run Commands

```bash
poetry install  # Install dependencies
poetry shell    # Activate virtual environment
poetry build    # Build package
```

## Development

### Test Commands
```bash
pytest                           # Run all tests
pytest tests/test_s2cs.py        # Run specific test file
pytest tests/test_s2cs.py::test_update_success  # Run specific test
pytest -xvs                      # Verbose mode
pytest --cov=src                 # Test with coverage
```

### Common CLI Commands
```bash
s2uc --help      # SciStream User Client CLI
s2cs --help      # SciStream Control Server CLI
appctrl --help   # Application Controller CLI
```

For more detailed development guidelines, see [CLAUDE.md](CLAUDE.md).
