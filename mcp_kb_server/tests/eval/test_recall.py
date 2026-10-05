"""Synthetic recall@k benchmark for the KB RAG pipeline.

For each chunk produced by the production loader/splitter, an LLM generates a
handful of questions whose answer should live in that chunk. We then embed and
query through the same `OpenAIEmbeddingFunction` the server uses and check how
often the *source* chunk shows up in the top-K results.

Question generation is cached on disk keyed by sha256 of the chunk text, so the
test is essentially free to re-run unless the chunking changes — which is
exactly when you want to regenerate.

Run with `make eval` (or `pytest --eval -s -v`).
"""
import hashlib
import json
import os
from pathlib import Path

import chromadb
import docx2md
import openai
import pytest

from mcp_kb_server.chroma_client import build_collection
from mcp_kb_server.config import settings
from mcp_kb_server.seed import build_splitter, chunk_file

CACHE_PATH = Path(__file__).parent / "question_cache.json"
N_QUESTIONS_PER_CHUNK = 3
TOP_K = 10
QUESTION_GEN_MODEL = "gpt-4o-mini"
RECALL_AT_5_FLOOR = 0.30  # very loose; raise once you have a baseline you trust


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_cache() -> dict[str, list[str]]:
    if not CACHE_PATH.exists():
        return {}
    return json.loads(CACHE_PATH.read_text(encoding="utf-8"))


def _save_cache(cache: dict[str, list[str]]) -> None:
    CACHE_PATH.write_text(
        json.dumps(cache, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )


def _generate_questions(client: openai.OpenAI, text: str, n: int) -> list[str]:
    resp = client.chat.completions.create(
        model=QUESTION_GEN_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Sei un generatore di domande di test per un sistema RAG nel dominio fiscale italiano. "
                    f"Genera ESATTAMENTE {n} domande in italiano che un cliente di un servizio di contabilità per Partite IVA potrebbe porre e la "
                    "cui risposta si trovi nel passaggio fornito. Le domande devono essere realistiche, "
                    "variate nel fraseggio e NON copiare il testo del passaggio alla lettera. "
                    'Rispondi solo con JSON nel formato {"questions": ["...", "..."]}.'
                ),
            },
            {"role": "user", "content": f"Passaggio:\n{text}"},
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
    )
    parsed = json.loads(resp.choices[0].message.content or "{}")
    qs = parsed.get("questions")
    if not isinstance(qs, list) or not qs:
        raise ValueError(f"unexpected JSON shape from question generator: {parsed!r}")
    return [str(q) for q in qs[:n]]


@pytest.fixture(scope="session")
def chunks():
    """Run the production loader + splitter; returns chunks with synthetic IDs and metadata."""
    splitter = build_splitter()
    out = []
    for path in sorted(settings.docs_path.glob("*.docx")):
        raw = docx2md.do_convert(str(path), use_md_table=True)
        for i, doc in enumerate(chunk_file(raw, splitter)):
            out.append(
                {
                    "id": f"{path.name}::{i}",
                    "text": doc.page_content,
                    "metadata": {"source": path.name, "chunk_index": i, **doc.metadata},
                }
            )
    assert out, "no chunks produced — check docs_path"
    return out


@pytest.fixture(scope="session")
def collection(chunks):
    """In-memory Chroma collection"""
    coll = build_collection(chromadb.EphemeralClient())
    coll.add(
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        metadatas=[c["metadata"] for c in chunks],
    )
    return coll


@pytest.fixture(scope="session")
def questions(chunks):
    """List of (source_chunk_id, question). Generated questions are cached by chunk-content hash."""
    cache = _load_cache()
    client = openai.OpenAI(api_key=settings.openai_api_key)
    pairs: list[tuple[str, str]] = []
    newly_generated = 0
    for c in chunks:
        h = _sha(c["text"])
        if h not in cache:
            cache[h] = _generate_questions(client, c["text"], N_QUESTIONS_PER_CHUNK)
            newly_generated += 1
        for q in cache[h]:
            pairs.append((c["id"], q))
    if newly_generated:
        _save_cache(cache)
        print(f"\n[eval] generated questions for {newly_generated} new chunks; cache size: {len(cache)}")
    return pairs


@pytest.mark.eval
def test_recall_benchmark(collection, questions):
    if not settings.openai_api_key or settings.openai_api_key.startswith("sk-replace"):
        pytest.skip("OPENAI_API_KEY not set")

    hits_at_1 = 0
    hits_at_5 = 0
    reciprocal_ranks: list[float] = []
    failed: list[tuple[str, str, list[str]]] = []

    for source_id, question in questions:
        res = collection.query(query_texts=[question], n_results=TOP_K)
        retrieved_ids: list[str] = res["ids"][0]
        if source_id in retrieved_ids:
            rank = retrieved_ids.index(source_id) + 1
            reciprocal_ranks.append(1.0 / rank)
            if rank == 1:
                hits_at_1 += 1
            if rank <= 5:
                hits_at_5 += 1
        else:
            reciprocal_ranks.append(0.0)
            failed.append((source_id, question, retrieved_ids))

    total = len(questions)
    recall_at_1 = hits_at_1 / total
    recall_at_5 = hits_at_5 / total
    mrr = sum(reciprocal_ranks) / total

    print()
    print(f"  questions:  {total}")
    print(f"  recall@1:   {recall_at_1:.2%}  ({hits_at_1}/{total})")
    print(f"  recall@5:   {recall_at_5:.2%}  ({hits_at_5}/{total})")
    print(f"  MRR:        {mrr:.4f}")
    if failed:
        print(f"\n  {len(failed)} questions did not retrieve their source in top-{TOP_K}:")
        for src, q, ret in failed[:5]:
            print(f"    expected={src!r}")
            print(f"      q={q!r}")
            print(f"      top-3 retrieved={ret[:3]}")
        if len(failed) > 5:
            print(f"    ... +{len(failed) - 5} more")

    assert recall_at_5 >= RECALL_AT_5_FLOOR, (
        f"recall@5 below floor: {recall_at_5:.2%} < {RECALL_AT_5_FLOOR:.0%}"
    )
