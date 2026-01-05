"""
Company Profiler Agent - Main entry point

A multi-agent system that:
1. Identifies top companies in a given industry
2. Gathers detailed company information IN PARALLEL (5 workers x 3 companies each)
3. Summarizes company data
4. Generates A2UI cards for visualization

Uses Google ADK SequentialAgent + ParallelAgent for orchestration.
"""

import json
import re
from google.adk.agents import Agent, SequentialAgent, ParallelAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import google_search

from company_profiler.a2ui_schema import A2UI_SCHEMA


def extract_a2ui_messages(text: str) -> list:
    """
    Extract A2UI JSON messages from text with ---a2ui_JSON--- delimiters.
    
    Args:
        text: Raw text output from A2UI generator containing delimited JSON
        
    Returns:
        List of parsed A2UI message dictionaries
    """
    messages = []
    
    # Split by the delimiter
    parts = text.split("---a2ui_JSON---")
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
            
        # Try to parse as JSON
        try:
            # Find JSON object in the part (may have extra text)
            json_match = re.search(r'\{[\s\S]*\}', part)
            if json_match:
                json_str = json_match.group()
                parsed = json.loads(json_str)
                if isinstance(parsed, dict):
                    messages.append(parsed)
        except json.JSONDecodeError:
            continue
    
    return messages


def process_a2ui_output(callback_context: CallbackContext) -> None:
    """
    Process the A2UI generator output and extract JSON messages.
    Stores parsed messages in state for A2A transmission.
    """
    a2ui_output = callback_context.state.get("a2ui_output", "")
    
    if isinstance(a2ui_output, str):
        messages = extract_a2ui_messages(a2ui_output)
        if messages:
            # Store parsed messages for A2A transmission
            callback_context.state["a2ui_messages"] = messages
            # Also store as JSON string for compatibility
            callback_context.state["a2ui_output_parsed"] = json.dumps(messages)


def validate_market_identifier_output(callback_context: CallbackContext) -> None:
    """
    Validates the market_identifier output after execution.
    Checks if company_list is a valid JSON array. Limits to 15 companies for parallel processing.
    """
    company_list = callback_context.state.get("company_list", "")
    print(f"DEBUG: Market Identifier output preview: {str(company_list)[:50]}...")
    
    # Check for error responses
    if isinstance(company_list, str):
        if company_list.startswith("ERROR:") or "No companies found" in company_list:
            callback_context.state["pipeline_error"] = company_list
            return
        
        # Try to parse as JSON
        try:
            parsed = json.loads(company_list)
            if not isinstance(parsed, list) or len(parsed) == 0:
                callback_context.state["pipeline_error"] = "ERROR: Market Identifier returned invalid company list format."
            else:
                # Limit to 15 companies for 5 parallel workers x 3 companies each
                print(f"DEBUG: Limiting companies from {len(parsed)} to 15")
                callback_context.state["company_list"] = json.dumps(parsed[:15])
        except json.JSONDecodeError:
            callback_context.state["pipeline_error"] = "ERROR: Market Identifier output is not valid JSON."
            
    # Fallback to ensure it exists
    if "company_list" not in callback_context.state or not callback_context.state["company_list"]:
         print("DEBUG: Setting default company_list to avoid crash")
         callback_context.state["company_list"] = "[]"


def combine_company_data(callback_context: CallbackContext) -> None:
    """
    Combines all 5 parallel gatherer outputs into a single company_data array.
    Each gatherer outputs to company_data_0 through company_data_4.
    """
    all_companies = []
    
    for i in range(5):
        key = f"company_data_{i}"
        data = callback_context.state.get(key, "[]")
        print(f"DEBUG: Combining {key}: {str(data)[:50]}...")
        
        if isinstance(data, str):
            try:
                parsed = json.loads(data)
                if isinstance(parsed, list):
                    all_companies.extend(parsed)
            except json.JSONDecodeError:
                print(f"DEBUG: Failed to parse {key}")
                continue
    
    print(f"DEBUG: Combined {len(all_companies)} companies from parallel gatherers")
    callback_context.state["company_data"] = json.dumps(all_companies)


