# Google ADK Technical Reference & Naming Clarification

## 🎯 Critical Naming Distinctions

### The Confusing Names - CLARIFIED

| Name | What It Is | NOT To Be Confused With |
|------|-----------|------------------------|
| **ADK** | Agent Development Kit - Python/TS/Go/Java framework for building agents | SDK (Software Development Kit) |
| **A2UI** | Agent-to-User Interface - Protocol for agents to generate UIs | ADK, A2A |
| **A2A** | Agent-to-Agent - Protocol for agent communication | A2UI, ADK |
| **Vertex AI SDK** | Google Cloud SDK for deploying to Vertex AI | ADK (which is the agent framework) |
| **GenAI SDK** | Google's Generative AI SDK (includes Gemini API) | ADK, Vertex AI SDK |
| **Agent Engine** | Vertex AI managed runtime for deploying agents | ADK (the framework), Vertex AI (the platform) |
| **GenUI SDK** | Flutter SDK that uses A2UI under the hood | A2UI (the protocol) |

### Quick Reference

```
ADK = Build agents (framework)
A2A = Agents talk to agents (protocol)
A2UI = Agents generate UIs (protocol)
Vertex AI Agent Engine = Deploy agents (cloud service)
Vertex AI SDK = Interface to deploy to Vertex AI
GenAI SDK = Access to Gemini models
```

---

## 📦 Installation Matrix

### Python

```bash
# Core ADK
pip install google-adk

# ADK with A2A support
pip install google-adk[a2a]

# ADK with Vertex AI Agent Engine support
pip install google-cloud-aiplatform[agent_engines,adk]

# Full installation (everything)
pip install google-cloud-aiplatform[agent_engines,adk] google-adk[a2a]

# Development version (latest from GitHub)
pip install git+https://github.com/google/adk-python.git@main
```

### TypeScript

```bash
# Initialize project
npm init -y

# Install ADK
npm install @google/adk

# Install A2UI renderer (if building UI)
npm install @a2ui/lit
# or
npm install @a2ui/angular
```

### Go

```bash
go get google.golang.org/adk
```

### Java

**Maven (pom.xml)**:
```xml
<dependency>
  <groupId>com.google.adk</groupId>
  <artifactId>google-adk</artifactId>
  <version>0.3.0</version>
</dependency>
```

**Gradle (build.gradle)**:
```gradle
dependencies {
  implementation 'com.google.adk:google-adk:0.3.0'
}
```

---

## 🔑 Authentication Setup

### Local Development

#### Option 1: Google AI Studio (Gemini API)

```bash
# 1. Get API key from https://aistudio.google.com/
# 2. Set environment variable
export GOOGLE_API_KEY="your_api_key_here"

# 3. Create .env file (optional)
echo "GOOGLE_GENAI_USE_VERTEXAI=FALSE" > .env
echo "GOOGLE_API_KEY=your_api_key_here" >> .env
```

#### Option 2: Vertex AI (Google Cloud)

```bash
# 1. Install gcloud CLI
# 2. Authenticate
gcloud auth application-default login

# 3. Set project
gcloud config set project YOUR_PROJECT_ID

# 4. Enable APIs
gcloud services enable aiplatform.googleapis.com
gcloud services enable storage.googleapis.com

# 5. Create .env file
echo "GOOGLE_GENAI_USE_VERTEXAI=TRUE" > .env
echo "GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID" >> .env
echo "GOOGLE_CLOUD_LOCATION=us-central1" >> .env
```

### Python Code Authentication

```python
import vertexai

# For Vertex AI
client = vertexai.Client(
    project="YOUR_PROJECT_ID",
    location="us-central1"
)

# For Google AI Studio (Gemini API)
# Just set GOOGLE_API_KEY environment variable
# ADK will automatically use it
```

---

## 🏗️ Project Structure

### Recommended Structure for ADK Project

