# Sectors API: Indonesia (IDX), Singapore (SGX) and Malaysia (KLSE) Stock Market Data

[Sectors Financial API](https://sectors.app/api) is a REST API for Southeast Asian stock market data. It covers stocks on the Indonesia Stock Exchange (IDX / BEI), Singapore Exchange (SGX), including S-REITs, and Bursa Malaysia (KLSE). It also has Indonesian mining and commodity data. All responses are JSON.

**Documentation:** [docs.sectors.app](https://docs.sectors.app) · **Get an API key:** [sectors.app/api](https://sectors.app/api) · **For AI agents:** [llms.txt](https://docs.sectors.app/llms.txt)

## What you can get

- **IDX stock data:**
  - historical stock prices, closing prices and IHSG/LQ45 index data
  - quarterly financial statements and company reports
  - a stock screener
  - dividends, corporate actions and shareholder composition
  - free float, insider trading filings, IPO performance and stock news
- **IDX broker and flow data:**
  - broker summary per stock, top buyers and sellers
  - broker activity by broker code (kode broker)
  - accumulation and distribution
  - daily foreign flow (net buy/sell asing)
- **SGX data:**
  - historical prices and a stock screener
  - company reports, dividends and corporate actions
  - insider filings, share buybacks, the short sell report and news
- **Singapore REITs (S-REITs):** a REIT screener, plus DPU and gearing, property portfolios, top tenants and property transactions.
- **KLSE / Bursa Malaysia:** company reports, listed companies by sector, and top stocks.
- **Indonesia mining:**
  - coal and nickel production
  - mining companies, sites and licenses (IUP/IUPK, WIUP auctions)
  - resources and reserves, and commodity prices and exports

## Quickstart

1. Get an API key from the [Sectors API page](https://sectors.app/api). The API requires a Sectors Insider plan.
2. Send the key in the `Authorization` header:

```bash
curl "https://api.sectors.app/v2/daily/BBCA/?start=2025-05-02&end=2025-05-02" \
  -H "Authorization: YOUR_API_KEY"
```

```python
import requests

response = requests.get(
    "https://api.sectors.app/v2/daily/BBCA/",
    params={"start": "2025-05-02", "end": "2025-05-02"},
    headers={"Authorization": "YOUR_API_KEY"},
)
print(response.json())
```

The [Get Started guide](https://docs.sectors.app/get-started/v2/overview) covers authentication, credits and every endpoint.

## Popular endpoints

### Indonesia (IDX)

| Use case | Docs |
|---|---|
| IDX stock screener | [Companies screener](https://docs.sectors.app/api-references/v2/indonesia/screener/companies) |
| Historical stock prices | [Daily transaction data](https://docs.sectors.app/api-references/v2/indonesia/transaction/daily) |
| IHSG and IDX index historical data | [Index daily](https://docs.sectors.app/api-references/v2/indonesia/transaction/index-daily) |
| Quarterly financial statements | [Quarterly financials](https://docs.sectors.app/api-references/v2/indonesia/report/quarterly-financials) |
| Company report: financials and valuation | [Company report](https://docs.sectors.app/api-references/v2/indonesia/report/company-report) |
| Broker summary: top buyers and sellers | [Broker summary top](https://docs.sectors.app/api-references/v2/indonesia/brokers/broker-summary-top) |
| Broker codes list (kode broker) | [Broker registry](https://docs.sectors.app/api-references/v2/indonesia/brokers/broker-registry) |
| Foreign flow (net buy asing) | [Foreign flow](https://docs.sectors.app/api-references/v2/indonesia/brokers/foreign-flow) |
| Dividend and corporate actions calendar | [Corporate actions](https://docs.sectors.app/api-references/v2/indonesia/news/corporate-actions) |
| Insider trading filings | [Filings](https://docs.sectors.app/api-references/v2/indonesia/news/filings) |
| Top gainers and losers | [Top changes](https://docs.sectors.app/api-references/v2/indonesia/ranking/top-changes) |
| Free float (free float saham) | [Free float](https://docs.sectors.app/api-references/v2/indonesia/screener/free-float) |

### Singapore (SGX) and S-REITs

| Use case | Docs |
|---|---|
| SGX stock screener | [SGX companies screener](https://docs.sectors.app/api-references/v2/singapore/screener/sgx-companies) |
| SGX historical stock prices | [SGX daily prices](https://docs.sectors.app/api-references/v2/singapore/transaction/daily) |
| Singapore REIT screener | [SGX REITs](https://docs.sectors.app/api-references/v2/singapore/reits/reits) |
| SGX dividends and corporate actions | [SGX corporate actions](https://docs.sectors.app/api-references/v2/singapore/report/corporate-actions) |
| SGX short sell report | [SGX short sell](https://docs.sectors.app/api-references/v2/singapore/transaction/short-sell) |
| SGX insider trading filings | [SGX filings](https://docs.sectors.app/api-references/v2/singapore/news/sgx-filings) |

### Malaysia (KLSE) and Indonesia mining

| Use case | Docs |
|---|---|
| Bursa Malaysia company report | [KLSE company report](https://docs.sectors.app/api-references/v2/malaysia/klse-report) |
| Indonesia coal and nickel production | [Commodity production](https://docs.sectors.app/api-references/v2/mining/sites-production/commodity-production) |
| Coal and nickel price history | [Commodity price](https://docs.sectors.app/api-references/v2/mining/commodities-trade/commodity-price) |
| Indonesia mining companies | [Mining companies](https://docs.sectors.app/api-references/v2/mining/companies/mining-companies) |

## Use with AI agents (MCP)

Connect Claude, ChatGPT, Cursor or any MCP client to Sectors data with the [Sectors MCP server](https://docs.sectors.app/recipes/sectors-for-ai-agents/00-sectors-mcp-guide). The full documentation is also available as [llms.txt](https://docs.sectors.app/llms.txt) for LLMs and coding agents.

## Contributing to these docs

This repository holds the source for [docs.sectors.app](https://docs.sectors.app), built with [Mintlify](https://mintlify.com). Endpoint pages under `api-references/` are generated from the backend OpenAPI schema by `scripts/generate_mdx_stubs.py`, so don't edit them by hand.

Preview locally:

```bash
npm i -g mintlify
mintlify dev   # run from the folder that contains docs.json
```

Changes deploy to production automatically when they are merged into `main`.

**Troubleshooting**
- If `mintlify dev` doesn't start, run `mintlify install` to reinstall dependencies.
- If a page loads as a 404, make sure you're running the command in the folder that contains `docs.json`.
