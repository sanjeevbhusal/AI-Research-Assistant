import json
import logging
import os
import smtplib
from datetime import date
from email.message import EmailMessage
from typing import cast

import requests
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from pydantic import BaseModel

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Secrets and configuration are loaded from the .env file.
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
SERPER_API_KEY = os.environ["SERPER_API_KEY"]
BROWSERLESS_API_KEY = os.environ["BROWSERLESS_API_KEY"]

# Gmail account used to send email. The app password is a 16-character
# password generated at https://myaccount.google.com/apppasswords
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
FROM_GMAIL_ADDRESS = os.environ["FROM_GMAIL_ADDRESS"]
TO_GMAIL_ADDRESS = os.environ["TO_GMAIL_ADDRESS"]


class SearchResult(BaseModel):
    """Search Result."""

    id: int
    title: str
    snippet: str
    link: str
    search_term: str


class MarkdownResult(BaseModel):
    """Markdown Result."""

    id: int
    title: str
    content: str
    link: str
    search_term: str


class FilteredResult(BaseModel):
    """AI Filtered Search Result."""

    id: int
    explanation: str


class FilteredResults(BaseModel):
    """AI Filtered Google Results."""

    results: list[FilteredResult]


class MarkdownSummary(BaseModel):
    """Markdown Summary."""

    summary: str
    link: str


def _search_google(search_term: str) -> list[SearchResult]:
    """Fetch google results for a serch term."""
    url = "https://google.serper.dev/search"

    payload = json.dumps({"q": search_term, "gl": "gb", "num": 10, "tbs": "qdr:d"})

    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "CONTENT-TYPE": "application/json",
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    response.raise_for_status()
    results = json.loads(response.text)
    organic_results = results["organic"]

    return [
        SearchResult(
            id=id,
            title=result["title"],
            snippet=result.get(
                "snippet", ""
            ),  # sometimes snippet isn't present on the response
            link=result["link"],
            search_term=search_term,
        )
        for id, result in enumerate(organic_results)
    ]


def get_search_results(search_terms: list[str]) -> list[SearchResult]:
    """Get Search Results."""
    search_results: list[SearchResult] = []
    for term in search_terms:
        results = _search_google(term)
        search_results.extend(results)

    return search_results


def filter_results(
    search_results: list[SearchResult],
    relevant_criteria: str,
    irrelevant_criteria: str,
) -> list[SearchResult]:
    """Filter search results."""
    with open("./prompts/relevance_filter.md") as file:
        prompt = file.read()

    search_terms = set([result.search_term for result in search_results])
    pretty = json.dumps(
        [item.model_dump() for item in search_results],
        indent=2,
        ensure_ascii=False,
    )

    prompt = prompt.replace("{search_terms}", str(search_terms))
    prompt = prompt.replace("{search_results}", pretty)
    prompt = prompt.replace("{relevant_criteria}", relevant_criteria)
    prompt = prompt.replace("{iirelevant_criteria}", irrelevant_criteria)

    model = init_chat_model(
        "gpt-4o-mini",
        api_key=OPENAI_API_KEY,
    ).with_structured_output(FilteredResults)
    response = cast(FilteredResults, model.invoke(prompt))

    filtered_results_ids = set([result.id for result in response.results])

    return [
        search_result
        for search_result in search_results
        if search_result.id in filtered_results_ids
    ]


def _fetch_markdown_content(url: str) -> str:
    """Fetch clean readable page content as markdown using Browserless Smart Scrape.

    Args:
        url: The page URL to fetch.
        api_token: Your Browserless API token.

    Returns:
        Clean markdown content from the page.

    Raises:
        requests.HTTPError: If the API request fails.
        ValueError: If markdown content is missing.
    """
    endpoint = (
        f"https://production-sfo.browserless.io/smart-scrape?token={BROWSERLESS_API_KEY}"
    )

    response = requests.post(
        endpoint,
        headers={"Content-Type": "application/json"},
        json={"url": url, "formats": ["markdown"]},
        timeout=120,
    )

    response.raise_for_status()
    data = response.json()

    markdown = data.get("markdown")
    if not markdown:
        raise ValueError("No markdown content returned")

    return markdown


