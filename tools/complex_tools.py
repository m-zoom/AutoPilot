"""
Complex tools for the AI agent to perform advanced operations.
Includes website navigation, content extraction, and file upload capabilities.
"""

import sys

import os
import json
import logging
import time
import re
import base64
import mimetypes
from typing import List, Dict, Any, Optional, Union, Tuple
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
    import requests
    from bs4 import BeautifulSoup
    import html2text
    WEB_TOOLS_AVAILABLE = True
except ImportError:
    logger.warning("Web tools dependencies not available. Web operations will be limited.")
    WEB_TOOLS_AVAILABLE = False

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import (
        TimeoutException, NoSuchElementException, WebDriverException,
        ElementClickInterceptedException, StaleElementReferenceException
    )
    SELENIUM_AVAILABLE = True
except ImportError:
    logger.warning("Selenium not available. Advanced web interactions will be limited.")
    SELENIUM_AVAILABLE = False


class WebDriverManager:
    """A singleton class to manage the web driver instance."""
    
    _instance = None
    _driver = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WebDriverManager, cls).__new__(cls)
            cls._instance._initialize_driver()
        return cls._instance
    
    def _initialize_driver(self):
        """Initialize the web driver if Selenium is available."""
        if not SELENIUM_AVAILABLE:
            logger.warning("Selenium not available. Advanced web interactions will be limited.")
            return
        
        try:
            options = Options()
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            
            self._driver = webdriver.Chrome(options=options)
            self._driver.set_page_load_timeout(30)
            logger.info("WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {str(e)}")
            self._driver = None
    
    def get_driver(self):
        """Get the WebDriver instance, re-initializing if necessary."""
        if self._driver is None:
            self._initialize_driver()
        return self._driver
    
    def close(self):
        """Close the WebDriver instance."""
        if self._driver is not None:
            try:
                self._driver.quit()
            except Exception as e:
                logger.error(f"Error closing WebDriver: {str(e)}")
            finally:
                self._driver = None


