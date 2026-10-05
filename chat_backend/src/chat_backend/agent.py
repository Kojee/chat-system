from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain_openai import ChatOpenAI

from .agent_params import AgentParams
from .config import settings
from .mcp_servers import build_mcp_client


async def build_agent(user_id: int, checkpointer, params: AgentParams):
    api_key = settings.openai_api_key.get_secret_value()
    model = ChatOpenAI(model=params.model_name, api_key=api_key)

    middleware = []
    if params.has_summarizer:
        summarizer_model = (
            model
            if params.summarizer_model_name == params.model_name
            else ChatOpenAI(model=params.summarizer_model_name, api_key=api_key)
        )
        middleware.append(
            SummarizationMiddleware(
                model=summarizer_model,
                trigger=("tokens", params.summarization_max_tokens),
            )
        )

    client = build_mcp_client(user_id)
    tools = await client.get_tools()

    return create_agent(
        model=model,
        tools=tools,
        system_prompt=params.system_prompt,
        middleware=middleware,
        checkpointer=checkpointer,
    )
