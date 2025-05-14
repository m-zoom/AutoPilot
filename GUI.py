import sys
import os
import json
from datetime import datetime
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,QTextEdit, QLineEdit, QPushButton, QLabel, QSplitter, QListWidget, QListWidgetItem, QScrollArea, QFrame, QCheckBox, QGroupBox, QGridLayout, QToolButton, QMenu, QStyleFactory
from PySide6.QtCore import Qt, Signal, QSize, QThread, Slot, QTimer
from PySide6.QtGui import QColor, QIcon, QFont, QTextCursor, QPalette
# ==========================================================
# BROWSER ENVIRONMENT SETUP FOR EXECUTABLE
# ==========================================================
# ==========================================================
# BROWSER ENVIRONMENT SETUP FOR EXECUTABLE
# ==========================================================
def setup_browser_environment():
    """
    Set up the browser environment when running as an executable.
    This ensures browser-use and Playwright can function properly.
    """
    import os
    import sys
    import tempfile
    import platform
    import logging
    
    logger = logging.getLogger("browser_setup")
    
    # Check if running as executable
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        logger.info("Running as executable, setting up browser environment")
        
        # Create a persistent directory for browser data
        browser_data_dir = os.path.join(tempfile.gettempdir(), 'ai_agent_browser_data')
        os.makedirs(browser_data_dir, exist_ok=True)
        
        # Set environment variables for browser-use and Playwright
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = browser_data_dir
        
        # Find system browser (Chrome or Edge)
        if platform.system() == 'Windows':
            browser_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
            ]
            
            for path in browser_paths:
                if os.path.exists(path):
                    os.environ['BROWSER_PATH'] = path
                    logger.info(f"Using system browser: {path}")
                    break
        
        # Add _MEIPASS to PATH to find bundled browser components
        if '_MEIPASS' in dir(sys):
            if not hasattr(sys, '_MEIPASS_BROWSER_PATH_ADDED'):
                os.environ['PATH'] = f"{sys._MEIPASS}{os.pathsep}{os.environ['PATH']}"
                setattr(sys, '_MEIPASS_BROWSER_PATH_ADDED', True)
                logger.info(f"Added {sys._MEIPASS} to PATH")
        
        # Set Chrome CDP debugging port for browser-use
        os.environ['CDP_PORT'] = '9222'
        
        logger.info("Browser environment setup complete")
        return True
    return False

# Run the setup function
setup_browser_environment()
# ==========================================================

# Import agent (assuming the same agent interface as in the original code)
from agent import create_agent

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


class ThinkingThread(QThread):
    """Thread for executing agent response."""
    response_ready = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, agent, user_input):
        super().__init__()
        self.agent = agent
        self.user_input = user_input

    def run(self):
        try:
            response = self.agent.invoke({"input": self.user_input})
            self.response_ready.emit(response)
        except Exception as e:
            self.error_occurred.emit(str(e))

