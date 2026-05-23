"""Multi-tool Pydantic AI agent."""

from pydantic_ai import Agent


def get_weather(location: str) -> str:
    """Get weather for a location."""
    return f"Weather in {location}: Sunny, 72°F"


def get_forecast(location: str, days: int) -> str:
    """Get weather forecast."""
    return f"{days}-day forecast for {location}: Mostly sunny"


def get_alerts(location: str) -> str:
    """Get weather alerts."""
    return f"No alerts for {location}"


# Agent with multiple tools
weather_agent = Agent(
    "anthropic:claude-3-5-sonnet-20241022",
    tools=[get_weather, get_forecast, get_alerts],
    system_prompt="You are a comprehensive weather assistant with access to current weather, forecasts, and alerts.",
)