```
my-agent-project/
├── .env                          # Environment variables
├── .gitignore                    # Git ignore file
├── requirements.txt              # Python dependencies
├── README.md                     # Project documentation
│
├── agents/                       # Agent definitions
│   ├── __init__.py
│   ├── main_agent/
│   │   ├── __init__.py
│   │   ├── agent.py             # Main agent definition
│   │   └── tools.py             # Custom tools
│   │
│   └── sub_agents/
│       ├── __init__.py
│       ├── research_agent/
│       │   ├── __init__.py
│       │   └── agent.py
│       └── analysis_agent/
│           ├── __init__.py
│           └── agent.py
│
├── tools/                        # Shared custom tools
│   ├── __init__.py
│   ├── database_tools.py
│   └── api_tools.py
│
├── tests/                        # Tests
│   ├── __init__.py
│   ├── test_agents.py
│   └── test_tools.py
│
├── evaluation/                   # Evaluation datasets
│   ├── test_cases.evalset.json
│   └── scenarios.json
│
└── deployment/                   # Deployment configs
    ├── agent_config.yaml
    └── requirements.txt
```

### Minimal Agent Structure

```
simple-agent/
├── .env
├── agent.py
└── __init__.py
```

---

## 🚀 Running Agents

### Method 1: ADK Web UI (Recommended for Development)

```bash
# Start web UI
adk web

# With specific path
adk web path/to/agents/

# With no-reload (Windows fix)
adk web --no-reload

# Open browser to http://localhost:8000
```

### Method 2: ADK CLI

```bash
# Run agent interactively
adk run path/to/agent

# Exit with Ctrl+C
```

### Method 3: Python Script

```python
import asyncio
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Define agent
agent = Agent(
    model="gemini-2.0-flash",
    name="my_agent",
    instruction="You are a helpful assistant.",
    tools=[]
)

async def main():
    # Setup
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name="my_app",
        user_id="user123",
        session_id="session123"
    )
    
    runner = Runner(
        agent=agent,
        app_name="my_app",
        session_service=session_service
    )
    
    # Query
    content = types.Content(
        role='user',
        parts=[types.Part(text="Hello!")]
    )
    
    events = runner.run(
        user_id="user123",
        session_id="session123",
        new_message=content
    )
    
    for event in events:
        if event.is_final_response():
            print(event.content.parts[0].text)

if __name__ == "__main__":
    asyncio.run(main())
```

### Method 4: API Server

```bash
# Start API server
adk api_server path/to/agent

# With A2A support
adk api_server --a2a path/to/agent

# Custom port
adk api_server --port 8080 path/to/agent
```

---

## 🧪 Evaluation

### Create Evaluation Dataset

**Format**: JSON file with `.evalset.json` extension

```json
{
  "test_cases": [
    {
      "id": "test_1",
      "input": "What is the weather in New York?",
      "expected_output": "Should use google_search tool",
      "metadata": {
        "category": "search",
        "difficulty": "easy"
      }
    },
    {
      "id": "test_2",
      "input": "Calculate 15% tip on $50",
      "expected_output": "Should calculate $7.50",
      "metadata": {
        "category": "math",
        "difficulty": "easy"
      }
    }
  ]
}
```

### Run Evaluation

```bash
# CLI evaluation
adk eval path/to/agent path/to/evalset.json

# With specific metrics
adk eval path/to/agent path/to/evalset.json --metrics accuracy,latency
```

### Programmatic Evaluation

```python
from vertexai import types
import pandas as pd

# Prepare dataset
session_inputs = types.evals.SessionInput(
    user_id="user_123",
    state={}
)

prompts = [
    "What is the weather in New York?",
    "Calculate 15% tip on $50"
]

dataset = pd.DataFrame({
    "prompt": prompts,
    "session_inputs": [session_inputs] * len(prompts)
})

# Run inference
dataset_with_inference = client.evals.run_inference(
    agent=agent_engine_resource_name,
    src=dataset
)

# Create evaluation run
agent_info = types.evals.AgentInfo.load_from_agent(
    my_agent,
    agent_engine_resource_name
)

evaluation_run = client.evals.create_evaluation_run(
    dataset=dataset_with_inference,
    agent_info=agent_info,
    metrics=[
        types.RubricMetric.FINAL_RESPONSE_QUALITY,
        types.RubricMetric.TOOL_USE_QUALITY,
        types.RubricMetric.HALLUCINATION,
        types.RubricMetric.SAFETY
    ],
    dest="gs://your-bucket/eval-results"
)

# View results
evaluation_run.show()
```

