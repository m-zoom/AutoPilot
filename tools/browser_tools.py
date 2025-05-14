"""
Tools for the AI agent to interact with web browsers.
Includes operations for opening browsers, visiting websites, and interacting with web pages.
"""

import sys

import os
import logging
import webbrowser
import requests
from typing import Optional, Dict, Any, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from langchain.callbacks.manager import CallbackManagerForToolRun
from langchain.tools.base import BaseTool

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

try:
    import html2text
    HTML2TEXT_AVAILABLE = True
except ImportError:
    logger.warning("html2text not available. Text conversion will be limited.")
    HTML2TEXT_AVAILABLE = False

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    logger.warning("Selenium not available. Advanced browser interactions will be limited.")
    SELENIUM_AVAILABLE = False


class OpenBrowserTool(BaseTool):
    """Tool for opening the default web browser."""
    
    name: str = "open_browser"
    description: str = """
    Opens the default web browser.
    
    No input is required.
    Returns a confirmation message or error.
    """
    
    def _run(self, _: str = "", run_manager: Optional[CallbackManagerForToolRun] = None, *args, **kwargs) -> str:
        """Open the default web browser."""
        try:
            webbrowser.open(resource_path('about:blank'))
            return "Browser opened successfully."
        except Exception as e:
            logger.error(f"Error opening browser: {str(e)}")
            return f"Error opening browser: {str(e)}"


class VisitWebsiteTool(BaseTool):
    """Tool for visiting a website in the default browser."""
    
    name: str = "visit_website"
    description: str = """
    Visits a website in the default browser.
    
    Input should be the URL of the website to visit.
    Returns a confirmation message or error.
    
    Example: "https://www.example.com"
    """
    
    def _run(self, url: str, run_manager: Optional[CallbackManagerForToolRun] = None, *args, **kwargs) -> str:
        """Visit a website."""
        try:
            # Validate the URL
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
                
            # Try to validate the URL format
            parsed_url = urlparse(url)
            if not parsed_url.netloc:
                return f"Invalid URL format: {url}"
            
            # Open the URL in the default browser
            webbrowser.open(url)
            return f"Opened website: {url}"
        except Exception as e:
            logger.error(f"Error visiting website: {str(e)}")
            return f"Error visiting website: {str(e)}"


class GetWebpageContentTool(BaseTool):
    """Tool for getting the content of a webpage and converting it to readable text."""
    
    name: str = "get_webpage_content"
    description: str = """
    Gets the content of a webpage and converts it to readable text.
    
    Input should be the URL of the webpage to get content from.
    Returns the text content of the webpage or error message.
    
    Example: "https://www.example.com"
    """
    
    def _run(self, url: str, run_manager: Optional[CallbackManagerForToolRun] = None, *args, **kwargs) -> str:
        """Get webpage content as readable text."""
        try:
            # Validate the URL
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
                
            # Try to validate the URL format
            parsed_url = urlparse(url)
            if not parsed_url.netloc:
                return f"Invalid URL format: {url}"
            
            # Fetch the webpage content
            response = requests.get(url, timeout=10)
            response.raise_for_status()  # Raise exception for 4XX/5XX responses
            html_content = response.text
            
            # Convert HTML to readable text
            if HTML2TEXT_AVAILABLE:
                h = html2text.HTML2Text()
                h.ignore_links = False
                h.ignore_images = True
                h.ignore_emphasis = True
                readable_text = h.handle(html_content)
            else:
                # Fallback to BeautifulSoup
                soup = BeautifulSoup(html_content, 'html.parser')
                readable_text = soup.get_text(separator='\n', strip=True)
            
            # Truncate if too long
            max_length = 2000
            if len(readable_text) > max_length:
                truncated_text = readable_text[:max_length]
                remaining_chars = len(readable_text) - max_length
                return f"{truncated_text}\n\n[Content truncated. {remaining_chars} more characters not shown.]"
            else:
                return readable_text
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching webpage: {str(e)}")
            return f"Error fetching webpage: {str(e)}"
        except Exception as e:
            logger.error(f"Error processing webpage content: {str(e)}")
            return f"Error processing webpage content: {str(e)}"


