"""
================================================================================
NATIVE SPREADSHEET ANALYSIS TOOLS (code_tools.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module defines local/native tools to parse and query CSV and Excel spreadsheets 
using Pandas. This replaces the paid/external E2B sandboxed execution flow.
"""

import os
import logging
from utils.logger import get_department_logger
import pandas as pd
from typing import List
from langchain_core.tools import tool, BaseTool
from core.database import get_db_cursor_async
from starlette.concurrency import run_in_threadpool

logger = get_department_logger("agent")

async def get_agent_documents(agent_id: str) -> List[str]:
    """Helper to query the filenames of documents uploaded for a specific agent."""
    try:
        async with get_db_cursor_async(commit=False) as cursor:
            await run_in_threadpool(
                cursor.execute,
                "SELECT filename FROM documents WHERE agent_id = %s",
                (agent_id,)
            )
            rows = cursor.fetchall()
            return [row[0] for row in rows]
    except Exception as e:
        logger.error(f"Error fetching agent documents: {e}", exc_info=True)
        return []

def create_code_tools(agent_id: str) -> List[BaseTool]:
    """
    Creates and returns native CSV & Excel parsing tools for the agent.
    """
    
    @tool(name="list_data_files")
    async def list_data_files() -> str:
        """
        Lists all CSV and Excel data files available for analysis in the agent's knowledge base.
        Use this tool first to check what files you have access to.
        """
        filenames = await get_agent_documents(agent_id)
        data_files = [f for f in filenames if f.lower().endswith(('.csv', '.xlsx', '.xls'))]
        if not data_files:
            return "No CSV or Excel files found in the knowledge base."
        return "Available data files for analysis:\n" + "\n".join(f"- {f}" for f in data_files)

    @tool(name="query_csv_file")
    def query_csv_file(filename: str, operation: str, query_expr: str = "", groupby_col: str = "", agg_func: str = "", agg_col: str = "") -> str:
        """
        Perform a native query or statistical analysis on an uploaded CSV file.
        
        Parameters:
            filename (str): Name of the CSV file to analyze (e.g. 'sales.csv').
            operation (str): Operation to perform. Options:
                - 'summary': Get general information, row count, column names, types, and the first 5 rows (head).
                - 'statistics': Compute descriptive stats (mean, min, max, std, percentiles) for numeric fields.
                - 'filter': Filter columns and rows based on a pandas-compatible query expression (e.g. "Age > 30").
                - 'aggregate': Group data by a column and compute an aggregate function (sum, mean, count) on another column.
            query_expr (str, optional): The pandas query expression string (required for 'filter', e.g. "Country == 'US' and Sales > 1000").
            groupby_col (str, optional): Column name to group by (required for 'aggregate', e.g. "Department").
            agg_func (str, optional): Aggregation function to run (required for 'aggregate', options: 'sum', 'mean', 'count').
            agg_col (str, optional): Column name to run the aggregation function on (required for 'aggregate', e.g. "Salary").
        """
        safe_filename = os.path.basename(filename)
        file_path = os.path.join("temp_uploads", safe_filename)
        
        if not os.path.exists(file_path):
            return f"Error: CSV file '{safe_filename}' not found."
            
        try:
            df = pd.read_csv(file_path)
            
            if operation == "summary":
                summary_str = f"Summary of '{safe_filename}':\n"
                summary_str += f"- Total Rows: {df.shape[0]}\n"
                summary_str += f"- Total Columns: {df.shape[1]}\n"
                summary_str += f"- Columns & Types:\n"
                for col, dtype in df.dtypes.items():
                    summary_str += f"  * {col} ({dtype})\n"
                summary_str += "\nFirst 5 Rows:\n"
                summary_str += df.head(5).to_string(index=False)
                return summary_str
                
            elif operation == "statistics":
                return df.describe(include='all').to_string()
                
            elif operation == "filter":
                if not query_expr:
                    return "Error: query_expr is required for filter operation."
                filtered_df = df.query(query_expr)
                row_count = filtered_df.shape[0]
                res_str = f"Filtered result ({row_count} rows match criteria):\n\n"
                res_str += filtered_df.head(50).to_string(index=False)
                if row_count > 50:
                    res_str += f"\n\n[Showing first 50 rows. Truncated {row_count - 50} rows.]"
                return res_str
                
            elif operation == "aggregate":
                if not groupby_col or not agg_col or not agg_func:
                    return "Error: groupby_col, agg_col, and agg_func are all required for aggregate operation."
                if groupby_col not in df.columns or agg_col not in df.columns:
                    return f"Error: groupby_col '{groupby_col}' or agg_col '{agg_col}' does not exist in columns: {list(df.columns)}"
                    
                grouped = df.groupby(groupby_col)[agg_col]
                if agg_func == "sum":
                    res = grouped.sum()
                elif agg_func == "mean":
                    res = grouped.mean()
                elif agg_func == "count":
                    res = grouped.count()
                else:
                    return f"Error: Unsupported agg_func '{agg_func}'. Use 'sum', 'mean', or 'count'."
                return f"Aggregation (group by {groupby_col}, {agg_func} of {agg_col}):\n\n{res.to_string()}"
                
            else:
                return "Error: Invalid operation. Choose from: 'summary', 'statistics', 'filter', 'aggregate'."
                
        except Exception as e:
            logger.error(f"Error querying CSV {safe_filename}: {e}", exc_info=True)
            return f"Error querying CSV file: {str(e)}"

    @tool(name="query_excel_file")
    def query_excel_file(filename: str, operation: str, sheet_name: str = "0", query_expr: str = "", groupby_col: str = "", agg_func: str = "", agg_col: str = "") -> str:
        """
        Perform a native query or statistical analysis on an uploaded Excel spreadsheet (.xlsx, .xls).
        
        Parameters:
            filename (str): Name of the Excel file to analyze (e.g. 'report.xlsx').
            operation (str): Operation to perform. Options:
                - 'sheets': List all worksheet names in the Excel workbook.
                - 'summary': Get general information, row count, column names, types, and the first 5 rows (head) of a sheet.
                - 'statistics': Compute descriptive stats (mean, min, max, std, percentiles) for numeric fields in a sheet.
                - 'filter': Filter columns and rows of a sheet based on a pandas-compatible query expression (e.g. "Status == 'Approved'").
                - 'aggregate': Group data by a column and compute an aggregate function (sum, mean, count) on another column.
            sheet_name (str, optional): Name or 0-indexed index of the worksheet to analyze. Defaults to the first sheet ("0").
            query_expr (str, optional): The pandas query expression string (required for 'filter').
            groupby_col (str, optional): Column name to group by (required for 'aggregate').
            agg_func (str, optional): Aggregation function to run (required for 'aggregate', options: 'sum', 'mean', 'count').
            agg_col (str, optional): Column name to run the aggregation function on (required for 'aggregate').
        """
        safe_filename = os.path.basename(filename)
        file_path = os.path.join("temp_uploads", safe_filename)
        
        if not os.path.exists(file_path):
            return f"Error: Excel file '{safe_filename}' not found."
            
        try:
            excel_file = pd.ExcelFile(file_path)
            
            if operation == "sheets":
                return f"Sheets in '{safe_filename}':\n" + "\n".join(f"- {s}" for s in excel_file.sheet_names)
                
            actual_sheet = sheet_name
            if sheet_name.isdigit():
                actual_sheet = int(sheet_name)
                if actual_sheet >= len(excel_file.sheet_names):
                    return f"Error: Sheet index {sheet_name} out of bounds. Available sheet names: {excel_file.sheet_names}"
                    
            df = pd.read_excel(file_path, sheet_name=actual_sheet)
            
            if operation == "summary":
                sheet_label = excel_file.sheet_names[actual_sheet] if isinstance(actual_sheet, int) else actual_sheet
                summary_str = f"Summary of Sheet '{sheet_label}' in '{safe_filename}':\n"
                summary_str += f"- Total Rows: {df.shape[0]}\n"
                summary_str += f"- Total Columns: {df.shape[1]}\n"
                summary_str += f"- Columns & Types:\n"
                for col, dtype in df.dtypes.items():
                    summary_str += f"  * {col} ({dtype})\n"
                summary_str += "\nFirst 5 Rows:\n"
                summary_str += df.head(5).to_string(index=False)
                return summary_str
                
            elif operation == "statistics":
                return df.describe(include='all').to_string()
                
            elif operation == "filter":
                if not query_expr:
                    return "Error: query_expr is required for filter operation."
                filtered_df = df.query(query_expr)
                row_count = filtered_df.shape[0]
                res_str = f"Filtered result ({row_count} rows match criteria):\n\n"
                res_str += filtered_df.head(50).to_string(index=False)
                if row_count > 50:
                    res_str += f"\n\n[Showing first 50 rows. Truncated {row_count - 50} rows.]"
                return res_str
                
            elif operation == "aggregate":
                if not groupby_col or not agg_col or not agg_func:
                    return "Error: groupby_col, agg_col, and agg_func are all required for aggregate operation."
                if groupby_col not in df.columns or agg_col not in df.columns:
                    return f"Error: groupby_col '{groupby_col}' or agg_col '{agg_col}' does not exist in columns: {list(df.columns)}"
                    
                grouped = df.groupby(groupby_col)[agg_col]
                if agg_func == "sum":
                    res = grouped.sum()
                elif agg_func == "mean":
                    res = grouped.mean()
                elif agg_func == "count":
                    res = grouped.count()
                else:
                    return f"Error: Unsupported agg_func '{agg_func}'. Use 'sum', 'mean', or 'count'."
                return f"Aggregation (group by {groupby_col}, {agg_func} of {agg_col}):\n\n{res.to_string()}"
                
            else:
                return "Error: Invalid operation. Choose from: 'sheets', 'summary', 'statistics', 'filter', 'aggregate'."
                
        except Exception as e:
            logger.error(f"Error querying Excel {safe_filename}: {e}", exc_info=True)
            return f"Error querying Excel file: {str(e)}"

    return [list_data_files, query_csv_file, query_excel_file]
