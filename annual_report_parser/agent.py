"""
Annual Report Parser Agent v2 - Nested Loop Architecture

Architecture:
1. Outer Loop (Company Orchestrator): Iterates over list of companies
2. Inner Loop (PDF Finder Retry): Retries finding/downloading PDFs up to 5 times
3. Sequential Pipeline per company: Analyze → Summarize → Store

Supports input formats:
- Single company: "Apple Inc."
- Comma-separated: "Apple, Microsoft, Tesla"
- JSON array: ["Apple", "Microsoft"]
"""

import json
import re
import os
from typing import Dict, Any, List, AsyncGenerator
from google.adk.agents import Agent, SequentialAgent, LoopAgent, BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.tools import google_search, FunctionTool
from google.adk.events import Event, EventActions
from google.genai import types as genai_types

from annual_report_parser.custom_tools import (

    download_pdf_from_url,
    read_pdf_as_base64,
    extract_pdf_url_from_search_results,
    store_in_pinecone,
    validate_pdf_url
)

from annual_report_parser.loop_tools import (
    exit_loop_success,
    exit_loop_failure,
    exit_all_companies_processed,
    increment_retry_counter,
    reset_company_state
)

# Wrap custom functions as ADK FunctionTools
download_tool = FunctionTool(func=download_pdf_from_url)
read_pdf_tool = FunctionTool(func=read_pdf_as_base64)
extract_url_tool = FunctionTool(func=extract_pdf_url_from_search_results)
store_tool = FunctionTool(func=store_in_pinecone)
validate_url_tool = FunctionTool(func=validate_pdf_url)

# Loop control tools
exit_success_tool = FunctionTool(func=exit_loop_success)
exit_failure_tool = FunctionTool(func=exit_loop_failure)
exit_all_done_tool = FunctionTool(func=exit_all_companies_processed)
increment_retry_tool = FunctionTool(func=increment_retry_counter)
reset_state_tool = FunctionTool(func=reset_company_state)


# ============================================================================
# CALLBACKS
# ============================================================================

def parse_company_list(callback_context: CallbackContext) -> None:
    """
    Parses the LLM's output to extract company list.
    The LLM outputs a JSON array of company names to 'parsed_companies' key.
    """
    # Read from the LLM's output (output_key='parsed_companies')
    llm_output = callback_context.state.get("parsed_companies", "")
    print(f"DEBUG [Parser Callback]: LLM output: {str(llm_output)[:300]}...")
    
    companies = []
    
    if isinstance(llm_output, str):
        llm_output = llm_output.strip()
        
        # Try to parse as JSON array
        try:
            # Clean markdown if present
            if llm_output.startswith("```"):
                llm_output = re.sub(r"^```[a-zA-Z]*\s*", "", llm_output)
                llm_output = re.sub(r"\s*```$", "", llm_output)
            
            parsed = json.loads(llm_output)
            if isinstance(parsed, list):
                companies = [str(c).strip() for c in parsed if c]
        except json.JSONDecodeError:
            # If not JSON, treat as single company name  
            if llm_output:
                companies = [llm_output]
    
    elif isinstance(llm_output, list):
        companies = [str(c).strip() for c in llm_output if c]
    
    # Fallback: If LLM output empty, try original user input
    if not companies:
        user_input = callback_context.state.get("user_input", "")
        if isinstance(user_input, str) and user_input.strip():
            companies = [user_input.strip()]
    
    if not companies:
        callback_context.state["pipeline_error"] = "ERROR: No company names provided."
        print("DEBUG [Parser Callback]: No companies found")
        return
    
    callback_context.state["company_list"] = companies
    callback_context.state["current_company_index"] = 0
    callback_context.state["total_companies"] = len(companies)
    callback_context.state["processed_companies"] = []
    
    print(f"DEBUG [Parser Callback]: Extracted {len(companies)} companies: {companies}")




