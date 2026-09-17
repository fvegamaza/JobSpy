"""MCP server exposing JobSpy searches to agents such as Hermes."""

from __future__ import annotations

from datetime import date, datetime
import os
from typing import Any

import pandas as pd
from jobspy import scrape_jobs
from mcp.server.fastmcp import FastMCP


mcp = FastMCP(
    "JobSpy",
    host=os.getenv("MCP_HOST", "127.0.0.1"),
    port=int(os.getenv("MCP_PORT", "8000")),
    stateless_http=True,
    json_response=True,
)

SUPPORTED_SITES = {
    "indeed",
    "linkedin",
    "glassdoor",
    "google",
    "zip_recruiter",
    "bayt",
    "bdjobs",
}


def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, (str, int, float, bool)):
        if not isinstance(value, str) and pd.isna(value):
            return None
        return value
    return str(value)


@mcp.tool()
def search_jobs(
    search_term: str,
    location: str,
    hours_old: int = 168,
    results_wanted: int = 25,
    sites: list[str] | None = None,
    country_indeed: str | None = None,
) -> dict[str, Any]:
    """Search public job boards for recent vacancies.

    Args:
        search_term: Role or keywords, for example "data scientist".
        location: City/region and country, for example "Vienna, Austria".
        hours_old: Maximum posting age in hours (1-720; 168 is one week).
        results_wanted: Maximum results requested per site (1-100).
        sites: Any of indeed, linkedin, glassdoor, google, zip_recruiter,
            bayt, or bdjobs. Defaults to Indeed and LinkedIn.
        country_indeed: Country name used by Indeed/Glassdoor, such as Austria.

    Returns:
        A JSON object containing the result count and job records.
    """
    if not search_term.strip() or not location.strip():
        raise ValueError("search_term and location must not be empty")
    if not 1 <= hours_old <= 720:
        raise ValueError("hours_old must be between 1 and 720")
    if not 1 <= results_wanted <= 100:
        raise ValueError("results_wanted must be between 1 and 100")

    selected_sites = sites or ["indeed", "linkedin"]
    unsupported = set(selected_sites) - SUPPORTED_SITES
    if unsupported:
        raise ValueError(f"Unsupported sites: {', '.join(sorted(unsupported))}")

    kwargs: dict[str, Any] = {
        "site_name": selected_sites,
        "search_term": search_term.strip(),
        "location": location.strip(),
        "hours_old": hours_old,
        "results_wanted": results_wanted,
        "verbose": 1,
    }
    if "google" in selected_sites:
        kwargs["google_search_term"] = (
            f"{search_term.strip()} jobs in {location.strip()} posted recently"
        )
    if country_indeed:
        kwargs["country_indeed"] = country_indeed

    jobs = scrape_jobs(**kwargs)
    records = [
        {key: _json_safe(value) for key, value in record.items()}
        for record in jobs.to_dict(orient="records")
    ]
    return {"count": len(records), "jobs": records}


if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport not in {"stdio", "sse", "streamable-http"}:
        raise ValueError("MCP_TRANSPORT must be stdio, sse, or streamable-http")
    mcp.run(transport=transport)
