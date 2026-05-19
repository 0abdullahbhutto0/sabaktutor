"""
SSE Streaming Helpers
Formats events for Server-Sent Events protocol.
"""

import json
from typing import Dict, Any


def sse_stream(event: str, data: Dict[str, Any]) -> str:
    """Format a single SSE event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"