def process_finder_output(callback_context: CallbackContext) -> None:
    """
    Processes the finder agent's output to extract and validate PDF URL.
    """
    finder_output = callback_context.state.get("pdf_url_raw", "")
    print(f"DEBUG [Finder]: Raw output preview: {str(finder_output)[:500]}...")
    
    callback_context.state["pdf_url"] = ""
    callback_context.state["url_valid"] = False
    
    if isinstance(finder_output, str):
        if "ERROR:" in finder_output or "no pdf" in finder_output.lower():
            callback_context.state["finder_error"] = finder_output
            return
        
        # Multiple regex patterns for PDF URLs
        pdf_patterns = [
            r'https?://[^\s<>"\'\`\[\]{}|\\^]+\.pdf(?:\?[^\s<>"\'\`]*)?',
            r'https?://[^\s<>"\'\`]+/files/[^\s<>"\'\`]+\.pdf',
            r'https?://[^\s<>"\'\`]+/doc[^\s<>"\'\`]*\.pdf',
        ]
        
        found_urls = []
        for pattern in pdf_patterns:
            matches = re.findall(pattern, finder_output, re.IGNORECASE)
            for url in matches:
                url = url.rstrip('.,;:!?)]\'\"')
                if url not in found_urls:
                    found_urls.append(url)
        
        if found_urls:
            # Prefer official domains
            preferred_domains = ['investor', 'ir.', 'annualreport', 'q4cdn', 'sec.gov']
            best_url = found_urls[0]
            for url in found_urls:
                for domain in preferred_domains:
                    if domain in url.lower():
                        best_url = url
                        break
            
            callback_context.state["pdf_url"] = best_url
            print(f"DEBUG [Finder]: Extracted PDF URL: {best_url}")
            return
        
        callback_context.state["finder_error"] = "No PDF URL found in search results"


def process_download_output(callback_context: CallbackContext) -> None:
    """
    Processes the downloader output and validates download success.
    """
    download_result = callback_context.state.get("download_result", "")
    print(f"DEBUG [Downloader]: Result preview: {str(download_result)[:200]}...")
    
    callback_context.state["pdf_file_path"] = ""
    callback_context.state["download_success"] = False
    
    if isinstance(download_result, str):
        try:
            json_match = re.search(r'\{[^{}]*"success"[^{}]*\}', download_result)
            if json_match:
                result = json.loads(json_match.group())
                if result.get("success") and result.get("file_path"):
                    callback_context.state["pdf_file_path"] = result["file_path"]
                    callback_context.state["pdf_file_size"] = result.get("file_size_mb", 0)
                    callback_context.state["download_success"] = True
                    print(f"DEBUG [Downloader]: PDF saved to: {result['file_path']}")
                else:
                    callback_context.state["download_error"] = result.get("error", "Unknown download error")
        except json.JSONDecodeError as e:
            print(f"DEBUG [Downloader]: Failed to parse JSON: {e}")
            if '.pdf' in download_result.lower():
                path_match = re.search(r'[A-Za-z]:[\\\/][^\s"\'<>|]+\.pdf', download_result)
                if path_match and os.path.exists(path_match.group()):
                    callback_context.state["pdf_file_path"] = path_match.group()
                    callback_context.state["download_success"] = True


def combine_analysis_results(callback_context: CallbackContext) -> None:
    """Combines analysis results from the analyst agent."""
    analysis = callback_context.state.get("raw_analysis", "")
    print(f"DEBUG [Analyst]: Raw analysis preview: {str(analysis)[:300]}...")
    callback_context.state["financial_analysis"] = analysis


def format_final_output(callback_context: CallbackContext) -> None:
    """Formats the final structured output."""
    summary = callback_context.state.get("final_summary", "")
    print(f"DEBUG [Summarizer]: Final output preview: {str(summary)[:300]}...")
    
    if isinstance(summary, str):
        try:
            clean_summary = summary.strip()
            if clean_summary.startswith("```"):
                clean_summary = re.sub(r"^```[a-zA-Z]*\s*", "", clean_summary)
                clean_summary = re.sub(r"\s*```$", "", clean_summary)
            
            parsed = json.loads(clean_summary)
            callback_context.state["structured_output"] = json.dumps(parsed, indent=2)
        except json.JSONDecodeError:
            callback_context.state["structured_output"] = summary


def track_processed_company(callback_context: CallbackContext) -> None:
    """Tracks successfully processed companies and increments index."""
    company_name = callback_context.state.get("company_name", "")
    processed = callback_context.state.get("processed_companies", [])
    
    if company_name and company_name not in processed:
        processed.append(company_name)
        callback_context.state["processed_companies"] = processed
    
    # Increment index for next iteration
    current_index = callback_context.state.get("current_company_index", 0)
    callback_context.state["current_company_index"] = current_index + 1
    
    print(f"DEBUG [Tracker]: Processed {len(processed)} companies so far")


