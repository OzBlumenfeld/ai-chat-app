import logging
import os
import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP
from email_sender import EmailNotificationSender
from logging_config import setup_logging

# Load environment variables from .env file
load_dotenv()

# Call setup_logging at the top level
setup_logging()

logger = logging.getLogger(__name__)


# Combine everything into ONE instance
mcp = FastMCP(
    name="MyAssistantServer",
    instructions="This server provides tools for basic math, sending email notifications, and fetching latest news."
)


@mcp.tool
def multiply(a: float, b: float) -> float:
    """Multiplies two numbers together."""
    return a * b


@mcp.tool
async def send_email(recipient_email: str, subject: str, body: str) -> str:
    logger.info("Send email called", extra={"recipient_email": recipient_email, "subject": subject, "body": body})
    email_sender = EmailNotificationSender()
    # Call directly without asyncio.run()
    success = await email_sender.send_email(recipient_email=recipient_email, subject=subject, body=body)
    if success:
        return f"Email sent successfully to {recipient_email}."
    else:
        return f"Failed to send email to {recipient_email}. Please check the server logs."


@mcp.tool
async def fetch_news(query: str = None, category: str = None) -> str:
    """
    Fetches the top 20 news headlines based on a query or category.
    Categories: business, entertainment, general, health, science, sports, technology.
    """
    api_key = os.getenv("NEWS_API_KEY")
    if not api_key or api_key == "your_news_api_key_here":
        return "Error: News API key not configured. Please add NEWS_API_KEY to your .env file."

    base_url = "https://newsapi.org/v2/top-headlines"
    params = {
        "apiKey": api_key,
        "pageSize": 20,
        "language": "en"
    }

    if query:
        params["q"] = query
    if category:
        params["category"] = category

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()

            articles = data.get("articles", [])
            if not articles:
                return f"No news found for query: {query}" if query else "No top headlines found."

            result = ["Latest News Headlines:"]
            for i, article in enumerate(articles, 1):
                title = article.get("title")
                source = article.get("source", {}).get("name")
                url = article.get("url")
                result.append(f"{i}. {title} (Source: {source}) - {url}")

            return "\n".join(result)
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            return f"Failed to fetch news: {str(e)}"



if __name__ == "__main__":
    mcp.run(transport="sse", port=9005)