from typing import List, Optional
import os
import logging
from langchain_core.tools import tool, BaseTool
from e2b_code_interpreter import Sandbox

logger = logging.getLogger(__name__)

def create_code_tools() -> List[BaseTool]:
    """
    Creates LangChain tools to execute Python code securely via E2B Sandbox.
    """
    @tool(name="execute_python_code")
    def execute_python_code(code: str) -> str:
        """
        Execute python code in a secure sandboxed environment.
        Useful for data analysis, math computations, and generating plots.
        If you generate an image/plot, the tool will return a message indicating success, but it won't render directly in the text payload yet.
        """
        api_key = os.getenv("E2B_API_KEY")
        if not api_key:
            return "Error: E2B_API_KEY is not configured in the server environment. Cannot execute code."
            
        try:
            with Sandbox(api_key=api_key) as sandbox:
                execution = sandbox.run_code(code)
                
                output_str = ""
                if execution.logs.stdout:
                    output_str += f"STDOUT:\n{execution.logs.stdout}\n"
                if execution.logs.stderr:
                    output_str += f"STDERR:\n{execution.logs.stderr}\n"
                    
                if execution.error:
                    output_str += f"ERROR:\n{execution.error.name}: {execution.error.value}\n{execution.error.traceback}\n"
                    
                if execution.results:
                    output_str += "RESULTS:\n"
                    for result in execution.results:
                        output_str += str(result.text) + "\n"
                        if result.png:
                            output_str += "[Note: A PNG image was generated but cannot be displayed inline yet.]\n"
                            
                if not output_str.strip():
                    output_str = "Code executed successfully with no output."
                    
                return output_str
        except Exception as e:
            logger.error(f"E2B Sandbox error: {e}")
            return f"Error executing code sandbox: {e}"

    return [execute_python_code]