class MessageWidget(QFrame):
    """Widget for displaying a chat message"""

    def __init__(self, role, content, tool_logs=None, parent=None):
        super().__init__(parent)
        self.role = role
        self.content = content
        self.tool_logs = tool_logs
        self.init_ui()
        
    def on_document_size_changed(self):
        """Handle document size change events"""
        self.adjust_text_height()
        
    def adjust_text_height(self):
        """Dynamically adjust the height of text edit based on content"""
        # Get document size
        document_height = int(self.message_text.document().size().height())
        
        # Add small padding
        ideal_height = document_height + 5
        
        # Set height within bounds
        self.message_text.setFixedHeight(min(300, max(20, ideal_height)))
        
        # Signal the application to process pending layout changes
        QApplication.processEvents()

    def init_ui(self):
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setFrameShadow(QFrame.Shadow.Plain)
        self.setLineWidth(0)

        # Set background color based on role
        if self.role == "user":
            self.setStyleSheet("background-color: #2b313e; border-radius: 4px; padding: 5px; margin: 2px;")
        else:
            self.setStyleSheet("background-color: #343541; border-radius: 4px; padding: 5px; margin: 2px;")

        # Main layout
        layout = QHBoxLayout()
        self.setLayout(layout)

        # Avatar
        avatar_label = QLabel()
        avatar_label.setFixedSize(30, 30)  # Smaller avatar
        avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_label.setStyleSheet(f"""
            background-color: {'#c4bffc' if self.role == 'user' else '#10a37f'};
            color: {'#343541' if self.role == 'user' else 'white'};
            border-radius: 5px;
            font-weight: bold;
            font-size: 20px;
        """)
        avatar_label.setText("👤" if self.role == "user" else "🤖")
        layout.addWidget(avatar_label)

        # Message content layout
        content_layout = QVBoxLayout()

        # Message text
        message_text = QTextEdit()
        message_text.setReadOnly(True)
        message_text.setMarkdown(self.content)
        message_text.setStyleSheet("""
            border: none;
            background-color: transparent;
            color: #ffffff;
            font-size: 14px;
            margin: 0;
            padding: 0;
        """)
        # Ensure text is visible by setting a contrasting text color
        message_text.document().setDefaultStyleSheet("""
            body { color: #ffffff; margin: 0; padding: 0; }
            code { background-color: #1e1e1e; color: #e6e6e6; padding: 2px 4px; border-radius: 3px; }
            pre { background-color: #1e1e1e; color: #e6e6e6; padding: 8px; border-radius: 4px; }
            a { color: #4b9eff; }
            p { margin-top: 2px; margin-bottom: 2px; }
        """)

        # Store reference to text edit
        self.message_text = message_text
        
        # Dynamic height adjustment based on content
        message_text.document().documentLayout().documentSizeChanged.connect(
            self.on_document_size_changed
        )
        
        # Start with a very compact height
        message_text.setMinimumHeight(10)  # Very small initial height
        message_text.setMaximumHeight(300) # Maximum height before scrolling
        
        # Initial height calculation
        QTimer.singleShot(0, lambda: self.adjust_text_height())

        content_layout.addWidget(message_text)

        # Tool logs if available
        if self.tool_logs and self.role == "assistant":
            tool_button = QPushButton("View Tool Execution Details")
            tool_button.setStyleSheet("""
                background-color: #4a4d59;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px;
            """)

            tool_logs_text = QTextEdit()
            tool_logs_text.setReadOnly(True)
            tool_logs_text.setMarkdown(self.tool_logs)
            tool_logs_text.setStyleSheet("""
                background-color: #363a45;
                color: #e6e6e6;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Courier New', monospace;
                font-size: 12px;
            """)
            # Ensure text is visible
            tool_logs_text.document().setDefaultStyleSheet("""
                body { color: #e6e6e6; }
                code { background-color: #2a2d36; color: #ffffff; }
            """)
            tool_logs_text.setFixedHeight(200)
            tool_logs_text.hide()

            # Toggle visibility of tool logs
            def toggle_logs():
                if tool_logs_text.isHidden():
                    tool_logs_text.show()
                    tool_button.setText("Hide Tool Execution Details")
                else:
                    tool_logs_text.hide()
                    tool_button.setText("View Tool Execution Details")

                # Force layout updates
                QApplication.processEvents()
                
                # Force update the layout
                # This will cause any containing scroll areas to update
                if self.parent():
                    QApplication.processEvents()

            tool_button.clicked.connect(toggle_logs)

            content_layout.addWidget(tool_button)
            content_layout.addWidget(tool_logs_text)

        layout.addLayout(content_layout)
        layout.setStretchFactor(content_layout, 1)

class ChatWidget(QScrollArea):
    """Widget for displaying the chat conversation"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #282c34;
            }
        """)

        # Container for messages
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)  # Fix for AlignTop
        self.container_layout.setSpacing(5)  # Reduced spacing between messages
        self.container_layout.setContentsMargins(5, 5, 5, 5)  # Reduced margins

        self.setWidget(self.container)

    def add_message(self, role, content, tool_logs=None):
        message = MessageWidget(role, content, tool_logs)
        self.container_layout.addWidget(message)
        
        # Process events to ensure immediate layout updates
        QApplication.processEvents()
        
        # Use QTimer to scroll after a short delay to allow layout updates
        QTimer.singleShot(50, self.scroll_to_bottom)
        
        # Immediate scroll attempt
        self.scroll_to_bottom()
    
    def scroll_to_bottom(self):
        """Scroll to bottom of the chat area"""
        # Scroll to bottom to show the latest message
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    def clear_messages(self):
        # Remove all messages
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

