from pathlib import Path

import docx2md
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter


_HEADERS_TO_SPLIT_ON = [
    ("#", "h1"),
    ("##", "h2"),
    ("###", "h3"),
    ("####", "h4"),
]


def build_splitter() -> MarkdownHeaderTextSplitter:
    """The production splitter — also used by the recall eval to mirror real behavior."""
    return MarkdownHeaderTextSplitter(
        headers_to_split_on=_HEADERS_TO_SPLIT_ON, strip_headers=False
    )


def chunk_file(content: str, splitter: MarkdownHeaderTextSplitter) -> list[Document]:
    # docx2md preserves headings, lists, and tables as Markdown; the splitter then cuts
    # along heading boundaries so each chunk is one semantic section, with the heading
    # hierarchy preserved on the chunk's metadata.
    return splitter.split_text(content)