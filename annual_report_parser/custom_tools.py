"""
Custom Tools for Financial Analyst Agent

Provides Python functions that can be wrapped as ADK FunctionTools for:
1. Downloading PDFs from URLs
2. Analyzing PDFs using Gemini with Files API
"""

import os
import re
import tempfile
import requests
from typing import Dict, Any, Optional
from urllib.parse import urlparse, unquote
import base64


def validate_pdf_url(url: str) -> Dict[str, Any]:
    """
    Validates a URL returns a PDF without downloading the full file.
    Uses HEAD request to check content-type and accessibility.
    
    Args:
        url: The URL to validate
        
    Returns:
        A dictionary containing:
        - valid: Boolean indicating if URL appears to point to a valid PDF
        - status_code: HTTP status code from HEAD request
        - content_type: Content-Type header value
        - accessible: Boolean indicating if URL is accessible
        - error: Error message if validation failed
    """
    if not url or not url.startswith(('http://', 'https://')):
        return {
            "valid": False,
            "accessible": False,
            "error": f"Invalid URL format: {url}"
        }
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/pdf,*/*"
        }
        
        # Try HEAD request first (faster)
        response = requests.head(url, headers=headers, timeout=15, allow_redirects=True)
        
        # Some servers don't support HEAD, try GET with stream
        if response.status_code == 405:
            response = requests.get(url, headers=headers, timeout=15, allow_redirects=True, stream=True)
            response.close()
        
        content_type = response.headers.get('Content-Type', '').lower()
        is_pdf = 'pdf' in content_type or url.lower().endswith('.pdf')
        is_accessible = response.status_code == 200
        
        return {
            "valid": is_pdf and is_accessible,
            "accessible": is_accessible,
            "status_code": response.status_code,
            "content_type": content_type,
            "url": url
        }
        
    except requests.exceptions.Timeout:
        return {
            "valid": False,
            "accessible": False,
            "error": "URL validation timed out"
        }
    except requests.exceptions.RequestException as e:
        return {
            "valid": False,
            "accessible": False,
            "error": f"URL validation failed: {str(e)}"
        }
    except Exception as e:
        return {
            "valid": False,
            "accessible": False,
            "error": f"Unexpected error during validation: {str(e)}"
        }

def download_pdf_from_url(url: str) -> Dict[str, Any]:
    """
    Downloads a PDF file from a given URL and saves it to a temporary location.
    
    Args:
        url: The URL of the PDF file to download.
        
    Returns:
        A dictionary containing:
        - success: Boolean indicating if download was successful
        - file_path: Local path where the PDF was saved (if successful)
        - file_size_mb: Size of the downloaded file in MB
        - error: Error message if download failed
    """
    try:
        # Validate URL
        if not url or not url.startswith(('http://', 'https://')):
            return {
                "success": False,
                "error": f"Invalid URL: {url}. Must start with http:// or https://"
            }
        
        # Check if URL likely points to a PDF
        parsed_url = urlparse(url)
        path_lower = parsed_url.path.lower()
        
        # Create temp directory for downloads
        download_dir = os.path.join(tempfile.gettempdir(), "financial_analyst_pdfs")
        os.makedirs(download_dir, exist_ok=True)
        
        # Generate filename from URL or use a default
        if path_lower.endswith('.pdf'):
            filename = os.path.basename(unquote(parsed_url.path))
        else:
            # Generate a filename based on URL hash
            import hashlib
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            filename = f"annual_report_{url_hash}.pdf"
        
        file_path = os.path.join(download_dir, filename)
        
        # Download the file with timeout and comprehensive browser-like headers
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/pdf,application/octet-stream,*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "Referer": f"https://{parsed_url.netloc}/",
        }
        
        response = requests.get(url, headers=headers, timeout=90, stream=True, allow_redirects=True)
        response.raise_for_status()
        
        # Check content type
        content_type = response.headers.get('Content-Type', '').lower()
        if 'pdf' not in content_type and not path_lower.endswith('.pdf'):
            print(f"Warning: Content-Type is '{content_type}', not PDF. Attempting download anyway.")
        
        # Write to file
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        
        # Basic PDF validation - check magic bytes
        with open(file_path, 'rb') as f:
            header = f.read(5)
            if header != b'%PDF-':
                os.remove(file_path)
                return {
                    "success": False,
                    "error": f"Downloaded file is not a valid PDF (magic bytes: {header})"
                }
        
        return {
            "success": True,
            "file_path": file_path,
            "file_size_mb": round(file_size_mb, 2),
            "filename": filename
        }
        
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Download timed out after 90 seconds"
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Download failed: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


def analyze_pdf_with_gemini(file_path: str, analysis_prompt: str = "") -> Dict[str, Any]:
    """
    Uploads a PDF to Gemini Files API and analyzes it, returning the actual analysis content.
    This tool handles both upload AND analysis in one step.
    
    Args:
        file_path: Local path to the PDF file.
        analysis_prompt: Optional custom prompt for analysis. If empty, uses default financial analysis prompt.
        
    Returns:
        A dictionary containing:
        - success: Boolean indicating if analysis was successful
        - analysis: The extracted analysis content from the PDF
        - file_size_mb: Size of the file in MB
        - error: Error message if analysis failed
    """
    try:
        if not file_path or not os.path.exists(file_path):
            return {
                "success": False,
                "error": f"File not found: {file_path}",
                "analysis": ""
            }
        
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        
        if file_size_mb > 50:
            return {
                "success": False,
                "error": f"PDF too large ({file_size_mb:.2f}MB). Limit is 50MB.",
                "analysis": ""
            }
        
        # Default analysis prompt for financial reports
        if not analysis_prompt:
            analysis_prompt = """Analyze this annual report PDF and extract the following information in detail:

1. **FINANCIAL DATA**
   - Revenue/Sales for ALL years mentioned (with exact figures)
   - Net Income/Profit for all available years
   - Year-over-year growth rates
   - Key financial ratios (gross margin, operating margin, EPS)

2. **PRODUCTS & SERVICES**
   - Complete list of products offered
   - Complete list of services offered
   - New products/services launched during the year

3. **BUSINESS SEGMENTS**
   - All business segments/divisions
   - Revenue breakdown by segment
   - Geographic segments and their performance

4. **CORPORATE STRUCTURE**
   - Subsidiaries
   - Parent company (if any)
   - Joint ventures and partnerships
   - Recent acquisitions or mergers

5. **LEADERSHIP**
   - CEO name and tenure
   - CFO and other key executives
   - Board members (if listed)

6. **KEY HIGHLIGHTS**
   - Major achievements during the year
   - Future outlook/guidance from management
   - Risk factors mentioned

Provide specific numbers and quotes from the report wherever available.
Format your response as a detailed structured analysis."""

        # Try using google.genai client (preferred)
        try:
            from google import genai
            
            client = genai.Client()
            
            # Upload the file
            print(f"DEBUG: Uploading PDF to Gemini Files API: {file_path}")
            uploaded_file = client.files.upload(file=file_path)
            print(f"DEBUG: File uploaded: {uploaded_file.uri}")
            
            # Now analyze the PDF with Gemini
            print("DEBUG: Analyzing PDF with Gemini...")
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[analysis_prompt, uploaded_file]
            )
            
            analysis_text = response.text if hasattr(response, 'text') else str(response)
            
            return {
                "success": True,
                "analysis": analysis_text,
                "file_size_mb": round(file_size_mb, 2),
                "file_uri": uploaded_file.uri
            }
            
        except ImportError:
            # Fallback to google.generativeai
            try:
                import google.generativeai as genai
                
                print(f"DEBUG: Using google.generativeai fallback")
                uploaded_file = genai.upload_file(
                    path=file_path,
                    mime_type="application/pdf"
                )
                
                model = genai.GenerativeModel('gemini-2.5-flash')
                response = model.generate_content([analysis_prompt, uploaded_file])
                
                return {
                    "success": True,
                    "analysis": response.text,
                    "file_size_mb": round(file_size_mb, 2),
                    "file_uri": uploaded_file.uri
                }
            except ImportError:
                # Last resort: base64 inline (may hit rate limits)
                return _analyze_pdf_inline(file_path, analysis_prompt)
                
    except Exception as e:
        error_msg = str(e)
        print(f"DEBUG: PDF analysis failed: {error_msg}")
        return {
            "success": False,
            "error": f"PDF analysis failed: {error_msg}",
            "analysis": ""
        }


def _analyze_pdf_inline(file_path: str, analysis_prompt: str) -> Dict[str, Any]:
    """
    Fallback: Analyze PDF using inline base64 data.
    WARNING: This may hit rate limits for large PDFs.
    """
    try:
        import google.generativeai as genai
        
        with open(file_path, 'rb') as f:
            pdf_bytes = f.read()
        
        file_size_mb = len(pdf_bytes) / (1024 * 1024)
        
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content([
            analysis_prompt,
            {"mime_type": "application/pdf", "data": base64.b64encode(pdf_bytes).decode('utf-8')}
        ])
        
        return {
            "success": True,
            "analysis": response.text,
            "file_size_mb": round(file_size_mb, 2),
            "method": "inline_base64"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Inline analysis failed: {str(e)}",
            "analysis": ""
        }


# Keep the old function name for backwards compatibility
def read_pdf_as_base64(file_path: str) -> Dict[str, Any]:
    """
    Alias for analyze_pdf_with_gemini for backwards compatibility.
    Now performs full analysis instead of just returning file_uri.
    """
    return analyze_pdf_with_gemini(file_path)


def extract_pdf_url_from_search_results(search_results: str) -> Dict[str, Any]:
    """
    Extracts a PDF URL from search results text.
    """
    try:
        url_pattern = r'https?://[^\s<>"\'()]+\.pdf(?:\?[^\s<>"\']*)?|https?://[^\s<>"\'()]+/pdf/[^\s<>"\']*'
        urls = re.findall(url_pattern, search_results, re.IGNORECASE)
        
        cleaned_urls = []
        for url in urls:
            url = url.rstrip('.,;:!?')
            cleaned_urls.append(url)
        
        if cleaned_urls:
            pdf_urls = [u for u in cleaned_urls if u.lower().endswith('.pdf')]
            best_url = pdf_urls[0] if pdf_urls else cleaned_urls[0]
            
            return {
                "success": True,
                "pdf_url": best_url,
                "all_urls": cleaned_urls[:5]
            }
        else:
            return {
                "success": False,
                "error": "No PDF URLs found in search results",
                "all_urls": []
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to extract PDF URL: {str(e)}",
            "all_urls": []
        }


def store_in_pinecone(company_name: str, report_year: str, structured_data: str, analysis_content: str = "") -> Dict[str, Any]:
    """
    Stores financial analysis data in Pinecone for retrieval.
    Uses the financial-reports index with namespaces per company.
    
    Args:
        company_name: Name of the company (used as namespace)
        report_year: The fiscal year of the report (e.g., "2024")
        structured_data: The structured JSON output from the summarizer
        analysis_content: Optional raw analysis text for embedding
        
    Returns:
        A dictionary containing:
        - success: Boolean indicating if storage was successful
        - record_id: ID of the stored record
        - namespace: The namespace used
        - error: Error message if storage failed
    """
    import json
    import hashlib
    from datetime import datetime
    
    try:
        # Configuration for Pinecone (from environment)
        PINECONE_INDEX = os.environ.get("PINECONE_INDEX", "financial-reports")
        PINECONE_HOST = os.environ.get("PINECONE_HOST", "")
        
        # Get API key from environment
        api_key = os.environ.get("PINECONE_API_KEY", "")
        if not api_key:
            # Try to get from .env file
            env_path = os.path.join(os.path.dirname(__file__), ".env")
            if os.path.exists(env_path):
                with open(env_path) as f:
                    for line in f:
                        if line.startswith("PINECONE_API_KEY="):
                            api_key = line.split("=", 1)[1].strip()
                            break
        
        if not api_key or not PINECONE_HOST:
            missing = []
            if not api_key:
                missing.append("PINECONE_API_KEY")
            if not PINECONE_HOST:
                missing.append("PINECONE_HOST")
            return {
                "success": False,
                "error": f"Missing Pinecone config: {', '.join(missing)}. Set in .env file."
            }
        
        # Create namespace from company name (clean it up)
        namespace = re.sub(r'[^a-zA-Z0-9_-]', '_', company_name.lower()).strip('_')
        
        # Generate record ID
        record_id = hashlib.md5(f"{company_name}_{report_year}_{datetime.now().isoformat()}".encode()).hexdigest()[:16]
        
        # Parse structured data if it's a string
        if isinstance(structured_data, str):
            try:
                data_obj = json.loads(structured_data)
            except json.JSONDecodeError:
                data_obj = {"raw_data": structured_data}
        else:
            data_obj = structured_data
        
        # Create content for embedding - combine key information
        content_parts = [
            f"Company: {company_name}",
            f"Report Year: {report_year}",
        ]
        
        # Add key financial info to content
        if isinstance(data_obj, dict):
            if "financial_summary" in data_obj:
                content_parts.append(f"Financial Summary: {json.dumps(data_obj['financial_summary'])}")
            if "products_services" in data_obj:
                content_parts.append(f"Products/Services: {json.dumps(data_obj['products_services'])}")
            if "business_segments" in data_obj:
                content_parts.append(f"Business Segments: {json.dumps(data_obj['business_segments'])}")
            if "highlights" in data_obj:
                content_parts.append(f"Highlights: {json.dumps(data_obj['highlights'])}")
        
        if analysis_content:
            content_parts.append(f"Analysis: {analysis_content[:2000]}")  # Limit analysis length
        
        content = "\n".join(content_parts)
        
        # Prepare the record for upsert
        record = {
            "id": record_id,  # Changed from _id to id
            "content": content,  # This is the field that gets embedded (per fieldMap)
            "company_name": company_name,
            "report_year": report_year,
            "structured_data": json.dumps(data_obj) if isinstance(data_obj, dict) else str(data_obj),
            "timestamp": datetime.now().isoformat(),
            "source": "financial_analyst_agent"
        }
        
        # Upsert to Pinecone using REST API (NDJSON format)
        url = f"https://{PINECONE_HOST}/records/namespaces/{namespace}/upsert"
        headers = {
            "Api-Key": api_key,
            "Content-Type": "application/x-ndjson",  # NDJSON format required
            "X-Pinecone-API-Version": "2025-01"
        }
        
        # NDJSON: each record is a separate JSON line
        ndjson_payload = json.dumps(record)
        
        print(f"DEBUG [Pinecone]: Upserting record {record_id} to namespace '{namespace}'")
        print(f"DEBUG [Pinecone]: Payload: {ndjson_payload[:200]}...")
        response = requests.post(url, headers=headers, data=ndjson_payload, timeout=30)
        
        if response.status_code in [200, 201]:
            return {
                "success": True,
                "record_id": record_id,
                "namespace": namespace,
                "index": PINECONE_INDEX,
                "message": f"Data stored successfully for {company_name} ({report_year})"
            }
        else:
            return {
                "success": False,
                "error": f"Pinecone API error: {response.status_code} - {response.text}",
                "record_id": record_id
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to store in Pinecone: {str(e)}"
        }


def search_pinecone(query: str, company_filter: str = "", top_k: int = 5) -> Dict[str, Any]:
    """
    Searches the Pinecone financial-reports index for relevant data.
    
    Args:
        query: The search query text
        company_filter: Optional company name to filter by namespace
        top_k: Number of results to return
        
    Returns:
        A dictionary containing search results or error
    """
    try:
        PINECONE_HOST = os.environ.get("PINECONE_HOST", "")
        
        if not PINECONE_HOST:
            return {"success": False, "error": "PINECONE_HOST not set in environment"}
        
        api_key = os.environ.get("PINECONE_API_KEY", "")
        if not api_key:
            env_path = os.path.join(os.path.dirname(__file__), ".env")
            if os.path.exists(env_path):
                with open(env_path) as f:
                    for line in f:
                        if line.startswith("PINECONE_API_KEY="):
                            api_key = line.split("=", 1)[1].strip()
                            break
        
        if not api_key:
            return {"success": False, "error": "PINECONE_API_KEY not found"}
        
        namespace = re.sub(r'[^a-zA-Z0-9_-]', '_', company_filter.lower()).strip('_') if company_filter else ""
        
        url = f"https://{PINECONE_HOST}/records/namespaces/{namespace}/search" if namespace else f"https://{PINECONE_HOST}/records/search"
        headers = {
            "Api-Key": api_key,
            "Content-Type": "application/json",
            "X-Pinecone-API-Version": "2025-01"
        }
        
        payload = {
            "query": {"inputs": {"text": query}, "top_k": top_k},
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            return {"success": True, "results": response.json()}
        else:
            return {"success": False, "error": f"Search failed: {response.status_code}"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