class CommandHistoryWidget(QListWidget):
    """Widget for displaying command history"""

    command_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QListWidget {
                background-color: #2b313e;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #3c4049;
            }
            QListWidget::item:selected {
                background-color: #4a5162;
            }
        """)

        self.itemClicked.connect(self.on_command_selected)

    def on_command_selected(self, item):
        self.command_selected.emit(item.text().split(": ", 1)[1])

    def add_command(self, command):
        num_items = self.count()
        trimmed_command = command[:30] + "..." if len(command) > 30 else command
        self.addItem(f"{num_items + 1}: {trimmed_command}")

    def clear_history(self):
        self.clear()

class SidebarWidget(QWidget):
    """Sidebar widget with tools info and command history"""

    command_selected = Signal(str)
    debug_toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Title
        title_label = QLabel("AI Assistant")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        layout.addWidget(title_label)

        # Debug mode toggle
        debug_toggle = QCheckBox("Debug Mode")
        debug_toggle.setStyleSheet("color: white;")
        debug_toggle.stateChanged.connect(lambda state: self.debug_toggled.emit(state == Qt.CheckState.Checked))
        layout.addWidget(debug_toggle)

        # Command history
        history_group = QGroupBox("Command History")
        history_group.setStyleSheet("""
            QGroupBox {
                color: white;
                border: 1px solid #3c4049;
                border-radius: 4px;
                margin-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
            }
        """)

        history_layout = QVBoxLayout()
        self.command_history = CommandHistoryWidget()
        self.command_history.command_selected.connect(self.command_selected)
        history_layout.addWidget(self.command_history)
        history_group.setLayout(history_layout)
        layout.addWidget(history_group)

        # Special commands
        commands_group = QGroupBox("Special Commands")
        commands_group.setStyleSheet("""
            QGroupBox {
                color: white;
                border: 1px solid #3c4049;
                border-radius: 4px;
                margin-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
            }
        """)

        commands_layout = QVBoxLayout()

        commands = [
            "- **!clear** - Clear conversation",
            "- **!help** - Show help menu",
            "- **!save** - Save conversation",
            "- **exit/quit/bye** - End session"
        ]

        for cmd in commands:
            cmd_label = QLabel(cmd)
            cmd_label.setTextFormat(Qt.TextFormat.MarkdownText)
            cmd_label.setStyleSheet("color: white;")
            commands_layout.addWidget(cmd_label)

        commands_group.setLayout(commands_layout)
        layout.addWidget(commands_group)

        layout.addStretch()

    def add_command(self, command):
        self.command_history.add_command(command)

    def clear_command_history(self):
        self.command_history.clear_history()

class ThinkingWidget(QWidget):
    """Widget showing a thinking animation"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()
        self.setLayout(layout)

        # Avatar
        avatar_label = QLabel()
        avatar_label.setFixedSize(30, 30)  # Smaller avatar
        avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_label.setStyleSheet("""
            background-color: #10a37f;
            color: white;
            border-radius: 5px;
            font-weight: bold;
            font-size: 20px;
        """)
        avatar_label.setText("🤖")
        layout.addWidget(avatar_label)

        # Thinking text and dots
        thinking_layout = QVBoxLayout()
        thinking_label = QLabel("Thinking...")
        thinking_label.setStyleSheet("color: white; font-size: 14px;")
        thinking_layout.addWidget(thinking_label)

        # Dots animation would go here (in a real app using QTimers)
        # For simplicity, just showing static dots
        dots_label = QLabel("⬤  ⬤  ⬤")
        dots_label.setStyleSheet("color: white; font-size: 8px;")
        thinking_layout.addWidget(dots_label)

        layout.addLayout(thinking_layout)
        layout.addStretch()

        self.setStyleSheet("""
            background-color: #343541;
            border-radius: 8px;
            padding: 10px;
            margin: 5px;
        """)

