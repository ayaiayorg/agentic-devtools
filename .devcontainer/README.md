# Python Development Container

This directory contains the configuration for a Python development container that can be used with:

- Visual Studio Code with the Dev Containers extension
- GitHub Codespaces
- Any tool that supports the Dev Container specification

## Features

- **Python 3.12**: Latest stable Python version
- **Development Tools**: Pre-configured with pytest, black, mypy, ruff, and isort
- **VS Code Extensions**:
  - Python language support (Pylance)
  - Black formatter
  - Ruff linter
  - mypy type checker
- **Auto-formatting**: Format on save enabled
- **Import organization**: Automatic import sorting on save
- **Testing**: pytest configured and ready to use

## Usage

### VS Code

1. Install the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
2. Open this repository in VS Code
3. When prompted, click "Reopen in Container" or use the command palette: `Dev Containers: Reopen in Container`
4. The container will build and install all dependencies automatically

### GitHub Codespaces

1. Create a new Codespace from this repository
2. The development environment will be set up automatically

## Post-Create Setup

After the container is created, the following command runs automatically:

```bash
pip install -e '.[dev]'
```

This installs the `agentic-devtools` package in editable mode with all development dependencies.

## Customization

To customize the development environment, edit the `devcontainer.json` file:

- Add more VS Code extensions to the `extensions` array
- Modify VS Code settings in the `settings` object
- Change the Python version by updating the `image` property
- Add additional features from the [devcontainer features catalog](https://containers.dev/features)
