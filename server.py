"""MCP server entry point — exposes news, finance, and Strava tools."""

from typing import Any

from dotenv import load_dotenv
from fastmcp import FastMCP

from tools import finance, news, strava

load_dotenv()

mcp: FastMCP = FastMCP(
    name="daily-briefing",
    instructions=(
        "Tools for your daily briefing: Israeli news, tech headlines, "
        "S&P 500 / ETF prices, and Strava activity summaries."
    ),
)


# ---------------------------------------------------------------------------
# News
# ---------------------------------------------------------------------------


@mcp.tool()
def get_israeli_news(limit_per_source: int = 3) -> list[dict[str, Any]]:
    """Fetch top headlines from Israeli news sources (Times of Israel, Haaretz, Ynet)."""
    return news.get_israeli_news(limit_per_source)


@mcp.tool()
def get_tech_news(limit_per_source: int = 3) -> list[dict[str, Any]]:
    """Fetch top tech headlines from Hacker News, TechCrunch, and The Verge."""
    return news.get_tech_news(limit_per_source)


# ---------------------------------------------------------------------------
# Finance
# ---------------------------------------------------------------------------


@mcp.tool()
def get_etf_price(symbol: str) -> dict[str, Any]:
    """Get current price and daily change for a stock or ETF (e.g. SPY, VOO, AAPL)."""
    return finance.get_etf_price(symbol)


@mcp.tool()
def get_market_snapshot(tickers: list[str] | None = None) -> list[dict[str, Any]]:
    """Get a price snapshot for multiple tickers. Defaults to SPY, VOO, IVV, QQQ, VTI."""
    return finance.get_market_snapshot(tickers)


# ---------------------------------------------------------------------------
# Strava
# ---------------------------------------------------------------------------


@mcp.tool()
def get_recent_activities(limit: int = 5) -> list[dict[str, Any]]:
    """Fetch the most recent Strava activities with distance, duration, HR, and elevation."""
    return strava.get_recent_activities(limit)


@mcp.tool()
def get_weekly_summary() -> dict[str, Any]:
    """Get a training load summary for the current week (Monday to today)."""
    return strava.get_weekly_summary()


# ---------------------------------------------------------------------------
# Daily briefing resource
# ---------------------------------------------------------------------------


@mcp.resource("briefing://daily")
def daily_briefing() -> str:
    """A combined morning briefing: news headlines, market snapshot, and weekly training."""
    sections: list[str] = []

    # News
    sections.append("## Israeli News")
    for src in news.get_israeli_news(limit_per_source=2):
        sections.append(f"### {src['source']}")
        for a in src["articles"]:
            sections.append(f"- [{a['title']}]({a['link']})")

    sections.append("\n## Tech News")
    for src in news.get_tech_news(limit_per_source=2):
        sections.append(f"### {src['source']}")
        for a in src["articles"]:
            sections.append(f"- [{a['title']}]({a['link']})")

    # Finance
    sections.append("\n## Market Snapshot")
    for q in finance.get_market_snapshot():
        if "error" in q:
            sections.append(f"- {q['symbol']}: error — {q['error']}")
        else:
            arrow = "▲" if q["change"] >= 0 else "▼"
            sections.append(
                f"- **{q['symbol']}**: ${q['price']} "
                f"{arrow} {q['change']:+.2f} ({q['change_pct']:+.2f}%)"
            )

    # Strava — optional, skipped if credentials are missing
    try:
        summary = strava.get_weekly_summary()
        sections.append("\n## Strava — This Week")
        sections.append(f"- Activities: {summary['activity_count']}")
        sections.append(f"- Distance: {summary['total_distance_km']} km")
        sections.append(f"- Duration: {summary['total_duration']}")
        sections.append(f"- Elevation: {summary['total_elevation_m']} m")
    except ValueError:
        sections.append("\n## Strava\n- _Credentials not configured — see .env.example_")

    return "\n".join(sections)


if __name__ == "__main__":
    mcp.run(transport="stdio")