class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()

        # Initialize state
        self.messages = []
        self.command_history = []
        self.max_history = 10
        self.agent = create_agent()
        self.debug_mode = False

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("AI Assistant")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet("background-color: #282c34;")

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QHBoxLayout(central_widget)

        # Create a splitter for resizable sidebar
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Sidebar
        self.sidebar = SidebarWidget()
        self.sidebar.command_selected.connect(self.handle_command)
        self.sidebar.debug_toggled.connect(self.toggle_debug)
        self.sidebar.setFixedWidth(250)
        splitter.addWidget(self.sidebar)

        # Chat area container
        chat_container = QWidget()
        chat_layout = QVBoxLayout(chat_container)
        chat_layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QLabel("Chat with AutoPilot")
        header.setStyleSheet("color: white; font-size: 24px; font-weight: bold; margin: 10px;")
        chat_layout.addWidget(header)

        # Chat widget
        self.chat_widget = ChatWidget()
        chat_layout.addWidget(self.chat_widget)

        # Thinking indicator (hidden by default)
        self.thinking_widget = ThinkingWidget()
        self.thinking_widget.hide()
        chat_layout.addWidget(self.thinking_widget)

        # Input area
        input_container = QWidget()
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(10, 10, 10, 10)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type your message here...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: #3c4049;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 10px;
                font-size: 14px;
            }
            QLineEdit::placeholder {
                color: #a0a0a0;
            }
        """)
        self.input_field.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.input_field)

        send_button = QPushButton("Send")
        send_button.setStyleSheet("""
            QPushButton {
                background-color: #10a37f;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0d8c6d;
            }
        """)
        send_button.clicked.connect(self.send_message)
        input_layout.addWidget(send_button)

        chat_layout.addWidget(input_container)

        # Footer
        footer = QLabel("AI Assistant powered by LangChain and OpenAI")
        footer.setStyleSheet("color: #6b7280; padding: 10px; text-align: center;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chat_layout.addWidget(footer)

        splitter.addWidget(chat_container)
        splitter.setSizes([250, 950])  # Initial sizes

        main_layout.addWidget(splitter)

    def send_message(self):
        user_input = self.input_field.text().strip()
        if not user_input:
            return

        self.input_field.clear()

        # Handle special commands
        if user_input.lower() in ["exit", "quit", "bye"]:
            self.add_message("user", user_input)
            self.add_message("assistant", "Goodbye! Have a great day!")
            return

        elif user_input == "!clear":
            self.messages = []
            self.chat_widget.clear_messages()
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

            self.add_message("user", user_input)
            self.add_message("assistant", help_content)
            return

        elif user_input == "!save":
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"conversation_{timestamp}.json"

            with open(filename, "w") as f:
                json.dump(self.messages, f, indent=2)

            self.add_message("user", user_input)
            self.add_message("assistant", f"Conversation saved to {filename}")
            return

        # Add user message
        self.add_message("user", user_input)

        # Add to command history if not a special command
        if not user_input.startswith("!"):
            self.command_history.append(user_input)
            self.sidebar.add_command(user_input)

            # Keep history within limit
            if len(self.command_history) > self.max_history:
                self.command_history.pop(0)

        # Show thinking indicator
        self.thinking_widget.show()

        # Process with agent in a separate thread
        self.thinking_thread = ThinkingThread(self.agent, user_input)
        self.thinking_thread.response_ready.connect(self.handle_response)
        self.thinking_thread.error_occurred.connect(self.handle_error)
        self.thinking_thread.start()

    @Slot(dict)
    def handle_response(self, response):
        # Hide thinking indicator
        self.thinking_widget.hide()

        # Process response
        assistant_content = response["output"]

        # Create logs if debug mode is enabled
        tool_logs = None
        if self.debug_mode and "intermediate_steps" in response:
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
                tool_logs = "<br>".join(logs)

        # Add assistant message
        self.add_message("assistant", assistant_content, tool_logs)

    @Slot(str)
    def handle_error(self, error_message):
        # Hide thinking indicator
        self.thinking_widget.hide()

        # Show error message
        self.add_message("assistant", f"Error: {error_message}")

    def handle_command(self, command):
        self.input_field.setText(command)
        self.send_message()

    def toggle_debug(self, enabled):
        self.debug_mode = enabled

    def add_message(self, role, content, tool_logs=None):
        # Add to internal message list
        message = {"role": role, "content": content}
        if tool_logs:
            message["tool_logs"] = tool_logs
        self.messages.append(message)

        # Add to UI
        self.chat_widget.add_message(role, content, tool_logs)

def main():
    app = QApplication(sys.argv)

    # Apply fusion style for a modern look
    app.setStyle(QStyleFactory.create("Fusion"))

    # Set application-wide dark palette
    dark_palette = app.palette()
    dark_palette.setColor(QPalette.ColorRole.Window, QColor(40, 44, 52))
    dark_palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.Base, QColor(60, 64, 73))
    dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(45, 49, 58))
    dark_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))

    app.setPalette(dark_palette)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()