# Annual Report Parser - Startup Guide

A powerful AI agent that automatically finds, downloads, and analyzes annual reports for any company, then stores structured insights in Pinecone for retrieval.

## ✨ Features

- **Multi-Company Support**: Process single companies or batches (e.g., "Apple, Microsoft, Tesla")
- **Smart PDF Discovery**: Nested retry loop with 5 different search strategies
- **Gemini PDF Analysis**: Uses Gemini's Files API for deep document understanding
- **Pinecone Storage**: Stores structured financial data for semantic search
- **Robust Architecture**: SequentialAgent + LoopAgent for reliable processing

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Google ADK (`pip install google-adk[web]`)
- Google Gemini API Key ([Get one here](https://aistudio.google.com/apikey))
- Pinecone account ([Free tier available](https://www.pinecone.io/))

### Setup

1. **Navigate to the agent directory**:
   ```bash
   cd annual_report_parser
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. **Set up Pinecone** (if using storage):
   - Create a new index named `financial-reports`
   - Use integrated embedding model (e.g., `llama-text-embed-v2`)
   - Copy your host URL to `.env`

5. **Run with ADK Web UI**:
   ```bash
   adk web
   ```
   Visit the displayed URL and select `annual_report_parser`.

## 📖 Usage Examples

### Single Company
```
Apple Inc.
```

### Multiple Companies (comma-separated)
```
Apple, Microsoft, Tesla, Amazon
```

### Ticker Symbols
```
AAPL, MSFT, TSLA
```

### JSON Array
```
["Apple Inc.", "Microsoft Corporation"]
```

## 🏗️ Architecture

```
annual_report_parser (SequentialAgent)
├── company_input_parser        # Parses user input to company list
└── company_orchestrator_loop   # Outer loop: iterates companies
    └── single_company_pipeline (SequentialAgent)
        ├── company_iterator    # Selects next company, resets state
        ├── pdf_find_retry_loop # Inner loop: find & download PDF (5 retries)
        │   ├── alternative_finder   # Searches with different strategies
        │   ├── url_validator        # Validates PDF accessibility
        │   ├── pdf_downloader       # Downloads the PDF
        │   └── download_checker     # Controls loop exit
        ├── report_analyst      # Analyzes PDF with Gemini
        ├── output_summarizer   # Structures into JSON
        └── data_storage        # Stores in Pinecone
```

## 🔧 Troubleshooting

### "No PDF found"
The agent tries 5 different search strategies. If all fail:
- Check if the company has a publicly available annual report
- Try using the official company name (e.g., "Apple Inc." instead of "Apple")

### Pinecone errors
- Verify your `PINECONE_HOST` includes the full URL (e.g., `index-name.svc.region.pinecone.io`)
- Ensure your index uses an integrated embedding model

### API rate limits
- The agent uses `gemini-2.5-flash` for cost efficiency
- For very large batches, consider adding delays between companies

## 📄 Output Schema

Each analyzed company produces structured JSON like:
```json
{
  "company_name": "Apple Inc.",
  "report_year": "FY2024",
  "financial_summary": {
    "revenue": [{"year": "2024", "amount": "$400B", "growth_yoy": "+5%"}],
    "net_income": [{"year": "2024", "amount": "$95B"}],
    "key_metrics": {"gross_margin": "45%", "operating_margin": "30%"}
  },
  "products_services": {"products": ["iPhone", "Mac", "iPad"], "services": ["iCloud", "Apple Music"]},
  "business_segments": [{"name": "iPhone", "revenue": "$200B", "percentage_of_total": "50%"}],
  "leadership": {"ceo": {"name": "Tim Cook", "since": "2011"}},
  "data_quality": {"completeness": "HIGH", "source": "Annual Report"}
}
```

## 📚 Related

- [Company Profiler Agent](../company_profiler/STARTUP_GUIDE.md) - Industry-wide company research
- [Google ADK Documentation](https://google.github.io/adk-docs/)
