# Company Profiler - Startup Guide

## Quick Start

### Option 1: ADK Web UI (Recommended for Testing/Debugging)
This provides a visual trace of the parallel agents.

```bash
cd c:\Users\saksh\Desktop\beacons\company_profiler
adk web
```
- Open browser to the URL shown in terminal (usually http://localhost:8000)
- Select `company_profiler` agent

### Option 2: A2A Server + Frontend (For Full App Experience)

**1. Start Backend Server**
```bash
cd c:\Users\saksh\Desktop\beacons\company_profiler
python run_a2a_server.py
```
- **Port**: 8001

**2. Start Frontend Client**
```bash
cd c:\Users\saksh\Desktop\beacons\a2ui\samples\client\lit\shell
npm run dev
```
- **URL**: http://localhost:5173/?app=company-profiler

## Architecture Overview

The system now uses a **Parallel Fan-Out Architecture** for high performance:

1. **Market Identifier**: Finds top 15 companies
2. **Parallel Research**: 5 simultaneous agents, each processing 3 companies
3. **Data Summarizer**: Aggregates all 15 results
4. **A2UI Generator**: Renders the final 15-card UI

**Performance**: reduced from ~150s to ~30-40s.

## Troubleshooting

### Backend Not Starting
- Check if port 8001 is in use: `netstat -ano | findstr :8001`
- Verify `.env` file exists with `GOOGLE_API_KEY`

### "Run adk web" fails
- Ensure you have the ADK installed: `pip install google-adk[web]`
- Ensure you are in the correct directory

## Files Modified
1. `agent.py` - Implements the 5-way parallel architecture
2. `a2a_server.py` - Includes error handling for stability
3. `configs/company-profiler.ts` - Pointing to port 8001
