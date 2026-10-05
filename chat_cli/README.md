# chat-cli
Minimal CLI client for `chat_backend`. Sends messages to the backend via HTTP and displays the agent's response by streaming tokens via SSE.

## Execution
```
make chat USER_ID=<id>                # new chat
make chat USER_ID=<id> THREAD_ID=<t>  # resume an existing chat
```
