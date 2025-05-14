"""
Unified browser tool for the AI agent that leverages browser-use library for all browser-related tasks.
This replaces the previous individual browser tools with a single powerful tool that can handle all browser operations.
"""

import sys

import os
import asyncio
import json
from typing import Any, Dict, Optional, List, Union
from langchain.tools import BaseTool
from langchain.callbacks.manager import CallbackManagerForToolRun
from langchain_openai import ChatOpenAI

# Importing browser-use components
from browser_use import Agent as BrowserAgent

def resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)


class UnifiedBrowserTool(BaseTool):
    """A single unified tool for all browser-related tasks using the browser-use library."""

    name: str = "browser_task"
    description: str = """
    Performs any browser-related task using a real browser. This tool can handle a wide range of browser operations
    including web searches, navigation, information extraction, form filling, and complex multi-step browser interactions.
    
    Input can be a simple string describing the task or a JSON object with the following optional parameters:
    - 'task': Description of the browser task to perform (REQUIRED)
    - 'url': Starting URL for the task (optional)
    
    Examples:
    Simple task: "Search for the weather in New York City"
    Complex task: {"task": "Find flights from Lagos to Maiduguri for next week"}
    Extraction task: {"task": "Go to example.com and extract all contact information", "url": "https://example.com"}
    Form submission: {"task": "Fill out the contact form on example.com with name 'John Doe' and email 'john@example.com'"}
    
    Returns the results from the browser operation as text.
    
    When to use this tool:
    - For any task that requires browser interactions
    - When you need to search the web
    - When you need to interact with a web page
    - When you need to extract information from a website
    - When you need to fill out forms or navigate complex websites
    """

    def _run(
        self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Run the browser task."""
        try:
            # Parse the input
            try:
                # Check if input is a JSON object
                task_info = json.loads(input_str)
                if isinstance(task_info, dict):
                    task = task_info.get("task")
                    url = task_info.get("url")
                else:
                    # If JSON parse succeeded but result is not a dict
                    task = input_str
                    url = None
            except (json.JSONDecodeError, TypeError):
                # If not valid JSON, assume it's just the task description
                task = input_str
                url = None
            
            if not task:
                return "Error: No task provided. Please specify a browser task to perform."
            
            # Check for API key
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                return "Error: OPENAI_API_KEY environment variable not set. Please provide your OpenAI API key."
            
            # Define async function to run the browser task
            async def run_browser_task():
                # Initialize the model
                llm = ChatOpenAI(
                    model="gpt-4o",
                    temperature=0.0,
                )
                
                # Create the browser agent with the task
                if url:
                    task_with_url = f"Go to {url} and {task}"
                    agent = BrowserAgent(task=task_with_url, llm=llm)
                else:
                    agent = BrowserAgent(task=task, llm=llm)
                
                # Run the browser agent
                result = await agent.run()
                return str(result)
            
            # Run the browser task
            result = asyncio.run(run_browser_task())
            return f"Browser task completed. Result: {result}"
        
        except Exception as e:
            return f"Error executing browser task: {str(e)}"