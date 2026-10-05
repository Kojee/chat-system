from uuid import uuid4

from markupsafe import Markup
from sqladmin import Admin, ModelView

from .chroma_client import get_collection
from .chroma_utils import build_splitter, chunk_file
from .db import SessionLocal, engine
from .models import Document


class DocumentAdmin(ModelView, model=Document):
    name = "Document"
    name_plural = "Documents"
    icon = "fa-solid fa-file-lines"

    column_list = [
        Document.id,
        Document.original_filename,
        Document.chunks,
        Document.uploaded_at,
        Document.updated_at,
    ]
    column_searchable_list = [Document.original_filename]
    column_sortable_list = [Document.id, Document.original_filename, Document.uploaded_at, Document.updated_at]

    column_formatters = {
        Document.chunks: lambda m, _: (
            Markup(f'<span class="badge bg-info">{len(m.chunks)} chunks</span>')
            if m.chunks
            else Markup('<span class="badge bg-secondary">No chunks</span>')
        ),
    }

    column_formatters_detail = {
        Document.chunks: lambda m, _: _render_chunks(m.chunks),
    }

    form_columns = [
        Document.original_filename,
        Document.content,
        Document.chroma_metadata,
    ]

    async def after_model_change(self, data, model: Document, is_created: bool, request) -> None:
        collection = get_collection()
        splitter = build_splitter()

        if not is_created:
            old_ids = [c["chroma_id"] for c in (model.chunks or [])]
            if old_ids:
                collection.delete(ids=old_ids)

        chunks = chunk_file(model.content, splitter)
        chunk_entries = [
            {"text": c.page_content, "chroma_id": str(uuid4())}
            for c in chunks
        ]
        chroma_ids = [e["chroma_id"] for e in chunk_entries]
        chunk_texts = [e["text"] for e in chunk_entries]
        metadatas = [
            {"source": model.original_filename, "chunk_index": i, **(model.chroma_metadata or {})}
            for i in range(len(chunk_entries))
        ]
        collection.add(ids=chroma_ids, documents=chunk_texts, metadatas=metadatas)

        with SessionLocal() as s:
            db_model = s.get(Document, model.id)
            db_model.chunks = chunk_entries
            s.commit()

    async def after_model_delete(self, model: Document, request) -> None:
        collection = get_collection()
        ids = [c["chroma_id"] for c in (model.chunks or [])]
        if ids:
            collection.delete(ids=ids)


def _render_chunks(chunks: list | None) -> Markup:
    if not chunks:
        return Markup('<span class="text-muted">No chunks</span>')

    cards = []
    for i, chunk in enumerate(chunks):
        text = chunk.get("text", "")
        chroma_id = chunk.get("chroma_id", "")
        card = f"""
        <div style="
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 12px;
            background: #f8f9fa;
        ">
            <div style="
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 8px;
            ">
                <strong style="font-size: 1rem;">📄 Chunk {i + 1}</strong>
                <code style="font-size: 0.75rem; color: #6c757d;">{chroma_id}</code>
            </div>
            <div style="
                background: white;
                border: 1px solid #e9ecef;
                border-radius: 4px;
                padding: 12px;
                font-size: 0.9rem;
                line-height: 1.6;
                white-space: pre-wrap;
                word-break: break-word;
                max-height: 300px;
                overflow-y: auto;
            ">{text}</div>
        </div>
        """
        cards.append(card)

    return Markup('<div style="max-width: 100%;">' + "".join(cards) + "</div>")


def create_admin(app) -> Admin:
    admin = Admin(app, engine)
    admin.add_view(DocumentAdmin)
    return admin