# ============================================================================
# CUSTOM BASE AGENTS FOR LOOP CONTROL
# ============================================================================

def _make_content(text: str) -> genai_types.Content:
    """Helper to create properly typed Content for Events."""
    return genai_types.Content(
        role="model",
        parts=[genai_types.Part(text=text)]
    )


class DownloadCheckerAgent(BaseAgent):
    """
    Custom agent that checks download result and decides to exit or continue loop.
    If download successful, exits with success. Otherwise, continues retry.
    """
    
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        download_success = ctx.session.state.get("download_success", False)
        attempt = ctx.session.state.get("pdf_find_attempt", 0)
        max_attempts = 5
        
        if download_success:
            print(f"  [DownloadChecker] PDF downloaded successfully - exiting loop")
            yield Event(
                author=self.name,
                content=_make_content("PDF found and downloaded successfully."),
                actions=EventActions(escalate=True)
            )
        elif attempt >= max_attempts:
            print(f"  [DownloadChecker] Max retries ({max_attempts}) reached - exiting with failure")
            yield Event(
                author=self.name,
                content=_make_content(f"Failed to find PDF after {max_attempts} attempts."),
                actions=EventActions(escalate=True)
            )
        else:
            # Increment attempt counter
            ctx.session.state["pdf_find_attempt"] = attempt + 1
            print(f"  [DownloadChecker] Attempt {attempt + 1}/{max_attempts} failed, will retry")
            yield Event(
                author=self.name,
                content=_make_content(f"Retry attempt {attempt + 1} of {max_attempts}")
            )


class CompanyIteratorAgent(BaseAgent):
    """
    Custom agent that selects the next company and checks if all are processed.
    Exits the outer loop when all companies are done.
    """
    
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        company_list = ctx.session.state.get("company_list", [])
        current_index = ctx.session.state.get("current_company_index", 0)
        total = ctx.session.state.get("total_companies", len(company_list))
        
        if current_index >= total:
            processed = ctx.session.state.get("processed_companies", [])
            print(f"  [CompanyIterator] All {total} companies processed: {processed}")
            yield Event(
                author=self.name,
                content=_make_content(f"All {total} companies processed: {processed}"),
                actions=EventActions(escalate=True)
            )
        else:
            company_name = company_list[current_index]
            ctx.session.state["company_name"] = company_name
            
            # Reset per-company state
            ctx.session.state["pdf_find_attempt"] = 0
            ctx.session.state["tried_urls"] = []
            ctx.session.state["pdf_url"] = ""
            ctx.session.state["pdf_file_path"] = ""
            ctx.session.state["download_success"] = False
            ctx.session.state["raw_analysis"] = ""
            ctx.session.state["financial_analysis"] = ""
            ctx.session.state["final_summary"] = ""
            
            print(f"  [CompanyIterator] Processing company {current_index + 1}/{total}: {company_name}")
            yield Event(
                author=self.name,
                content=_make_content(f"Processing company {current_index + 1}/{total}: {company_name}")
            )




# ============================================================================
# AGENT DEFINITIONS
# ============================================================================

# 1. COMPANY INPUT PARSER - Parses single or list of companies
company_input_parser = Agent(
    model="gemini-2.5-flash",
    name="company_input_parser",
    description="Parses user input to extract company name(s) as a list.",
    instruction="""You are an input parser. Extract company names from the user input.

SUPPORTED FORMATS:
1. Single company: "Apple Inc." → ["Apple Inc."]
2. Comma-separated: "Apple, Microsoft, Tesla" → ["Apple Inc.", "Microsoft Corporation", "Tesla Inc."]
3. JSON array: ["Apple", "Microsoft"] → ["Apple Inc.", "Microsoft Corporation"]
4. Ticker symbols: "AAPL, MSFT" → ["Apple Inc.", "Microsoft Corporation"]

OUTPUT:
Return ONLY a JSON array of official company names. Example:
["Apple Inc.", "Microsoft Corporation", "Tesla Inc."]

RULES:
- Convert ticker symbols to full company names
- Remove duplicates
- Ensure proper company name format (Inc., Corporation, etc.)
""",
    output_key="parsed_companies",
    after_agent_callback=parse_company_list
)


