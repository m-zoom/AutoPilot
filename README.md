# AI Assistant Application

## Overview
This project is an AI Assistant application built with both Streamlit and PySide6 interfaces. It provides a powerful agent that can perform various tasks including conversation, file management, application control, and browser automation.

## Features
- **Dual Interface**: Run as either a Streamlit web application or a PySide6 desktop application
- **Conversational AI**: Engage in natural language conversations with the AI assistant
- **File Operations**: Create, edit, and manage files through the assistant
- **Application Control**: Open and interact with applications on your system
- **Browser Automation**: Perform web-based tasks using integrated browser capabilities
- **ChatGPT-like UI**: Clean, modern interface with message history
- **Command Buttons**: Quick access to common functions

## Getting Started

### Prerequisites
- Python 3.11 or higher
- Required Python packages (see installation section)

### Installation

1. Clone this repository or download the source code
2. Install the required dependencies:

```bash
pip install -r requirements.txt  # If requirements.txt exists
# Or install the main dependencies manually:
pip install streamlit pyside6 langchain
```

3. Additional dependencies for browser automation:

```bash
pip install browser-use playwright
playwright install chromium
```

## Usage

### Running the Streamlit Interface

```bash
streamlit run streamlit_app.py
```

This will start the web interface, accessible through your browser.

### Running the Desktop Interface

```bash
python GUI.py
```

This will launch the desktop application built with PySide6.

## Project Structure

- `streamlit_app.py`: Streamlit web interface implementation
- `GUI.py`: PySide6 desktop application implementation
- `agent.py`: Core agent implementation with LangChain
- `tools/`: Directory containing various tool implementations for the agent
- `browser-use/`: Browser automation capabilities

## Browser Automation

The application includes browser automation capabilities through the `browser-use` package. This allows the agent to:

- Open web pages
- Fill out forms
- Click buttons and navigate websites
- Extract information from web pages
- Perform complex web-based workflows

## Building Executable

The application includes support for being packaged as an executable, with special handling for browser environment setup when running in this mode.

## License

[Specify your license here]

## Acknowledgements

- This project uses [LangChain](https://github.com/langchain-ai/langchain) for AI agent capabilities
- Browser automation powered by [browser-use](https://github.com/browser-use/browser-use) and [Playwright](https://playwright.dev/)
- UI built with [Streamlit](https://streamlit.io/) and [PySide6](https://doc.qt.io/qtforpython-6/)
