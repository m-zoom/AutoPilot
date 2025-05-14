import streamlit as st
import os
import json
import re
from datetime import datetime
from agent import create_agent

# Set page configuration
st.set_page_config(
    page_title="AI Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom CSS for a ChatGPT-like interface
st.markdown("""
<style>
    .chat-message {
        padding: 1.5rem; 
        border-radius: 0.5rem; 
        margin-bottom: 1rem; 
        display: flex;
        flex-direction: row;
        align-items: flex-start;
        gap: 0.75rem;
    }
    .chat-message.user {
        background-color: #2b313e;
    }
    .chat-message.assistant {
        background-color: #343541;
    }
    .chat-message .avatar {
        width: 2.5rem;
        height: 2.5rem;
        border-radius: 0.25rem;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1rem;
        font-weight: bold;
        text-transform: uppercase;
    }
    .chat-message .avatar.user {
        background-color: #c4bffc;
        color: #343541;
    }
    .chat-message .avatar.assistant {
        background-color: #10a37f;
        color: white;
    }
    .chat-message .message {
        flex-grow: 1;
        padding-top: 0.25rem;
        line-height: 1.5;
    }
    .command-buttons {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin-top: 1rem;
    }
    .command-buttons button {
        background-color: #2b313e;
        color: white;
        border: none;
        border-radius: 0.25rem;
        padding: 0.5rem 1rem;
        cursor: pointer;
    }
    .sidebar-content {
        padding: 1rem;
    }
    .sidebar-content h3 {
        margin-top: 1.5rem;
    }
    pre {
        white-space: pre-wrap;
        word-wrap: break-word;
        background-color: #1e1e1e;
        padding: 1rem;
        border-radius: 0.5rem;
        overflow-x: auto;
    }
    code {
        font-family: 'Courier New', Courier, monospace;
    }
    /* Responsive layout adjustments */
    @media (max-width: 768px) {
        .chat-message {
            padding: 1rem;
            flex-direction: column;
        }
        .chat-message .avatar {
            margin-bottom: 0.5rem;
        }
    }
    /* Tool execution log styling */
    .tool-execution {
        background-color: #363a45;
        border-radius: 0.5rem;
        padding: 0.75rem;
        margin-top: 0.5rem;
        font-family: 'Courier New', Courier, monospace;
        font-size: 0.9rem;
    }
    /* Thinking animation */
    @keyframes thinking {
        0% { opacity: 0.3; }
        50% { opacity: 1; }
        100% { opacity: 0.3; }
    }
    .thinking {
        display: flex;
        gap: 0.5rem;
    }
    .thinking span {
        height: 0.5rem;
        width: 0.5rem;
        background-color: #ffffff;
        border-radius: 50%;
        display: inline-block;
        animation: thinking 1.5s infinite;
    }
    .thinking span:nth-child(2) {
        animation-delay: 0.2s;
    }
    .thinking span:nth-child(3) {
        animation-delay: 0.4s;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state variables
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'command_history' not in st.session_state:
    st.session_state.command_history = []
if 'max_history' not in st.session_state:
    st.session_state.max_history = 10
if 'agent' not in st.session_state:
    st.session_state.agent = create_agent()
if 'thinking' not in st.session_state:
    st.session_state.thinking = False
if 'debug_mode' not in st.session_state:
    st.session_state.debug_mode = False

# Sidebar with tool info and command history
with st.sidebar:
    st.title("AI Assistant")
    
    # Toggle debug mode
    st.session_state.debug_mode = st.toggle("Debug Mode", st.session_state.debug_mode)
    
    st.subheader("Command History")
    
    if not st.session_state.command_history:
        st.info("No commands yet. Start interacting with the assistant!")
    else:
        for i, cmd in enumerate(st.session_state.command_history):
            cmd_display = cmd[:30] + "..." if len(cmd) > 30 else cmd
            if st.button(f"{i+1}: {cmd_display}", key=f"hist_{i}"):
                st.session_state.messages.append({"role": "user", "content": cmd})
                st.session_state.thinking = True
                st.rerun()
    
    st.subheader("Special Commands")
    st.write("- **!clear** - Clear conversation")
    st.write("- **!help** - Show help menu")
    st.write("- **!save** - Save conversation")
    st.write("- **exit/quit/bye** - End session")

# Function to display chat messages
def clean_html_content(content):
    """Clean up any stray HTML tags or formatting issues"""
    if not content:
        return content
    
    # Even simpler approach to avoid regex issues
    # Just use string replacement for common problematic tags
    problematic_tags = [
        '</div>', '</p>', '</span>', '</h1>', '</h2>', '</h3>', 
        '</h4>', '</h5>', '</h6>', '</ul>', '</ol>', '</li>', 
        '</table>', '</tr>', '</td>', '</th>'
    ]
    
    # Check if any problematic tags are in the content
    # Don't modify content if no problematic tags found (optimization)
    if not any(tag in content for tag in problematic_tags):
        return content
    
    # For safety, we'll just add a space before any closing tags
    # This simple approach won't catch all cases but will work for our needs
    # and is much safer than complex regex patterns
    cleaned_content = content
    for tag in problematic_tags:
        # Only replace tags that appear to be standalone (not preceded by opening tag)
        opening_tag = f"<{tag[2:]}"
        if tag in cleaned_content and opening_tag not in cleaned_content:
            cleaned_content = cleaned_content.replace(tag, '')
    
    return cleaned_content

def display_messages():
    for message in st.session_state.messages:
        role = message["role"]
        content = message["content"]
        
        # Clean the content to remove problematic HTML tags
        content = clean_html_content(content)
        
        # Display user message
        if role == "user":
            # Use Streamlit's built-in chat message for user
            with st.chat_message("user", avatar="👤"):
                st.write(content)
        
        # Display assistant message
        elif role == "assistant":
            tool_logs = ""
            if "tool_logs" in message:
                tool_logs_content = clean_html_content(message["tool_logs"])
                
                # Create a formatted version of the tool logs
                tool_logs = f"**Tool Execution:**\n\n{tool_logs_content}"
            
            # Use Streamlit's built-in chat message for assistant
            with st.chat_message("assistant", avatar="🤖"):
                st.write(content)
                
                # Show tool logs if available
                if tool_logs:
                    with st.expander("View Tool Execution Details"):
                        st.markdown(tool_logs)

# Function to process user input
def process_user_input(user_input):
    if not user_input.strip():
        return
    
    # Handle special commands
    if user_input.lower() in ["exit", "quit", "bye"]:
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.messages.append({"role": "assistant", "content": "Goodbye! Have a great day!"})
        return
    
    elif user_input == "!clear":
        st.session_state.messages = []
        return
    
    elif user_input == "!help":
        help_content = """
        ## AI Assistant Help
        
        This AI assistant can help you with various tasks on your computer:
        
        ### Available Tools:
        
        1. **open_application** - Opens applications on Mac or Windows
           Example: "Open Chrome" or "Launch Notepad"
        
        2. **navigate_directory** - Navigates to directories in your file system
           Example: "Go to Documents folder" or "Navigate to Downloads"
        
        3. **create_file** - Creates files with specific content
           Example: "Create a text file called notes.txt with content 'My important notes'"
           Example: "Make a Python script that prints Hello World"
        
        ### Special Commands:
        
        - **!clear** - Clear the conversation history
        - **!help** - Display this help message
        - **!save** - Save the conversation to a file
        - **exit/quit/bye** - End the conversation
        
        For complex tasks, the assistant can plan and execute multiple steps. For example:
        "Create a Python script in my Documents folder that prints Hello World"
        """
        
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.messages.append({"role": "assistant", "content": help_content})
        return
    
    elif user_input == "!save":
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"conversation_{timestamp}.json"
        with open(filename, "w") as f:
            json.dump(st.session_state.messages, f, indent=2)
        
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.messages.append({"role": "assistant", "content": f"Conversation saved to {filename}"})
        return
    
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Add to command history if it's not a special command
    if not user_input.startswith("!") and user_input.strip():
        st.session_state.command_history.append(user_input)
        # Keep history within maximum size
        if len(st.session_state.command_history) > st.session_state.max_history:
            st.session_state.command_history.pop(0)
    
    # Set thinking state to show the thinking animation
    st.session_state.thinking = True

# Display "AI is thinking" animation if needed
def display_thinking():
    if st.session_state.thinking:
        with st.chat_message("assistant", avatar="🤖"):
            st.write("Thinking...")
            with st.spinner("Processing your request..."): 
                # Streamlit spinner provides a native loading animation
                pass

# Process the response from the agent
def process_agent_response():
    if st.session_state.thinking:
        # Capture logs if debug mode is on
        tool_logs = None
        
        try:
            # Get last user message
            user_input = [msg for msg in st.session_state.messages if msg["role"] == "user"][-1]["content"]
            
            # Get response from agent
            response = st.session_state.agent.invoke({"input": user_input})
            
            # Add assistant message to chat history
            assistant_message = {"role": "assistant", "content": response["output"]}
            
            # Add debug logs if enabled
            if st.session_state.debug_mode and "intermediate_steps" in response:
                logs = []
                for step in response["intermediate_steps"]:
                    if hasattr(step[0], "tool") and hasattr(step[0], "tool_input"):
                        tool_name = step[0].tool
                        tool_input = step[0].tool_input
                        tool_output = step[1]
                        logs.append(f"Tool: {tool_name}")
                        logs.append(f"Input: {tool_input}")
                        logs.append(f"Output: {tool_output}")
                        logs.append("---")
                
                if logs:
                    assistant_message["tool_logs"] = "<br>".join(logs)
            
            st.session_state.messages.append(assistant_message)
        
        except Exception as e:
            error_message = f"Error: {str(e)}"
            st.session_state.messages.append({"role": "assistant", "content": error_message})
        
        finally:
            # Set thinking state to False to remove the thinking animation
            st.session_state.thinking = False

# Display example buttons for quick prompts

# Main chat interface
st.header("Chat with AutoPilot")

# Display existing messages
display_messages()

# Process the agent response if in thinking state
if st.session_state.thinking:
    display_thinking()
    process_agent_response()
    st.rerun()

# Chat input at the bottom
with st.container():
    user_input = st.chat_input("Type your message here...", key="user_input")
    if user_input:
        process_user_input(user_input)
        st.rerun()

# Add a footer
st.markdown("---")
st.markdown("AI Assistant powered by LangChain and OpenAI")