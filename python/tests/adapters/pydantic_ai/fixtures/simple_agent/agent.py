"""Simple Pydantic AI agent with structured output."""

from pydantic import BaseModel
from pydantic_ai import Agent


class WeatherResponse(BaseModel):
    """Structured weather response."""

    temperature: float
    condition: str
    location: str


# Simple agent with structured output
weather_agent = Agent(
    "openai:gpt-4o-mini",
    result_type=WeatherResponse,
    system_prompt="You are a weather assistant.",
)
