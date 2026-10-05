import logging
from uuid import uuid4

import docx2md
from sqlalchemy import func, select

from mcp_kb_server.chroma_utils import build_splitter, chunk_file

from .chroma_client import get_collection
from .config import settings
from .db import Base, SessionLocal, engine
from .models import Document

logger = logging.getLogger(__name__)


def run() -> None:
    Base.metadata.create_all(engine)

    with SessionLocal() as session:
        existing = session.scalar(select(func.count(Document.id)))
    if existing:
        logger.info("documents table already populated (%d rows); skipping seed", existing)
        return

    splitter = build_splitter()
    collection = get_collection()

    total_chunks = 0
    for path in sorted(settings.docs_path.glob("*.docx")):
        raw = docx2md.do_convert(str(path), use_md_table=True)
        docs = chunk_file(raw, splitter)
        if not docs:
            logger.warning("no chunks extracted from %s", path.name)
            continue

        chunk_entries = [
            {"text": d.page_content, "chroma_id": str(uuid4())}
            for d in docs
        ]
        chroma_ids = [e["chroma_id"] for e in chunk_entries]
        chunk_texts = [e["text"] for e in chunk_entries]
        metadatas = [
            {"source": path.name, "chunk_index": i, **d.metadata}
            for i, d in enumerate(docs)
        ]
        collection.add(ids=chroma_ids, documents=chunk_texts, metadatas=metadatas)

        with SessionLocal() as session:
            doc = Document(
                original_filename=path.name,
                content=raw,
                chunks=chunk_entries,
                chroma_metadata={"source": path.name},
            )
            session.add(doc)
            session.commit()

        logger.info("seeded %d chunks from %s", len(chunk_entries), path.name)
        total_chunks += len(chunk_entries)

    logger.info("seeded %d total chunks into '%s'", total_chunks, settings.chroma_collection)