# 2. ALTERNATIVE FINDER AGENT - Tries different search strategies
alternative_finder_agent = Agent(
    model="gemini-2.5-flash",  # Reverted to Flash for speed/cost
    name="alternative_finder",
    description="Searches for annual report PDF using multiple strategies.",
    instruction="""You are a fast financial researcher.

COMPANY: {company_name}
ATTEMPT: {pdf_find_attempt} of 5
PREVIOUSLY TRIED URLs: {tried_urls}

OBJECTIVE: Find the DIRECT PDF LINK for the Annual Report.

SEARCH STRATEGY (Choose ONE based on attempt number):
1. Attempt 0 (First Try): "{company_name} annual report 2024 pdf" 
   -> Look for the OFFICIAL company website result first.
2. Attempt 1: "{company_name} investor relations annual report pdf"
3. Attempt 2: "{company_name} 10-K annual report filetype:pdf"
4. Attempt 3: "{company_name} financial results 2023 pdf"
5. Attempt 4: "{company_name} annual report 2023 pdf download"

CRITICAL INSTRUCTIONS:
- You MUST use the `google_search` tool to perform the search query defined above.
- On Attempt 0, you MUST try to find the official company PDF immediately.
- Prioritize links ending in `.pdf`.
- If you find a direct PDF link, return it immediately.
- If you see a "Downloads" or "Reports" page on the official site, look for the PDF link there.

OUTPUT:
Return ONLY the raw PDF URL.
If absolutely no PDF is found, return string: "ERROR: No PDF found"
""",
    tools=[google_search],
    output_key="pdf_url_raw",
    after_agent_callback=process_finder_output
)


# 3. URL VALIDATOR AGENT - Validates PDF URL accessibility
url_validator_agent = Agent(
    model="gemini-2.5-flash",
    name="url_validator",
    description="Validates that a PDF URL is accessible before downloading.",
    instruction="""You are a URL validator.

URL to validate: {pdf_url}

Use the validate_pdf_url tool to check if the URL is valid and accessible.

If the validation result shows valid=True, respond with:
"URL_VALID: {pdf_url}"

If invalid, respond with:
"URL_INVALID: [reason from validation result]"
""",
    tools=[validate_url_tool],
    output_key="url_validation_result"
)


# 4. PDF DOWNLOADER AGENT
downloader_agent = Agent(
    model="gemini-2.5-flash",
    name="pdf_downloader",
    description="Downloads the annual report PDF from the validated URL.",
    instruction="""You are a file download specialist.

TASK: Download the PDF file from {pdf_url}

STEPS:
1. Check if {pdf_url} is valid and not empty
2. Use the download_pdf_from_url tool with the URL
3. Report the complete result including file_path

ERROR HANDLING:
- If {pdf_url} is empty: respond with {"success": false, "error": "No PDF URL provided"}
- If download fails: include the error message

IMPORTANT: Always use the download_pdf_from_url tool and report exact results.
""",
    tools=[download_tool],
    output_key="download_result",
    after_agent_callback=process_download_output
)


# 5. DOWNLOAD CHECKER - Custom BaseAgent for loop control
download_checker_agent = DownloadCheckerAgent(
    name="download_checker",
    description="Checks download result and controls retry loop flow."
)


# 6. PDF ANALYST AGENT
analyst_agent = Agent(
    model="gemini-2.5-flash",
    name="report_analyst",
    description="Analyzes the annual report PDF to extract financial data.",
    instruction="""You are a senior financial analyst.

TASK: Analyze the annual report for {company_name}.
PDF file path: {pdf_file_path}

If {pdf_file_path} is empty or missing, respond with:
ERROR: No PDF file available for analysis.

STEPS:
1. Use read_pdf_as_base64 tool with file path: {pdf_file_path}
2. The tool uploads AND analyzes the PDF, returning detailed analysis
3. Return the analysis content directly

The tool extracts: financial data, products/services, business segments,
corporate structure, leadership, and key highlights.

OUTPUT: Return the analysis from the tool.
""",
    tools=[read_pdf_tool],
    output_key="raw_analysis",
    after_agent_callback=combine_analysis_results
)


