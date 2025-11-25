# Development Guidelines for OCP CAD Viewer

## Build & Test Commands

### TypeScript/VSCode Extension
- `yarn compile` - Compile TypeScript to JavaScript
- `yarn watch` - Watch mode for compilation
- `yarn lint` - Run ESLint on src directory
- `yarn test` - Run VSCode extension tests
- `yarn pretest` - Compile and lint before testing

### Python Package
- `pytest -v -s pytests/` - Run Python tests
- `NATIVE_TESSELLATOR=1 pytest -v -s pytests/` - Run tests with native tessellator
- `ruff check ocp_vscode/` - Lint Python code
- `ruff format ocp_vscode/` - Format Python code

### Single Test
- `pytest -v -s pytests/test_show.py::Tests::test_method` - Run specific test method

## Code Style Guidelines

### TypeScript
- Use strict TypeScript compilation (enabled in tsconfig.json)
- Import style: `import * as vscode from "vscode"`
- Use ES2020 target, CommonJS modules
- 4-space indentation, 80 char line length
- No trailing commas in objects/arrays
- Apache 2.0 license header required

### Python
- Use ruff for linting and formatting (line-length: 88)
- Import style: `from module import name` or `import module`
- Use type hints where applicable
- Apache 2.0 license header required
- `# ruff: noqa: F403, F401` for __init__.py wildcard imports

### General
- Follow existing naming conventions (camelCase for TS, snake_case for Python)
- Error handling: use proper try/catch blocks and logging
- Maintain backward compatibility in API changes
- Test all new functionality with appropriate test cases