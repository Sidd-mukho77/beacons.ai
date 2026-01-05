#!/usr/bin/env python3
"""
A2A Server Startup Script for Company Profiler Agent

This script starts the Company Profiler agent as an A2A server,
exposing it via the Agent-to-Agent protocol for client communication.

Usage:
    # Using Python directly:
    python run_a2a_server.py
    
    # With custom port:
    A2A_PORT=9000 python run_a2a_server.py

Environment Variables:
    A2A_PORT: Port to run the A2A server on (default: 8001)
    GOOGLE_API_KEY: Google API key for Gemini models
    
Requirements:
    - google-adk[a2a] must be installed
    - uvicorn must be installed
    
Endpoints:
    - http://localhost:8001/.well-known/agent-card.json - Agent card metadata
    - http://localhost:8001/ - A2A message endpoint
"""

import os
import sys


def main():
    """Start the A2A server using uvicorn."""
    # Ensure the parent directory is in the path for imports
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    
    # Load environment variables from .env file
    env_file = os.path.join(script_dir, ".env")
    if os.path.exists(env_file):
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            print(f"Loaded environment from {env_file}")
        except ImportError:
            # Manually load .env if python-dotenv is not installed
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
            print(f"Loaded environment from {env_file} (manual parsing)")
    
    try:
        import uvicorn
    except ImportError:
        print("Error: uvicorn is not installed.")
        print("Install it with: pip install uvicorn")
        sys.exit(1)
    
    # Get port from environment or use default
    port = int(os.environ.get("A2A_PORT", 8001))
    host = os.environ.get("A2A_HOST", "localhost")
    
    print(f"Starting Company Profiler A2A Server...")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Agent Card: http://{host}:{port}/.well-known/agent-card.json")
    print(f"A2A Endpoint: http://{host}:{port}/")
    print("-" * 50)
    
    # Create and run the custom A2A app
    from company_profiler.a2a_server import create_a2a_app
    app = create_a2a_app(port=port)
    
    # Run the server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        reload=False
    )


if __name__ == "__main__":
    main()
