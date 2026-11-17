# Searchplex 1.2.0 — Perplexity-style web research for OpenCode (MCP)

Searchplex connects a model in [OpenCode](https://opencode.ai) (or any other MCP client with the stdio
transport) to the internet. The model decides when to search, Searchplex finds and reads the pages, and the
model answers with numbered sources, as in Perplexity. It works with a local model (LM Studio, Ollama,
llama.cpp, vLLM) or a cloud OpenAI-compatible API, and needs no subscriptions or API keys.

- One file, `srchplex.py`, Python 3.9+ standard library only.
- Search engines: your own [SearXNG](https://github.com/searxng/searxng) (installed with one command), then
  DuckDuckGo, Yandex and Bing; Bing News, arXiv and OpenAlex; Stack Overflow, GitHub and Hacker News APIs for
  code and discussions; optionally the [Tavily](https://tavily.com) and
  [Brave Search](https://brave.com/search/api/) APIs. The order of the engines is yours to choose (see
  [Search priority](#search-priority-tavily-and-brave)).
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

Get the project first: `git clone <repository URL> ~/searchplex`, or download the release archive. Run the
commands below from that folder.

### Quick install

```bash
python3 install.py
```

The installer asks a few questions and does the rest:

- adds the `srchplex` server to `~/.config/opencode/opencode.json` (or updates it), keeping a backup of the old
  file next to it (`opencode.json.bak-<date>`); OpenCode 1.x and 2.x config layouts are both handled;
- asks for the model API address (`LLM_BASE_URL`) and the optional Tavily and Brave keys; a key is saved to
  `~/.config/opencode/.tavily_key` / `.brave_key`, readable only by you, and the config refers to it as
  `{file:...}`;
- asks for the [order of the search engines](#search-priority-tavily-and-brave) on this machine; Enter keeps
  the default;
- offers to install SearXNG, to copy the rules for the model (`AGENTS.md`) and to run `--doctor`.

Run it again at any time to change the keys or the order. `python3 install.py --dry-run` shows the result
without writing anything; `--yes` asks nothing; `--engines "searxng,brave,tavily,duckduckgo,yandex,bing"` sets
the order from the command line. Restart OpenCode afterwards.

### Manual install

The same steps by hand, if you prefer to edit the config yourself or the installer cannot read it.

1. Optional, recommended: install SearXNG. The script downloads it, enables autostart and automatic updates,
   and runs a test search:

   ```bash
   python3 searxng_setup.py
   ```

2. Register the server in `~/.config/opencode/opencode.json` (`%USERPROFILE%\.config\opencode\opencode.json`
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
             "TAVILY_API_KEY": "{file:~/.config/opencode/.tavily_key}",
             "BRAVE_API_KEY": "{file:~/.config/opencode/.brave_key}",
             "SRCHPLEX_ENGINES": "searxng,tavily,brave,duckduckgo,yandex,bing"
           }
         }
       }
     }
   }
   ```

   OpenCode 1.x puts the servers directly under `"mcp"`, without `"servers"`. `LLM_BASE_URL` is LM Studio
   (`http://localhost:1234/v1`), Ollama (`http://localhost:11434/v1`) or any OpenAI-compatible server. Drop the
   `TAVILY_API_KEY` and `BRAVE_API_KEY` lines if you do not use those APIs, and `SRCHPLEX_ENGINES` to keep the
   default order. A key file holds only the key: `echo "<key>" > ~/.config/opencode/.brave_key && chmod 600
   ~/.config/opencode/.brave_key`. Keep the `srchplex` name: `AGENTS.md` refers to the tools by it.
3. Copy the rules for the model, or append them to your own `AGENTS.md`:

   ```bash
   mkdir -p ~/.config/opencode && cp AGENTS.md ~/.config/opencode/AGENTS.md
   ```

4. Restart OpenCode and check everything:

   ```bash
   python3 srchplex.py --doctor
   ```

## SearXNG updates

SearXNG has no releases, only the master branch, which fixes engines broken by search sites every few days.
The installer keeps it current:

- A scheduled job checks every day at 12:00 and after login and updates at most once a week: a second
  LaunchAgent `org.searxng.srchplex.update` on macOS, the Task Scheduler task "SearXNG (srchplex) update" on
  Windows. On Linux the installer prints a `crontab` line instead.
- Nothing is downloaded unless GitHub has a newer commit than the installed one.
- The new version is downloaded while the old one keeps running; the old `src/` and `venv/` are kept aside
  until the new version has started and answered a test search (with results, if the old one found any).
  Otherwise the old version comes back and starts again.
- `python3 searxng_setup.py status` shows the last check and its result; the log is `update.log` in the
  SearXNG folder. `--no-autoupdate` at install turns the schedule off.

To update by hand right now, run the update script from the project folder:

```bash
python3 searxng_update.py            # update if there is a newer version
python3 searxng_update.py --check    # only say whether there is one
python3 searxng_update.py --force    # reinstall the latest version anyway
```

It is the same safe update with the rollback, without the once-a-week limit, and it also refreshes the copy of
`searxng_setup.py` the scheduled job runs, so fixes from a newer Searchplex reach the automatic updates too.
`--dir` points it to a SearXNG installed into another folder.

## Search priority, Tavily and Brave

Tavily (1000 free searches a month) and Brave Search (plans and free credit: see the
[Brave dashboard](https://api-dashboard.search.brave.com)) are optional cloud search APIs. Without a key an API
is never used. Engines are asked in turn; the next one only when the previous one fails or finds fewer than 3
results (then the results are merged).

The default order, unchanged from earlier versions when you add no Brave key:

| Keys | Web | News |
|---|---|---|
| none | SearXNG → DuckDuckGo → Yandex → Bing | SearXNG → Bing News |
| Tavily | SearXNG → **Tavily** → DuckDuckGo → Yandex → Bing | SearXNG → Bing News and **Tavily** together |
| Tavily and Brave | SearXNG → **Tavily** → **Brave** → DuckDuckGo → Yandex → Bing | SearXNG → Bing News, **Tavily**, **Brave** together |

**Your own order.** `SRCHPLEX_ENGINES` in the server's `environment` lists the web engines in the order to ask
them; `python3 install.py` writes it for you. Names: `searxng`, `tavily`, `brave`, `duckduckgo` (`ddg`),
`yandex`, `bing`. Engines left out are not used; an API without its key is skipped. For example:

| `SRCHPLEX_ENGINES` | Meaning |
|---|---|
| `brave,tavily,searxng,duckduckgo,yandex,bing` | APIs first: steadier results, every search spends credits |
| `searxng,duckduckgo,yandex,bing,brave,tavily` | APIs last: they step in only when everything free fails |
| `searxng,brave` | SearXNG and Brave only, no scraped engines |

News follow the same order: an API before `searxng` is asked before SearXNG news; one between SearXNG and the
built-in engines runs together with Bing News; one after the built-in engines is not used for news. Papers,
code and discussions never use the APIs: they have their own sources. Restart OpenCode after a change.

Instead of the whole order you can move just one API with `SRCHPLEX_TAVILY` or `SRCHPLEX_BRAVE`:
`fallback` (default, after SearXNG), `primary` (first, before SearXNG), `last` (after the built-in engines) or
`off`. `SRCHPLEX_ENGINES` wins over them.

A wrong key or used-up credits pause the API for an hour and the search goes on with the next engine. Brave
requests are spaced 1.1 s apart (the basic plan allows 1 request a second); with a higher limit lower
`BRAVE_MIN_INTERVAL_MS`.

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
| `SRCHPLEX_ENGINES` | — | Web search order, e.g. `searxng,brave,tavily,duckduckgo,yandex,bing`; see [Search priority](#search-priority-tavily-and-brave) |
| `TAVILY_API_KEY` | — | Tavily key; without it Tavily is not used |
| `SRCHPLEX_TAVILY` | `fallback` | Tavily's place: `fallback`, `primary` (first), `last`, `off` |
| `TAVILY_TIMEOUT_MS` | `10000` | Tavily request timeout |
| `BRAVE_API_KEY` (`BRAVE_SEARCH_API_KEY`) | — | Brave Search API key; without it Brave is not used |
| `SRCHPLEX_BRAVE` | `fallback` | Brave's place: `fallback` (after Tavily), `primary`, `last`, `off` |
| `BRAVE_TIMEOUT_MS` | `10000` | Brave request timeout |
| `BRAVE_MIN_INTERVAL_MS` | `1100` | Pause between Brave requests (plan's requests per second) |
| `SEARCH_PROVIDER` | — | Compatibility with configs of other search MCP servers: `ddg` = no APIs, `tavily` / `brave` = that API first; `SRCHPLEX_TAVILY` / `SRCHPLEX_BRAVE` win |
| `SRCHPLEX_BROWSER` | `auto` | `off`: do not render JavaScript pages with Playwright |
| `SRCHPLEX_REGION` | — | DuckDuckGo region (`kl`), e.g. `us-en` |
| `SRCHPLEX_CACHE_DIR` | `<tmp>/srchplex_cache` | Cache folder |
| `SRCHPLEX_BLOCK_PRIVATE` | — | `1`: `fetch` refuses localhost and LAN addresses |

## Diagnostics

```bash
python3 srchplex.py --doctor       # certificates, cache, search order, SearXNG, Tavily, Brave, every source, LLM, embeddings, PDF
python3 searxng_setup.py status    # SearXNG: installation, autostart, test search
```

Optional packages, picked up when installed into the Python that runs Searchplex: `pypdf` (PDF in
`local_search` and `fetch`), `playwright` with `playwright install chromium` (pages that are empty without
JavaScript), `certifi` (root certificates for python.org builds on macOS).

## Limitations

DuckDuckGo, Yandex, Bing and Bing News are read as ordinary web pages, without an official API: their pages
change, they rate-limit frequent queries and their terms may not allow automated access. For steady use install
SearXNG or add Tavily or Brave. Searchplex is meant for personal research, not bulk data collection.

Search improves facts, not reasoning: the model can still misread a source. Ask for the official docs when
details matter.

## License

[MIT](LICENSE). Includes the MIT notice of Vane (Perplexica).
