# Searchplex 1.1.0 — Perplexity-style web research for OpenCode (MCP)

Searchplex connects a model in [OpenCode](https://opencode.ai) (or any other MCP client with the stdio
transport) to the internet. The model decides when to search, Searchplex finds and reads the pages, and the
model answers with numbered sources, as in Perplexity. It works with a local model (LM Studio, Ollama,
llama.cpp, vLLM) or a cloud OpenAI-compatible API, and needs no subscriptions or API keys.

- One file, `srchplex.py`, Python 3.9+ standard library only.
- Search engines: your own [SearXNG](https://github.com/searxng/searxng) (installed with one command), then
  DuckDuckGo, Yandex and Bing; Bing News, arXiv and OpenAlex; Stack Overflow, GitHub and Hacker News APIs for
  code and discussions; optionally [Tavily](https://tavily.com), after SearXNG by default or first if you
  prefer (see [Search priority](#search-priority-and-tavily)).
- Pages are read as clean Markdown with code blocks and tables; PDF, GitHub, Stack Overflow, Hacker News and
  Reddit are read through their APIs or feeds.
- Ranking with BM25 or embeddings, deduplication, iterative research rounds with reflection.
- Search inside local PDF, DOCX, ODT, PPTX and EPUB files; an exact calculator.

Tested with the local models `qwen3.8-27b` and `qwen3.8-flash-next`.

The research pipeline is ported from [Vane (Perplexica)](https://github.com/ItzCrazyKns/Vane).

## Tools

In OpenCode the names get the server prefix: `srchplex_deep_search` and so on.

| Tool | What it does |
|---|---|
| `deep_search` | Research: evidence passages with numbered sources; `mode` = `speed`, `balanced` (default) or `quality` (also a cited report, 1–5 min) |
| `search` | Quick results without reading pages: title, URL, snippet |
| `fetch` | Up to 3 pages as Markdown; `query` keeps only the relevant parts, `start` continues reading, `extract` extracts facts with the LLM |
| `local_search` | Passages from PDF, DOCX, ODT, PPTX and EPUB files in `paths` |
| `calculate` | Exact calculator with variables and math functions |

`focus`: `web`, `news`, `academic`, `discussions`, `code`. `time_range`: `day`, `week`, `month`, `year`.
`domains`: only these sites, e.g. `["docs.python.org"]`.

## Install

You need OpenCode, Python 3.10+ (3.9+ for Searchplex itself; SearXNG needs 3.10) and a model in LM Studio,
Ollama or a cloud API. On Windows write `python` instead of `python3`.

1. Get the project: `git clone <repository URL> ~/searchplex`, or download the release archive. Run the
   commands below from that folder.
2. Optional, recommended: install SearXNG. The script downloads it, enables autostart and runs a test search:

   ```bash
   python3 searxng_setup.py
   ```

3. Register the server in `~/.config/opencode/opencode.json` (`%USERPROFILE%\.config\opencode\opencode.json`
   on Windows). OpenCode 2.x:

   ```jsonc
   {
     "mcp": {
       "servers": {
         "srchplex": {
           "type": "local",
           "command": ["<path to python>", "<project folder>/srchplex.py"],
           "environment": {
             "LLM_BASE_URL": "http://localhost:1234/v1",
             "TAVILY_API_KEY": "{file:~/.config/opencode/.tavily_key}"
           }
         }
       }
     }
   }
   ```

   OpenCode 1.x puts the servers directly under `"mcp"`, without `"servers"`. `LLM_BASE_URL` is LM Studio
   (`http://localhost:1234/v1`), Ollama (`http://localhost:11434/v1`) or any OpenAI-compatible server. Drop the
   `TAVILY_API_KEY` line if you do not use Tavily. Keep the `srchplex` name: `AGENTS.md` refers to the tools
   by it.
4. Copy the rules for the model, or append them to your own `AGENTS.md`:

   ```bash
   mkdir -p ~/.config/opencode && cp AGENTS.md ~/.config/opencode/AGENTS.md
   ```

5. Restart OpenCode and check everything:

   ```bash
   python3 srchplex.py --doctor
   ```

## Search priority and Tavily

Tavily is an optional cloud search API (1000 free searches a month). Without `TAVILY_API_KEY` it is never used.
With a key, `SRCHPLEX_TAVILY` in the server's `environment` sets its place in the order. Engines are asked in
turn; the next one only when the previous one fails or finds fewer than 3 results (then the results are merged).

| `SRCHPLEX_TAVILY` | Web | News |
|---|---|---|
| `fallback` (default) | SearXNG → **Tavily** → DuckDuckGo → Yandex → Bing | SearXNG → Bing News and **Tavily** together |
| `primary` (Tavily first) | **Tavily** → SearXNG → DuckDuckGo → Yandex → Bing | **Tavily** → SearXNG → Bing News |
| `last` (save credits) | SearXNG → DuckDuckGo → Yandex → Bing → **Tavily** | no Tavily |
| `off` | no Tavily, even with a key | no Tavily |

Papers, code and discussions never use Tavily: they have their own sources. Restart OpenCode after changing it.

A wrong key or used-up credits pause Tavily for an hour and the search goes on with the next engine.

## Settings

Set them in the `environment` of the server entry in the OpenCode config; for the CLI, in the terminal.

| Variable | Default | Purpose |
|---|---|---|
| `LLM_BASE_URL` | `http://localhost:1234/v1` | OpenAI-compatible model API: LM Studio, Ollama, llama.cpp, a cloud API |
| `LLM_API_KEY` | `lm-studio` | API key, if the server needs one (cloud) |
| `SRCHPLEX_LLM_MODEL` (`LMSTUDIO_MODEL`, `LLM_MODEL`) | the loaded model | The model to use; required for cloud APIs and servers with several models. LM Studio and Ollama load a model that is not loaded yet |
| `SRCHPLEX_LLM` | `auto` | `off`: no LLM at all |
| `SRCHPLEX_REASONING_EFFORT` | `none` | Sent as `reasoning_effort`; `off`: not sent |
| `SRCHPLEX_LLM_CONCURRENCY` | `2` | Parallel LLM requests |
| `EMBEDDING_MODEL` | the loaded embedding model | The embedding model; required for cloud APIs |
| `SRCHPLEX_EMBEDDINGS` | `auto` | `off`: BM25 only |
| `SEARXNG_URL` | `http://localhost:8080` | SearXNG address; `off`: do not use it |
| `GITHUB_TOKEN` | — | Higher GitHub API limits |
| `TAVILY_API_KEY` | — | Tavily key; without it Tavily is not used |
| `SRCHPLEX_TAVILY` | `fallback` | Tavily's place: `fallback`, `primary` (first), `last`, `off`; see [Search priority](#search-priority-and-tavily) |
| `TAVILY_TIMEOUT_MS` | `10000` | Tavily request timeout |
| `SEARCH_PROVIDER` | — | Compatibility with configs of other search MCP servers: `ddg` = no Tavily, `tavily` = Tavily first; `SRCHPLEX_TAVILY` wins |
| `SRCHPLEX_BROWSER` | `auto` | `off`: do not render JavaScript pages with Playwright |
| `SRCHPLEX_REGION` | — | DuckDuckGo region (`kl`), e.g. `us-en` |
| `SRCHPLEX_CACHE_DIR` | `<tmp>/srchplex_cache` | Cache folder |
| `SRCHPLEX_BLOCK_PRIVATE` | — | `1`: `fetch` refuses localhost and LAN addresses |

## Diagnostics

```bash
python3 srchplex.py --doctor       # certificates, cache, SearXNG, Tavily, every search source, LLM, embeddings, PDF
python3 searxng_setup.py status    # SearXNG: installation, autostart, test search
```

Optional packages, picked up when installed into the Python that runs Searchplex: `pypdf` (PDF in
`local_search` and `fetch`), `playwright` with `playwright install chromium` (pages that are empty without
JavaScript), `certifi` (root certificates for python.org builds on macOS).

## Limitations

DuckDuckGo, Yandex, Bing and Bing News are read as ordinary web pages, without an official API: their pages
change, they rate-limit frequent queries and their terms may not allow automated access. For steady use install
SearXNG or add Tavily. Searchplex is meant for personal research, not bulk data collection.

Search improves facts, not reasoning: the model can still misread a source. Ask for the official docs when
details matter.

## License

[MIT](LICENSE). Includes the MIT notice of Vane (Perplexica).
