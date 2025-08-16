"""
A simple calculator tool

Auto-generated tool created by the agent.
"""

from pydantic import BaseModel, Field
from agent.tools import tool

class TestCalculatorArguments(BaseModel):
    """Arguments for the test_calculator tool."""
    operation: str = Field(..., description="The operation to perform (add, subtract, multiply, divide)")
    a: float = Field(..., description="First number")
    b: float = Field(..., description="Second number")

@tool(
    name="test_calculator",
    description="A simple calculator tool",
    args_model=TestCalculatorArguments
)
def test_calculator(operation: str, a: float, b: float) -> str:
    """
    Performs basic arithmetic operations like addition, subtraction, multiplication, and division
    
    This tool was auto-generated. Modify the implementation below as needed.
    """
    
    # TODO: Implement the actual functionality
    # This is a template - replace with actual implementation
    
    result = f"Tool 'test_calculator' executed successfully!\n"
    result += f"Functionality: Performs basic arithmetic operations like addition, subtraction, multiplication, and division\n"
    
    # Add parameter information
    result += f"Parameter operation: {operation}\n"
    result += f"Parameter a: {a}\n"
    result += f"Parameter b: {b}\n"
    
    result += "\nNote: This is a template implementation. Please modify the code in tools/test_calculator.py to add actual functionality."
    
    return result