def fetch_markdown_contents(results: list[SearchResult]) -> list[MarkdownResult]:
    """Fetch Markdown content."""
    markdown_results: list[MarkdownResult] = []
    for result in results:
        content = _fetch_markdown_content(result.link)
        logger.info(f"Fetched markdown content for {result.link}")
        result = MarkdownResult(
            id=result.id,
            link=result.link,
            title=result.title,
            content=content,
            search_term=result.search_term,
        )
        markdown_results.append(result)

    return markdown_results


def generate_summaries(markdown_results: list[MarkdownResult]) -> list[MarkdownSummary]:
    """Generate summaries."""
    model = init_chat_model(
        "gpt-4o-mini",
        api_key=OPENAI_API_KEY,
    )

    with open("./prompts/generate_summary.md") as file:
        original_prompt = file.read()

    summaries: list[MarkdownSummary] = []

    for result in markdown_results:
        prompt = original_prompt.replace("{markdown_content}", result.content)
        response = model.invoke(prompt)
        logger.info(f"Summarized {result.link}")
        summaries.append(
            MarkdownSummary(summary=cast(str, response.content), link=result.link)
        )

    return summaries


def generate_report(markdown_summaries: list[MarkdownSummary]) -> str:
    """Generate report."""
    model = init_chat_model(
        "gpt-4o-mini",
        api_key=OPENAI_API_KEY,
    )

    with open("./prompts/generate_report.md") as file:
        prompt = file.read()

    pretty = json.dumps(
        [item.model_dump() for item in markdown_summaries],
        indent=2,
        ensure_ascii=False,
    )

    prompt = prompt.replace("{summaries}", pretty)

    response = model.invoke(prompt)
    content = cast(str, response.content).strip()

    # The model sometimes wraps the HTML in a ```html ... ``` markdown fence.
    if content.startswith("```"):
        content = content.split("\n", 1)[-1]  # drop the opening ```html line
        content = content.rsplit("```", 1)[0]  # drop the closing ```

    return content.strip()


def send_email(to: str, subject: str, html_body: str) -> None:
    """Send an HTML email from a Gmail account over SMTP using an app password.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        html_body: HTML content of the email.
    """
    message = EmailMessage()
    message.set_content("This email requires an HTML-capable client to view.")
    message.add_alternative(html_body, subtype="html")
    message["To"] = to
    message["From"] = FROM_GMAIL_ADDRESS
    message["Subject"] = subject

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(FROM_GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.send_message(message)

    logger.info(f"Email sent to {to}")


search_terms = [
    "AI Agents",
    "AI Context management",
    "New AI Benchmarks",
    "Coding agents",
    "AI Token Cost Management",
]


RELEVANT_CRITERIA = f"""
- Developments in {", ".join(search_terms)} from large AI players such as Google, OpenAI, Anthropic, Mistal, Chinese models, Agentic Code Editors etc.
- How people are building AI tools in industries. Their experience shared via blog posts, linkedin/twitter posts etc. 
"""


IRRELEVANT_CRITERIA = """
- Posts from small startups since it will most likely be marketing related stuff. 
- Generic or Research articles which cannot be applied to a industry. 
- Generic Advice from people sharing how they use AI to do simple tasks.
"""


def main():
    logger.info(f"Fetching search results for {search_terms} ")
    search_results = get_search_results(search_terms)

    logger.info(f"Found {len(search_results)} results. Filtering for relevance")
    filtered_results = filter_results(
        search_results, RELEVANT_CRITERIA, IRRELEVANT_CRITERIA
    )

    logger.info(
        f"Filtered {len(filtered_results)} results. Fetching their markdown contents"
    )
    markdown_results = fetch_markdown_contents(filtered_results)

    # Trim markdown result to 2000 character max so we don't use too much tokens.
    for result in markdown_results:
        result.content = result.content[:2000]

    logger.info("Generating summaries")
    summaries = generate_summaries(markdown_results)

    logger.info("Generating report")
    report = generate_report(summaries)

    with open("./report.html", "w") as file:
        file.write(report)
    logger.info("Stored report at ./report.html")

    logger.info("Emailing report")
    send_email(
        to=TO_GMAIL_ADDRESS,
        subject=f"AI Research Report - {date.today():%B %d, %Y}",
        html_body=report,
    )


if __name__ == "__main__":
    main()