---

## 🔧 Configuration

### Agent Configuration

```python
from google.adk.agents import Agent
from google.genai import types

agent = Agent(
    # Required
    model="gemini-2.0-flash",           # Model to use
    name="my_agent",                     # Unique agent name
    
    # Optional - Instructions
    instruction="Your main instructions",
    global_instruction="Context for all agents",
    static_instruction="Never changes",
    
    # Optional - Tools
    tools=[tool1, tool2],
    
    # Optional - Sub-agents
    sub_agents=[agent1, agent2],
    description="Description for routing",
    
    # Optional - Advanced
    generate_content_config=types.GenerateContentConfig(
        temperature=0.7,
        max_output_tokens=2048,
        top_p=0.95,
        top_k=40,
        safety_settings=[
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.OFF
            )
        ]
    ),
    
    # Optional - State management
    output_key="result",                 # Key to store output in state
    
    # Optional - Schema
    input_schema={"type": "object"},     # Input validation schema
    output_schema={"type": "object"}     # Output validation schema
)
```

### Session Configuration

```python
from google.adk.sessions import InMemorySessionService, FileSessionService

# In-memory (for local testing)
session_service = InMemorySessionService()

# File-based (persistent)
session_service = FileSessionService(
    base_path="./sessions"
)

# Create session
await session_service.create_session(
    app_name="my_app",
    user_id="user123",
    session_id="session123"
)
```

### Run Configuration

```python
from google.adk.agents import RunConfig

run_config = RunConfig(
    max_llm_calls=10,                    # Max LLM calls per invocation
    streaming_mode="full",               # "full", "partial", or "none"
    response_modalities=["text"],        # ["text", "audio", "image"]
    enable_affective_dialog=False,       # Emotional responses
    save_input_blobs_as_artifacts=True   # Save uploaded files
)
```

---

## 🌐 Deployment to Vertex AI Agent Engine

### Prerequisites

```bash
# 1. Enable APIs
gcloud services enable aiplatform.googleapis.com
gcloud services enable storage.googleapis.com

# 2. Create Cloud Storage bucket
gsutil mb gs://your-agent-bucket

# 3. Set IAM permissions
# - Vertex AI User (roles/aiplatform.user)
# - Storage Admin (roles/storage.admin)
```

### Deploy Agent

```python
import vertexai
from vertexai.agent_engines import AdkApp

# Initialize client
client = vertexai.Client(
    project="YOUR_PROJECT_ID",
    location="us-central1"
)

# Create AdkApp
app = AdkApp(agent=your_agent)

# Deploy to Agent Engine
remote_agent = client.agent_engines.create(
    agent=app,
    config={
        "requirements": [
            "google-cloud-aiplatform[agent_engines,adk]",
            "requests",  # Add your dependencies
        ],
        "staging_bucket": "gs://your-agent-bucket",
        "env_vars": {
            "CUSTOM_VAR": "value"
        }
    }
)

print(f"Agent deployed: {remote_agent.api_resource.name}")
```

### Query Deployed Agent

```python
# Query the deployed agent
async for event in remote_agent.async_stream_query(
    user_id="user123",
    message="Hello, agent!"
):
    print(event)
```

### Manage Deployed Agents

```python
# List agents
agents = client.agent_engines.list()
for agent in agents:
    print(f"Agent: {agent.name}")

# Get specific agent
agent = client.agent_engines.get(name="agent_resource_name")

# Delete agent
remote_agent.delete(force=True)
```

---

## 🔌 A2A Protocol Setup

### Exposing an Agent

#### Method 1: Using `to_a2a()`

