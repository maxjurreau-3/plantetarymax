"""
HTTP Message Handler
Rebuild 3: Worker Integration

Handles HTTP requests from Cloudflare Workers.
Converts HTTP to internal message format.
"""

from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import json
import uuid


@dataclass
class HTTPRequest:
    """Parsed HTTP request"""
    method: str
    path: str
    headers: Dict[str, str]
    body: Dict[str, Any]
    request_id: str


@dataclass
class HTTPResponse:
    """HTTP response to send back"""
    status: int
    headers: Dict[str, str]
    body: Dict[str, Any]
    request_id: str


class HTTPMessageHandler:
    """
    Converts HTTP requests to internal messages.
    Validates and enriches request data.
    """
    
    def __init__(self):
        self.request_count = 0
    
    def parse_request(self, http_request: Dict[str, Any]) -> Optional[HTTPRequest]:
        """
        Parse HTTP request into internal format.
        Validates required fields.
        """
        try:
            method = http_request.get("method", "POST")
            path = http_request.get("path", "/")
            headers = http_request.get("headers", {})
            
            # Parse body
            body_str = http_request.get("body", "{}")
            if isinstance(body_str, str):
                body = json.loads(body_str)
            else:
                body = body_str
            
            # Generate request ID if not present
            request_id = headers.get("X-Request-ID", str(uuid.uuid4()))
            
            return HTTPRequest(
                method=method,
                path=path,
                headers=headers,
                body=body,
                request_id=request_id,
            )
        except Exception as e:
            print(f"[HTTP] Parse failed: {e}")
            return None
    
    def build_response(self, status: int, body: Dict[str, Any], request_id: str) -> HTTPResponse:
        """
        Build HTTP response.
        """
        return HTTPResponse(
            status=status,
            headers={
                "Content-Type": "application/json",
                "X-Request-ID": request_id,
            },
            body=body,
            request_id=request_id,
        )


class MessageRouter:
    """
    Routes parsed HTTP messages to appropriate handlers.
    """
    
    def __init__(self):
        self.routes: Dict[str, callable] = {}
    
    def register_route(self, path: str, handler: callable) -> None:
        """
        Register a route handler.
        """
        self.routes[path] = handler
    
    def route_message(self, request: HTTPRequest) -> Optional[Dict[str, Any]]:
        """
        Route message to appropriate handler.
        Returns response body.
        """
        handler = self.routes.get(request.path)
        if not handler:
            return {"error": f"No handler for {request.path}"}
        
        try:
            return handler(request.body)
        except Exception as e:
            print(f"[ROUTING] Handler error: {e}")
            return {"error": str(e)}