# 7. SUMMARIZER AGENT
summarizer_agent = Agent(
    model="gemini-2.5-flash",
    name="output_summarizer",
    description="Summarizes extracted information into structured JSON.",
    instruction="""You are a data structuring specialist.

TASK: Structure the financial analysis from {financial_analysis} into clean JSON.

OUTPUT FORMAT - Return ONLY valid JSON (no markdown):
{
    "company_name": "Official Name",
    "report_year": "FY2024",
    "analysis_timestamp": "ISO date",
    "financial_summary": {
        "revenue": [{"year": "2024", "amount": "$XXX billion", "growth_yoy": "+X%"}],
        "net_income": [{"year": "2024", "amount": "$XX billion"}],
        "key_metrics": {"gross_margin": "XX%", "operating_margin": "XX%", "eps": "$X.XX"}
    },
    "products_services": {"products": [], "services": [], "new_launches": []},
    "business_segments": [{"name": "", "revenue": "", "percentage_of_total": ""}],
    "geographic_segments": [{"region": "", "revenue": "", "percentage_of_total": ""}],
    "corporate_structure": {"parent_company": null, "subsidiaries": [], "recent_acquisitions": []},
    "leadership": {"ceo": {"name": "", "since": ""}, "cfo": {"name": ""}, "key_executives": []},
    "highlights": {"achievements": [], "future_outlook": "", "risk_factors": []},
    "data_quality": {"completeness": "HIGH/MEDIUM/LOW", "source": "Annual Report", "notes": ""}
}

GUIDELINES:
1. Return ONLY valid JSON
2. Use "N/A" for missing strings, [] for missing lists, null for unknown
""",
    output_key="final_summary",
    after_agent_callback=format_final_output
)


# 8. STORAGE AGENT
storage_agent = Agent(
    model="gemini-2.5-flash",
    name="data_storage",
    description="Stores the financial analysis in Pinecone.",
    instruction="""You MUST call the store_in_pinecone tool to save the analysis.

REQUIRED PARAMETERS:
- company_name: "{company_name}"
- report_year: "2024"
- structured_data: JSON from {structured_output}
- analysis_content: Analysis from {financial_analysis}

DO NOT skip calling the tool. You MUST execute store_in_pinecone.
After calling, report success or failure.
""",
    tools=[store_tool],
    output_key="storage_result",
    after_agent_callback=track_processed_company
)


# 9. COMPANY ITERATOR - Custom BaseAgent for outer loop control
company_iterator_agent = CompanyIteratorAgent(
    name="company_iterator",
    description="Selects next company and controls outer loop flow."
)


# ============================================================================
# NESTED LOOP ORCHESTRATION
# ============================================================================

# Inner Loop: PDF Find & Download with Retry (max 5 attempts)
pdf_find_retry_loop = LoopAgent(
    name="pdf_find_retry_loop",
    description="Retries finding and downloading PDF up to 5 times with alternative search strategies.",
    sub_agents=[
        alternative_finder_agent,
        url_validator_agent,
        downloader_agent,
        download_checker_agent,  # Controls loop exit
    ],
    max_iterations=5
)

# Per-Company Analysis Pipeline (Sequential)
single_company_pipeline = SequentialAgent(
    name="single_company_analysis",
    description="Processes a single company: find PDF → analyze → summarize → store.",
    sub_agents=[
        company_iterator_agent,  # Selects next company, resets state
        pdf_find_retry_loop,      # Inner loop: find & download PDF
        analyst_agent,            # Analyze PDF content
        summarizer_agent,         # Structure into JSON
        storage_agent,            # Store in Pinecone
    ]
)

# Outer Loop: Company Orchestrator
company_orchestrator_loop = LoopAgent(
    name="company_orchestrator",
    description="Iterates through all companies in the list, processing each sequentially.",
    sub_agents=[single_company_pipeline],
    max_iterations=50  # Max companies per run
)

# Root Agent: Parse Input → Process All Companies
root_agent = SequentialAgent(
    name="annual_report_parser",
    description="""Analyzes annual reports for one or multiple companies.

INPUT FORMATS SUPPORTED:
- Single company: "Apple Inc."
- Comma-separated: "Apple, Microsoft, Tesla"
- JSON array: ["Apple", "Microsoft"]

For each company, this agent:
1. Searches for the company's annual report PDF (with retry logic)
2. Downloads and analyzes the PDF using Gemini
3. Extracts financial data, products, segments, leadership
4. Stores structured results in Pinecone

OUTPUT: Structured JSON analysis for each company stored in Pinecone.""",
    sub_agents=[
        company_input_parser,      # Parse input to company list
        company_orchestrator_loop  # Outer loop: process each company
    ]
)
