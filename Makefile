SHELL := /bin/bash

.PHONY: help up down logs chat eval redteam test test-user-mcp test-kb-mcp test-chat

help:
	@echo "Targets:"
	@echo "  make up                            Start the full stack in Docker (Postgres x2 + MCP x2 + chat backend)"
	@echo "  make down                          Stop the stack"
	@echo "  make logs                          Tail container logs"
	@echo "  make chat USER_ID=N [THREAD_ID=T]  Run the chat CLI client (ensures the stack is up)"
	@echo "  make eval                          Run the KB RAG recall benchmark (paid OpenAI calls; cached)"
	@echo "  make redteam                       Run the cross-user leak red-team suite (paid OpenAI calls)"
	@echo "  make test                          Run all sub-project test suites (skips paid eval/redteam)"
	@echo "  make test-user-mcp                 Run mcp_user_server tests"
	@echo "  make test-kb-mcp                   Run mcp_kb_server tests (eval marker excluded)"
	@echo "  make test-chat                     Run chat_backend tests"

up:
	docker compose up --build -d --wait

down:
	docker compose down

logs:
	docker compose logs -f

eval:
	cd mcp_kb_server && OPENAI_API_KEY=$$(grep '^OPENAI_API_KEY=' ../.env | cut -d= -f2-) uv run pytest --eval -s -v tests/eval

redteam: up
	cd chat_backend && uv run pytest --redteam -s -v tests/redteam

test: test-user-mcp test-kb-mcp test-chat
	@echo "all suites passed"

test-user-mcp:
	cd mcp_user_server && uv run pytest -v

test-kb-mcp:
	cd mcp_kb_server && uv run pytest -v

test-chat:
	cd chat_backend && uv run pytest -v

chat: up
ifndef USER_ID
	$(error USER_ID is required, e.g. `make chat USER_ID=1`)
endif
	cd chat_cli && uv run chat-cli --user-id $(USER_ID) $(if $(THREAD_ID),--thread-id $(THREAD_ID),)
