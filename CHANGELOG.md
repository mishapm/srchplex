# Changelog

## 1.1.0 — 2026-10-25

- Tavily as an optional search engine, used only with `TAVILY_API_KEY`; without the key the search order is
  unchanged. `SRCHPLEX_TAVILY` sets its place in the web search: `fallback` (default, after SearXNG and before
  DuckDuckGo, Yandex and Bing), `primary` (first, before SearXNG, in the web and in news), `last`, `off`.
  With `fallback` it also serves news together with Bing News.
  A wrong key or used-up credits pause it for an hour; `--doctor` shows the key masked, warns about obvious
  mistakes and prints Tavily's own error message.
- Compatibility with clients of other search MCP servers: `fetch` accepts `max_length` as a synonym of
  `max_chars`; `SEARCH_PROVIDER=ddg|tavily` and `TAVILY_TIMEOUT_MS` are read.
- Keys from the environment are read without a BOM and surrounding whitespace or quotes (a key file saved in
  Windows Notepad no longer breaks the authorization).
- README in English: OpenCode 2.x config format (`"mcp": {"servers": …}`), search priority, all settings,
  limitations of the built-in engines; MIT license.

## 1.0.3 — 2026-10-02

- Sites that refuse scripts: a Reddit thread is read from its RSS feed (with its rate limit respected), a page
  refused with 403/401/429/503 is looked up in the site's RSS feed, a Hacker News item without discussion is
  completed with the linked article; a site that refused without a feed is not picked for an hour.
- A research round that brings almost only already seen pages stops the research; a page with the same text
  as one already read is not read again; sources are ordered by relevance computed for all of them together.

## 1.0.2 — 2026-10-02

- SearXNG is the primary engine for the web, news and papers; the built-in sources (DuckDuckGo lite, Yandex,
  Bing; Bing News; arXiv, OpenAlex) only step in when it is down or finds too little. Code and discussions always
  use their own APIs.
- A query planner instead of the query translator; queries written by the agent are searched as written;
  searches in the topic's own language for word meanings, slang and local topics; any OpenAI-compatible model
  server.
- `local_search` reads documents only (PDF, DOCX, ODT, PPTX, EPUB); the `weather` and `quote` tools are removed.

## 1.0.1 — 2026-10

- Renamed to Searchplex: `srchplex.py`, `SRCHPLEX_*` variables, `srchplex_*` tools.
- Fixes for the 12 defects found by the QA cycle, each with a regression check.

## 1.0.0 — 2026-10

- First version (as Websearch MCP): web research tools over MCP, ported from the research pipeline of
  Vane (Perplexica).
