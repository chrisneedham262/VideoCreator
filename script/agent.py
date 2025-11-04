"""
AI Agent for script generation following proper agent architecture patterns
"""
from openai import OpenAI
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ScriptAgent:
    """
    AI Agent for generating 35-second video scripts.
    Follows standard agent architecture with memory, state management, and error handling.
    """
    
    SYSTEM_PROMPT = """
You are a script writer for short-form video content that will be used with text-to-speech.

When a user provides a prompt, you must:
1. Convert their idea into a 35-second script
2. Keep the script concise and engaging
3. Write in a natural, conversational tone suitable for narration
4. Output ONLY the spoken script text

CRITICAL FORMATTING RULES:
- Do NOT include timestamps or time markers (no [0:00], 0:05, etc.)
- Do NOT include labels like "Narrator:", "Speaker:", "Voice:", etc.
- Do NOT include stage directions or scene descriptions
- Do NOT include any formatting or structural elements
- Output ONLY the words that should be spoken
- Write as one continuous, flowing narration

Your output will be fed directly into text-to-speech, so it must be clean, readable text only.
"""
    
    def __init__(self, api_key: str, model: str = "gpt-4", temperature: float = 0.7, max_tokens: int = 1000):
        """
        Initialize the ScriptAgent
        
        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4)
            temperature: Temperature for generation (default: 0.7)
            max_tokens: Maximum tokens to generate (default: 1000)
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.memory: List[Dict[str, str]] = []
        self.additional_instructions: List[str] = []
        
    def set_additional_instructions(self, instructions: List[str]):
        """
        Set additional system instructions beyond the base prompt
        
        Args:
            instructions: List of additional instruction strings
        """
        self.additional_instructions = instructions
        
    def load_memory(self, messages: List[Dict[str, str]]):
        """
        Load conversation history into agent memory
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
        """
        self.memory = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in messages
            if msg["role"] in ["user", "assistant"]
        ]
        
    def clear_memory(self):
        """Clear all conversation history"""
        self.memory = []
        
    def _build_messages(self) -> List[Dict[str, str]]:
        """
        Build the complete message list for LLM including system prompts and memory
        
        Returns:
            List of formatted messages
        """
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT.strip()}]
        
        # Add any additional instructions
        if self.additional_instructions:
            combined_additional = "\n\n".join(self.additional_instructions)
            messages.append({"role": "system", "content": combined_additional})
        
        # Add conversation memory
        messages.extend(self.memory)
        
        return messages
        
    def run(self, user_input: str) -> str:
        """
        Main agent execution method
        
        Args:
            user_input: User's prompt/message
            
        Returns:
            Agent's response
        """
        try:
            # Add user message to memory
            self.memory.append({"role": "user", "content": user_input})
            
            # Build complete message list
            messages = self._build_messages()
            
            # Call LLM
            response_content = self._call_llm(messages)
            
            # Add assistant response to memory
            self.memory.append({"role": "assistant", "content": response_content})
            
            return response_content
            
        except Exception as e:
            logger.error(f"Agent execution error: {str(e)}")
            raise
            
    def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        """
        Internal method to call the LLM with error handling
        
        Args:
            messages: Complete message list
            
        Returns:
            LLM response content
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"LLM call failed: {str(e)}")
            raise ValueError(f"Failed to get response from LLM: {str(e)}")
            
    def get_state(self) -> Dict:
        """
        Get current agent state
        
        Returns:
            Dict containing agent state information
        """
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "memory_length": len(self.memory),
            "additional_instructions_count": len(self.additional_instructions)
        }

