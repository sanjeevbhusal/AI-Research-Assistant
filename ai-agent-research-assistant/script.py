import json
import logging
import operator
import os
import smtplib
import tempfile
from email.message import EmailMessage
from pathlib import Path
from typing import Annotated

import requests
from dotenv import load_dotenv

# Show the agent
from langchain.chat_models import init_chat_model
from langchain.messages import (
    AnyMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain.tools import tool
from typing_extensions import TypedDict

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

TEMP_FILES_DIR = Path(__file__).resolve().parent / "temporary-files"


class MessagesState(TypedDict):
    google_search_results: Annotated[list[dict], operator.add]
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int


@tool(description="Fetch top 10 google results for last 24 hours for a search query")
def search_google(search_query: str):
    """Fetch top 10 google results for last 24 hours for a search query"""
    logger.info(f"Searching google for {search_query}")
    url = "https://google.serper.dev/search"

    payload = json.dumps({"q": search_query, "gl": "gb", "num": 10, "tbs": "qdr:d"})

    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "CONTENT-TYPE": "application/json",
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    response.raise_for_status()
    results = json.loads(response.text)
    organic_results = results["organic"]
    return organic_results


@tool(description="Send email to a user")
def send_email(email: str, subject: str, body: str):
    """Send email to a user"""

    message = EmailMessage()
    message.set_content("This email requires an HTML-capable client to view.")
    message.add_alternative(body, subtype="html")
    message["To"] = email
    message["From"] = FROM_GMAIL_ADDRESS
    message["Subject"] = subject

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(FROM_GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.send_message(message)

    logger.info(f"Email sent to {email}")

    return {"success": True}


@tool(description="Save data to a temporary file.")
def save_temp_file(data: str) -> str:
    """Saves data to a temporary file."""
    TEMP_FILES_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        delete=False,
        dir=TEMP_FILES_DIR,
    ) as f:
        f.write(data)
        return f.name


@tool
def scrape_url(url: str):
    """Scrape a url and return its page contents as markdown. This tool only returns upto 2000 characters"""
    logger.info(f"Scraping page for {url}")

    endpoint = f"https://production-sfo.browserless.io/smart-scrape?token={BROWSERLESS_API_KEY}"

    response = requests.post(
        endpoint,
        headers={"Content-Type": "application/json"},
        json={"url": url, "formats": ["markdown"]},
        timeout=120,
    )

    response.raise_for_status()
    data = response.json()

    markdown = data.get("markdown")
    return markdown[:2000]


tools = [search_google, scrape_url, send_email, save_temp_file]
tools_by_name = {tool.name: tool for tool in tools}

model = init_chat_model("gpt-4o-mini", temperature=0)
# Augment the LLM with tools
model_with_tools = model.bind_tools(tools)


def normal_loop_implementation():
    """Normal Loop implementation."""
    system_message = SystemMessage(
        content=f"""
You are an expert research assistant.

Your job is to conduct thorough research on user-provided topics, synthesize information from reliable sources, produce a concise, 
well-structured html report, save it as a html file in filesystem and email it to {TO_GMAIL_ADDRESS}.

Your responsibilities:
- Understand the user's research request and identify the key questions to answer.
- Gather information from credible and up-to-date sources.
- Cross-reference important facts when possible and avoid presenting unsupported claims.
- Distinguish between facts, analysis, and opinions.
- Summarize information rather than copying it.
- Highlight the most important findings, trends, statistics, and takeaways.
- Mention uncertainties, conflicting viewpoints, or limitations when they exist.

The report should:
- Be visually clean and easy to scan.
- Use semantic HTML (headings, paragraphs, lists, tables where appropriate).
- Include a clear title.
- Include a short executive summary at the beginning.
- Organize content into logical sections with descriptive headings.
- Highlight key insights using callout boxes, bullet points, or emphasis.
- Include relevant statistics and important facts.
- Provide a brief conclusion with the main takeaways.
- Include a Link to view the full article next to each summary point

Writing style:
- Professional, objective, and concise.
- Prioritize clarity over length.
- Do not write like a long-form blog post.
- Avoid unnecessary filler or repetition.
- Assume the reader wants to understand the topic quickly.

To get the actual article contents, follow these steps:
- Search for articles published in last 24 hours using google.
- Check their title and summary to see which articles might be relevant.  
- Fetch the actual contents of relevant articles. 

The report should contain enough detail to be informative while remaining concise enough to be comfortably read in approximately 5–10 minutes.
"""
    )
    human_message = HumanMessage(
        content="Research about new things happening in AI space, particularly about AI agents, AI Context Management, AI Token Cost, etc."
    )
    messages = [system_message, human_message]

    system_message.pretty_print()
    human_message.pretty_print()

    end = False
    while not end:
        response = model_with_tools.invoke(messages)
        print(f"Agent Response: {response}")
        messages.append(response)

        if response.tool_calls:
            for tool_call in response.tool_calls:
                logger.info(f"Calling tool {tool_call['name']} ")
                tool = tools_by_name[tool_call["name"]]
                observation = tool.invoke(tool_call["args"])
                if not isinstance(observation, str):
                    observation = json.dumps(observation)
                tool_message = ToolMessage(
                    content=observation, tool_call_id=tool_call["id"]
                )
                messages.append(tool_message)
        else:
            end = True

    return messages


if __name__ == "__main__":
    normal_loop_implementation()
