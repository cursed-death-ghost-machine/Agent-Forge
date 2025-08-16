"""
Meta-tool for creating new tools dynamically.

Allows the agent to create its own tools based on user requests.
"""

import os
import re
from pathlib import Path
from pydantic import BaseModel, Field
from agent.tools import tool
from agent.config import config

class CreateToolArguments(BaseModel):
    """Arguments for creating a new tool."""
    tool_name: str = Field(..., description="Name of the new tool (snake_case, no spaces)")
    tool_description: str = Field(..., description="Brief description of what the tool does")
    functionality: str = Field(..., description="Detailed description of the tool's functionality and behavior")
    parameters: str = Field("", description="Optional: JSON-like description of parameters the tool should accept")

@tool(
    name="create_tool",
    description="Create a new Python tool for the agent to use. The agent can create tools for any functionality needed.",
    args_model=CreateToolArguments
)
def create_new_tool(tool_name: str, tool_description: str, functionality: str, parameters: str = "") -> str:
    """Create a new tool file and make it available to the agent."""
    
    # Validate tool name
    if not re.match(r'^[a-z][a-z0-9_]*$', tool_name):
        return "Error: Tool name must be snake_case (lowercase letters, numbers, underscores only, start with letter)"
    
    # Check if tool already exists
    tools_dir = Path(config.tools_directory_path)
    tool_file = tools_dir / f"{tool_name}.py"
    
    if tool_file.exists():
        return f"Error: Tool '{tool_name}' already exists at {tool_file}"
    
    # Generate the tool code
    tool_code = generate_tool_code(tool_name, tool_description, functionality, parameters)
    
    try:
        # Ensure tools directory exists
        tools_dir.mkdir(exist_ok=True)
        
        # Write the tool file
        with open(tool_file, 'w') as f:
            f.write(tool_code)
        
        # Refresh the tool registry to make the new tool available immediately
        from agent.tools import tool_registry
        tool_registry.discover_tools()
        
        return f"Successfully created tool '{tool_name}' at {tool_file}. The tool is now available for use!"
        
    except Exception as e:
        return f"Error creating tool: {e}"

def generate_tool_code(tool_name: str, tool_description: str, functionality: str, parameters: str) -> str:
    """Generate Python code for a new tool based on the specifications."""
    
    # Create a clean module name and class name
    module_name = tool_name
    class_name = ''.join(word.capitalize() for word in tool_name.split('_')) + 'Arguments'
    function_name = tool_name
    
    # Parse parameters if provided
    param_fields = []
    function_params = []
    
    if parameters.strip():
        # Try to parse parameter descriptions
        # This is a simple parser - could be enhanced for more complex cases
        try:
            # Look for parameter patterns like "param_name (type): description"
            import json
            
            # Try to parse as JSON first
            try:
                param_dict = json.loads(parameters)
                for param_name, param_info in param_dict.items():
                    if isinstance(param_info, dict):
                        param_type = param_info.get('type', 'str')
                        param_desc = param_info.get('description', f'Parameter {param_name}')
                        required = param_info.get('required', True)
                        default = param_info.get('default', '...' if required else 'None')
                    else:
                        param_type = 'str'
                        param_desc = str(param_info)
                        required = True
                        default = '...'
                    
                    param_fields.append(f'    {param_name}: {param_type} = Field({default}, description="{param_desc}")')
                    
                    if required and default == '...':
                        function_params.append(f'{param_name}: {param_type}')
                    else:
                        function_params.append(f'{param_name}: {param_type} = {default}')
                        
            except json.JSONDecodeError:
                # Fallback to simple text parsing
                lines = parameters.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if line:
                        # Simple format: "param_name: description"
                        if ':' in line:
                            param_name, param_desc = line.split(':', 1)
                            param_name = param_name.strip()
                            param_desc = param_desc.strip()
                            
                            if param_name:
                                param_fields.append(f'    {param_name}: str = Field(..., description="{param_desc}")')
                                function_params.append(f'{param_name}: str')
                        
        except Exception:
            # If parsing fails, create a simple text input parameter
            param_fields.append('    input_text: str = Field(..., description="Input for the tool")')
            function_params.append('input_text: str')
    
    # Generate the tool code
    if param_fields:
        # Tool with parameters
        code = f'''"""
{tool_description}

Auto-generated tool created by the agent.
"""

from pydantic import BaseModel, Field
from agent.tools import tool

class {class_name}(BaseModel):
    """Arguments for the {tool_name} tool."""
{chr(10).join(param_fields)}

@tool(
    name="{tool_name}",
    description="{tool_description}",
    args_model={class_name}
)
def {function_name}({", ".join(function_params)}) -> str:
    """
    {functionality}
    
    This tool was auto-generated. Modify the implementation below as needed.
    """
    
    # TODO: Implement the actual functionality
    # This is a template - replace with actual implementation
    
    result = f"Tool '{tool_name}' executed successfully!\\n"
    result += f"Functionality: {functionality}\\n"
    
    # Add parameter information
{generate_param_processing(function_params)}
    
    result += "\\nNote: This is a template implementation. Please modify the code in tools/{tool_name}.py to add actual functionality."
    
    return result
'''
    else:
        # Simple tool without parameters
        code = f'''"""
{tool_description}

Auto-generated tool created by the agent.
"""

from agent.tools import tool

@tool(
    name="{tool_name}",
    description="{tool_description}"
)
def {function_name}() -> str:
    """
    {functionality}
    
    This tool was auto-generated. Modify the implementation below as needed.
    """
    
    # TODO: Implement the actual functionality
    # This is a template - replace with actual implementation
    
    result = f"Tool '{tool_name}' executed successfully!\\n"
    result += f"Functionality: {functionality}\\n"
    result += "\\nNote: This is a template implementation. Please modify the code in tools/{tool_name}.py to add actual functionality."
    
    return result
'''
    
    return code

def generate_param_processing(function_params):
    """Generate code to process function parameters."""
    if not function_params:
        return ""
    
    lines = []
    for param in function_params:
        param_name = param.split(':')[0].strip()
        if '=' in param_name:
            param_name = param_name.split('=')[0].strip()
        lines.append(f'    result += f"Parameter {param_name}: {{{param_name}}}\\n"')
    
    return '\n'.join(lines)
