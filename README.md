# Beacons.ai 🚦

**Open Source Market Research & Analytics Agents**

Beacons.ai is an open-source suite of specialized AI agents designed to automate complex market research and analytics workflows. Built using the Google Agent Development Kit (ADK) and the Agent-to-Agent (A2A) protocol.

## 🎯 TheVision

To democratize access to high-quality, autonomous market intelligence. Beacons.ai provides drop-in agents that can:

- **Map Industries**: Identify key players in any sector.
- **Deep Dive**: Gather detailed financial, leadership, and product data.
- **Synthesize**: Aggregate multi-source data into structured, actionable insights.
- **Visualize**: Generate interactive UI cards for immediate consumption.

## 🤖 Available Agents Right Now

### 1. Company Profiler

A high-performance parallel agent system that profiles companies in a given industry.

- **Capabilities**:
  - Finds top 15 companies in a target industry (e.g., "Drone Automation").
  - **Parallel Processing**: Spawns 5 concurrent researchers to gather data 5x faster.
  - **Outputs**: Structured JSON + Interactive A2UI Cards.
- **Tech Stack**: `SequentialAgent`, `ParallelAgent`, `A2UI`.
- **Guide**: [Startup Guide](./company_profiler/STARTUP_GUIDE.md)

### 2. Annual Report Parser

An intelligent agent that automatically finds, downloads, and analyzes company annual reports.

- **Capabilities**:
  - Processes single companies or batches (e.g., "Apple, Microsoft, Tesla").
  - **Smart PDF Discovery**: Nested retry loop with 5 different search strategies.
  - **Gemini PDF Analysis**: Uses Gemini's Files API for deep document understanding.
  - **Pinecone Storage**: Stores structured financial data for semantic search.
- **Tech Stack**: `SequentialAgent`, `LoopAgent`, Gemini Files API, Pinecone.
- **Guide**: [Startup Guide](./annual_report_parser/STARTUP_GUIDE.md)

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Google ADK (`pip install google-adk[web]`)
- Google Gemini API Key

### Running the Company Profiler

1.  **Clone the repo**:

    ```bash
    git clone https://github.com/Sidd-mukho77/beacons.ai.git
    cd beacons.ai
    ```

2.  **Run with ADK Web UI** (Easiest Method):
    ```bash
    cd company_profiler
    echo "GOOGLE_API_KEY=your_key" > .env
    adk web
    ```
    Then visit the displayed URL (e.g., `http://localhost:8000`) and select `company_profiler`.

## 🤝 Contributing

We welcome contributions! Whether it's adding a new specialized agent, improving current prompts, or fixing bugs.

1.  Fork the repository
2.  Create your feature branch (`git checkout -b feature/amazing-agent`)
3.  Commit your changes
4.  Push to the branch
5.  Open a Pull Request

## 📄 License

MIT License
