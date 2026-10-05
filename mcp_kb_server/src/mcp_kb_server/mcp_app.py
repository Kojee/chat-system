from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import BaseModel, Field

from .chroma_client import get_collection


class KnowledgeChunk(BaseModel):
    content: str
    source: str = Field(description="Filename of the source document the chunk was taken from")
    score: float = Field(description="Cosine distance; lower is more relevant")


class SearchResult(BaseModel):
    query: str
    chunks: list[KnowledgeChunk]


mcp = FastMCP(
    "kb-mcp-server",
    streamable_http_path="/",
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


@mcp.tool()
def search_knowledge_base(query: str, k: int = 5) -> SearchResult:
    """
    Search the tax knowledge base for chunks relevant to the user's question.
    Returns up to `k` chunks ranked by semantic similarity (cosine distance, ascending).
    """
    collection = get_collection()
    res = collection.query(query_texts=[query], n_results=k)
    docs = res["documents"][0]
    metas = res["metadatas"][0]
    dists = res["distances"][0]
    chunks = [
        KnowledgeChunk(content=d, source=m["source"], score=float(s))
        for d, m, s in zip(docs, metas, dists)
    ]
    return SearchResult(query=query, chunks=chunks)