class NavigateComplexWebsiteTool(BaseTool):
    """Tool for navigating complex websites with multiple interactions."""
    
    name: str = "navigate_complex_website"
    description: str = """
    Navigates a complex website by performing a sequence of actions.
    
    Input should be a JSON object with:
    - 'url': URL of the website to navigate
    - 'actions': Array of actions to perform, each with:
      - 'type': 'click', 'fill', 'wait', 'extract', 'submit'
      - 'selector': CSS selector or XPath (required for click, fill, extract)
      - 'selector_type': 'css' or 'xpath' (default: 'css')
      - 'value': Value to fill (required for 'fill' action)
      - 'wait_time': Time to wait in seconds (for 'wait' action)
    
    Example: {
      "url": "https://example.com",
      "actions": [
        {"type": "click", "selector": "a.login", "selector_type": "css"},
        {"type": "fill", "selector": "input[name='username']", "value": "user123"},
        {"type": "fill", "selector": "input[name='password']", "value": "pass123"},
        {"type": "click", "selector": "button[type='submit']"}
      ]
    }
    
    Returns content or confirmation of successful navigation, or error message.
    """
    
    def _run(self, navigation_info_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Navigate a complex website."""
        if not SELENIUM_AVAILABLE:
            return "This tool requires Selenium to be installed. Please install Selenium to use this functionality."
        
        try:
            # Parse the input
            import json
            try:
                navigation_info = json.loads(navigation_info_str)
            except json.JSONDecodeError:
                return "Error: Invalid JSON input. Expected a JSON object with 'url' and 'actions'."
            
            if not isinstance(navigation_info, dict):
                return "Error: Input must be a dictionary/JSON object"
            
            if "url" not in navigation_info or "actions" not in navigation_info:
                return "Error: Input must contain 'url' and 'actions'"
            
            url = navigation_info["url"]
            actions = navigation_info["actions"]
            
            if not isinstance(actions, list):
                return "Error: 'actions' must be an array"
            
            # Get WebDriver instance
            driver_manager = WebDriverManager()
            driver = driver_manager.get_driver()
            
            if driver is None:
                return "Error: Failed to initialize WebDriver"
            
            # Navigate to the URL
            try:
                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url
                
                driver.get(url)
                logger.info(f"Navigated to URL: {url}")
                time.sleep(2)  # Brief pause to ensure page loads
            except Exception as e:
                return f"Error: Failed to navigate to URL: {str(e)}"
            
            # Perform each action in sequence
            results = []
            
            for i, action in enumerate(actions, 1):
                try:
                    if not isinstance(action, dict):
                        results.append(f"Error on action {i}: Action must be an object")
                        continue
                    
                    action_type = action.get("type")
                    if not action_type:
                        results.append(f"Error on action {i}: Missing 'type'")
                        continue
                    
                    # Handle different action types
                    if action_type == "click":
                        selector = action.get("selector")
                        selector_type = action.get("selector_type", "css").lower()
                        
                        if not selector:
                            results.append(f"Error on action {i}: 'click' action requires 'selector'")
                            continue
                        
                        by_method = By.CSS_SELECTOR if selector_type == "css" else By.XPATH
                        
                        try:
                            element = WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((by_method, selector))
                            )
                            driver.execute_script("arguments[0].scrollIntoView(true);", element)
                            time.sleep(0.5)
                            
                            try:
                                element.click()
                                results.append(f"Clicked element: {selector}")
                            except ElementClickInterceptedException:
                                # Try JavaScript click if normal click is intercepted
                                driver.execute_script("arguments[0].click();", element)
                                results.append(f"Clicked element (via JavaScript): {selector}")
                                
                            time.sleep(1)  # Brief pause after click
                            
                        except TimeoutException:
                            results.append(f"Timeout waiting for element: {selector}")
                            continue
                        except NoSuchElementException:
                            results.append(f"Element not found: {selector}")
                            continue
                        except Exception as e:
                            results.append(f"Error clicking element: {str(e)}")
                            continue
                    
                    elif action_type == "fill":
                        selector = action.get("selector")
                        selector_type = action.get("selector_type", "css").lower()
                        value = action.get("value")
                        
                        if not selector:
                            results.append(f"Error on action {i}: 'fill' action requires 'selector'")
                            continue
                        
                        if value is None:
                            results.append(f"Error on action {i}: 'fill' action requires 'value'")
                            continue
                        
                        by_method = By.CSS_SELECTOR if selector_type == "css" else By.XPATH
                        
                        try:
                            element = WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((by_method, selector))
                            )
                            driver.execute_script("arguments[0].scrollIntoView(true);", element)
                            time.sleep(0.5)
                            
                            element.clear()
                            element.send_keys(str(value))
                            results.append(f"Filled form field '{selector}' with value '{value}'")
                            time.sleep(0.5)  # Brief pause after filling
                            
                        except TimeoutException:
                            results.append(f"Timeout waiting for element: {selector}")
                            continue
                        except NoSuchElementException:
                            results.append(f"Element not found: {selector}")
                            continue
                        except Exception as e:
                            results.append(f"Error filling element: {str(e)}")
                            continue
                    
                    elif action_type == "wait":
                        wait_time = action.get("wait_time", 1)
                        
                        try:
                            wait_time = float(wait_time)
                            if wait_time < 0 or wait_time > 30:
                                wait_time = min(max(wait_time, 0), 30)  # Clamp between 0 and 30
                                
                            time.sleep(wait_time)
                            results.append(f"Waited for {wait_time} seconds")
                            
                        except ValueError:
                            results.append(f"Error on action {i}: 'wait_time' must be a number")
                            continue
                        except Exception as e:
                            results.append(f"Error during wait: {str(e)}")
                            continue
                    
                    elif action_type == "extract":
                        selector = action.get("selector")
                        selector_type = action.get("selector_type", "css").lower()
                        
                        if not selector:
                            results.append(f"Error on action {i}: 'extract' action requires 'selector'")
                            continue
                        
                        by_method = By.CSS_SELECTOR if selector_type == "css" else By.XPATH
                        
                        try:
                            elements = driver.find_elements(by_method, selector)
                            
                            if not elements:
                                results.append(f"No elements found for selector: {selector}")
                                continue
                            
                            extracted_texts = []
                            for elem in elements:
                                extracted_texts.append(elem.text.strip())
                            
                            combined_text = "\n".join(extracted_texts)
                            if len(combined_text) > 500:
                                combined_text = combined_text[:497] + "..."
                                
                            results.append(f"Extracted from '{selector}':\n{combined_text}")
                            
                        except Exception as e:
                            results.append(f"Error extracting content: {str(e)}")
                            continue
                    
                    elif action_type == "submit":
                        selector = action.get("selector")
                        selector_type = action.get("selector_type", "css").lower()
                        
                        if not selector:
                            # Try to find a form and submit it
                            try:
                                forms = driver.find_elements(By.TAG_NAME, "form")
                                if forms:
                                    forms[0].submit()
                                    results.append("Submitted form")
                                    time.sleep(2)  # Wait for form submission
                                else:
                                    results.append("No form found to submit")
                            except Exception as e:
                                results.append(f"Error submitting form: {str(e)}")
                            continue
                        
                        by_method = By.CSS_SELECTOR if selector_type == "css" else By.XPATH
                        
                        try:
                            element = WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((by_method, selector))
                            )
                            
                            # Check if it's a form
                            if element.tag_name.lower() == "form":
                                element.submit()
                                results.append(f"Submitted form: {selector}")
                            else:
                                # Try to find the parent form and submit it
                                try:
                                    parent_form = element.find_element(By.XPATH, "./ancestor::form")
                                    parent_form.submit()
                                    results.append(f"Submitted parent form of: {selector}")
                                except:
                                    # Otherwise just click the element (might be a submit button)
                                    element.click()
                                    results.append(f"Clicked submit element: {selector}")
                                    
                            time.sleep(2)  # Wait for form submission
                            
                        except TimeoutException:
                            results.append(f"Timeout waiting for element: {selector}")
                            continue
                        except NoSuchElementException:
                            results.append(f"Element not found: {selector}")
                            continue
                        except Exception as e:
                            results.append(f"Error submitting form: {str(e)}")
                            continue
                    
                    else:
                        results.append(f"Error on action {i}: Unknown action type '{action_type}'")
                        
                except Exception as e:
                    results.append(f"Error on action {i}: {str(e)}")
            
            # Capture final page state
            current_url = driver.current_url
            page_title = driver.title
            
            # Format the results
            output = [
                f"Complex website navigation completed.",
                f"Final URL: {current_url}",
                f"Page Title: {page_title}",
                "\nAction Results:"
            ]
            
            for i, result in enumerate(results, 1):
                output.append(f"{i}. {result}")
            
            return "\n".join(output)
            
        except Exception as e:
            logger.error(f"Error in complex website navigation: {str(e)}")
            return f"Error in complex website navigation: {str(e)}"


class UploadFileToWebsiteTool(BaseTool):
    """Tool for uploading a file to a website."""
    
    name: str = "upload_file_to_website"
    description: str = """
    Uploads a file from the local system to a website.
    
    Input should be a JSON object with:
    - 'url': URL of the website to navigate to
    - 'file_path': Path to the file to upload
    - 'upload_selector': CSS selector or XPath for the file input element
    - 'selector_type' (optional): 'css' or 'xpath' (default: 'css')
    - 'submit_selector' (optional): Selector for the submit button after selecting file
    
    Example: {
      "url": "https://example.com/upload",
      "file_path": "documents/report.pdf",
      "upload_selector": "input[type='file']",
      "submit_selector": "button[type='submit']"
    }
    
    Returns confirmation of successful upload or error message.
    """
    
    def _run(self, upload_info_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Upload a file to a website."""
        if not SELENIUM_AVAILABLE:
            return "This tool requires Selenium to be installed. Please install Selenium to use this functionality."
        
        try:
            # Parse the input
            import json
            try:
                upload_info = json.loads(upload_info_str)
            except json.JSONDecodeError:
                return "Error: Invalid JSON input. Expected a JSON object with 'url', 'file_path', and 'upload_selector'."
            
            if not isinstance(upload_info, dict):
                return "Error: Input must be a dictionary/JSON object"
            
            required_keys = ["url", "file_path", "upload_selector"]
            for key in required_keys:
                if key not in upload_info:
                    return f"Error: Input must contain '{key}'"
            
            url = upload_info["url"]
            file_path = upload_info["file_path"]
            upload_selector = upload_info["upload_selector"]
            selector_type = upload_info.get("selector_type", "css").lower()
            submit_selector = upload_info.get("submit_selector", None)
            
            # Check if file exists
            expanded_path = os.path.expanduser(file_path)
            if not os.path.exists(expanded_path):
                return f"Error: File '{file_path}' does not exist"
            
            if not os.path.isfile(expanded_path):
                return f"Error: '{file_path}' is not a file"
            
            # Get WebDriver instance
            driver_manager = WebDriverManager()
            driver = driver_manager.get_driver()
            
            if driver is None:
                return "Error: Failed to initialize WebDriver"
            
            # Navigate to the URL
            try:
                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url
                
                driver.get(url)
                logger.info(f"Navigated to URL: {url}")
                time.sleep(2)  # Brief pause to ensure page loads
            except Exception as e:
                return f"Error: Failed to navigate to URL: {str(e)}"
            
            # Find the file input element
            by_method = By.CSS_SELECTOR if selector_type == "css" else By.XPATH
            
            try:
                file_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((by_method, upload_selector))
                )
                
                # Use absolute path for the file
                abs_file_path = os.path.abspath(expanded_path)
                
                # Send the file path to the input
                file_input.send_keys(abs_file_path)
                logger.info(f"File selected: {abs_file_path}")
                time.sleep(1)  # Brief pause after selecting file
                
                # Click submit button if provided
                if submit_selector:
                    submit_by_method = By.CSS_SELECTOR if selector_type == "css" else By.XPATH
                    
                    try:
                        submit_button = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((submit_by_method, submit_selector))
                        )
                        
                        driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
                        time.sleep(0.5)
                        
                        submit_button.click()
                        logger.info("Clicked submit button")
                        time.sleep(2)  # Wait for upload to complete
                        
                    except TimeoutException:
                        return f"Timeout waiting for submit button: {submit_selector}"
                    except NoSuchElementException:
                        return f"Submit button not found: {submit_selector}"
                    except Exception as e:
                        return f"Error clicking submit button: {str(e)}"
                
                # Get current state of the page
                current_url = driver.current_url
                page_title = driver.title
                
                # Format the results
                file_name = os.path.basename(file_path)
                file_size = os.path.getsize(expanded_path)
                file_size_formatted = f"{file_size / 1024:.2f} KB" if file_size < 1024 * 1024 else f"{file_size / (1024 * 1024):.2f} MB"
                
                output = [
                    f"File upload completed: {file_name} ({file_size_formatted})",
                    f"Upload URL: {url}",
                    f"Current URL: {current_url}",
                    f"Page Title: {page_title}",
                ]
                
                return "\n".join(output)
                
            except TimeoutException:
                return f"Timeout waiting for file input element: {upload_selector}"
            except NoSuchElementException:
                return f"File input element not found: {upload_selector}"
            except Exception as e:
                return f"Error during file upload: {str(e)}"
            
        except Exception as e:
            logger.error(f"Error in file upload: {str(e)}")
            return f"Error in file upload: {str(e)}"


