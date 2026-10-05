from functools import cache

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.api import ClientAPI
from chromadb.utils import embedding_functions

from .config import settings


def build_collection(client: ClientAPI) -> Collection:
    """
    Single source of truth for embedder + similarity metric + collection name.
    """
    embedder = embedding_functions.OpenAIEmbeddingFunction(
        api_key_env_var="OPENAI_API_KEY",
        model_name=settings.openai_embedding_model,
    )
    return client.get_or_create_collection(
        name=settings.chroma_collection,
        embedding_function=embedder,
        metadata={"hnsw:space": "cosine"},
    )


@cache
def get_collection() -> Collection:
    """Production accessor — lazy-builds the persistent client + collection on first call."""
    client = chromadb.PersistentClient(path=str(settings.chroma_path))
    return build_collection(client)
