# Google ADK Ecosystem Overview

## Core Components

### 1. **Agent Development Kit (ADK)**
- **Repository**: https://github.com/google/adk-python
- **Purpose**: Open-source, code-first Python framework for building AI agents
- **Key Features**:
  - Multi-agent systems with hierarchical structures
  - Model-agnostic (optimized for Gemini but works with others via LiteLLM)
  - Rich tool ecosystem (pre-built tools, MCP, OpenAPI, custom functions)
  - Built-in evaluation and testing
  - Local development with CLI and Web UI
  - Deploy anywhere (Cloud Run, Vertex AI Agent Engine)

**Installation**:
```bash
pip install google-adk
# or for latest dev version
pip install git+https://github.com/google/adk-python.git@main
```

### 2. **Vertex AI Agent Engine**
- **Purpose**: Managed runtime environment for deploying agents in production
- **Features**:
  - End-to-end managed infrastructure
  - Automatic session management
  - Scalable deployment
  - Integration with Google Cloud services
- **Pricing**: Paid service with no-cost tier available

### 3. **A2UI (Agent-to-User Interface)**
- **Repository**: https://github.com/google/A2UI
- **Purpose**: Open standard for agents to generate rich, interactive UIs
- **Key Concepts**:
  - Declarative JSON format (not executable code)
  - Security-first approach
  - LLM-friendly and incrementally updateable
  - Framework-agnostic (Flutter, React, Lit, etc.)
  - Separates UI generation from UI execution

**Status**: v0.8 Public Preview

### 4. **Vertex AI SDK for Python**
- **Installation**: 
```bash
pip install --upgrade google-cloud-aiplatform[agent_engines,adk]>=1.112
```
- **Purpose**: Interface for deploying and managing agents on Vertex AI

## Development Workflow

### Local Development → Testing → Deployment

```
1. Develop locally with ADK
   ↓
2. Test with built-in Web UI/CLI
   ↓
3. Evaluate with test datasets
   ↓
4. Deploy to Vertex AI Agent Engine
```

## Multi-Agent Design Patterns

ADK supports 8 essential patterns:

1. **Sequential Pipeline** - Assembly line processing
2. **Coordinator/Dispatcher** - Central routing agent
3. **Parallel Fan-Out/Gather** - Concurrent execution with aggregation
4. **Hierarchical Decomposition** - Nested agent delegation
5. **Generator and Critic** - Draft and review loop
6. **Iterative Refinement** - Quality improvement cycles
7. **Human-in-the-Loop** - Tool confirmation flows
8. **Dynamic Routing** - LLM-driven delegation

## Basic Agent Structure

```python
from google.adk.agents import Agent
from google.adk.tools import google_search

# Define a simple agent
agent = Agent(
    model="gemini-2.0-flash",
    name="my_agent",
    instruction="You are a helpful assistant",
    description="Agent description for routing",
    tools=[google_search]
)

# For local testing
from vertexai.agent_engines import AdkApp
app = AdkApp(agent=agent)

# Deploy to Vertex AI
import vertexai
client = vertexai.Client(project="PROJECT_ID", location="LOCATION")
remote_agent = client.agent_engines.create(
    agent=app,
    config={
        "requirements": ["google-cloud-aiplatform[agent_engines,adk]"],
        "staging_bucket": "gs://BUCKET_NAME"
    }
)
```

## Key Differences Between Components

| Component | Purpose | When to Use |
|-----------|---------|-------------|
| **ADK** | Agent development framework | Building agent logic and workflows |
| **Vertex AI Agent Engine** | Managed runtime | Production deployment with scaling |
| **A2UI** | UI generation protocol | When agents need rich interactive UIs |
| **Vertex AI SDK** | Deployment interface | Deploying and managing agents on GCP |

## Authentication Setup

```bash
# Local development
gcloud auth application-default login

# In Colab
from google.colab import auth
auth.authenticate_user(project_id="PROJECT_ID")
```

## Required GCP Setup

1. Enable APIs:
   - Vertex AI API
   - Cloud Storage API

2. IAM Roles needed:
   - Vertex AI User (`roles/aiplatform.user`)
   - Storage Admin (`roles/storage.admin`)

3. Create Cloud Storage bucket for staging

## Evaluation

