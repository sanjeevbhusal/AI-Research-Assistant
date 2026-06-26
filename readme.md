## Summary

Create a AI system that researchs about a certain topic using google search. User provides list of topics they are interested in, system does all the research and generates a report.
The system will search for articles/blogs/social media posts that ranked in google in last 24 hours.

1. for each topic, system will fetch top 10 resource from google.
2. for each resouce, system will decide if it is relevant enough. A resource is only relevant if it meets the criteria. Eg: Only use resources published by big tech labs such as Google, OpenAI, Anthropic, Mistral etc and ignore the ones published by startups or published for marketing purposes etc.
3. For each relevant resource, system will fetch the entire content.
4. It will then summarize the content since articles can be thousands of words.
5. Finally, system will generate a report using the summarized article

## Setup

1. Copy the example env file and fill in your credentials:

   ```sh
   cp .env.example .env
   ```

   Then open `.env` and set each value:
   - `OPENAI_API_KEY` — OpenAI API key.
   - `SERPER_API_KEY` — Serper (Google search) API key.
   - `BROWSERLESS_API_KEY` — Browserless scraping API token.
   - `GMAIL_APP_PASSWORD` — 16-character Gmail app password from https://myaccount.google.com/apppasswords (requires 2-Step Verification).
   - `FROM_GMAIL_ADDRESS` — Gmail account that sends the report.
   - `TO_GMAIL_ADDRESS` — recipient of the report.

   `.env` is gitignored, so your credentials stay out of version control.

2. Run the script:

   ```sh
   uv run main.py
   ```

## Detailed Technical Plan

1. Ask user about 5 topics that they are interested in. Eg: [AI Agents, AI Context management, New AI Benchmarks, Coding agents, AI Token Cost Management ]

2. Use serper to fetch the google results for each of these topics.

   ```py
   topic = "AI Context Management"
   results = fetch_google_results(topic)

   def fetch_google_results(topic):
    # make api call to serper to fetch top 10 results.
   ```

3. Decide if the fetched results are worthy exploring further. Google returns headlines for each article. Ask a LLM if the headline is relevant for us. Humans navigate google search in similar way.

   ```py
   results = fetch_google_results(topic)
   filtered_results = filter_relevance_results(results)

   def filter_relevance_results(results):
      # craft a prompt that tells llm who the user is, what their purpose is,
      # how it should decide if a result is relevant.
   ```

4. Fetch the page content from the filtered results by scraping the link

   ```py
   page_contents = scrape_results(filtered_results)

   def scrape_results(results):
      # make a api call to browserless service to fetch the page content

   ```

5. Page results can contain thousands of words. Use LLM to summarize each of them before the final report

   ```py
   summarized_page_contents = summarize_page_contents(page_contents)

   def summarize_page_contents(page_contents):
     # craft a prompt that tells llm how to summarize the page contents.

   ```

6. Generate a report from all the summarized page contents.

   ```py
   report = generate_report(summarized_page_contents)
   send_email(report, user_email@gmail.com)


   def generate_report(summarized_page_contents):
      # craft a prompt that tells llm how to structure the report.
   ```

> Note:
> There are other approaches to building a AI Research Assitant. Eg: You can paste all the page contents into LLM in one go and ask it to generate report. I choose this approach to ensure less halucination and to preserve tokens wherever possible.

## Output generated

When the script is run, output for each step is logged to terminal. It looks something like:

