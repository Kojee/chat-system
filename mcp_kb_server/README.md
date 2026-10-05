# mcp-kb-server
MCP Server for retrieving documentation stored in `data/*.docx`. The documents are chunked and saved in a vector db (Chroma) so they can be searched by similarity against the query provided by the agent (the client's message).
To best preserve the data structure, it was decided to convert the docx files to md, in order to maintain the structure (headers, subheaders, ...) and thus split the text into sections based on the md headers.

## Exposed MCP Tool
- `search_knowledge_base(query: str, k: int = 5) -> SearchResult` (see `src/mcp_kb_server/mcp_app.py`). Returns up to `k` chunks sorted by increasing cosine distance, with `content`, `source` (original file name), and `score`.

## Auth
The `AuthHeadersMiddleware` (`src/mcp_kb_server/auth.py`) requires the `X-Api-Key` header on all requests to `/mcp`. For now, only the presence of the header is validated, not the value — the KB contents are shared among all users anyway, so there is no per-user filtering.

## Seeding
On first startup (`lifespan` in `main.py`), `seed.run()` checks if the Chroma collection is empty and, if so, indexes all `.docx` files in `data/` using `docx2md` + `MarkdownHeaderTextSplitter`. If the collection is already populated, seeding is skipped. The collection is persisted in the `kb-chroma` volume mounted at `/app/chroma_data` (see `docker-compose.yml`), so it survives restarts. To re-index, simply delete the volume: `docker compose down -v`.

## Settings
Variables read from `.env` or the environment (see `src/mcp_kb_server/config.py`):
- `OPENAI_API_KEY` — required by Chroma for computing embeddings. Via `make up` it is taken from the root repo `.env`.
- `OPENAI_EMBEDDING_MODEL` (default `text-embedding-3-small`).
- `HOST`, `PORT` — service binding (default `0.0.0.0:8002`).
- `CHROMA_PATH`, `CHROMA_COLLECTION`, `DOCS_PATH` — paths and collection name.

## Execution
Launch the entire stack from the root with: `make up`

## Tests
A test for verifying some metrics on the effectiveness of the RAG setup has been implemented in `tests/eval/test_recall.py`. The test requires an `OPENAI_API_KEY` set in the `.env` at the root of the service (it is set on the fly by reading from the file via the `make eval` command) to work, as it calls an OpenAI embedding model and generates questions from the chunks (if the knowledge base and chunking method do not change, the questions are reused from `tests/eval/question_cache.json`).

The eval test is gated by the pytest flag `--eval` (see `tests/conftest.py`), so it is skipped by default to avoid accidental costs.

To run it (from the root of the repo):
```
make eval
```

There is also a `make test-kb-mcp` command, created for completeness with respect to the other projects, which runs tests skipping the RAG test mentioned above. Currently there are no other tests, so this command will report that no tests were run.
