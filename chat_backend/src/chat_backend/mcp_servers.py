from langchain_mcp_adapters.client import MultiServerMCPClient

from .config import settings


def build_mcp_client(user_id: int) -> MultiServerMCPClient:
    """Configure MultiServerMCPClient with per-server headers.

    user_id is bound at session start, so every call to the user MCP server
    carries the matching X-User-Id for row-level segmentation.
    """
    return MultiServerMCPClient(
        {
            "user_mcp": {
                "url": settings.user_mcp_url,
                "transport": "streamable_http",
                "headers": {
                    "X-Api-Key": settings.mcp_api_key,
                    "X-User-Id": str(user_id),
                },
            },
            "kb_mcp": {
                "url": settings.kb_mcp_url,
                "transport": "streamable_http",
                "headers": {"X-Api-Key": settings.mcp_api_key},
            },
        }
    )