```python
from google.adk.a2a.utils.agent_to_a2a import to_a2a

# Your agent
root_agent = Agent(
    model='gemini-2.0-flash',
    name='my_service_agent',
    instruction="Your instructions",
    tools=[your_tools]
)

# Convert to A2A
a2a_app = to_a2a(root_agent, port=8001)

# Save to file (e.g., agent.py)
# Then run with uvicorn:
# uvicorn path.to.agent:a2a_app --host localhost --port 8001
```

#### Method 2: Using `adk api_server`

```bash
# Create agent card (agent-card.json)
# Then start server
adk api_server --a2a --port 8001 path/to/agent/folder
```

### Consuming a Remote Agent

```python
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.agents.remote_a2a_agent import AGENT_CARD_WELL_KNOWN_PATH

# Connect to remote agent
remote_agent = RemoteA2aAgent(
    name="remote_service",
    description="Description for routing",
    agent_card=f"http://localhost:8001/a2a/agent_name{AGENT_CARD_WELL_KNOWN_PATH}"
)

# Use in your agent
main_agent = Agent(
    model="gemini-2.0-flash",
    name="main_agent",
    instruction="Use remote_service for specific tasks",
    sub_agents=[remote_agent]
)
```

---

## 🎨 A2UI Integration

### Agent Side (Generating UI)

```python
from google.adk.agents import Agent

# Agent that generates A2UI responses
ui_agent = Agent(
    model="gemini-2.0-flash",
    name="ui_agent",
    instruction="""
    Generate A2UI responses for user requests.
    Use Card, Button, TextField components as needed.
    """,
    tools=[your_tools]
)

# Expose via A2A with A2UI support
from google.adk.a2a.utils.agent_to_a2a import to_a2a
a2a_app = to_a2a(ui_agent, port=8001)
```

### Client Side (Rendering UI)

#### Lit (Web Components)

```bash
# Install
npm install @a2ui/lit

# Build
npm run build
```

```typescript
import { A2UIRenderer } from '@a2ui/lit';

// Initialize renderer
const renderer = new A2UIRenderer({
  container: document.getElementById('app'),
  componentCatalog: standardComponents
});

// Connect to agent
const agent = new A2AClient('http://localhost:8001');

// Handle messages
agent.onMessage((message) => {
  renderer.processMessage(message);
});
```

#### Flutter (GenUI SDK)

```bash
flutter pub add flutter_genui
```

```dart
import 'package:flutter_genui/flutter_genui.dart';

// Use GenUI widgets
GenUIWidget(
  agentUrl: 'http://localhost:8001',
  onAction: (action) {
    // Handle user actions
  },
)
```

---

## 📊 Monitoring and Debugging

### Enable Telemetry

```python
# When deploying to Agent Engine
config = {
    "env_vars": {
        "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY": "true"
    }
}
```

### View Traces

```python
# Traces are automatically generated when telemetry is enabled
# View in Google Cloud Console:
# Navigation Menu > Vertex AI > Agent Builder > Traces
```

### Debug with ADK Web UI

```bash
# Start with debug mode
adk web --debug

# Inspect:
# - Event history
# - State changes
# - Tool calls
# - Agent transfers
```

### Logging

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# In your tools
def my_tool(param: str):
    """Tool with logging"""
    logging.info(f"Tool called with param: {param}")
    # ... tool logic
    logging.debug(f"Tool result: {result}")
    return result
```

---

## 🛠️ Common Patterns

### Pattern: Tool with Error Handling

```python
def robust_tool(param: str) -> dict:
    """Tool with proper error handling"""
    try:
        # Tool logic
        result = perform_operation(param)
        return {
            "status": "success",
            "data": result
        }
    except ValueError as e:
        return {
            "status": "error",
            "error_type": "validation",
            "message": str(e)
        }
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return {
            "status": "error",
            "error_type": "unexpected",
            "message": "An unexpected error occurred"
        }
```

### Pattern: Stateful Tool

```python
from google.adk.tools import ToolContext

