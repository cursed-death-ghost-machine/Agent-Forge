"""
Tools for managing the agent's tool system.

Provides capabilities to refresh, list, and modify existing tools.
"""

import os
from pathlib import Path
from pydantic import BaseModel, Field
from agent.tools import tool
from agent.config import config

@tool(
    name="refresh_tools",
    description="Refresh the tool registry to discover newly created or modified tools without restarting"
)
def refresh_tool_registry() -> str:
    """Refresh the tool registry to pick up new or modified tools."""
    
    try:
        from agent.tools import tool_registry
        
        # Get current tool count
        old_tools = set(tool_registry.get_tool_names())
        
        # Refresh the registry
        tool_registry.discover_tools()
        
        # Get new tool count
        new_tools = set(tool_registry.get_tool_names())
        
        added_tools = new_tools - old_tools
        removed_tools = old_tools - new_tools
        
        result = f"Tool registry refreshed successfully!\n"
        result += f"Total tools: {len(new_tools)}\n"
        
        if added_tools:
            result += f"Added tools: {', '.join(sorted(added_tools))}\n"
        
        if removed_tools:
            result += f"Removed tools: {', '.join(sorted(removed_tools))}\n"
        
        if not added_tools and not removed_tools:
            result += "No changes detected.\n"
        
        return result
        
    except Exception as e:
        return f"Error refreshing tool registry: {e}"

class EditToolArguments(BaseModel):
    """Arguments for editing an existing tool."""
    tool_name: str = Field(..., description="Name of the tool to edit")
    new_functionality: str = Field(..., description="New functionality description or code modifications needed")

@tool(
    name="edit_tool",
    description="Edit an existing tool's functionality or implementation",
    args_model=EditToolArguments
)
def edit_existing_tool(tool_name: str, new_functionality: str) -> str:
    """Edit an existing tool's implementation."""
    
    tools_dir = Path(config.tools_directory_path)
    tool_file = tools_dir / f"{tool_name}.py"
    
    if not tool_file.exists():
        return f"Error: Tool '{tool_name}' not found at {tool_file}"
    
    try:
        # Read the current tool file
        with open(tool_file, 'r') as f:
            current_code = f.read()
        
        # For now, we'll create a backup and provide guidance
        # In a more advanced version, we could parse and modify the AST
        
        backup_file = tools_dir / f"{tool_name}_backup.py"
        with open(backup_file, 'w') as f:
            f.write(current_code)
        
        result = f"Tool '{tool_name}' is ready for editing.\n"
        result += f"Current file: {tool_file}\n"
        result += f"Backup created: {backup_file}\n\n"
        result += f"Requested modifications: {new_functionality}\n\n"
        result += "To edit the tool:\n"
        result += f"1. Modify the implementation in {tool_file}\n"
        result += "2. Use 'refresh_tools' to reload the changes\n"
        result += "3. Test the updated tool\n\n"
        result += "Current tool code:\n"
        result += "=" * 50 + "\n"
        result += current_code[:1000]  # Show first 1000 chars
        if len(current_code) > 1000:
            result += "\n... (truncated, see full file for complete code)"
        
        return result
        
    except Exception as e:
        return f"Error editing tool: {e}"

@tool(
    name="list_tool_files",
    description="List all tool files in the tools directory with their basic information"
)
def list_tool_files() -> str:
    """List all available tool files and their basic information."""
    
    tools_dir = Path(config.tools_directory_path)
    
    if not tools_dir.exists():
        return f"Tools directory not found: {tools_dir}"
    
    tool_files = list(tools_dir.glob("*.py"))
    
    if not tool_files:
        return "No tool files found in the tools directory."
    
    result = f"Tool files in {tools_dir}:\n\n"
    
    for tool_file in sorted(tool_files):
        if tool_file.name.startswith("__"):
            continue
            
        try:
            with open(tool_file, 'r') as f:
                content = f.read()
            
            # Extract basic info
            lines = content.split('\n')
            docstring = ""
            
            # Look for module docstring
            in_docstring = False
            for line in lines:
                line = line.strip()
                if line.startswith('"""') or line.startswith("'''"):
                    if in_docstring:
                        break
                    in_docstring = True
                    docstring += line[3:] + " "
                elif in_docstring:
                    if line.endswith('"""') or line.endswith("'''"):
                        docstring += line[:-3]
                        break
                    docstring += line + " "
            
            result += f"📄 {tool_file.name}\n"
            if docstring.strip():
                result += f"   {docstring.strip()[:100]}{'...' if len(docstring) > 100 else ''}\n"
            
            # Get file size
            size = tool_file.stat().st_size
            result += f"   Size: {size} bytes\n\n"
            
        except Exception as e:
            result += f"📄 {tool_file.name} (Error reading: {e})\n\n"
    
    return result

class DeleteToolArguments(BaseModel):
    """Arguments for deleting a tool."""
    tool_name: str = Field(..., description="Name of the tool to delete")
    confirm: bool = Field(False, description="Set to true to confirm deletion")

@tool(
    name="delete_tool",
    description="Delete an existing tool file (use with caution)",
    args_model=DeleteToolArguments
)
def delete_tool(tool_name: str, confirm: bool = False) -> str:
    """Delete an existing tool file."""
    
    if not confirm:
        return f"To delete tool '{tool_name}', call this function again with confirm=true"
    
    tools_dir = Path(config.tools_directory_path)
    tool_file = tools_dir / f"{tool_name}.py"
    
    if not tool_file.exists():
        return f"Error: Tool '{tool_name}' not found at {tool_file}"
    
    try:
        # Create backup before deletion
        backup_file = tools_dir / f"{tool_name}_deleted_backup.py"
        tool_file.rename(backup_file)
        
        # Refresh tool registry
        from agent.tools import tool_registry
        tool_registry.discover_tools()
        
        return f"Tool '{tool_name}' deleted successfully. Backup saved as {backup_file.name}"
        
    except Exception as e:
        return f"Error deleting tool: {e}"
