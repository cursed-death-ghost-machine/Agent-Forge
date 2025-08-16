"""
Example system information tool for Chimera CLI.

Demonstrates basic tool creation with simple system queries.
"""

import platform
import datetime
import os
from agent.tools import tool

@tool(
    name="system_info",
    description="Get basic system information including OS, Python version, and current time"
)
def get_system_info() -> str:
    """Get basic system information."""
    info = {
        "Operating System": f"{platform.system()} {platform.release()}",
        "Python Version": platform.python_version(),
        "Current Time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Current Directory": os.getcwd(),
        "Username": os.getenv("USER", os.getenv("USERNAME", "Unknown"))
    }
    
    result = "System Information:\n"
    for key, value in info.items():
        result += f"• {key}: {value}\n"
    
    return result.strip()