class ExtractWebsiteStructureTool(BaseTool):
    """Tool for extracting the structure of a website."""
    
    name: str = "extract_website_structure"
    description: str = """
    Extracts and analyzes the structure of a website, including navigation, links, and major sections.
    
    Input should be a URL of the website to analyze.
    Returns a structured analysis of the site's navigation, major sections, and link hierarchy.
    
    Example: "https://example.com"
    """
    
    def _run(self, url: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Extract and analyze website structure."""
        if not WEB_TOOLS_AVAILABLE:
            return "This tool requires web tools dependencies to be installed (requests, BeautifulSoup)."
        
        try:
            # Validate and clean the URL
            url = url.strip()
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            # Fetch the webpage
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                html_content = response.text
            except requests.exceptions.RequestException as e:
                return f"Error fetching website: {str(e)}"
            
            # Parse the HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract the title and meta description
            title = soup.title.string.strip() if soup.title else "No title found"
            
            meta_description = ""
            description_tag = soup.find("meta", attrs={"name": "description"})
            if description_tag and description_tag.get("content"):
                meta_description = description_tag.get("content").strip()
            
            # Extract navigation links
            nav_elements = soup.find_all(['nav', 'div'], class_=lambda c: c and (
                'nav' in c.lower() or
                'menu' in c.lower() or
                'navigation' in c.lower() or
                'header' in c.lower()
            ))
            
            nav_links = []
            main_menu_items = []
            
            if nav_elements:
                # Extract links from the first navigation element (usually the main navigation)
                links = nav_elements[0].find_all('a')
                for link in links:
                    if link.get('href') and link.text.strip():
                        nav_links.append({
                            'text': link.text.strip(),
                            'href': link.get('href')
                        })
                
                # Extract main menu items as text only for a cleaner overview
                main_menu_items = [link['text'] for link in nav_links[:8]]  # Limit to first 8 items
            
            # Find major sections of the page
            potential_sections = soup.find_all(['section', 'div', 'article'], class_=lambda c: c and (
                'section' in str(c).lower() or
                'container' in str(c).lower() or
                'content' in str(c).lower() or
                'wrapper' in str(c).lower() or
                'block' in str(c).lower()
            ))
            
            major_sections = []
            for section in potential_sections[:5]:  # Limit to first 5 potential sections
                # Try to find a heading in this section
                heading = section.find(['h1', 'h2', 'h3'])
                if heading and heading.text.strip():
                    section_text = heading.text.strip()
                else:
                    # If no heading, try to use a class or id as identifier
                    section_id = section.get('id', '')
                    section_class = section.get('class', [])
                    section_text = section_id if section_id else ' '.join(section_class[:2])
                
                if section_text and section_text not in [s['name'] for s in major_sections]:
                    major_sections.append({
                        'name': section_text,
                        'type': section.name
                    })
            
            # Extract footer links (often important for site structure)
            footer = soup.find(['footer', 'div'], class_=lambda c: c and 'footer' in str(c).lower())
            footer_links = []
            
            if footer:
                links = footer.find_all('a')
                for link in links:
                    if link.get('href') and link.text.strip():
                        footer_links.append({
                            'text': link.text.strip(),
                            'href': link.get('href')
                        })
            
            # Count different types of content
            num_images = len(soup.find_all('img'))
            num_forms = len(soup.find_all('form'))
            num_buttons = len(soup.find_all('button'))
            num_links = len(soup.find_all('a'))
            
            # Format the output
            output = [
                f"Website Structure Analysis for: {url}",
                f"Title: {title}",
                f"Description: {meta_description}" if meta_description else "Description: None found",
                "\nMain Navigation:",
            ]
            
            if main_menu_items:
                output.append("  - " + ", ".join(main_menu_items))
            else:
                output.append("  No clear navigation menu found")
            
            output.append("\nMajor Sections:")
            if major_sections:
                for section in major_sections:
                    output.append(f"  - {section['name']} ({section['type']})")
            else:
                output.append("  No clear sections identified")
            
            output.append("\nFooter Links:")
            if footer_links:
                for i, link in enumerate(footer_links[:5]):  # Show first 5 footer links
                    output.append(f"  - {link['text']}")
                if len(footer_links) > 5:
                    output.append(f"  - ... and {len(footer_links) - 5} more links")
            else:
                output.append("  No footer links found")
            
            output.append("\nContent Summary:")
            output.append(f"  - {num_images} images")
            output.append(f"  - {num_forms} forms")
            output.append(f"  - {num_buttons} buttons")
            output.append(f"  - {num_links} links total")
            
            return "\n".join(output)
            
        except Exception as e:
            logger.error(f"Error analyzing website structure: {str(e)}")
            return f"Error analyzing website structure: {str(e)}"


class SaveWebsiteContentTool(BaseTool):
    """Tool for extracting and saving content from a website to a local file."""
    
    name: str = "save_website_content"
    description: str = """
    Extracts content from a website and saves it to a local file.
    
    Input should be a JSON object with:
    - 'url': URL of the website to extract content from
    - 'file_path': Path where to save the content
    - 'content_type' (optional): 'text' (default), 'html', or 'markdown'
    - 'selector' (optional): CSS selector to extract specific content
    
    Example: {
      "url": "https://example.com/article",
      "file_path": "documents/article.txt",
      "content_type": "text"
    }
    
    Returns confirmation of successful save or error message.
    """
    
    def _run(self, save_info_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Extract website content and save to local file."""
        if not WEB_TOOLS_AVAILABLE:
            return "This tool requires web tools dependencies to be installed (requests, BeautifulSoup)."
        
        try:
            # Parse the input
            import json
            try:
                save_info = json.loads(save_info_str)
            except json.JSONDecodeError:
                return "Error: Invalid JSON input. Expected a JSON object with 'url' and 'file_path'."
            
            if not isinstance(save_info, dict):
                return "Error: Input must be a dictionary/JSON object"
            
            required_keys = ["url", "file_path"]
            for key in required_keys:
                if key not in save_info:
                    return f"Error: Input must contain '{key}'"
            
            url = save_info["url"]
            file_path = save_info["file_path"]
            content_type = save_info.get("content_type", "text").lower()
            selector = save_info.get("selector", None)
            
            if content_type not in ["text", "html", "markdown"]:
                return f"Error: 'content_type' must be one of: 'text', 'html', 'markdown'"
            
            # Validate and clean the URL
            url = url.strip()
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            # Fetch the webpage
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                html_content = response.text
            except requests.exceptions.RequestException as e:
                return f"Error fetching website: {str(e)}"
            
            # Parse the HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract specific content if a selector is provided
            if selector:
                elements = soup.select(selector)
                if not elements:
                    return f"Error: No elements found matching selector '{selector}'"
                
                # Create a new soup with just the selected elements
                from bs4 import BeautifulSoup as BS
                selected_soup = BS("<div></div>", "html.parser")
                div = selected_soup.div
                
                for element in elements:
                    div.append(selected_soup.new_tag(element.name))
                    div.contents[-1].append(element)
                
                soup = selected_soup
            
            # Clean up the HTML (remove scripts, styles, etc.)
            for script in soup(["script", "style", "iframe", "noscript"]):
                script.decompose()
            
            # Prepare the content based on content_type
            if content_type == "html":
                content = str(soup)
            elif content_type == "markdown":
                if html2text:
                    h = html2text.HTML2Text()
                    h.ignore_links = False
                    h.ignore_images = False
                    h.ignore_emphasis = False
                    h.body_width = 0  # No wrapping
                    content = h.handle(str(soup))
                else:
                    content = soup.get_text(separator="\n\n")
                    content = f"HTML to Markdown conversion not available.\nPlain text content:\n\n{content}"
            else:  # text
                content = soup.get_text(separator="\n\n")
                content = re.sub(r'\n{3,}', '\n\n', content)  # Remove excessive newlines
            
            # Save content to the specified file
            try:
                # Ensure directory exists
                directory = os.path.dirname(file_path)
                if directory and not os.path.exists(directory):
                    os.makedirs(directory)
                
                # Write content to file
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(content)
                
                # Get file stats
                file_size = os.path.getsize(file_path)
                file_size_formatted = f"{file_size / 1024:.2f} KB" if file_size < 1024 * 1024 else f"{file_size / (1024 * 1024):.2f} MB"
                
                # Count number of lines
                num_lines = len(content.split('\n'))
                
                return f"Successfully saved {content_type} content from {url} to {file_path}\nSize: {file_size_formatted}, Lines: {num_lines}"
                
            except Exception as e:
                return f"Error saving content to file: {str(e)}"
            
        except Exception as e:
            logger.error(f"Error in save_website_content: {str(e)}")
            return f"Error in save_website_content: {str(e)}"


class LoginWebsiteTool(BaseTool):
    """Tool for logging into a website with credentials."""
    
    name: str = "login_website"
    description: str = """
    Logs into a website using provided credentials.
    
    Input should be a JSON object with:
    - 'url': URL of the login page
    - 'username': Username or email to use for login
    - 'password': Password to use for login
    - 'username_selector': CSS selector for the username/email input field
    - 'password_selector': CSS selector for the password input field
    - 'submit_selector': CSS selector for the login/submit button
    - 'success_indicator' (optional): Text or CSS selector to verify successful login
    
    Example: {
      "url": "https://example.com/login",
      "username": "user@example.com",
      "password": "password123",
      "username_selector": "input[name='email']",
      "password_selector": "input[name='password']",
      "submit_selector": "button[type='submit']",
      "success_indicator": ".welcome-message"
    }
    
    Returns confirmation of successful login or error message.
    
    SECURITY NOTE: This tool will not expose passwords in its response.
    """
    
    def _run(self, login_info_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Log into a website."""
        if not SELENIUM_AVAILABLE:
            return "This tool requires Selenium to be installed. Please install Selenium to use this functionality."
        
        try:
            # Parse the input
            import json
            try:
                login_info = json.loads(login_info_str)
            except json.JSONDecodeError:
                return "Error: Invalid JSON input. Expected a JSON object with login information."
            
            if not isinstance(login_info, dict):
                return "Error: Input must be a dictionary/JSON object"
            
            required_keys = ["url", "username", "password", "username_selector", "password_selector", "submit_selector"]
            for key in required_keys:
                if key not in login_info:
                    return f"Error: Input must contain '{key}'"
            
            url = login_info["url"]
            username = login_info["username"]
            password = login_info["password"]
            username_selector = login_info["username_selector"]
            password_selector = login_info["password_selector"]
            submit_selector = login_info["submit_selector"]
            success_indicator = login_info.get("success_indicator")
            
            # Get WebDriver instance
            driver_manager = WebDriverManager()
            driver = driver_manager.get_driver()
            
            if driver is None:
                return "Error: Failed to initialize WebDriver"
            
            # Navigate to the login page
            try:
                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url
                
                driver.get(url)
                logger.info(f"Navigated to login page: {url}")
                time.sleep(2)  # Brief pause to ensure page loads
            except Exception as e:
                return f"Error: Failed to navigate to login page: {str(e)}"
            
            # Fill in the username field
            try:
                username_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, username_selector))
                )
                username_field.clear()
                username_field.send_keys(username)
                logger.info("Filled username field")
            except TimeoutException:
                return f"Timeout waiting for username field: {username_selector}"
            except NoSuchElementException:
                return f"Username field not found: {username_selector}"
            except Exception as e:
                return f"Error filling username field: {str(e)}"
            
            # Fill in the password field
            try:
                password_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, password_selector))
                )
                password_field.clear()
                password_field.send_keys(password)
                logger.info("Filled password field")
            except TimeoutException:
                return f"Timeout waiting for password field: {password_selector}"
            except NoSuchElementException:
                return f"Password field not found: {password_selector}"
            except Exception as e:
                return f"Error filling password field: {str(e)}"
            
            # Click the submit button
            try:
                submit_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, submit_selector))
                )
                
                driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
                time.sleep(0.5)
                
                submit_button.click()
                logger.info("Clicked submit button")
                time.sleep(3)  # Wait longer for login to complete
            except TimeoutException:
                return f"Timeout waiting for submit button: {submit_selector}"
            except NoSuchElementException:
                return f"Submit button not found: {submit_selector}"
            except Exception as e:
                return f"Error clicking submit button: {str(e)}"
            
            # Check for successful login if success indicator is provided
            if success_indicator:
                try:
                    # Check if success_indicator is a CSS selector or plain text
                    if success_indicator.startswith('.') or success_indicator.startswith('#') or '[' in success_indicator:
                        # It's likely a CSS selector
                        try:
                            # Wait for the success element to be present
                            WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, success_indicator))
                            )
                            login_successful = True
                        except:
                            login_successful = False
                    else:
                        # It's likely plain text to find in the page
                        login_successful = success_indicator in driver.page_source
                    
                    if not login_successful:
                        # Check for common error messages
                        error_patterns = [
                            "incorrect password", "invalid password",
                            "incorrect username", "invalid username",
                            "invalid login", "incorrect login",
                            "wrong credentials", "login failed"
                        ]
                        
                        page_text = driver.page_source.lower()
                        found_errors = [error for error in error_patterns if error in page_text]
                        
                        if found_errors:
                            return f"Login failed. Possible error: {found_errors[0]}"
                        else:
                            return "Login appears to have failed. Success indicator not found."
                except Exception as e:
                    return f"Error checking login success: {str(e)}"
            
            # Get current state of the page
            current_url = driver.current_url
            page_title = driver.title
            
            # Format the results (do not include the password in the response for security)
            obfuscated_username = username[:2] + '*' * (len(username) - 4) + username[-2:] if len(username) > 4 else '****'
            
            output = [
                f"Login attempt completed for: {obfuscated_username}",
                f"Login URL: {url}",
                f"Current URL: {current_url}",
                f"Page Title: {page_title}",
            ]
            
            # Try to determine login status based on URL change
            if url != current_url and '/login' not in current_url.lower():
                output.insert(0, "Login appears to be successful (URL changed).")
            else:
                output.insert(0, "Login status uncertain. Please check the page details below.")
            
            return "\n".join(output)
            
        except Exception as e:
            logger.error(f"Error in login process: {str(e)}")
            return f"Error in login process: {str(e)}"