def stateful_tool(param: str, tool_context: ToolContext) -> str:
    """Tool that uses session state"""
    # Read from state
    previous_value = tool_context.state.get("counter", 0)
    
    # Update state
    new_value = previous_value + 1
    tool_context.state["counter"] = new_value
    
    return f"Counter: {new_value}"
```

### Pattern: Async Tool

```python
import asyncio

async def async_tool(url: str) -> dict:
    """Async tool for I/O operations"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            return data
```

### Pattern: Long-Running Tool

```python
from google.adk.tools import LongRunningTool

class DataProcessingTool(LongRunningTool):
    """Tool for long-running operations"""
    
    async def execute(self, data: list) -> dict:
        """Process data asynchronously"""
        # Long-running operation
        result = await process_large_dataset(data)
        return {"status": "complete", "result": result}
```

---

## 🔍 Troubleshooting

### Common Issues

#### Issue: "Module not found"

```bash
# Solution: Install dependencies
pip install google-adk
pip install google-cloud-aiplatform[agent_engines,adk]
```

#### Issue: "Authentication failed"

```bash
# Solution: Re-authenticate
gcloud auth application-default login

# Or set API key
export GOOGLE_API_KEY="your_key"
```

#### Issue: "Agent not found in dropdown (adk web)"

```bash
# Solution: Run adk web from parent folder
cd parent_folder
adk web

# Not from inside agent folder
```

#### Issue: "Port already in use"

```bash
# Solution: Use different port
adk web --port 8080

# Or kill process using port
# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac:
lsof -ti:8000 | xargs kill -9
```

#### Issue: "NotImplementedError: _make_subprocess_transport" (Windows)

```bash
# Solution: Use --no-reload flag
adk web --no-reload
```

---

## 📚 API Reference Quick Links

### Python

- **Agents**: `google.adk.agents`
  - `Agent`, `LlmAgent`, `SequentialAgent`, `ParallelAgent`, `LoopAgent`
  - `RemoteA2aAgent`, `BaseAgent`

- **Tools**: `google.adk.tools`
  - `FunctionTool`, `AgentTool`, `LongRunningTool`
  - `google_search`, `code_execution`

- **Sessions**: `google.adk.sessions`
  - `InMemorySessionService`, `FileSessionService`

- **Runners**: `google.adk.runners`
  - `Runner`

- **A2A**: `google.adk.a2a`
  - `to_a2a()`

### TypeScript

- **Agents**: `@google/adk`
  - `LlmAgent`, `SequentialAgent`, `ParallelAgent`

- **Tools**: `@google/adk`
  - `GOOGLE_SEARCH`, `CODE_EXECUTION`

---

## � Visual BuPilder & Agent Config

### Visual Builder (Experimental v1.18.0+)

**Web-based tool for creating agents with graphical interface**

```bash
# Start Visual Builder
adk web --port 8000
```

**Steps**:
1. Click `+` in top left to create agent
2. Edit in left panel (components), center panel (add), right panel (AI assistant)
3. Save in bottom left
4. Test your agent

**AI Assistant Example**:
```
Help me add a dice roll tool to my current agent.
Use the default model if you need to configure that.
```

**Output**: Generates Agent Config YAML files

### Agent Config (No-Code, Experimental v1.11.0+)

**Build agents with YAML instead of code**

```bash
# Create config-based agent
adk create --type=config my_agent

# Edit .env
echo "GOOGLE_API_KEY=your_key" > my_agent/.env

# Edit root_agent.yaml
# Run
cd my_agent
adk web
```

**Basic Example**:
```yaml
name: assistant_agent
model: gemini-2.5-flash
description: A helper agent
instruction: You are a helpful assistant
```

**With Tools**:
```yaml
name: search_agent
model: gemini-2.0-flash
instruction: Perform Google searches
tools:
  - name: google_search
```

**With Sub-Agents**:
```yaml
name: root_agent
model: gemini-2.5-flash
instruction: Coordinate tasks
sub_agents:
  - config_path: sub_agent_1.yaml
  - config_path: sub_agent_2.yaml
```

**Limitations**:
- Only Gemini models
- Python-only for custom tools
- Limited tool support

---

## 🎓 Learning Path

### Beginner

1. Install ADK
2. **Option A**: Use Visual Builder to create first agent (no code)
3. **Option B**: Use Agent Config YAML (minimal code)
4. **Option C**: Write Python code for full control
5. Run with `adk web`
6. Test with basic queries

### Intermediate

1. Create multi-agent system with sub-agents
2. Implement custom tools
3. Use sequential and parallel patterns
4. Add evaluation datasets
5. Try Agent Config for rapid prototyping

### Advanced

1. Deploy to Vertex AI Agent Engine
2. Implement A2A protocol for remote agents
3. Create A2UI interfaces
4. Build complex multi-agent workflows
5. Implement custom code executors
6. Build custom agents extending BaseAgent

---

## 🤖 Coding with AI (llms.txt Support)

ADK documentation supports the `/llms.txt` standard for AI-powered development.

### Available Files

| File | Best For | URL |
|------|----------|-----|
| **llms.txt** | Tools that fetch links dynamically | https://google.github.io/adk-docs/llms.txt |
| **llms-full.txt** | Tools needing full static text dump | https://google.github.io/adk-docs/llms-full.txt |

### Setup for Popular Tools

#### Gemini CLI

```bash
# Install extension
gemini extensions install https://github.com/derailed-dash/adk-docs-ext

# Use directly
# Ask: "How do I create a function tool using Agent Development Kit?"
```

#### Cursor IDE

1. Open Cursor Settings → Tools & MCP
2. Click New MCP Server
3. Add to `mcp.json`:

```json
{
  "mcpServers": {
    "adk-docs-mcp": {
      "command": "uvx",
      "args": [
        "--from", "mcpdoc", "mcpdoc",
        "--urls", "AgentDevelopmentKit:https://google.github.io/adk-docs/llms.txt",
        "--transport", "stdio"
      ]
    }
  }
}
```

#### Claude Code

```bash
claude mcp add adk-docs --transport stdio -- uvx --from mcpdoc mcpdoc --urls AgentDevelopmentKit:https://google.github.io/adk-docs/llms.txt --transport stdio
```

#### Antigravity IDE

1. Open MCP store → Manage MCP Servers → View raw config
2. Add to `mcp_config.json`:

```json
{
  "mcpServers": {
    "adk-docs-mcp": {
      "command": "uvx",
      "args": [
        "--from", "mcpdoc", "mcpdoc",
        "--urls", "AgentDevelopmentKit:https://google.github.io/adk-docs/llms.txt",
        "--transport", "stdio"
      ]
    }
  }
}
```

### Example Prompts

```
Use the ADK docs to build a multi-tool agent that uses Gemini 2.5 Pro 
and includes a mock weather lookup tool and a custom calculator tool. 
Verify the agent using adk run.
```

---

## 📖 Additional Resources

### Official Documentation
- ADK Docs: https://google.github.io/adk-docs/
- API Reference: https://google.github.io/adk-docs/api-reference/python/
- Vertex AI Docs: https://cloud.google.com/vertex-ai/docs

### Community
- GitHub: https://github.com/google/adk-python
- Issues: https://github.com/google/adk-python/issues
- Discussions: https://github.com/google/adk-python/discussions

### Examples
- Samples: https://github.com/google/adk-python/tree/main/contributing/samples
- Community Repo: adk-python-community

---

## 🔄 Version Compatibility

| ADK Version | Python | Node.js | Gemini Models |
|-------------|--------|---------|---------------|
| 1.21.0+ | 3.10+ | 18+ | gemini-2.0-flash, gemini-2.5-flash |
| 1.20.0+ | 3.10+ | 18+ | gemini-2.0-flash-exp |
| 1.0.0+ | 3.10+ | 16+ | gemini-1.5-pro, gemini-1.5-flash |

### Supported Regions (Vertex AI)

- us-central1
- us-east1
- us-west1
- europe-west1
- europe-west4
- asia-northeast1
- asia-southeast1

---

This technical reference should serve as your go-to guide for all ADK-related development tasks!
