# mcp-user-server
MCP Server used to expose user data. Each request must include the id of the user who triggered it. This id is used to filter data to prevent leaks.

## Exposed MCP Tool
- `get_user_info() -> UserInfo` (see `src/mcp_user_server/mcp_app.py`). Takes no parameters: the `user_id` is taken from the context set by the middleware from the `X-User-Id` header. This is intentional, to ensure the model cannot decide which user to read. `UserInfo` exposes first name, last name, tax regime, social security fund, accountant, VAT opening date, and revenue for the last two years.

## Auth
`AuthHeadersMiddleware` (`src/mcp_user_server/auth.py`) requires two headers on `/mcp`:
- `X-Api-Key` — for now, only the presence is validated, not the value.
- `X-User-Id` — must be an integer; it is placed in a `ContextVar` (`current_user_id`) and used by the tool to perform the filtered query.

## Seeding
On first startup (`seed.run()` invoked from the `lifespan` in `main.py`), the service creates the schema and populates the `users` table from `data/customer_data.csv` if empty. The seeded rows have `id` from 1 to 4 (one user per CSV row): these are the ones to pass to `make chat USER_ID=…`.

## Settings
Variables read from environment / `.env` (see `src/mcp_user_server/config.py`):
- `DATABASE_URL` — connection to the Postgres database for users.
- `HOST`, `PORT` — service binding (default `0.0.0.0:8001`).
- `CSV_PATH` — path to the CSV for seeding (default `data/customer_data.csv`).

In docker compose all these variables are already set and the service does not require any local configuration; for standalone usage outside compose, at least a reachable `DATABASE_URL` is needed.

## Execution
Launch the entire stack from the root with: `make up`

## Tests
A test suite has been implemented to verify that the endpoint offered by the mcp server returns only the data of the user provided via the header. It uses `testcontainers` to spin up a dedicated Postgres for the test session, so Docker needs to be running on the machine. Test data is created on the fly via `factory_boy` (`tests/factories.py`), not from the CSV.

To run it, from the root of the repo:
```
make test-user-mcp
```
