# Development Scripts

This directory contains scripts for maintaining code quality in the project.

## Available Scripts

### Format Code

Automatically format code using black and organize imports with isort:

**Windows:**
```bash
scripts\format.bat
```

**Linux/Mac:**
```bash
chmod +x scripts/format.sh
./scripts/format.sh
```

### Lint Code

Run flake8 to check for code style issues:

**Windows:**
```bash
scripts\lint.bat
```

**Linux/Mac:**
```bash
chmod +x scripts/lint.sh
./scripts/lint.sh
```

### Type Check

Run mypy to perform static type checking:

**Windows:**
```bash
scripts\typecheck.bat
```

**Linux/Mac:**
```bash
chmod +x scripts/typecheck.sh
./scripts/typecheck.sh
```

### Run All Checks

Run all quality checks (formatting, import sorting, linting, and type checking):

**Windows:**
```bash
scripts\check-all.bat
```

**Linux/Mac:**
```bash
chmod +x scripts/check-all.sh
./scripts/check-all.sh
```

## Quick Reference

| Tool | Purpose | Config File |
|------|---------|-------------|
| **black** | Code formatter | `pyproject.toml` |
| **isort** | Import sorter | `pyproject.toml` |
| **flake8** | Linter | `.flake8` |
| **mypy** | Type checker | `pyproject.toml` |

## Best Practices

1. **Before committing:** Run `check-all` to ensure all quality checks pass
2. **Fix formatting issues:** Run `format` to automatically fix most formatting issues
3. **Regular checks:** Run quality checks regularly during development
4. **CI/CD:** Consider adding these checks to your CI/CD pipeline

## Configuration

All tool configurations are centralized in:
- `pyproject.toml` - black, isort, and mypy configuration
- `.flake8` - flake8 configuration (doesn't support pyproject.toml)

### Customization

To adjust tool behavior, edit the configuration files:

**Line length:**
- All tools are configured to use 88 characters (black's default)
- Modify in both `pyproject.toml` and `.flake8` to keep consistent

**Excluded directories:**
- `.venv`, `build`, `dist`, `chroma_db` are excluded by default
- Add more exclusions in the respective config files
