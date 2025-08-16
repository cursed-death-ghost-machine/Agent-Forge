"""
CLI interface for Chimera CLI.

Provides rich interactive command-line experience with auto-completion
and formatted output.
"""

import asyncio
import logging
import sys
from typing import List
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.logging import RichHandler
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory

from .config import config
from .core import AICore
from .tools import tool_registry

# Set up rich console and logging
console = Console()

def setup_logging():
    """Configure logging with Rich handler."""
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper()),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)]
    )

app = typer.Typer(
    name="chimera",
    help="Chimera CLI - An Extensible AI Assistant",
    add_completion=False
)

class ToolCompleter(WordCompleter):
    """Dynamic completer for tool names."""
    
    def __init__(self):
        super().__init__([])
        self.update_completions()
    
    def update_completions(self):
        """Update completion words with current tool names."""
        tool_names = tool_registry.get_tool_names()
        commands = ["help", "clear", "exit", "quit", "tools"] + tool_names
        self.words = commands

@app.command()
def chat():
    """Start interactive chat session with Chimera."""
    asyncio.run(async_chat())
async def async_chat():
    """Async chat session implementation."""
    setup_logging()
    
    # Initialize components
    ai_core = AICore()
    
    # Discover tools
    console.print("[yellow]Discovering tools...[/yellow]")
    tool_registry.discover_tools()
    
    tool_names = tool_registry.get_tool_names()
    if tool_names:
        console.print(f"[green]Loaded {len(tool_names)} tools: {', '.join(tool_names)}[/green]")
    else:
        console.print("[yellow]No tools found. You can add tools to the 'tools' directory.[/yellow]")
    
    # Set up prompt session with history and completion
    history_file = Path.home() / ".chimera_history"
    completer = ToolCompleter()
    completer.update_completions()  # Refresh after tool discovery
    
    session = PromptSession(
        history=FileHistory(str(history_file)),
        completer=completer,
        complete_while_typing=True
    )
    
    # Welcome message
    welcome_panel = Panel(
        Text("Welcome to Chimera CLI!\n\nType your messages to chat with the AI assistant.\nSpecial commands: 'help', 'clear', 'tools', 'exit'", 
             justify="center"),
        title="🔮 Chimera CLI",
        border_style="blue"
    )
    console.print(welcome_panel)
    
    # Main chat loop
    while True:
        try:
            # Get user input
            user_input = session.prompt("🔮 You: ")
            
            if not user_input.strip():
                continue
            
            # Handle special commands
            if user_input.lower() in ["exit", "quit"]:
                console.print("[yellow]Goodbye![/yellow]")
                break
            elif user_input.lower() == "clear":
                ai_core.clear_history()
                console.clear()
                console.print("[green]Conversation history cleared.[/green]")
                continue
            elif user_input.lower() == "help":
                show_help()
                continue
            elif user_input.lower() == "tools":
                show_tools()
                continue
            
            # Process with AI
            console.print("[dim]Thinking...[/dim]")
            
            try:
                response = await ai_core.process_user_input(user_input)
                
                # Display response
                response_panel = Panel(
                    response,
                    title="🤖 Chimera",
                    border_style="green"
                )
                console.print(response_panel)
                
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
        
        except KeyboardInterrupt:
            console.print("\n[yellow]Use 'exit' to quit.[/yellow]")
        except EOFError:
            console.print("\n[yellow]Goodbye![/yellow]")
            break

def show_help():
    """Display help information."""
    help_text = """
[bold blue]Chimera CLI Help[/bold blue]

[bold]Special Commands:[/bold]
• help    - Show this help message
• clear   - Clear conversation history
• tools   - List available tools
• exit    - Exit the application

[bold]Usage:[/bold]
Simply type your message and press Enter to chat with Chimera.
The AI can use various tools to help you accomplish tasks.

[bold]Creating Tools:[/bold]
Add Python files to the 'tools' directory with @tool decorated functions.
See the README.md for detailed instructions.
"""
    console.print(Panel(help_text, title="Help", border_style="cyan"))

def show_tools():
    """Display available tools."""
    tool_manifest = tool_registry.get_tool_manifest()
    
    if not tool_manifest:
        console.print("[yellow]No tools available. Add tools to the 'tools' directory.[/yellow]")
        return
    
    tools_text = "[bold blue]Available Tools:[/bold blue]\n\n"
    
    for tool_info in tool_manifest:
        tools_text += f"• [bold]{tool_info['name']}[/bold]: {tool_info['description']}\n"
    
    console.print(Panel(tools_text, title="Tools", border_style="magenta"))

@app.command("tools")
def list_tools():
    """List available tools."""
    setup_logging()
    tool_registry.discover_tools()
    show_tools()

@app.command("status")
def show_status():
    """Show API key rotation status."""
    setup_logging()
    
    from .core import LLMClient
    
    try:
        llm_client = LLMClient()
        status = llm_client.get_key_status()
        
        console.print(f"\n[bold blue]API Key Rotation Status[/bold blue]")
        console.print(f"Total Keys: {status['total_keys']}")
        console.print(f"Available Now: [green]{status['available_keys']}[/green]")
        console.print(f"Rate Limited: [yellow]{status['rate_limited_keys']}[/yellow]")
        console.print(f"Disabled: [red]{status['disabled_keys']}[/red]")
        
        if status['keys']:
            console.print("\n[bold]Individual Key Status:[/bold]")
            for key_info in status['keys']:
                if not key_info['is_available']:
                    status_color = "red"
                    ready_text = "Disabled"
                elif key_info['ready_now']:
                    status_color = "green"
                    ready_text = "Ready"
                else:
                    status_color = "yellow"
                    ready_text = f"Wait {key_info['time_until_available']:.1f}s"
                
                console.print(f"  Key {key_info['key_suffix']}: [{status_color}]{ready_text}[/{status_color}] "
                             f"(errors: {key_info['error_count']})")
        else:
            console.print("[red]No API keys configured![/red]")
            console.print("Add keys to POLLINATIONS_API_KEYS in your config or environment.")
            
    except Exception as e:
        console.print(f"[red]Error checking status: {e}[/red]")

@app.command()
def version():
    """Show version information."""
    from . import __version__
    console.print(f"Chimera CLI version {__version__}")

def main():
    """Main entry point."""
    # If no command provided, default to chat
    if len(sys.argv) == 1:
        chat()
    else:
        app()

if __name__ == "__main__":
    main()
