"""
Loop Control Tools for Financial Analyst Agent

Provides tools for controlling LoopAgent flow:
- exit_loop_success: Signal PDF found and downloaded successfully
- exit_loop_failure: Signal all retries exhausted
- exit_all_companies_processed: Signal outer loop completion
"""

from typing import Dict, Any
from google.adk.tools.tool_context import ToolContext


def exit_loop_success(tool_context: ToolContext) -> dict:
    """
    Signals successful loop completion. 
    Call this when PDF is found and downloaded successfully.
    This will cause the inner PDF retry loop to exit.
    """
    print(f"  [Loop Control] exit_loop_success called by {tool_context.agent_name}")
    tool_context.actions.escalate = True
    return {"status": "success", "message": "PDF found and downloaded successfully"}


def exit_loop_failure(tool_context: ToolContext) -> dict:
    """
    Signals loop failure after max retries.
    Call this when all PDF search alternatives have been exhausted.
    This will cause the inner PDF retry loop to exit with failure status.
    """
    print(f"  [Loop Control] exit_loop_failure called by {tool_context.agent_name}")
    tool_context.actions.escalate = True
    return {"status": "failure", "message": "Could not find valid PDF after all retries"}


def exit_all_companies_processed(tool_context: ToolContext) -> dict:
    """
    Signals outer loop completion.
    Call this when all companies in the list have been processed.
    This will cause the company orchestrator loop to exit.
    """
    print(f"  [Loop Control] exit_all_companies_processed called by {tool_context.agent_name}")
    tool_context.actions.escalate = True
    return {"status": "complete", "message": "All companies processed"}


def increment_retry_counter(tool_context: ToolContext) -> dict:
    """
    Increments the PDF find retry counter.
    Returns the current attempt number and remaining retries.
    """
    current_attempt = tool_context.state.get("pdf_find_attempt", 0)
    new_attempt = current_attempt + 1
    tool_context.state["pdf_find_attempt"] = new_attempt
    
    # Track tried URLs
    tried_urls = tool_context.state.get("tried_urls", [])
    current_url = tool_context.state.get("pdf_url", "")
    if current_url and current_url not in tried_urls:
        tried_urls.append(current_url)
        tool_context.state["tried_urls"] = tried_urls
    
    max_retries = 5
    remaining = max_retries - new_attempt
    
    print(f"  [Loop Control] Retry attempt {new_attempt}/{max_retries}")
    
    return {
        "attempt": new_attempt,
        "max_retries": max_retries,
        "remaining_retries": remaining,
        "should_continue": remaining > 0,
        "tried_urls": tried_urls
    }


def reset_company_state(tool_context: ToolContext) -> dict:
    """
    Resets per-company state variables before processing a new company.
    Called at the start of each company iteration.
    """
    # Reset retry counters
    tool_context.state["pdf_find_attempt"] = 0
    tool_context.state["tried_urls"] = []
    
    # Reset intermediate results
    tool_context.state["pdf_url"] = ""
    tool_context.state["pdf_url_raw"] = ""
    tool_context.state["pdf_file_path"] = ""
    tool_context.state["download_result"] = ""
    tool_context.state["raw_analysis"] = ""
    tool_context.state["financial_analysis"] = ""
    tool_context.state["final_summary"] = ""
    tool_context.state["structured_output"] = ""
    
    company_name = tool_context.state.get("company_name", "Unknown")
    print(f"  [Loop Control] State reset for new company: {company_name}")
    
    return {"status": "reset", "company": company_name}