class ClickWebpageElementTool(BaseTool):
    """Tool for clicking an element on a webpage."""
    
    name: str = "click_webpage_element"
    description: str = """
    Clicks an element on a webpage using a CSS selector or XPath.
    Note: This tool requires Selenium to be installed.
    
    Input should be a JSON object with:
    - 'url' (optional): URL of the webpage if not already on the page
    - 'selector': CSS selector or XPath to identify the element to click
    - 'selector_type' (optional): 'css' (default) or 'xpath'
    
    Example: {"url": "https://example.com", "selector": "button.download", "selector_type": "css"}
    
    Returns success/failure message.
    """
    
    def _run(self, element_info_str: str, run_manager: Optional[CallbackManagerForToolRun] = None, *args, **kwargs) -> str:
        """Click an element on a webpage."""
        if not SELENIUM_AVAILABLE:
            return "This tool requires Selenium to be installed. Please install Selenium to use this functionality."
        
        try:
            import json
            try:
                element_info = json.loads(element_info_str)
            except json.JSONDecodeError:
                # Try to extract info from plain text
                import re
                url_match = re.search(r"url['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]", element_info_str)
                selector_match = re.search(r"selector['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]", element_info_str)
                type_match = re.search(r"selector_type['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]", element_info_str)
                
                if selector_match:
                    element_info = {
                        "selector": selector_match.group(1)
                    }
                    if url_match:
                        element_info["url"] = url_match.group(1)
                    if type_match:
                        element_info["selector_type"] = type_match.group(1)
                else:
                    return "Error: Invalid input format. Expected JSON with 'selector' and optional 'url' and 'selector_type'"
            
            if not isinstance(element_info, dict):
                return "Error: Input must be a dictionary/JSON object"
            
            if "selector" not in element_info:
                return "Error: Input must contain 'selector'"
            
            url = element_info.get("url", None)
            selector = element_info["selector"]
            selector_type = element_info.get("selector_type", "css").lower()
            
            if selector_type not in ["css", "xpath"]:
                return "Error: selector_type must be 'css' or 'xpath'"
            
            # Initialize Selenium WebDriver
            options = Options()
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            
            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(30)
            
            try:
                # Navigate to the URL if provided
                if url:
                    if not url.startswith(('http://', 'https://')):
                        url = 'https://' + url
                    driver.get(url)
                
                # Set up the selector method
                by_method = By.CSS_SELECTOR if selector_type == "css" else By.XPATH
                
                # Wait for the element to be present and click it
                element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((by_method, selector))
                )
                
                # Scroll the element into view
                driver.execute_script("arguments[0].scrollIntoView(true);", element)
                
                # Click the element
                element.click()
                
                # Get the current URL after the click
                current_url = driver.current_url
                
                return f"Successfully clicked element with selector '{selector}'. Current URL: {current_url}"
                
            except TimeoutException:
                return f"Timed out waiting for element with selector: {selector}"
            except NoSuchElementException:
                return f"Element not found with selector: {selector}"
            except Exception as e:
                return f"Error during browser interaction: {str(e)}"
            finally:
                driver.quit()
                
        except Exception as e:
            logger.error(f"Error with click_webpage_element: {str(e)}")
            return f"Error with click_webpage_element: {str(e)}"


class FillWebpageFormTool(BaseTool):
    """Tool for filling a form field on a webpage."""
    
    name: str = "fill_webpage_form"
    description: str = """
    Fills a form field on a webpage with a value.
    Note: This tool requires Selenium to be installed.
    
    Input should be a JSON object with:
    - 'url' (optional): URL of the webpage if not already on the page
    - 'field_selector': CSS selector or XPath to identify the form field
    - 'selector_type' (optional): 'css' (default) or 'xpath'
    - 'value': The value to fill in the form field
    
    Example: {"url": "https://example.com", "field_selector": "input[name='username']", "value": "john_doe", "selector_type": "css"}
    
    Returns success/failure message.
    """
    
    def _run(self, form_info_str: str, run_manager: Optional[CallbackManagerForToolRun] = None, *args, **kwargs) -> str:
        """Fill a form field on a webpage."""
        if not SELENIUM_AVAILABLE:
            return "This tool requires Selenium to be installed. Please install Selenium to use this functionality."
        
        try:
            import json
            try:
                form_info = json.loads(form_info_str)
            except json.JSONDecodeError:
                # Try to extract info from plain text
                import re
                url_match = re.search(r"url['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]", form_info_str)
                selector_match = re.search(r"field_selector['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]", form_info_str)
                type_match = re.search(r"selector_type['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]", form_info_str)
                value_match = re.search(r"value['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]", form_info_str)
                
                if selector_match and value_match:
                    form_info = {
                        "field_selector": selector_match.group(1),
                        "value": value_match.group(1)
                    }
                    if url_match:
                        form_info["url"] = url_match.group(1)
                    if type_match:
                        form_info["selector_type"] = type_match.group(1)
                else:
                    return "Error: Invalid input format. Expected JSON with 'field_selector', 'value', and optional 'url' and 'selector_type'"
            
            if not isinstance(form_info, dict):
                return "Error: Input must be a dictionary/JSON object"
            
            if "field_selector" not in form_info or "value" not in form_info:
                return "Error: Input must contain 'field_selector' and 'value'"
            
            url = form_info.get("url", None)
            field_selector = form_info["field_selector"]
            value = form_info["value"]
            selector_type = form_info.get("selector_type", "css").lower()
            
            if selector_type not in ["css", "xpath"]:
                return "Error: selector_type must be 'css' or 'xpath'"
            
            # Initialize Selenium WebDriver
            options = Options()
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            
            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(30)
            
            try:
                # Navigate to the URL if provided
                if url:
                    if not url.startswith(('http://', 'https://')):
                        url = 'https://' + url
                    driver.get(url)
                
                # Set up the selector method
                by_method = By.CSS_SELECTOR if selector_type == "css" else By.XPATH
                
                # Wait for the element to be present
                field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((by_method, field_selector))
                )
                
                # Scroll the element into view
                driver.execute_script("arguments[0].scrollIntoView(true);", field)
                
                # Clear the field and fill it with the value
                field.clear()
                field.send_keys(value)
                
                return f"Successfully filled form field '{field_selector}' with value '{value}'"
                
            except TimeoutException:
                return f"Timed out waiting for form field with selector: {field_selector}"
            except NoSuchElementException:
                return f"Form field not found with selector: {field_selector}"
            except Exception as e:
                return f"Error during form filling: {str(e)}"
            finally:
                driver.quit()
                
        except Exception as e:
            logger.error(f"Error with fill_webpage_form: {str(e)}")
            return f"Error with fill_webpage_form: {str(e)}"