# Market Identifier Agent - Identifies top 15 companies in a given industry
market_identifier = Agent(
    model="gemini-2.5-flash",
    name="market_identifier",
    description="Identifies top companies in a given industry using web search with URL context.",
    instruction="""You are an expert market research analyst specializing in industry landscape analysis.

IMPORTANT INPUT VALIDATION:
- If the user's input is empty or contains only whitespace characters, respond with:
  "ERROR: Invalid input. Please provide a valid industry title (e.g., 'Drone Automation', 'Electric Vehicles', 'Cloud Computing')."
- Do NOT proceed with any search if the input is invalid.

TASK:
When given a valid industry title (e.g., "Drone Automation"), conduct comprehensive market research to identify the top 15 companies operating in that industry.

RESEARCH METHODOLOGY:
1. Use Google Search to find authoritative sources about the industry:
   - Industry reports and market analysis (e.g., Gartner, Forrester, CB Insights)
   - Business news articles from reputable sources (Bloomberg, Reuters, TechCrunch)
   - Industry association websites and directories
   - Company ranking lists and market share reports

2. Cross-reference multiple sources to ensure accuracy:
   - Verify company names are spelled correctly
   - Confirm companies are actually operating in the specified industry
   - Prioritize companies with significant market presence

COMPANY SELECTION CRITERIA:
- Market leaders with significant revenue or market share
- Well-funded startups with notable growth trajectory
- Companies with innovative products/services in the space
- Both public and private companies
- Global and regional players if relevant

OUTPUT FORMAT - CRITICAL:
You MUST return ONLY a valid JSON array of exactly 15 company names as strings. No other text, no explanations.

CORRECT OUTPUT EXAMPLE:
["Company1", "Company2", "Company3", "Company4", "Company5", "Company6", "Company7", "Company8", "Company9", "Company10", "Company11", "Company12", "Company13", "Company14", "Company15"]

GUIDELINES:
1. Return exactly 15 companies
2. Use official company names
3. If no companies are found, respond with:
   "No companies found for the specified industry."

Your output will be stored in session state as "company_list" for use by parallel gatherer agents.""",
    tools=[google_search],
    output_key="company_list",
    after_agent_callback=validate_market_identifier_output
)


# Create a template for info gatherer instructions
def create_gatherer_instruction(start_idx: int, end_idx: int) -> str:
    """Creates instruction for a parallel gatherer handling specific company indices."""
    return f"""You are a senior financial analyst. Research companies from the session state variable {{company_list}}.

IMPORTANT: You are responsible for researching companies at indices {start_idx} to {end_idx} (inclusive) from the company_list array.

INPUT:
{{company_list}} contains a JSON array of 15 company names. You MUST research ONLY companies at indices {start_idx}, {start_idx + 1}, and {end_idx}.

TASK:
For each of your 3 assigned companies, gather:
1. Stock ticker (or "Private")
2. Latest annual revenue (e.g., "$4.2B")
3. CEO name
4. Headquarters location
5. Main business segments (2-5 items)
6. Revenue history (last 3 years)

OUTPUT FORMAT - CRITICAL:
Return ONLY a valid JSON array containing exactly 3 company objects:

[
  {{
    "name": "Company Name",
    "ticker": "TICK",
    "latest_revenue": "$X.XB",
    "ceo": "CEO Name",
    "headquarters": "City, Country",
    "segments": ["Segment1", "Segment2"],
    "revenue_history": [
      {{"year": 2022, "revenue": 1.0}},
      {{"year": 2023, "revenue": 1.2}},
      {{"year": 2024, "revenue": 1.5}}
    ]
  }}
]

FALLBACK:
- Use "N/A" for unavailable fields
- Use [] for unavailable arrays
- NEVER skip a company - always output exactly 3 companies"""


# Create 5 parallel info gatherers, each handling 3 companies
# Gatherer 0: indices 0-2, Gatherer 1: indices 3-5, etc.
company_gatherer_0 = Agent(
    model="gemini-2.5-flash",
    name="company_gatherer_0",
    description="Gathers info for companies 0-2",
    instruction=create_gatherer_instruction(0, 2),
    tools=[google_search],
    output_key="company_data_0"
)

company_gatherer_1 = Agent(
    model="gemini-2.5-flash",
    name="company_gatherer_1",
    description="Gathers info for companies 3-5",
    instruction=create_gatherer_instruction(3, 5),
    tools=[google_search],
    output_key="company_data_1"
)

company_gatherer_2 = Agent(
    model="gemini-2.5-flash",
    name="company_gatherer_2",
    description="Gathers info for companies 6-8",
    instruction=create_gatherer_instruction(6, 8),
    tools=[google_search],
    output_key="company_data_2"
)

company_gatherer_3 = Agent(
    model="gemini-2.5-flash",
    name="company_gatherer_3",
    description="Gathers info for companies 9-11",
    instruction=create_gatherer_instruction(9, 11),
    tools=[google_search],
    output_key="company_data_3"
)

company_gatherer_4 = Agent(
    model="gemini-2.5-flash",
    name="company_gatherer_4",
    description="Gathers info for companies 12-14",
    instruction=create_gatherer_instruction(12, 14),
    tools=[google_search],
    output_key="company_data_4"
)

# Parallel Agent - runs all 5 gatherers concurrently
parallel_research = ParallelAgent(
    name="parallel_research",
    sub_agents=[
        company_gatherer_0,
        company_gatherer_1,
        company_gatherer_2,
        company_gatherer_3,
        company_gatherer_4
    ]
)

