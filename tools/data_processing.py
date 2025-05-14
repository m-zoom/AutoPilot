"""
Data Processing Tools

Tools for processing CSV files, database operations, data visualization,
and regular expression operations.
"""

import sys

import os
import logging
import tempfile
from typing import Optional, Dict, Any, List
from langchain.tools import BaseTool
from langchain.callbacks.manager import CallbackManagerForToolRun

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


logger = logging.getLogger(__name__)

class CSVProcessingTool(BaseTool):
    """Tool for reading, writing, and manipulating CSV files."""
    
    name: str = "csv_processing"
    description: str = """
    Reads, writes, and manipulates CSV files.
    
    Input should be a JSON object with the following structure:
    For reading: {"action": "read", "file_path": "data.csv", "limit": 10}
    For writing: {"action": "write", "file_path": "data.csv", "data": [["col1", "col2"], ["val1", "val2"], ...]}
    For filtering: {"action": "filter", "file_path": "data.csv", "column": "Age", "condition": ">", "value": 30}
    For sorting: {"action": "sort", "file_path": "data.csv", "column": "Name", "ascending": true}
    
    Returns the processed data or a success message.
    
    Example: {"action": "read", "file_path": "C:\\Data\\employees.csv", "limit": 5}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Process CSV files."""
        try:
            import json
            import csv
            import io
            
            params = json.loads(input_str)
            
            action = params.get("action", "").lower()
            file_path = params.get("file_path", "")
            
            if not action:
                return "Error: Missing action parameter"
                
            if not file_path:
                return "Error: Missing file_path parameter"
            
            if action == "read":
                # Read CSV file
                limit = params.get("limit")
                
                try:
                    with open(file_path, 'r', newline='', encoding='utf-8-sig') as f:
                        reader = csv.reader(f)
                        headers = next(reader)
                        
                        if limit:
                            try:
                                limit = int(limit)
                                rows = [headers] + [row for _, row in zip(range(limit), reader)]
                            except ValueError:
                                return "Error: Limit must be a number"
                        else:
                            rows = [headers] + list(reader)
                        
                        # Format as a table
                        column_widths = [max(len(str(row[i])) for row in rows) for i in range(len(headers))]
                        
                        output = []
                        # Header row
                        header_row = " | ".join(str(headers[i]).ljust(column_widths[i]) for i in range(len(headers)))
                        output.append(header_row)
                        output.append("-" * len(header_row))
                        
                        # Data rows
                        for row in rows[1:]:
                            output.append(" | ".join(str(row[i]).ljust(column_widths[i]) for i in range(len(row))))
                        
                        total_rows = len(rows) - 1  # Subtract header row
                        output.append(f"\nTotal: {total_rows} row(s)")
                        
                        return "\n".join(output)
                
                except FileNotFoundError:
                    return f"Error: CSV file not found: {file_path}"
                except Exception as e:
                    return f"Error reading CSV file: {str(e)}"
            
            elif action == "write":
                # Write to CSV file
                data = params.get("data")
                
                if not data:
                    return "Error: Missing data parameter"
                
                try:
                    # Ensure the directory exists
                    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
                    
                    with open(file_path, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        for row in data:
                            writer.writerow(row)
                    
                    return f"Successfully wrote {len(data)} rows to {file_path}"
                
                except Exception as e:
                    return f"Error writing to CSV file: {str(e)}"
            
            elif action == "filter":
                # Filter CSV data
                column = params.get("column")
                condition = params.get("condition")
                value = params.get("value")
                
                if not column:
                    return "Error: Missing column parameter"
                    
                if not condition:
                    return "Error: Missing condition parameter"
                    
                if value is None:
                    return "Error: Missing value parameter"
                
                # Valid conditions
                valid_conditions = ["=", "==", "!=", ">", "<", ">=", "<=", "contains", "startswith", "endswith"]
                
                if condition not in valid_conditions:
                    return f"Error: Invalid condition. Valid conditions are: {', '.join(valid_conditions)}"
                
                try:
                    with open(file_path, 'r', newline='', encoding='utf-8-sig') as f:
                        reader = csv.reader(f)
                        headers = next(reader)
                        
                        # Find the column index
                        try:
                            col_index = headers.index(column)
                        except ValueError:
                            return f"Error: Column '{column}' not found in the CSV file"
                        
                        # Filter the rows
                        filtered_rows = [headers]
                        
                        for row in reader:
                            if len(row) <= col_index:
                                continue  # Skip rows with missing columns
                            
                            cell_value = row[col_index]
                            
                            # Try to convert to number for numeric comparisons
                            try:
                                if condition in [">", "<", ">=", "<="]:
                                    cell_num = float(cell_value)
                                    value_num = float(value)
                                    
                                    if condition == ">" and cell_num > value_num:
                                        filtered_rows.append(row)
                                    elif condition == "<" and cell_num < value_num:
                                        filtered_rows.append(row)
                                    elif condition == ">=" and cell_num >= value_num:
                                        filtered_rows.append(row)
                                    elif condition == "<=" and cell_num <= value_num:
                                        filtered_rows.append(row)
                                else:
                                    # String-based comparisons
                                    if condition in ["=", "=="] and str(cell_value) == str(value):
                                        filtered_rows.append(row)
                                    elif condition == "!=" and str(cell_value) != str(value):
                                        filtered_rows.append(row)
                                    elif condition == "contains" and str(value) in str(cell_value):
                                        filtered_rows.append(row)
                                    elif condition == "startswith" and str(cell_value).startswith(str(value)):
                                        filtered_rows.append(row)
                                    elif condition == "endswith" and str(cell_value).endswith(str(value)):
                                        filtered_rows.append(row)
                            except ValueError:
                                # If conversion fails, fall back to string comparison
                                if condition in ["=", "=="] and str(cell_value) == str(value):
                                    filtered_rows.append(row)
                                elif condition == "!=" and str(cell_value) != str(value):
                                    filtered_rows.append(row)
                                elif condition == "contains" and str(value) in str(cell_value):
                                    filtered_rows.append(row)
                                elif condition == "startswith" and str(cell_value).startswith(str(value)):
                                    filtered_rows.append(row)
                                elif condition == "endswith" and str(cell_value).endswith(str(value)):
                                    filtered_rows.append(row)
                        
                        # Format as a table
                        if len(filtered_rows) == 1:
                            return f"No rows match the filter condition: {column} {condition} {value}"
                        
                        column_widths = [max(len(str(row[i])) for row in filtered_rows) for i in range(len(headers))]
                        
                        output = []
                        # Header row
                        header_row = " | ".join(str(headers[i]).ljust(column_widths[i]) for i in range(len(headers)))
                        output.append(header_row)
                        output.append("-" * len(header_row))
                        
                        # Data rows
                        for row in filtered_rows[1:]:
                            output.append(" | ".join(str(row[i]).ljust(column_widths[i]) for i in range(len(row))))
                        
                        filtered_count = len(filtered_rows) - 1  # Subtract header row
                        output.append(f"\nFiltered rows: {filtered_count}")
                        
                        return "\n".join(output)
                
                except FileNotFoundError:
                    return f"Error: CSV file not found: {file_path}"
                except Exception as e:
                    return f"Error filtering CSV file: {str(e)}"
            
            elif action == "sort":
                # Sort CSV data
                column = params.get("column")
                ascending = params.get("ascending", True)
                
                if not column:
                    return "Error: Missing column parameter"
                
                try:
                    with open(file_path, 'r', newline='', encoding='utf-8-sig') as f:
                        reader = csv.reader(f)
                        headers = next(reader)
                        
                        # Find the column index
                        try:
                            col_index = headers.index(column)
                        except ValueError:
                            return f"Error: Column '{column}' not found in the CSV file"
                        
                        # Read all rows
                        rows = list(reader)
                        
                        # Sort the rows
                        def sort_key(row):
                            if len(row) <= col_index:
                                return "" if ascending else "z" * 100  # Place rows with missing columns at start or end
                            
                            val = row[col_index]
                            
                            # Try to convert to number for numeric sorting
                            try:
                                return float(val)
                            except ValueError:
                                return val
                        
                        rows.sort(key=sort_key, reverse=not ascending)
                        
                        # Format as a table
                        all_rows = [headers] + rows
                        column_widths = [max(len(str(row[i])) for row in all_rows if i < len(row)) for i in range(len(headers))]
                        
                        output = []
                        # Header row
                        header_row = " | ".join(str(headers[i]).ljust(column_widths[i]) for i in range(len(headers)))
                        output.append(header_row)
                        output.append("-" * len(header_row))
                        
                        # Data rows
                        for row in rows:
                            padded_row = [str(row[i]).ljust(column_widths[i]) if i < len(row) else " " * column_widths[i] for i in range(len(headers))]
                            output.append(" | ".join(padded_row))
                        
                        order = "ascending" if ascending else "descending"
                        output.append(f"\nSorted {len(rows)} rows by '{column}' in {order} order")
                        
                        return "\n".join(output)
                
                except FileNotFoundError:
                    return f"Error: CSV file not found: {file_path}"
                except Exception as e:
                    return f"Error sorting CSV file: {str(e)}"
            
            else:
                return f"Error: Unknown action '{action}'. Valid actions are: read, write, filter, sort"
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except Exception as e:
            logger.error(f"Error in CSV processing: {str(e)}")
            return f"Error in CSV processing: {str(e)}"


class DatabaseQueryTool(BaseTool):
    """Tool for executing database queries."""
    
    name: str = "database_query"
    description: str = """
    Executes SQL queries on various database types.
    
    Input should be a JSON object with the following structure:
    {
        "type": "sqlite/mysql/postgresql",
        "connection": {
            "host": "localhost",
            "port": 3306,
            "database": "db_name",
            "username": "user",
            "password": "password",
            "file_path": "path_to_sqlite_file.db"
        },
        "query": "SELECT * FROM users LIMIT 10",
        "params": [param1, param2]
    }
    
    Connection parameters vary by database type. For SQLite, only file_path is required.
    Params is optional and used for parameterized queries.
    
    Returns the query results or an error.
    
    Example: {"type": "sqlite", "connection": {"file_path": "C:\\Data\\database.db"}, "query": "SELECT * FROM users LIMIT 5"}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute database queries."""
        try:
            import json
            
            params = json.loads(input_str)
            
            db_type = params.get("type", "").lower()
            connection_params = params.get("connection", {})
            query = params.get("query", "")
            query_params = params.get("params", [])
            
            if not db_type:
                return "Error: Missing database type parameter"
                
            if not connection_params:
                return "Error: Missing connection parameters"
                
            if not query:
                return "Error: Missing query parameter"
            
            # Restrict query to SELECT statements for safety
            if not query.strip().upper().startswith("SELECT"):
                return "Error: Only SELECT queries are allowed for security reasons"
            
            # Execute the query based on database type
            if db_type == "sqlite":
                return self._sqlite_query(connection_params, query, query_params)
            elif db_type == "mysql":
                return self._mysql_query(connection_params, query, query_params)
            elif db_type == "postgresql":
                return self._postgresql_query(connection_params, query, query_params)
            else:
                return f"Error: Unsupported database type '{db_type}'. Supported types are: sqlite, mysql, postgresql"
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except ImportError as e:
            return f"Error: Required module not installed: {str(e)}"
        except Exception as e:
            logger.error(f"Error in database query: {str(e)}")
            return f"Error in database query: {str(e)}"
    
    def _sqlite_query(self, connection_params: Dict[str, Any], query: str, params: List) -> str:
        """Execute a query on a SQLite database."""
        try:
            import sqlite3
            
            file_path = connection_params.get("file_path", "")
            
            if not file_path:
                return "Error: Missing file_path parameter for SQLite connection"
                
            if not os.path.exists(file_path):
                return f"Error: SQLite database file not found: {file_path}"
            
            # Connect to the database
            conn = sqlite3.connect(file_path)
            try:
                cursor = conn.cursor()
                
                # Execute the query
                cursor.execute(query, params)
                
                # Get column names
                column_names = [description[0] for description in cursor.description]
                
                # Fetch all rows
                rows = cursor.fetchall()
                
                # Format as a table
                if not rows:
                    return "Query returned no results"
                
                # Convert all values to strings
                str_rows = [[str(cell) for cell in row] for row in rows]
                all_rows = [column_names] + str_rows
                
                # Get maximum width for each column
                column_widths = [max(len(row[i]) for row in all_rows) for i in range(len(column_names))]
                
                output = []
                # Header row
                header_row = " | ".join(column_names[i].ljust(column_widths[i]) for i in range(len(column_names)))
                output.append(header_row)
                output.append("-" * len(header_row))
                
                # Data rows
                for row in str_rows:
                    output.append(" | ".join(row[i].ljust(column_widths[i]) for i in range(len(row))))
                
                output.append(f"\nTotal: {len(rows)} row(s)")
                
                return "\n".join(output)
            
            finally:
                conn.close()
        
        except sqlite3.Error as e:
            return f"SQLite error: {str(e)}"
        except Exception as e:
            return f"Error executing SQLite query: {str(e)}"
    
    def _mysql_query(self, connection_params: Dict[str, Any], query: str, params: List) -> str:
        """Execute a query on a MySQL database."""
        try:
            import pymysql
            
            host = connection_params.get("host", "localhost")
            port = connection_params.get("port", 3306)
            database = connection_params.get("database", "")
            username = connection_params.get("username", "")
            password = connection_params.get("password", "")
            
            if not database:
                return "Error: Missing database parameter for MySQL connection"
                
            if not username:
                return "Error: Missing username parameter for MySQL connection"
            
            # Connect to the database
            conn = pymysql.connect(
                host=host,
                port=port,
                user=username,
                password=password,
                database=database
            )
            
            try:
                cursor = conn.cursor()
                
                # Execute the query
                cursor.execute(query, params)
                
                # Get column names
                column_names = [column[0] for column in cursor.description]
                
                # Fetch all rows
                rows = cursor.fetchall()
                
                # Format as a table
                if not rows:
                    return "Query returned no results"
                
                # Convert all values to strings
                str_rows = [[str(cell) for cell in row] for row in rows]
                all_rows = [column_names] + str_rows
                
                # Get maximum width for each column
                column_widths = [max(len(row[i]) for row in all_rows) for i in range(len(column_names))]
                
                output = []
                # Header row
                header_row = " | ".join(column_names[i].ljust(column_widths[i]) for i in range(len(column_names)))
                output.append(header_row)
                output.append("-" * len(header_row))
                
                # Data rows
                for row in str_rows:
                    output.append(" | ".join(row[i].ljust(column_widths[i]) for i in range(len(row))))
                
                output.append(f"\nTotal: {len(rows)} row(s)")
                
                return "\n".join(output)
            
            finally:
                conn.close()
        
        except pymysql.Error as e:
            return f"MySQL error: {str(e)}"
        except ImportError:
            return "Error: PyMySQL module is not installed. Please install it with 'pip install pymysql'"
        except Exception as e:
            return f"Error executing MySQL query: {str(e)}"
    
    def _postgresql_query(self, connection_params: Dict[str, Any], query: str, params: List) -> str:
        """Execute a query on a PostgreSQL database."""
        try:
            import psycopg2
            
            host = connection_params.get("host", "localhost")
            port = connection_params.get("port", 5432)
            database = connection_params.get("database", "")
            username = connection_params.get("username", "")
            password = connection_params.get("password", "")
            
            if not database:
                return "Error: Missing database parameter for PostgreSQL connection"
                
            if not username:
                return "Error: Missing username parameter for PostgreSQL connection"
            
            # Connect to the database
            conn = psycopg2.connect(
                host=host,
                port=port,
                dbname=database,
                user=username,
                password=password
            )
            
            try:
                cursor = conn.cursor()
                
                # Execute the query
                cursor.execute(query, params)
                
                # Get column names
                column_names = [desc[0] for desc in cursor.description]
                
                # Fetch all rows
                rows = cursor.fetchall()
                
                # Format as a table
                if not rows:
                    return "Query returned no results"
                
                # Convert all values to strings
                str_rows = [[str(cell) for cell in row] for row in rows]
                all_rows = [column_names] + str_rows
                
                # Get maximum width for each column
                column_widths = [max(len(row[i]) for row in all_rows) for i in range(len(column_names))]
                
                output = []
                # Header row
                header_row = " | ".join(column_names[i].ljust(column_widths[i]) for i in range(len(column_names)))
                output.append(header_row)
                output.append("-" * len(header_row))
                
                # Data rows
                for row in str_rows:
                    output.append(" | ".join(row[i].ljust(column_widths[i]) for i in range(len(row))))
                
                output.append(f"\nTotal: {len(rows)} row(s)")
                
                return "\n".join(output)
            
            finally:
                conn.close()
        
        except psycopg2.Error as e:
            return f"PostgreSQL error: {str(e)}"
        except ImportError:
            return "Error: psycopg2 module is not installed. Please install it with 'pip install psycopg2'"
        except Exception as e:
            return f"Error executing PostgreSQL query: {str(e)}"


class DataVisualizationTool(BaseTool):
    """Tool for generating charts and graphs."""
    
    name: str = "data_visualization"
    description: str = """
    Generates various charts and graphs from data.
    
    Input should be a JSON object with the following structure:
    {
        "type": "bar/line/pie/scatter/histogram",
        "data": {
            "labels": ["Label1", "Label2", ...],
            "datasets": [
                {
                    "label": "Dataset1",
                    "data": [1, 2, 3, ...]
                },
                ...
            ]
        },
        "options": {
            "title": "Chart Title",
            "xlabel": "X Axis Label",
            "ylabel": "Y Axis Label"
        },
        "output": "path_to_save.png"
    }
    
    Returns the path to the saved chart or an error.
    
    Example: {"type": "bar", "data": {"labels": ["A", "B", "C"], "datasets": [{"label": "Values", "data": [1, 2, 3]}]}, "options": {"title": "Example Chart"}, "output": "C:\\Charts\\chart.png"}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Generate charts and graphs."""
        try:
            import json
            import matplotlib.pyplot as plt
            import numpy as np
            
            params = json.loads(input_str)
            
            chart_type = params.get("type", "").lower()
            data = params.get("data", {})
            options = params.get("options", {})
            output_path = params.get("output", "")
            
            if not chart_type:
                return "Error: Missing chart type parameter"
                
            if not data:
                return "Error: Missing data parameter"
                
            if not output_path:
                return "Error: Missing output parameter"
            
            # Check if the chart type is supported
            supported_types = ["bar", "line", "pie", "scatter", "histogram"]
            if chart_type not in supported_types:
                return f"Error: Unsupported chart type '{chart_type}'. Supported types are: {', '.join(supported_types)}"
            
            # Extract data
            labels = data.get("labels", [])
            datasets = data.get("datasets", [])
            
            if not datasets:
                return "Error: No datasets provided"
            
            # Extract options
            title = options.get("title", "")
            xlabel = options.get("xlabel", "")
            ylabel = options.get("ylabel", "")
            
            # Create the figure
            plt.figure(figsize=(10, 6))
            
            if chart_type == "bar":
                # Bar chart
                width = 0.8 / len(datasets)
                x = np.arange(len(labels))
                
                for i, dataset in enumerate(datasets):
                    data_values = dataset.get("data", [])
                    label = dataset.get("label", f"Dataset {i+1}")
                    
                    plt.bar(x + i * width - (len(datasets) - 1) * width / 2, data_values, width, label=label)
                
                plt.xticks(x, labels)
                
            elif chart_type == "line":
                # Line chart
                for i, dataset in enumerate(datasets):
                    data_values = dataset.get("data", [])
                    label = dataset.get("label", f"Dataset {i+1}")
                    
                    if len(labels) == len(data_values):
                        plt.plot(labels, data_values, marker='o', label=label)
                    else:
                        plt.plot(data_values, marker='o', label=label)
                
            elif chart_type == "pie":
                # Pie chart
                # Use only the first dataset for a pie chart
                dataset = datasets[0]
                data_values = dataset.get("data", [])
                
                if len(labels) != len(data_values):
                    return "Error: For pie charts, the number of labels must match the number of data points"
                
                plt.pie(data_values, labels=labels, autopct='%1.1f%%', startangle=90)
                plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
                
            elif chart_type == "scatter":
                # Scatter plot
                for i, dataset in enumerate(datasets):
                    data_values = dataset.get("data", [])
                    label = dataset.get("label", f"Dataset {i+1}")
                    
                    # For scatter plots, data should be pairs of [x, y] coordinates
                    x_values = [point[0] if isinstance(point, list) and len(point) >= 2 else point for point in data_values]
                    y_values = [point[1] if isinstance(point, list) and len(point) >= 2 else i for i, point in enumerate(data_values)]
                    
                    plt.scatter(x_values, y_values, label=label)
                
            elif chart_type == "histogram":
                # Histogram
                for i, dataset in enumerate(datasets):
                    data_values = dataset.get("data", [])
                    label = dataset.get("label", f"Dataset {i+1}")
                    bins = options.get("bins", 10)
                    
                    plt.hist(data_values, bins=bins, alpha=0.7, label=label)
            
            # Add labels and title
            if title:
                plt.title(title)
            if xlabel:
                plt.xlabel(xlabel)
            if ylabel:
                plt.ylabel(ylabel)
            
            # Add legend if multiple datasets
            if len(datasets) > 1 or chart_type in ["line", "scatter"]:
                plt.legend()
            
            # Save the chart
            try:
                # Ensure the directory exists
                os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                
                plt.tight_layout()
                plt.savefig(output_path)
                plt.close()
                
                return f"Chart successfully saved to {output_path}"
            except Exception as e:
                return f"Error saving chart: {str(e)}"
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except ImportError as e:
            return f"Error: Required module not installed: {str(e)}"
        except Exception as e:
            logger.error(f"Error generating chart: {str(e)}")
            return f"Error generating chart: {str(e)}"


class RegexSearchReplaceTool(BaseTool):
    """Tool for finding and replacing text using regex patterns."""
    
    name: str = "regex_search_replace"
    description: str = """
    Finds and replaces text in files or strings using regular expression patterns.
    
    Input should be a JSON object with the following structure:
    For file operations: {"source": "file", "file_path": "path.txt", "pattern": "regex_pattern", "replacement": "replacement_text", "flags": "ig"}
    For string operations: {"source": "string", "text": "input text", "pattern": "regex_pattern", "replacement": "replacement_text", "flags": "ig"}
    
    Flags are optional regex flags: i (case-insensitive), g (global), m (multiline), s (dotall).
    
    Returns the modified text, match information, or an error.
    
    Example: {"source": "string", "text": "Hello world", "pattern": "world", "replacement": "Python"}
    """
    
    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Find and replace text using regex patterns."""
        try:
            import json
            import re
            
            params = json.loads(input_str)
            
            source = params.get("source", "").lower()
            pattern = params.get("pattern", "")
            replacement = params.get("replacement")
            flags_str = params.get("flags", "")
            
            if not source:
                return "Error: Missing source parameter"
                
            if not pattern:
                return "Error: Missing pattern parameter"
            
            # Parse regex flags
            flags = 0
            if 'i' in flags_str:
                flags |= re.IGNORECASE
            if 'm' in flags_str:
                flags |= re.MULTILINE
            if 's' in flags_str:
                flags |= re.DOTALL
            
            # Global flag handling will be done manually
            global_replace = 'g' in flags_str
            
            if source == "file":
                file_path = params.get("file_path", "")
                
                if not file_path:
                    return "Error: Missing file_path parameter for file operations"
                    
                if not os.path.exists(file_path):
                    return f"Error: File not found: {file_path}"
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()
                    
                    # Search mode if no replacement is provided
                    if replacement is None:
                        matches = re.finditer(pattern, content, flags)
                        
                        match_list = []
                        for i, match in enumerate(matches):
                            match_list.append({
                                "match_num": i + 1,
                                "start": match.start(),
                                "end": match.end(),
                                "text": match.group(),
                                "groups": match.groups() if match.groups() else []
                            })
                        
                        if not match_list:
                            return f"No matches found for pattern '{pattern}' in file {file_path}"
                        
                        # Format the output
                        output = [f"Found {len(match_list)} matches for pattern '{pattern}' in file {file_path}:"]
                        
                        for match in match_list:
                            output.append(f"Match {match['match_num']}: {match['text']} (positions {match['start']}-{match['end']})")
                            
                            if match['groups']:
                                output.append("  Groups:")
                                for i, group in enumerate(match['groups']):
                                    output.append(f"    {i+1}: {group}")
                        
                        return "\n".join(output)
                    
                    # Replace mode
                    if global_replace:
                        new_content = re.sub(pattern, replacement, content, flags=flags)
                        
                        # Count replacements
                        matches = re.findall(pattern, content, flags)
                        num_replacements = len(matches)
                    else:
                        # Replace only the first occurrence
                        new_content = re.sub(pattern, replacement, content, count=1, flags=flags)
                        
                        # Check if a replacement was made
                        if new_content == content:
                            num_replacements = 0
                        else:
                            num_replacements = 1
                    
                    # Save the modified content
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    
                    if num_replacements == 0:
                        return f"No replacements made - pattern '{pattern}' not found in file {file_path}"
                    else:
                        return f"Made {num_replacements} replacement(s) in file {file_path}"
                
                except Exception as e:
                    return f"Error processing file: {str(e)}"
            
            elif source == "string":
                text = params.get("text", "")
                
                if not text:
                    return "Error: Missing text parameter for string operations"
                
                # Search mode if no replacement is provided
                if replacement is None:
                    matches = re.finditer(pattern, text, flags)
                    
                    match_list = []
                    for i, match in enumerate(matches):
                        match_list.append({
                            "match_num": i + 1,
                            "start": match.start(),
                            "end": match.end(),
                            "text": match.group(),
                            "groups": match.groups() if match.groups() else []
                        })
                    
                    if not match_list:
                        return f"No matches found for pattern '{pattern}'"
                    
                    # Format the output
                    output = [f"Found {len(match_list)} matches for pattern '{pattern}':"]
                    
                    for match in match_list:
                        output.append(f"Match {match['match_num']}: {match['text']} (positions {match['start']}-{match['end']})")
                        
                        if match['groups']:
                            output.append("  Groups:")
                            for i, group in enumerate(match['groups']):
                                output.append(f"    {i+1}: {group}")
                    
                    return "\n".join(output)
                
                # Replace mode
                if global_replace:
                    new_text = re.sub(pattern, replacement, text, flags=flags)
                    
                    # Count replacements
                    matches = re.findall(pattern, text, flags)
                    num_replacements = len(matches)
                else:
                    # Replace only the first occurrence
                    new_text = re.sub(pattern, replacement, text, count=1, flags=flags)
                    
                    # Check if a replacement was made
                    if new_text == text:
                        num_replacements = 0
                    else:
                        num_replacements = 1
                
                if num_replacements == 0:
                    return f"No replacements made - pattern '{pattern}' not found"
                else:
                    return f"Made {num_replacements} replacement(s):\n\nOriginal:\n{text}\n\nModified:\n{new_text}"
            
            else:
                return f"Error: Invalid source '{source}'. Use 'file' or 'string'"
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON input"
        except re.error as e:
            return f"Regular expression error: {str(e)}"
        except Exception as e:
            logger.error(f"Error in regex operation: {str(e)}")
            return f"Error in regex operation: {str(e)}"
