# chat-backend
Service implementing the chat system backend where the agent is set up and responses to user messages are generated.

## Endpoints
- `POST /login` — simulates login: sets the `user_id` cookie in the response. Everything under `/chats` requires this cookie (validated for presence, not value, by `CookieAuthMiddleware` in `src/chat_backend/auth.py`).
- `POST /chats` — creates a new chat for the logged-in user and returns `thread_id` and `agent_settings_id` linked to the default settings.
- `GET /chats/{thread_id}/messages` — returns chat messages in chronological order (only if the `thread_id` belongs to the logged-in user).
- `POST /chats/{thread_id}/messages` — sends a message and streams the agent's response via SSE (events: `token`, `error`, `done`).
- `GET /health` — healthcheck also used by docker compose.

## Models
The service uses the following models (`src/chat_backend/models.py`):
- Chat: contains the thread_id for resuming a chat, the user_id to associate it with a user, and agent_settings_id to associate it with a particular agent setup.
- Message: chat messages, differentiated by `role` ("agent", "user").
- AgentSettings: the setup of a particular agent (system prompt, model, summarization parameters, `is_default` flag). A deferrable `EXCLUDE` constraint ensures that at most one row with `is_default = true` exists, but allows swapping the default in a single transaction.

At startup, the lifespan creates the tables (`Base.metadata.create_all`) and, if empty, seeds a default `AgentSettings` row from config (see `seed_default_agent_settings` in `persistence.py`). The system prompt is read from `config/system_prompt.txt`, so it can be edited without touching the code.

## Chat Flow
The implementation is in `src/chat_backend/routes.py`, function `send_message`. At the start of each request, the existence of a chat is verified if a thread id was provided; otherwise a new one is created. Then, the agent is initialized using `build_agent` (`src/chat_backend/agent.py`) and the chat loop is started. The endpoint uses SSE to stream tokens and make the chat more responsive.

`build_agent` retrieves the agent parameters from the settings linked to the chat (or from the default if not linked), then mounts the MCP tools via `MultiServerMCPClient` (`src/chat_backend/mcp_servers.py`), injecting the logged-in user's `X-User-Id` and the configured `X-Api-Key` on requests to MCP servers. Short-term memory is handled by `SummarizationMiddleware` when the agent setup provides for it.

Database access functions are in `src/chat_backend/persistence.py`, config (env-driven via pydantic-settings) in `src/chat_backend/config.py`.

## Settings
Variables are read from `.env` (see `.env.example`):
```
cp .env.example .env
```
The most important ones:
- `OPENAI_API_KEY` — required at runtime for the model.
- `OPENAI_MODEL`, `SUMMARIZATION_MAX_TOKENS` — bootstrap defaults for settings seeded at first startup.
- `MCP_API_KEY`, `USER_MCP_URL`, `KB_MCP_URL` — injected on calls to MCP servers.
- `CHATDB_DSN`, `BACKEND_HOST`, `BACKEND_PORT` — database connection and service binding.

In docker compose all these variables are already set (except `OPENAI_API_KEY` which is read from the root repo `.env`).

## Tests
A test suite for database access functions is in `tests/test_persistence.py`. It uses `testcontainers` to spin up a dedicated Postgres for each session, so Docker needs to be running on the machine. No `OPENAI_API_KEY` is required: the tests do not invoke the model.

To run them, from the root of the repo:
```
make test-chat
```

## Execution
Run from the root of the repo:
```
make up
```

The command also launches the mcp servers and the various postgres instances used by the services via docker compose.