# Data Summarizer - combines all parallel outputs into unified company_data
data_summarizer = Agent(
    model="gemini-2.5-flash",
    name="data_summarizer",
    description="Combines parallel gatherer outputs into a single company data array.",
    instruction="""You are a data aggregator. Your job is to combine company data from 5 parallel research agents.

INPUT:
You have access to 5 state variables:
- {company_data_0} - Companies 0-2
- {company_data_1} - Companies 3-5
- {company_data_2} - Companies 6-8
- {company_data_3} - Companies 9-11
- {company_data_4} - Companies 12-14

Each contains a JSON array of company objects.

TASK:
Combine ALL company objects from all 5 sources into a single JSON array.

OUTPUT FORMAT - CRITICAL:
Return ONLY a valid JSON array containing all 15 company objects combined:

[
  {"name": "Company1", ...},
  {"name": "Company2", ...},
  ...
  {"name": "Company15", ...}
]

GUIDELINES:
1. Include ALL companies from ALL sources
2. Preserve the exact structure of each company object
3. Do NOT modify any data
4. Output pure JSON only, no explanation text""",
    output_key="company_data",
    after_agent_callback=combine_company_data
)


# A2UI Generator Agent - Transforms company data into A2UI JSON messages
A2UI_GENERATOR_INSTRUCTION = f"""You are an A2UI generator specialist that transforms company data into rich, interactive UI cards.

INPUT:
You will receive company data from the session state variable {{company_data}}.
This is a JSON array of 15 company objects with the following structure:
- name: Company name
- ticker: Stock ticker or "Private"
- latest_revenue: Revenue formatted like "$4.2B"
- ceo: CEO name
- headquarters: Location as "City, Country"
- segments: Array of business segment strings
- revenue_history: Array of {{year, revenue}} objects

TASK:
Generate A2UI JSON messages to render company profile cards. You MUST output exactly THREE A2UI messages in sequence, separated by the delimiter ---a2ui_JSON---

A2UI SCHEMA REFERENCE:
{A2UI_SCHEMA}

OUTPUT FORMAT - CRITICAL:
Your output MUST follow this exact structure with the delimiter between each message:

---a2ui_JSON---
<surfaceUpdate JSON>
---a2ui_JSON---
<dataModelUpdate JSON>
---a2ui_JSON---
<beginRendering JSON>
---a2ui_JSON---

MESSAGE 1 - surfaceUpdate:
Define the component tree for company cards using this structure:
- Root: Column with id "company-grid" containing a template card
- Template Card: Card with id "company-card-template" bound to "/companies" for dynamic list rendering
- Card Content: Column containing header, details, segments, revenue history

MESSAGE 2 - dataModelUpdate:
Populate the data model with ALL 15 companies from {{company_data}}:
{{
  "dataModelUpdate": {{
    "surfaceId": "company-profiler",
    "path": "/",
    "contents": [
      {{
        "key": "companies",
        "valueMap": [
          {{"key": "0", "valueMap": [...company 0 data...]}},
          {{"key": "1", "valueMap": [...company 1 data...]}},
          ... all 15 companies ...
          {{"key": "14", "valueMap": [...company 14 data...]}}
        ]
      }}
    ]
  }}
}}

MESSAGE 3 - beginRendering:
Signal the client to start rendering:
{{
  "beginRendering": {{
    "surfaceId": "company-profiler",
    "root": "company-grid"
  }}
}}

GUIDELINES:
1. Generate EXACTLY three A2UI messages separated by ---a2ui_JSON---
2. Each message MUST be valid JSON (NO comments like //)
3. Transform ALL 15 companies into the dataModelUpdate
4. Use keys "0" through "14" for the company entries

Your output will be stored in session state as "a2ui_output"."""

a2ui_generator = Agent(
    model="gemini-2.5-flash",
    name="a2ui_generator",
    description="Generates A2UI JSON messages to render company profile cards.",
    instruction=A2UI_GENERATOR_INSTRUCTION,
    output_key="a2ui_output",
    after_agent_callback=process_a2ui_output
)

# Sequential Pipeline Orchestrator
# Flow: market_identifier → parallel_research (5 gatherers) → data_summarizer → a2ui_generator
company_profiler = SequentialAgent(
    name="company_profiler",
    description="Orchestrates the company profiling pipeline with parallel info gathering.",
    sub_agents=[market_identifier, parallel_research, data_summarizer, a2ui_generator]
)

# Export as root_agent for ADK web UI
root_agent = company_profiler

# A2A Server Configuration
import os

A2A_PORT = int(os.environ.get("A2A_PORT", 8001))

try:
    from google.adk.a2a.utils.agent_to_a2a import to_a2a
    from starlette.middleware.cors import CORSMiddleware
    
    # Create A2A-compatible application
    a2a_app = to_a2a(root_agent, port=A2A_PORT)
    
    # Add CORS middleware to allow browser requests from Lit client
    a2a_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
except ImportError:
    # A2A support not installed - google-adk[a2a] required
    a2a_app = None
