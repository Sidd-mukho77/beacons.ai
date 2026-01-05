# A2UI Client Setup for Company Profiler

This guide explains how to set up the A2UI Lit client to test the Company Profiler agent.

## Prerequisites

1. [Node.js](https://nodejs.org/en) (v18 or later)
2. [Git](https://git-scm.com/)
3. Company Profiler agent running on port 8001

## Quick Start

If you've already cloned the A2UI repository and it's in the `a2ui/` folder:

1. **Start the Company Profiler Agent**:
   ```bash
   cd company_profiler
   python run_a2a_server.py
   ```

2. **Start the A2UI Client**:
   ```bash
   cd a2ui/samples/client/lit/shell
   npm run dev
   ```

3. **Open in Browser**:
   ```
   http://localhost:5173/?app=company-profiler
   ```

## Full Setup Instructions

### Step 1: Clone the A2UI Repository (if not already done)

```bash
git clone https://github.com/google/a2ui.git
cd a2ui
```

### Step 2: Build the Lit Renderer

```bash
cd renderers/lit
npm install
npm run build
```

### Step 3: Set Up the Shell Client

```bash
cd ../../samples/client/lit/shell
npm install
```

### Step 4: Verify Company Profiler Configuration

The configuration file should already exist at:
`a2ui/samples/client/lit/shell/configs/company-profiler.ts`

If it doesn't exist, copy from this directory:
```bash
cp a2ui_client/company-profiler.ts a2ui/samples/client/lit/shell/configs/
```

### Step 5: Verify App Configuration

The `app.ts` file should already include the company profiler config. Verify these lines exist:

```typescript
// Import at top with other configs
import { config as companyProfilerConfig } from "./configs/company-profiler.js";

// In the configs object
const configs: Record<string, AppConfig> = {
  restaurant: restaurantConfig,
  contacts: contactsConfig,
  "company-profiler": companyProfilerConfig,
};
```

### Step 6: Start the Servers

1. **Start the Company Profiler Agent** (in this project directory):
   ```bash
   cd company_profiler
   python run_a2a_server.py
   ```
   The agent will start on http://localhost:8001

2. **Start the A2UI Client** (in the a2ui directory):
   ```bash
   cd a2ui/samples/client/lit/shell
   npm run dev
   ```
   The client will start on http://localhost:5173

### Step 7: Access the Application

Open your browser and navigate to:
```
http://localhost:5173/?app=company-profiler
```

Enter an industry title (e.g., "Drone Automation") and click send to see the company profile cards.

## Configuration Files

| File | Location | Purpose |
|------|----------|---------|
| `company-profiler.ts` | `a2ui/samples/client/lit/shell/configs/` | Client config with serverUrl |
| `CONNECTION.md` | `a2ui_client/` | Connection architecture details |
| `TESTING.md` | `a2ui_client/` | Testing instructions |

## A2A Connection Settings

- **Server URL**: `http://localhost:8001`
- **Agent Card**: `http://localhost:8001/.well-known/agent-card.json`
- **A2A Endpoint**: `http://localhost:8001/a2a/company_profiler`

To change the port, update both:
1. Server: `A2A_PORT=9000 python run_a2a_server.py`
2. Client: Edit `serverUrl` in `company-profiler.ts`

## Troubleshooting

### Agent Connection Issues

- Ensure the Company Profiler agent is running on port 8001
- Check that CORS is properly configured (ADK's to_a2a handles this)
- Verify the agent card is accessible at: http://localhost:8001/.well-known/agent-card.json

### Build Errors

- Make sure you've built the renderer before running the shell
- Clear node_modules and reinstall if you encounter dependency issues:
  ```bash
  rm -rf node_modules package-lock.json
  npm install
  ```

### No UI Rendering

- Check browser console for errors
- Verify the agent is returning valid A2UI JSON messages
- Ensure the A2UI messages include surfaceUpdate, dataModelUpdate, and beginRendering

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Browser (localhost:5173)                  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                   A2UI Shell Client                     │ │
│  │                                                         │ │
│  │  ┌─────────────┐    ┌─────────────┐    ┌────────────┐  │ │
│  │  │   Input     │───>│  A2AClient  │───>│  Renderer  │  │ │
│  │  │   Form      │    │             │    │  (Lit)     │  │ │
│  │  └─────────────┘    └─────────────┘    └────────────┘  │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ A2A Protocol (HTTP/SSE)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Company Profiler Agent (localhost:8001)         │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                    ADK Pipeline                         │ │
│  │                                                         │ │
│  │  Market Identifier → Info Gatherer → A2UI Generator    │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```
