---
title: "Building Multi-Agent Workflows"
description: "Learn how to orchestrate multiple AI agents using the OpenAI Agents SDK and Sectors API to perform complex financial research."
---

# Building Multi-Agent Workflows for Financial Research

## Overview

In our previous [Agent Skills Guide](https://docs.sectors.app/recipes/sectors-for-ai-agents/01-agent-skills-guide), we explored how to give a single AI agent access to Sectors Financial API tools. But what happens when a task is too complex for a single agent to handle reliably? 

In this recipe, we will build a **Multi-Agent Workflow** using the [OpenAI Agents SDK](https://pypi.org/project/openai-agents/) and the Sectors API. We'll design a robust IDX research assistant using two powerful agentic patterns:
1. **Sequential Chain:** Passing the output of one specialized agent (a screener) to another (a researcher).
2. **Judge and Critic:** Using a third agent (an evaluator) to rigorously grade the output and demand revisions if it falls short.

## Prerequisites

This recipe assumes you are familiar with generating an API key and completing a basic request. If you haven't already, review:
* [Your First Request!](https://docs.sectors.app/recipes/quick-start-in-python/00-your-first-request)
* [Agent Skills Guide](https://docs.sectors.app/recipes/sectors-for-ai-agents/01-agent-skills-guide)

You will need the `openai-agents` package for this recipe:

```bash
pip install openai-agents 
```

## Step 1: Define the Tools

First, we will wrap two Sectors API endpoints into Python tools: a flexible stock screener and a company overview retrieval tool.

```python
import os
import json
import requests
import asyncio
from typing import Literal
from dataclasses import dataclass
from agents import Agent, Runner, function_tool

API_KEYS = os.getenv("SECTORS_API_KEY")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

HEADERS = {"Authorization": API_KEYS}

@function_tool
def find_companies_screener(order_by: str, limit: int, where: str = "") -> str:
    """Screen and rank IDX companies via Sectors v2 API"""
    # URL-encode to handle special chars in filter expressions like >, <, etc
    params = [f"order_by={requests.utils.quote(order_by)}", f"limit={limit}"]
    if where:
        params.insert(0, f"where={requests.utils.quote(where.strip())}")
    
    url = f"https://api.sectors.app/v2/companies/?" + "&".join(params) 
    response = requests.get(url, headers=HEADERS)
    return json.dumps(response.json())

@function_tool
def get_company_overview(ticker: str) -> str:
    """Get company overview and financials for an IDX ticker"""
    url = f"https://api.sectors.app/v1/company/report/{ticker}/?sections=overview,financials"
    response = requests.get(url, headers=HEADERS)
    return json.dumps(response.json())
```

## Step 2: Create the Agents

Instead of using one massive prompt, we create three distinct agents with narrow, specialized responsibilities. This vastly reduces hallucinations and improves accuracy.

```python
screener_agent = Agent(
    name="IDX Screener",
    instructions=(
        "You screen the Indonesia Stock Exchange (IDX) by calling the appropriate tool. "
        "Return ONLY a Python list of clean ticker symbols without the .JK suffix. "
        "Example: ['BBCA', 'BBRI', 'TLKM']"
    ),
    tools=[find_companies_screener],
    model="gpt-4o-mini"
)

researcher_agent = Agent(
    name="IDX Researcher",
    instructions=(
        "You are a financial researcher. You receive a user query and a list of IDX tickers. "
        "Call get_company_overview for every ticker to gather data. "
        "Return ONLY a raw JSON object containing 'metric_fields' and a 'results' array. "
        "Do not use markdown fences."
    ),
    tools=[get_company_overview],
    model="gpt-4o"
)

@dataclass
class EvaluationFeedback:
    feedback: str
    score: Literal["pass", "expect_improvement", "fail"]

evaluator_agent = Agent(
    name="Evaluator",
    instructions=(
        "Grade the provided JSON object. Check that: "
        "1. Every result has a 'ticker' and 'company_name'. "
        "2. The metric fields contain non-null numeric values. "
        "Score 'pass' if all checks pass, otherwise 'expect_improvement' or 'fail'."
    ),
    model="gpt-4o-mini",
    output_type=EvaluationFeedback
)
```

## Step 3: Orchestrate the Workflow

Now we bring it all together. We run the Screener to get tickers and pass those to the Researcher. 
To ensure quality, we use a `for` loop to let the Evaluator critique the Researcher's output. If the output fails, the Researcher is prompted to fix it dynamically.

```python
async def main():
    query = "Top 5 IDX banks by market cap"
    
    # Run the screener
    screener_resp = await Runner.run(screener_agent, query)
    tickers = screener_resp.final_output
    print(f"Tickers found: {tickers}")

    # Initial data gathering
    research_input = f"User query: '{query}'\nTickers: {tickers}"
    research_resp = await Runner.run(researcher_agent, research_input)
    current_draft = research_resp.final_output

    # Evaluate and iterate
    final_output = None
    max_attempts = 3

    for attempt in range(1, max_attempts + 1):
        print(f"Evaluating draft (Attempt {attempt}/{max_attempts})...")
        eval_resp = await Runner.run(evaluator_agent, current_draft)
        
        # Cast the raw output into our structured EvaluationFeedback dataclass
        feedback_obj = eval_resp.final_output_as(EvaluationFeedback)
        
        if feedback_obj.score == "pass":
            final_output = current_draft
            break
        
        print(f"Revision needed. Feedback: {feedback_obj.feedback}")
        revision_input = (
            f"User query: '{query}'\nTickers: {tickers}\n"
            f"Previous output graded '{feedback_obj.score}'.\n"
            f"Feedback: {feedback_obj.feedback}\n"
            "Fix the issues and return the corrected JSON object."
        )
        research_resp = await Runner.run(researcher_agent, revision_input)
        current_draft = research_resp.final_output

    # Use the last draft even if it never passed evaluation
    if not final_output:
        final_output = current_draft

    print("Final Output:")
    print(final_output)

if __name__ == "__main__":
    asyncio.run(main())
```

## Summary
By separating concerns into highly specialized agents, we built an AI workflow infinitely more reliable than a single generic prompt. The **Screener** acts as a targeted retrieval mechanism, the **Researcher** executes complex data fetching against our financial API, and the **Evaluator** ensures the final JSON structure matches strict application requirements. 

You can now reliably pipe this JSON output into a data analysis tool like `pandas` or build an interactive dashboard!