```sh
uv run main.py

2026-06-25 23:59:54,489 INFO [__main__] Fetching search results for ['AI Agents', 'AI Context management', 'New AI Benchmarks', 'Coding agents', 'AI Token Cost Management']
2026-06-26 00:00:04,696 INFO [__main__] Found 29 results. Filtering for relevance
2026-06-26 00:00:09,729 INFO [httpx] HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2026-06-26 00:00:09,746 INFO [__main__] Filtered 15 results. Fetching their markdown contents
2026-06-26 00:00:18,976 INFO [__main__] Fetched markdown content for https://news.mit.edu/2026/improving-ai-agent-speed-and-energy-efficiency-0625
2026-06-26 00:01:43,870 INFO [__main__] Fetched markdown content for https://openai.com/index/how-agents-are-transforming-work/
2026-06-26 00:01:49,740 INFO [__main__] Fetched markdown content for https://www.reddit.com/r/AI_Agents/comments/1uenk8t/building_a_feedback_memory_layer_for_ai_agents/
2026-06-26 00:02:02,192 INFO [__main__] Fetched markdown content for https://www.oneadvanced.com/resources/ai-agents-examples/
2026-06-26 00:02:09,770 INFO [__main__] Fetched markdown content for https://krazimo.com/ai-agents-for-business/
2026-06-26 00:02:21,240 INFO [__main__] Fetched markdown content for https://github.com/volcengine/OpenViking
2026-06-26 00:02:25,102 INFO [__main__] Fetched markdown content for https://tana.inc/blog/what-is-context-engineering-for-ai-agents
2026-06-26 00:02:30,937 INFO [__main__] Fetched markdown content for https://www.ovaledge.com/blog/agentic-context-engineering
2026-06-26 00:02:42,492 INFO [__main__] Fetched markdown content for https://www.oreilly.com/radar/so-long-and-thanks-for-all-the-context/
2026-06-26 00:02:48,640 INFO [__main__] Fetched markdown content for https://www.ibm.com/think/topics/ai-agent-deployment
2026-06-26 00:03:09,827 INFO [__main__] Fetched markdown content for https://sedai.io/blog/ai-failed-human-benchmark
2026-06-26 00:03:17,894 INFO [__main__] Fetched markdown content for https://tech.einnews.com/pr_news/921958846/pearl-education-launches-grade-an-open-benchmark-for-evaluating-ai-on-education-program-data
2026-06-26 00:03:25,299 INFO [__main__] Fetched markdown content for https://www.linkedin.com/posts/parikshitpruthi_palantir-just-broke-your-ai-benchmark-obsession-activity-7475778576059932673-zWEp
2026-06-26 00:03:31,430 INFO [__main__] Fetched markdown content for https://www.rand.org/pubs/research_reports/RRA3892-2.html
2026-06-26 00:03:49,279 INFO [__main__] Fetched markdown content for https://www.getaleph.com/answers/cac-payback-period-saas-2026
2026-06-26 00:03:49,280 INFO [__main__] Generating summaries
2026-06-26 00:03:55,219 INFO [httpx] HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2026-06-26 00:03:55,220 INFO [__main__] Summarized https://news.mit.edu/2026/improving-ai-agent-speed-and-energy-efficiency-0625
2026-06-26 00:04:01,884 INFO [httpx] HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2026-06-26 00:04:01,886 INFO [__main__] Summarized https://openai.com/index/how-agents-are-transforming-work/
2026-06-26 00:04:04,782 INFO [httpx] HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2026-06-26 00:04:04,788 INFO [__main__] Summarized https://www.reddit.com/r/AI_Agents/comments/1uenk8t/building_a_feedback_memory_layer_for_ai_agents/
2026-06-26 00:04:11,080 INFO [httpx] HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2026-06-26 00:04:11,083 INFO [__main__] Summarized https://www.oneadvanced.com/resources/ai-agents-examples/
2026-06-26 00:04:21,708 INFO [httpx] HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2026-06-26 00:04:21,736 INFO [__main__] Summarized https://krazimo.com/ai-agents-for-business/
2026-06-26 00:04:25,425 INFO [httpx] HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2026-06-26 00:04:25,435 INFO [__main__] Summarized https://github.com/volcengine/OpenViking
2026-06-26 00:04:30,352 INFO [httpx] HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2026-06-26 00:04:30,356 INFO [__main__] Summarized https://tana.inc/blog/what-is-context-engineering-for-ai-agents
2026-06-26 00:04:35,034 INFO [httpx] HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2026-06-26 00:04:35,043 INFO [__main__] Summarized https://www.ovaledge.com/blog/agentic-context-engineering
2026-06-26 00:04:41,474 INFO [httpx] HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2026-06-26 00:04:41,477 INFO [__main__] Summarized https://www.oreilly.com/radar/so-long-and-thanks-for-all-the-context/
2026-06-26 00:04:46,348 INFO [httpx] HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2026-06-26 00:04:46,359 INFO [__main__] Summarized https://www.ibm.com/think/topics/ai-agent-deployment
2026-06-26 00:04:50,821 INFO [httpx] HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2026-06-26 00:04:50,824 INFO [__main__] Summarized https://sedai.io/blog/ai-failed-human-benchmark
2026-06-26 00:05:01,890 INFO [httpx] HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2026-06-26 00:05:01,892 INFO [__main__] Summarized https://tech.einnews.com/pr_news/921958846/pearl-education-launches-grade-an-open-benchmark-for-evaluating-ai-on-education-program-data
2026-06-26 00:05:06,070 INFO [httpx] HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2026-06-26 00:05:06,080 INFO [__main__] Summarized https://www.linkedin.com/posts/parikshitpruthi_palantir-just-broke-your-ai-benchmark-obsession-activity-7475778576059932673-zWEp
2026-06-26 00:05:11,737 INFO [httpx] HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2026-06-26 00:05:11,740 INFO [__main__] Summarized https://www.rand.org/pubs/research_reports/RRA3892-2.html
2026-06-26 00:05:17,003 INFO [httpx] HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2026-06-26 00:05:17,011 INFO [__main__] Summarized https://www.getaleph.com/answers/cac-payback-period-saas-2026
2026-06-26 00:05:17,011 INFO [__main__] Generating report
2026-06-26 00:05:42,543 INFO [httpx] HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2026-06-26 00:05:42,549 INFO [__main__] Stored report at ./report.html
2026-06-26 00:05:42,549 INFO [__main__] Emailing report
2026-06-26 00:05:46,441 INFO [__main__] Email sent to bhusalsanjeev23@gmail.com

```

## Tools/Technology Used

1. Serper: SAAS service that returns google results for a search.
2. OpenAI: LLM service for filtering relevancy and generating summaries.
3. Browserless: SAAS service that scraps a web page and returns it in markdown format.
4. SMTP service: to send email.
5. Lanngchain: for api calls to LLM
