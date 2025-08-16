"""
AI Core for Chimera CLI.

Handles LLM communication, prompt construction, and response parsing.
"""

import asyncio
import json
import logging
import requests
from typing import Dict, Any, Optional, List, Tuple
from .config import config
from .tools import tool_registry, tool_dispatcher, ToolError
from .api_rotation import APIKeyRotationManager

logger = logging.getLogger(__name__)

class LLMClient:
    """Handles communication with Pollinations.ai API with key rotation."""
    
    def __init__(self):
        self.base_url = config.llm_api_base_url
        self.model_name = config.llm_model_name
        self.session = requests.Session()
        
        # Initialize API key rotation manager
        api_keys = config.pollinations_api_keys
        if not api_keys:
            logger.warning("No Pollinations API keys configured. Add keys to POLLINATIONS_API_KEYS.")
            logger.info("You can add multiple keys separated by commas for rate limit rotation.")
        
        self.key_manager = APIKeyRotationManager(api_keys, rate_limit_seconds=15.0)
        logger.info(f"Initialized with {len(api_keys)} API keys for rotation")
    
    def chat_completion(self, messages: List[Dict[str, str]]) -> str:
        """
        Send chat completion request to Pollinations.ai with API key rotation.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            
        Returns:
            LLM response text
        """
        # Get an available API key (with rate limiting)
        api_key = self.key_manager.wait_for_available_key(max_wait_seconds=30.0)
        if not api_key:
            raise Exception("No API keys available. All keys are rate limited or disabled.")
        
        try:
            # Construct request payload (OpenAI-compatible format)
            payload = {
                "model": self.model_name,
                "messages": messages,
                "stream": False,
                "temperature": 0.7
            }
            
            # Set up headers with API key
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # Send request to Pollinations.ai
            response = self.session.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=60  # Increased timeout for external API
            )
            
            # Handle rate limiting specifically
            if response.status_code == 429:
                logger.warning(f"Rate limit hit for API key ending in ...{api_key[-4:]}")
                self.key_manager.mark_key_error(api_key, disable_temporarily=False)
                raise Exception("Rate limit exceeded. Try again in a moment.")
            
            response.raise_for_status()
            result = response.json()
            
            # Extract response content
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                # Mark key as used only after successful response
                self.key_manager.mark_key_used(api_key)
                logger.debug(f"Successfully got response using API key ...{api_key[-4:]}")
                return content
            else:
                raise Exception("Invalid response format from Pollinations.ai")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Pollinations.ai request failed: {e}")
            self.key_manager.mark_key_error(api_key, disable_temporarily=False)
            raise Exception(f"Failed to communicate with Pollinations.ai: {e}")
        except Exception as e:
            logger.error(f"LLM processing error: {e}")
            if "rate limit" not in str(e).lower():
                self.key_manager.mark_key_error(api_key, disable_temporarily=False)
            raise
    
    def get_key_status(self) -> dict:
        """Get current status of API key rotation."""
        return self.key_manager.get_status()

class AICore:
    """Central orchestration for AI agent functionality."""
    
    def __init__(self):
        self.llm_client = LLMClient()
        self.conversation_history: List[Dict[str, str]] = []
    
    def _generate_system_prompt(self) -> str:
        """Generate system prompt with tool manifest."""
        tool_manifest = tool_registry.get_tool_manifest()
        
        system_prompt = """You are Chimera, a helpful AI assistant with access to various tools.

When a user asks you to do something that requires using a tool, respond with a JSON object in this exact format:
{
    "tool_call": {
        "name": "tool_name",
        "arguments": {"arg1": "value1", "arg2": "value2"}
    }
}

Available tools:
"""
        
        # Add tool descriptions
        for tool in tool_manifest:
            system_prompt += f"\n- {tool['name']}: {tool['description']}"
            if tool['parameters']['properties']:
                system_prompt += f"\n  Parameters: {json.dumps(tool['parameters']['properties'], indent=2)}"
        
        system_prompt += """

If no tool is needed, respond naturally in plain text. Only use the JSON format when you need to call a tool.
Be helpful, accurate, and concise in your responses."""
        
        return system_prompt
    
    def _parse_llm_response(self, response: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Parse LLM response to detect tool calls.
        
        Returns:
            Tuple of (natural_response, tool_call_dict)
        """
        response = response.strip()
        
        # Try to extract JSON from response
        try:
            # Look for JSON object in response
            if response.startswith('{') and response.endswith('}'):
                parsed = json.loads(response)
                if 'tool_call' in parsed:
                    return None, parsed['tool_call']
            
            # Check if JSON is embedded in text
            start_idx = response.find('{')
            end_idx = response.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                json_str = response[start_idx:end_idx + 1]
                parsed = json.loads(json_str)
                if 'tool_call' in parsed:
                    return None, parsed['tool_call']
            
        except json.JSONDecodeError:
            pass
        
        # No valid tool call found, return as natural response
        return response, None
    
    async def process_user_input(self, user_input: str) -> str:
        """
        Process user input and generate response.
        
        Args:
            user_input: User's message
            
        Returns:
            Agent's response
        """
        try:
            # Add user message to conversation history
            self.conversation_history.append({
                "role": "user",
                "content": user_input
            })
            
            # Prepare messages for LLM
            messages = [
                {"role": "system", "content": self._generate_system_prompt()}
            ] + self.conversation_history
            
            # Get LLM response
            llm_response = await asyncio.to_thread(self.llm_client.chat_completion, messages)
            
            # Parse response for tool calls
            natural_response, tool_call = self._parse_llm_response(llm_response)
            
            if tool_call:
                # Execute tool
                try:
                    tool_name = tool_call.get('name')
                    tool_args = tool_call.get('arguments', {})
                    
                    if not tool_name:
                        raise ToolError("Tool name not specified")
                    
                    tool_result = tool_dispatcher.execute_tool(tool_name, tool_args)
                    
                    # Add tool result to conversation and get final response
                    tool_message = f"Tool '{tool_name}' executed successfully. Result: {tool_result}"
                    
                    self.conversation_history.append({
                        "role": "assistant", 
                        "content": f"I'll use the {tool_name} tool to help you."
                    })
                    
                    self.conversation_history.append({
                        "role": "user",
                        "content": f"Tool result: {tool_result}"
                    })
                    
                    # Get final response from LLM
                    messages = [
                        {"role": "system", "content": "You are Chimera, a helpful AI assistant. The user has provided you with tool results. Respond naturally based on the results."}
                    ] + self.conversation_history
                    
                    final_response = await asyncio.to_thread(self.llm_client.chat_completion, messages)
                    
                    # Add final response to history
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": final_response
                    })
                    
                    return final_response
                    
                except ToolError as e:
                    error_response = f"I encountered an error while using the tool: {e}"
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": error_response
                    })
                    return error_response
            
            else:
                # Natural response, no tool needed
                self.conversation_history.append({
                    "role": "assistant",
                    "content": natural_response
                })
                return natural_response
                
        except Exception as e:
            error_msg = f"I encountered an error: {e}"
            logger.error(f"Error processing user input: {e}")
            return error_msg
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history.clear()
