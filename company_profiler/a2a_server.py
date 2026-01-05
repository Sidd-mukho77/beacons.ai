# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Custom A2A Server for Company Profiler with A2UI support."""

import json
import logging
import os
import re
import uuid
from typing import Any

from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from company_profiler.a2ui_extension import A2UI_MIME_TYPE, A2UI_EXTENSION_URI

logger = logging.getLogger(__name__)


def extract_a2ui_messages(text: str) -> list:
    """
    Extract A2UI JSON messages from text with ---a2ui_JSON--- delimiters.
    """
    messages = []
    parts = text.split("---a2ui_JSON---")
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
        try:
            # Remove markdown code blocks if present
            part = part.strip().lstrip("```json").rstrip("```").strip()
            json_match = re.search(r'\{[\s\S]*\}', part)
            if json_match:
                json_str = json_match.group()
                parsed = json.loads(json_str)
                if isinstance(parsed, dict):
                    messages.append(parsed)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse A2UI JSON: {e}")
            continue
    
    return messages


class CompanyProfilerA2AServer:
    """Custom A2A server for Company Profiler with A2UI support."""
    
    def __init__(self, port: int = 8001):
        self.port = port
        self._agent = None
        self._runner = None
        self._user_id = "a2a_user"
        
    def _get_agent(self):
        """Lazy load the agent to avoid import issues."""
        if self._agent is None:
            from company_profiler.agent import company_profiler
            from google.adk.artifacts import InMemoryArtifactService
            from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
            from google.adk.runners import Runner
            from google.adk.sessions import InMemorySessionService
            
            self._agent = company_profiler
            self._runner = Runner(
                app_name=self._agent.name,
                agent=self._agent,
                artifact_service=InMemoryArtifactService(),
                session_service=InMemorySessionService(),
                memory_service=InMemoryMemoryService(),
            )
        return self._agent, self._runner
    
    async def get_agent_card(self, request: Request) -> JSONResponse:
        """Return the agent card metadata."""
        agent, _ = self._get_agent()
        
        card = {
            "name": agent.name,
            "description": agent.description or "Company Profiler Agent",
            "version": "0.0.1",
            "protocolVersion": "0.3.0",
            "url": f"http://localhost:{self.port}",
            "capabilities": {},
            "defaultInputModes": ["text/plain"],
            "defaultOutputModes": ["text/plain"],
            "preferredTransport": "JSONRPC",
            "supportsAuthenticatedExtendedCard": False,
            "skills": [
                {
                    "id": agent.name,
                    "name": "Company Profiler",
                    "description": agent.description,
                    "tags": ["company", "profiler", "a2ui"]
                }
            ],
            "extensions": [
                {
                    "uri": A2UI_EXTENSION_URI,
                    "description": "Provides agent driven UI using the A2UI JSON format."
                }
            ]
        }
        
        return JSONResponse(card)
    
    async def handle_message(self, request: Request) -> JSONResponse:
        """Handle incoming A2A messages."""
        from google.genai import types
        
        try:
            body = await request.json()
            print(f"DEBUG: Received request body: {body}")
        except Exception as e:
            logger.error(f"Failed to parse request body: {e}")
            return JSONResponse({"error": {"message": str(e)}}, status_code=400)
        
        # Extract the message from JSON-RPC format
        method = body.get("method", "")
        params = body.get("params", {})
        request_id = body.get("id", str(uuid.uuid4()))
        
        # Check for A2UI extension in headers
        a2ui_requested = A2UI_EXTENSION_URI in request.headers.get("X-A2A-Extensions", "")
        
        # Get the user message
        message_data = params.get("message", {})
        parts = message_data.get("parts", [])
        
        query = ""
        for part in parts:
            if part.get("kind") == "text":
                query = part.get("text", "")
                break
            elif part.get("kind") == "data":
                # Handle A2UI client events
                data = part.get("data", {})
                if "userAction" in data:
                    query = json.dumps(data)
                    break
        
        if not query:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32600, "message": "No message content provided"}
            })
        
        logger.info(f"Processing query: {query[:100]}...")
        
        # Run the agent
        agent, runner = self._get_agent()
        
        task_id = params.get("id", str(uuid.uuid4()))
        context_id = str(uuid.uuid4())
        
        # Get or create session
        session = await runner.session_service.get_session(
            app_name=agent.name,
            user_id=self._user_id,
            session_id=context_id,
        )
        if session is None:
            session = await runner.session_service.create_session(
                app_name=agent.name,
                user_id=self._user_id,
                state={},
                session_id=context_id,
            )
        
        # Run the agent
        current_message = types.Content(
            role="user", parts=[types.Part.from_text(text=query)]
        )
        
        final_response_content = None
        
        try:
            async for event in runner.run_async(
                user_id=self._user_id,
                session_id=session.id,
                new_message=current_message,
            ):
                logger.info(f"Event: {type(event).__name__}, author: {getattr(event, 'author', 'unknown')}")
                
                # Check if this is the final response from the last agent (a2ui_generator)
                if event.is_final_response():
                    author = getattr(event, 'author', '')
                    logger.info(f"Final response from: {author}")
                    
                    if event.content and event.content.parts:
                        text_content = "\n".join(
                            [p.text for p in event.content.parts if p.text]
                        )
                        # Only capture the final response if it contains A2UI output
                        # or if it's from the a2ui_generator
                        if "---a2ui_JSON---" in text_content or author == "a2ui_generator":
                            final_response_content = text_content
                            logger.info(f"Captured final A2UI response: {len(text_content)} chars")
                            break
                        elif not final_response_content:
                            # Store intermediate responses in case we don't get A2UI
                            final_response_content = text_content

        except Exception as e:
            logger.error(f"Error running agent: {e}")
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32603, "message": f"Agent execution failed: {str(e)}"}
            })
        
        # Build response parts
        response_parts = []
        
        if final_response_content:
            # Check if response contains A2UI JSON
            if "---a2ui_JSON---" in final_response_content and a2ui_requested:
                logger.info("Extracting A2UI messages from response")
                
                # Split text and JSON parts
                text_part, json_part = final_response_content.split("---a2ui_JSON---", 1)
                
                if text_part.strip():
                    response_parts.append({
                        "kind": "text",
                        "text": text_part.strip()
                    })
                
                # Extract A2UI messages
                a2ui_messages = extract_a2ui_messages("---a2ui_JSON---" + json_part)
                
                for msg in a2ui_messages:
                    response_parts.append({
                        "kind": "data",
                        "data": msg,
                        "mimeType": A2UI_MIME_TYPE
                    })
                
                logger.info(f"Extracted {len(a2ui_messages)} A2UI messages")
            else:
                # Plain text response
                response_parts.append({
                    "kind": "text",
                    "text": final_response_content
                })
        else:
            response_parts.append({
                "kind": "text",
                "text": "I'm sorry, I encountered an error processing your request."
            })
        
        # Build JSON-RPC response
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "kind": "task",
                "id": task_id,
                "contextId": context_id,
                "status": {
                    "state": "input-required",
                    "message": {
                        "role": "agent",
                        "parts": response_parts
                    }
                }
            }
        }
        
        return JSONResponse(response)
    
    async def handle_root(self, request: Request) -> JSONResponse:
        """Handle root path - dispatch based on method."""
        if request.method == "POST":
            return await self.handle_message(request)
        return JSONResponse({"status": "ok", "agent": "company_profiler"})
    
    def create_app(self) -> Starlette:
        """Create the Starlette application."""
        routes = [
            Route("/.well-known/agent-card.json", self.get_agent_card, methods=["GET", "OPTIONS"]),
            Route("/", self.handle_root, methods=["GET", "POST", "OPTIONS"]),
        ]
        
        app = Starlette(routes=routes)
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        return app


def create_a2a_app(port: int = 8001) -> Starlette:
    """Create the A2A application."""
    server = CompanyProfilerA2AServer(port=port)
    return server.create_app()
