"""
Example echo tool for Chimera CLI.

Demonstrates tool creation with arguments and Pydantic validation.
"""

from pydantic import BaseModel, Field
from agent.tools import tool

class EchoArguments(BaseModel):
    """Arguments for the echo tool."""
    message: str = Field(..., description="The message to echo back")
    repeat: int = Field(1, description="Number of times to repeat the message", ge=1, le=10)
    uppercase: bool = Field(False, description="Whether to convert message to uppercase")

@tool(
    name="echo",
    description="Echo a message back, optionally repeating it and converting to uppercase",
    args_model=EchoArguments
)
def echo_message(message: str, repeat: int = 1, uppercase: bool = False) -> str:
    """Echo a message with optional modifications."""
    
    # Apply transformations
    output_message = message.upper() if uppercase else message
    
    # Repeat message
    result_lines = []
    for i in range(repeat):
        if repeat > 1:
            result_lines.append(f"{i+1}. {output_message}")
        else:
            result_lines.append(output_message)
    
    return "\n".join(result_lines)