ADK includes built-in evaluation tools:

```bash
# CLI evaluation
adk eval <agent_path> <evalset.json>

# Programmatic evaluation
from vertexai import types

evaluation_run = client.evals.create_evaluation_run(
    dataset=dataset_with_inference,
    agent_info=agent_info,
    metrics=[
        types.RubricMetric.FINAL_RESPONSE_QUALITY,
        types.RubricMetric.TOOL_USE_QUALITY,
        types.RubricMetric.HALLUCINATION,
    ]
)
```

## Session Management

- **Local**: In-memory sessions
- **Deployed**: Managed cloud-based sessions
- Sessions track conversation state across interactions

```python
# Create session
session = await app.async_create_session(user_id="user-123")

# Query with session
async for event in app.async_stream_query(
    user_id="user-123",
    session_id=session.id,
    message="Your query here"
):
    print(event)
```

## Next Steps for Your Project

1. **Setup Phase**:
   - Install ADK and Vertex AI SDK
   - Set up GCP project and authentication
   - Create Cloud Storage bucket

2. **Development Phase**:
   - Define your agent's tools and capabilities
   - Build agent locally using ADK
   - Test with ADK Web UI or CLI

3. **Evaluation Phase**:
   - Create evaluation datasets
   - Run evaluations locally
   - Iterate on agent design

4. **Deployment Phase**:
   - Deploy to Vertex AI Agent Engine
   - Test deployed agent
   - Monitor and iterate

## Useful Links

### Core Documentation
- **ADK Docs**: https://google.github.io/adk-docs/
- **ADK Python Repo**: https://github.com/google/adk-python
- **ADK Technical Overview**: https://google.github.io/adk-docs/get-started/about/
- **A2UI Website**: https://a2ui.org/
- **A2UI Repo**: https://github.com/google/A2UI
- **Vertex AI Agent Engine Docs**: https://docs.cloud.google.com/agent-builder/agent-engine/

### Guides and Tutorials
- **Multi-Agent Patterns Guide**: https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/
- **A2UI Introduction Blog**: https://developers.googleblog.com/introducing-a2ui-an-open-project-for-agent-driven-interfaces/
- **ADK Quickstart**: https://docs.cloud.google.com/agent-builder/agent-engine/quickstart-adk
- **A2UI Quickstart**: https://a2ui.org/quickstart/

### Tools and Features
- **Custom Tools Guide**: https://google.github.io/adk-docs/tools-custom/
- **Pre-built Tools**: https://google.github.io/adk-docs/tools/
- **Gemini API Tools**: https://google.github.io/adk-docs/tools/gemini-api/
- **Google Search Grounding**: https://google.github.io/adk-docs/grounding/google_search_grounding/

### A2A Protocol
- **A2A Introduction**: https://google.github.io/adk-docs/a2a/intro/
- **A2A Quickstart (Exposing)**: https://google.github.io/adk-docs/a2a/quickstart-exposing/
- **A2A Quickstart (Consuming)**: https://google.github.io/adk-docs/a2a/quickstart-consuming/

### Advanced Topics
- **Agents Overview**: https://google.github.io/adk-docs/agents/
- **API Reference (Python)**: https://google.github.io/adk-docs/api-reference/python/
- **Evaluation Guide**: https://docs.cloud.google.com/agent-builder/agent-engine/evaluate
- **Deployment Guide**: https://google.github.io/adk-docs/deploy/agent-engine/

### Renderers
- **A2UI Renderers**: https://a2ui.org/renderers/
- **Flutter GenUI SDK**: https://github.com/flutter/genui
- **CopilotKit A2UI Widget Builder**: https://go.copilotkit.ai/A2UI-widget-builder

## Community

- ADK has an active community with regular meetings
- Community contributions repo: adk-python-community
- For LLM context: Use `llms.txt` or `llms-full.txt` from the repo
- GitHub Issues for bug reports and feature requests
- GitHub Discussions for questions and community support

## Additional Documentation Files

This repository includes comprehensive guides:

1. **google-adk-overview.md** (this file) - High-level overview of the ecosystem
2. **adk-tools-and-multi-agent-patterns.md** - Deep dive into tools and multi-agent patterns
3. **a2ui-comprehensive-guide.md** - Complete guide to A2UI protocol and implementation
