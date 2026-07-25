"""
================================================================================
E2B SECURE SANDBOX CODE EXECUTION SYSTEM (code_tools.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module defines the integration layer for executing raw Python code within a secure, 
isolated cloud sandbox. This capability allows LLM agents to run complex calculations, 
data analyses, mathematical computations, and plot generations.

KEY COMPONENT WORKFLOWS:
1. Sandbox Setup (E2B Code Interpreter):
   - Rather than executing user/agent code locally (which poses severe security risks like 
     directory traversal or privilege escalation), the system spawns a secure, isolated micro-VM 
     instance managed by the E2B platform using an E2B API Key.
2. execution logs Capture:
   - Captures standard outputs (stdout) and standard errors (stderr) from the micro-VM.
   - Handles exceptions and traceback outputs.
3. Media Assets & Results Handling:
   - Processes execution outputs and tracks generated binary media formats (like PNG images).
4. LangChain Tool Registration:
   - Registers the execution function as a LangChain `BaseTool` using decorators, making it 
     accessible to the agent graph.

BEGINNER COMPUTER SECURITY CONCEPTS:
- Sandboxing: A security practice where untrusted code is executed inside a restricted, isolated 
  environment (a virtual machine or container) separated from the host operating system.
- Standard Out (stdout) vs Standard Error (stderr):
  - stdout: The default destination where a program writes its output logs (e.g. `print()`).
  - stderr: A separate destination dedicated to writing error diagnostic outputs.
"""

from typing import List, Optional
import os
import logging
from langchain_core.tools import tool, BaseTool
from e2b_code_interpreter import Sandbox

# Initialize standard module logger.
logger = logging.getLogger(__name__)


# ==========================================
# PUBLIC CODE TOOL CONSTRUCTORS
# ==========================================

def create_code_tools() -> List[BaseTool]:
    """
    Creates a list of LangChain tools for executing Python code.

    Purpose:
        Instantiates and returns the `execute_python_code` tool wrapped as a LangChain BaseTool.

    Parameters:
        None.

    Returns:
        list of BaseTool: List containing the wrapped sandboxed execution tool.
    """
    
    # Decorate function as a LangChain tool.
    @tool(name="execute_python_code")
    def execute_python_code(code: str) -> str:
        """
        Execute python code in a secure sandboxed environment.
        Useful for data analysis, math computations, and generating plots.
        If you generate an image/plot, the tool will return a message indicating success, but it won't render directly in the text payload yet.

        Purpose:
            Connects to the E2B client SDK, provisions a sandbox micro-VM, executes
            the raw python code input block, and returns standard outputs.

        Parameters:
            code (str): The Python code block to execute in the sandbox.

        Returns:
            str: Log results containing stdout, stderr, or execution tracebacks.

        Side Effects:
            - Provisions and terminates a virtual machine instance in the E2B cloud.
            - Consumes E2B API key quotas.

        Errors / Exceptions:
            - Catches sandbox provisioning exceptions, returning them as error strings.
        """
        # Retrieve the E2B client API credential from the server environment.
        api_key = os.getenv("E2B_API_KEY")
        if not api_key:
            # Return an error description if the API key is not configured.
            return "Error: E2B_API_KEY is not configured in the server environment. Cannot execute code."
            
        try:
            # Initialize the E2B Sandbox using a context manager.
            # The context manager ensures the sandbox is closed and terminated when the block exits.
            with Sandbox(api_key=api_key) as sandbox:
                # Execute the code block in the sandbox.
                execution = sandbox.run_code(code)
                
                # Initialize output log string.
                output_str = ""
                # Append standard outputs.
                if execution.logs.stdout:
                    output_str += f"STDOUT:\n{execution.logs.stdout}\n"
                # Append standard errors.
                if execution.logs.stderr:
                    output_str += f"STDERR:\n{execution.logs.stderr}\n"
                    
                # Append syntax or runtime tracebacks if execution failed.
                if execution.error:
                    output_str += f"ERROR:\n{execution.error.name}: {execution.error.value}\n{execution.error.traceback}\n"
                    
                # Process return values (results).
                if execution.results:
                    output_str += "RESULTS:\n"
                    for result in execution.results:
                        # Append the textual result representation.
                        output_str += str(result.text) + "\n"
                        # Check for binary image outputs (like matplotlib charts).
                        if result.png:
                            output_str += "[Note: A PNG image was generated but cannot be displayed inline yet.]\n"
                            
                # Fallback message if the code executed successfully with no output logs.
                if not output_str.strip():
                    output_str = "Code executed successfully with no output."
                    
                # Return the execution results.
                return output_str
        except Exception as e:
            # Log exceptions and return error details.
            logger.error(f"E2B Sandbox error: {e}")
            return f"Error executing code sandbox: {e}"

    # Return the tool list.
    return [execute_python_code]

