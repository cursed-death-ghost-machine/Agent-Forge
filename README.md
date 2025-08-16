# 🔮 Chimera CLI - An Extensible AI Assistant

A bare-bones CLI AI agent designed for easy extensibility through Python tools. Similar to Gemini CLI but built for maximum customization and local deployment.

## ✨ Features

- **Conversational AI**: Powered by Pollinations.ai with intelligent API key rotation
- **Rate Limit Management**: Automatic rotation of multiple API keys to avoid rate limits
- **Dynamic Tool Discovery**: Automatically discovers and loads Python tools
- **Rich CLI Experience**: Interactive interface with history, auto-completion, and beautiful formatting
- **Easy Extensibility**: Simple `@tool` decorator for creating new capabilities
- **Robust Validation**: Pydantic-powered argument validation for tools
- **Continuous Operation**: Smart key rotation allows uninterrupted usage

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Pollinations.ai API keys (multiple recommended for rate limit avoidance)

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd chimera-cli
   ```

2. **Set up virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure API Keys**:
   ```bash
   # Edit config.toml and add your Pollinations.ai API keys
   # Add multiple keys separated by commas for rate limit rotation
   POLLINATIONS_API_KEYS = "key1,key2,key3,key4"
   ```

5. **Configure Chimera** (optional):
   ```bash
   cp config.toml.example config.toml
   # Edit config.toml with your settings
   ```

6. **Run Chimera**:
   ```bash
   python -m agent.cli
   ```

## 🛠️ Configuration

Chimera uses a layered configuration system:

1. **config.toml**: Main configuration file
2. **.env**: Environment variables (overrides config.toml)
3. **Environment variables**: Highest priority

### Key Settings

- `LLM_API_BASE_URL`: Pollinations.ai endpoint (default: `https://text.pollinations.ai/openai`)
- `LLM_MODEL_NAME`: Model to use (default: `openai`)
- `POLLINATIONS_API_KEYS`: Comma-separated API keys for rotation
- `TOOLS_DIRECTORY_PATH`: Where to find tools (default: `tools`)
- `LOG_LEVEL`: Logging verbosity (default: `INFO`)

### API Key Rotation

Chimera automatically rotates through multiple API keys to avoid Pollinations.ai's rate limit (1 call per 15 seconds per key). 

**Recommended Setup:**
- Add 4+ API keys for smooth continuous operation
- Keys are rotated automatically with intelligent rate limiting
- Failed keys are temporarily disabled and re-enabled automatically
- Use `chimera status` to monitor key rotation status

## 🔧 Creating Custom Tools

Creating tools is simple! Just add a Python file to the `tools/` directory.

### Basic Tool Example

```python
# tools/my_tool.py
from agent.tools import tool

@tool(
    name="greet",
    description="Greet a user by name"
)
def greet_user(name: str) -> str:
    return f"Hello, {name}! Nice to meet you."
```

### Advanced Tool with Validation

```python
# tools/calculator.py
from pydantic import BaseModel, Field
from agent.tools import tool

class CalculatorArgs(BaseModel):
    operation: str = Field(..., description="Operation: add, subtract, multiply, divide")
    a: float = Field(..., description="First number")
    b: float = Field(..., description="Second number")

@tool(
    name="calculator",
    description="Perform basic mathematical operations",
    args_model=CalculatorArgs
)
def calculate(operation: str, a: float, b: float) -> str:
    operations = {
        "add": a + b,
        "subtract": a - b,
        "multiply": a * b,
        "divide": a / b if b != 0 else "Error: Division by zero"
    }
    
    result = operations.get(operation.lower(), "Error: Unknown operation")
    return f"{a} {operation} {b} = {result}"
```

### Tool Creation Guidelines

1. **File Location**: Place tools in the `tools/` directory
2. **Decorator**: Use `@tool(name, description)` decorator
3. **Type Hints**: Use Python type hints for arguments
4. **Return String**: Tools should return string results
5. **Validation**: Use Pydantic models for complex argument validation
6. **Restart**: Restart Chimera to discover new tools

## 🎮 Usage

### Interactive Commands

- **Regular chat**: Just type your message
- **help**: Show help information
- **tools**: List available tools
- **status**: Show API key rotation status
- **clear**: Clear conversation history
- **exit**: Quit the application

### CLI Commands

- `python -m agent.cli` - Start interactive chat
- `python -m agent.cli tools` - List available tools  
- `python -m agent.cli status` - Show API key rotation status
- `python -m agent.cli version` - Show version info

### Example Interactions

```
🔮 You: What's my system information?
🤖 Chimera: I'll check your system information for you.

[System information displayed]

🔮 You: Echo "Hello World" 3 times in uppercase
🤖 Chimera: I'll echo that message for you.

1. HELLO WORLD
2. HELLO WORLD  
3. HELLO WORLD
```

## 🏗️ Architecture

```
chimera-cli/
├── agent/
│   ├── cli.py      # CLI interface and main loop
│   ├── core.py     # AI orchestration and LLM communication
│   ├── tools.py    # Tool registry and dispatcher
│   └── config.py   # Configuration management
├── tools/          # User-defined tools
│   ├── example_system_info.py
│   └── example_echo.py
└── config files...
```

### Key Components

- **CLI Layer**: Rich interactive interface with Typer and Prompt Toolkit
- **AI Core**: LLM communication and response parsing
- **Tool System**: Dynamic discovery, validation, and execution
- **Configuration**: Flexible TOML/environment variable system

## 🔍 Troubleshooting

### Common Issues

1. **API Connection Failed**:
   - Verify your Pollinations.ai API keys are valid
   - Check `POLLINATIONS_API_KEYS` in configuration
   - Use `chimera status` to check key rotation status

2. **Rate Limit Errors**:
   - Add more API keys to `POLLINATIONS_API_KEYS`
   - Each key allows 1 call per 15 seconds
   - Recommended: 4+ keys for continuous operation

3. **Tools Not Loading**:
   - Check tools are in the correct directory
   - Ensure Python files have `@tool` decorator
   - Look for syntax errors in tool files

3. **Import Errors**:
   - Activate your virtual environment
   - Install all requirements: `pip install -r requirements.txt`

### Logging

Set `LOG_LEVEL=DEBUG` in your configuration for detailed logging.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is open source. See LICENSE file for details.

## 🙏 Acknowledgments

- Built with [Typer](https://typer.tiangolo.com/) for CLI
- [Rich](https://rich.readthedocs.io/) for beautiful terminal output
- [Pydantic](https://pydantic-docs.helpmanual.io/) for data validation
- [Prompt Toolkit](https://python-prompt-toolkit.readthedocs.io/) for interactive features
- Powered by [Pollinations.ai](https://pollinations.ai/) for AI inference

---

**Happy coding with Chimera CLI!** 🔮✨
