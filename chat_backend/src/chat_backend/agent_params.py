from pydantic import BaseModel, Field, model_validator


class AgentParams(BaseModel):
    """Pydantic schema for the JSONB `agent_settings.params` column.

    Validated on both insert and read so the rest of the code can rely on
    well-typed fields, even though the storage is schema-less.
    """

    system_prompt: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    has_summarizer: bool = False
    summarizer_model_name: str | None = None
    summarization_max_tokens: int | None = None

    @model_validator(mode="after")
    def _summarizer_fields_required(self) -> "AgentParams":
        if self.has_summarizer:
            if not self.summarizer_model_name:
                raise ValueError("summarizer_model_name is required when has_summarizer is True")
            if not self.summarization_max_tokens or self.summarization_max_tokens <= 0:
                raise ValueError(
                    "summarization_max_tokens must be a positive integer when has_summarizer is True"
                )
        return self
