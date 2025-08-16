"""
Tool Registry and Dispatcher for Chimera CLI.

Handles dynamic tool discovery, registration, and execution with robust
argument validation using Pydantic.
"""

import importlib.util
import inspect
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Type
from pydantic import BaseModel, ValidationError, create_model

from .config import config

logger = logging.getLogger(__name__)

# Global tool registry
TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {}

class ToolError(Exception):
    """Custom exception for tool-related errors."""
    pass

def tool(name: str, description: str, args_model: Optional[Type[BaseModel]] = None):
    """
    Decorator for registering tools with the agent.
    
    Args:
        name: Tool name for LLM reference
        description: Tool description for LLM understanding
        args_model: Optional Pydantic model for argument validation
    """
    def decorator(func: Callable) -> Callable:
        # Get function signature for argument schema generation
        sig = inspect.signature(func)
        
        # If no args_model provided, create one from function signature
        if args_model is None:
            # Create Pydantic model from function signature
            fields = {}
            for param_name, param in sig.parameters.items():
                param_type = param.annotation if param.annotation != inspect.Parameter.empty else str
                default_value = param.default if param.default != inspect.Parameter.empty else ...
                fields[param_name] = (param_type, default_value)
            
            # Create dynamic Pydantic model
            dynamic_model = create_model(f"{name}Args", **fields)
        else:
            dynamic_model = args_model
        
        # Register tool in global registry
        TOOL_REGISTRY[name] = {
            'name': name,
            'description': description,
            'callable': func,
            'args_model': dynamic_model,
            'signature': sig
        }
        
        logger.debug(f"Registered tool: {name}")
        
        return func
    
    return decorator

class ToolRegistry:
    """Manages tool discovery and registration."""
    
    @staticmethod
    def discover_tools():
        """Discover and load tools from the tools directory."""
        tools_path = Path(config.tools_directory_path)
        
        if not tools_path.exists():
            logger.warning(f"Tools directory not found: {tools_path}")
            return
        
        # Clear existing registry (only tools loaded from files)
        # Keep any programmatically registered tools
        file_loaded_tools = [name for name, info in TOOL_REGISTRY.items() 
                           if hasattr(info.get('callable'), '__module__') 
                           and info['callable'].__module__.startswith('tools.')]
        for tool_name in file_loaded_tools:
            TOOL_REGISTRY.pop(tool_name, None)
        
        # Scan for Python files in tools directory
        for tool_file in tools_path.glob("*.py"):
            if tool_file.name.startswith("__"):
                continue
                
            try:
                # Load module dynamically
                spec = importlib.util.spec_from_file_location(
                    tool_file.stem, tool_file
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    logger.debug(f"Loaded tool module: {tool_file.name}")
                    
            except Exception as e:
                logger.error(f"Failed to load tool {tool_file.name}: {e}")
    
    @staticmethod
    def get_tool_names() -> List[str]:
        """Get list of registered tool names."""
        return list(TOOL_REGISTRY.keys())
    
    @staticmethod
    def get_tool_manifest() -> List[Dict[str, Any]]:
        """Generate tool manifest for LLM consumption."""
        manifest = []
        
        for tool_name, tool_info in TOOL_REGISTRY.items():
            args_model = tool_info['args_model']
            
            # Generate JSON schema from Pydantic model
            schema = args_model.model_json_schema()
            
            tool_spec = {
                'name': tool_name,
                'description': tool_info['description'],
                'parameters': {
                    'type': 'object',
                    'properties': schema.get('properties', {}),
                    'required': schema.get('required', [])
                }
            }
            
            manifest.append(tool_spec)
        
        return manifest

class ToolDispatcher:
    """Handles tool execution with argument validation."""
    
    @staticmethod
    def execute_tool(tool_name: str, tool_arguments: Dict[str, Any]) -> str:
        """
        Execute a tool with validated arguments.
        
        Args:
            tool_name: Name of the tool to execute
            tool_arguments: Dictionary of arguments for the tool
            
        Returns:
            Tool output as string
            
        Raises:
            ToolError: If tool execution fails
        """
        if tool_name not in TOOL_REGISTRY:
            raise ToolError(f"Tool '{tool_name}' not found")
        
        tool_info = TOOL_REGISTRY[tool_name]
        tool_callable = tool_info['callable']
        args_model = tool_info['args_model']
        
        try:
            # Validate and coerce arguments using Pydantic
            validated_args = args_model(**tool_arguments)
            
            # Execute tool with validated arguments
            result = tool_callable(**validated_args.model_dump())
            
            # Convert result to string if it isn't already
            if not isinstance(result, str):
                result = str(result)
            
            logger.info(f"Tool '{tool_name}' executed successfully")
            return result
            
        except ValidationError as e:
            error_msg = f"Invalid arguments for tool '{tool_name}': {e}"
            logger.error(error_msg)
            raise ToolError(error_msg)
            
        except Exception as e:
            error_msg = f"Tool '{tool_name}' execution failed: {e}"
            logger.error(error_msg)
            raise ToolError(error_msg)

# Initialize tool registry on module import
tool_registry = ToolRegistry()
tool_dispatcher = ToolDispatcher()
