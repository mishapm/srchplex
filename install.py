#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Register Searchplex in OpenCode: one command, a few questions.

    python3 install.py                  interactive
    python3 install.py --yes            no questions: keep what is set, defaults for the rest
    python3 install.py --engines "searxng,brave,tavily,duckduckgo,yandex,bing" --yes
    python3 install.py --dry-run        show the resulting config, change nothing

What it does:
  1. adds (or updates) the "srchplex" server in ~/.config/opencode/opencode.json, with a backup of the old file;
  2. asks for the model API address and the optional Tavily and Brave keys (kept in files next to the config,
     readable only by you, and referenced as {file:...});
  3. asks for the order of the search engines on this machine (SRCHPLEX_ENGINES); Enter keeps the default;
  4. offers to install SearXNG (searxng_setup.py) and to copy the rules for the model (AGENTS.md).

Standard library only, Python 3.9+. Restart OpenCode afterwards.
"""
import argparse
import getpass
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.join(HERE, "srchplex.py")
SETUP = os.path.join(HERE, "searxng_setup.py")
RULES = os.path.join(HERE, "AGENTS.md")
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "opencode")
NAME = "srchplex"  # AGENTS.md refers to the tools as srchplex_*
SCHEMA = "https://opencode.ai/config.json"
DEFAULT_LLM = "http://localhost:1234/v1"
SCRAPED = ["duckduckgo", "yandex", "bing"]
ENGINES = ["searxng", "tavily", "brave"] + SCRAPED
ALIASES = {"ddg": "duckduckgo", "searx": "searxng"}
KEYS = {"tavily": ("TAVILY_API_KEY", ".tavily_key", "https://app.tavily.com (1000 free searches a month)"),
        "brave": ("BRAVE_API_KEY", ".brave_key", "https://api-dashboard.search.brave.com (Search plan)")}
ASSUME_YES = False


def say(text=""):
    print(text, flush=True)


def ask(question, default=""):
    if ASSUME_YES:
        return default
    try:
        answer = input("%s%s: " % (question, (" [%s]" % default) if default else "")).strip()
    except EOFError:
        answer = ""
    return answer or default


def yes(question, default=True):
    if ASSUME_YES:
        return default
    answer = ask(question + (" [Y/n]" if default else " [y/N]")).lower()
    return default if not answer else answer in ("y", "yes", "д", "да")


# --------------------------------------------------------------------------- #
# The OpenCode config (JSON with comments and trailing commas allowed)
# --------------------------------------------------------------------------- #

def strip_jsonc(text):
    """Remove // and /* */ comments outside strings, and trailing commas. Returns (json, had_comments)."""
    out, i, n, in_str, comments = [], 0, len(text), False, False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 1
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
            out.append(c)
        elif text.startswith("//", i):
            comments = True
            while i < n and text[i] not in "\r\n":
                i += 1
            continue
        elif text.startswith("/*", i):
            comments = True
            end = text.find("*/", i + 2)
            i = n if end < 0 else end + 2
            continue
        else:
            out.append(c)
        i += 1
    return re.sub(r",(\s*[}\]])", r"\1", "".join(out)), comments


def find_config(path):
    if path:
        return os.path.abspath(os.path.expanduser(path))
    for name in ("opencode.json", "opencode.jsonc"):
        candidate = os.path.join(CONFIG_DIR, name)
        if os.path.exists(candidate):
            return candidate
    return os.path.join(CONFIG_DIR, "opencode.json")


def load_config(path):
    if not os.path.exists(path):
        return {"$schema": SCHEMA}, False
    with open(path, encoding="utf-8-sig") as f:
        text, comments = strip_jsonc(f.read())
    try:
        data = json.loads(text) if text.strip() else {}
    except ValueError as e:
        sys.exit("ERROR: %s is not valid JSON (%s). Fix it or register the server by hand (README, Manual "
                 "install)." % (path, e))
    if not isinstance(data, dict):
        sys.exit("ERROR: %s does not hold a JSON object" % path)
    return data, comments


def opencode_major():
    exe = shutil.which("opencode")
    if not exe:
        return None
    try:
        out = subprocess.run([exe, "--version"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             encoding="utf-8", errors="replace", timeout=20).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    m = re.search(r"(\d+)\.\d+", out)
    return int(m.group(1)) if m else None


def servers_of(config):
    """The dict that holds the MCP servers: mcp.servers in OpenCode 2.x, mcp itself in 1.x."""
    mcp = config.setdefault("mcp", {})
    if "servers" in mcp:
        return mcp["servers"]
    others = [v for v in mcp.values() if isinstance(v, dict) and ("command" in v or "type" in v)]
    if others:
        return mcp  # 1.x: the servers sit right under "mcp"
    major = opencode_major()
    if major is None:
        major = 1 if ask("OpenCode version: 2 (mcp.servers) or 1 (servers right under mcp)?", "2") == "1" else 2
    if major >= 2:
        mcp["servers"] = {}
        return mcp["servers"]
    return mcp


# --------------------------------------------------------------------------- #
# Questions
# --------------------------------------------------------------------------- #

def key_file_ref(filename):
    return "{file:~/.config/opencode/%s}" % filename


def resolve(value):
    """The real value of an environment entry: {file:...} and {env:...} are read like OpenCode does."""
    m = re.fullmatch(r"\{file:(.+)\}", value or "")
    if m:
        try:
            with open(os.path.expanduser(m.group(1)), encoding="utf-8-sig") as f:
                return f.read().strip()
        except OSError:
            return ""
    m = re.fullmatch(r"\{env:(.+)\}", value or "")
    return os.environ.get(m.group(1), "") if m else (value or "")


def ask_key(env, engine, dry_run):
    var, filename, site = KEYS[engine]
    current = env.get(var, "")
    have = bool(resolve(current))
    say("\n%s API key, optional: %s" % (engine.capitalize(), site))
    if ASSUME_YES:
        return have
    prompt = ("  key is set; Enter keeps it, a new key replaces it, '-' removes it: " if have
              else "  paste the key, or Enter to skip: ")
    try:
        answer = getpass.getpass(prompt).strip().strip("\"'")
    except (EOFError, getpass.GetPassWarning):
        answer = ""
    if not answer:
        return have
    if answer == "-":
        env.pop(var, None)
        return False
    path = os.path.join(CONFIG_DIR, filename)
    if not dry_run:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(answer + "\n")
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    env[var] = key_file_ref(filename)
    say("  %s %s" % ("would be saved to" if dry_run else "saved to", path))
    return True


def parse_engines(text):
    order = []
    for part in re.split(r"[\s,;>]+", text.lower()):
        if part.isdigit() and 1 <= int(part) <= len(ENGINES):
            part = ENGINES[int(part) - 1]
        name = ALIASES.get(part, part)
        if name in ENGINES and name not in order:
            order.append(name)
        elif part:
            say("  unknown engine '%s' ignored" % part)
    return order


def default_order(keys):
    """Searchplex's own order when SRCHPLEX_ENGINES is not set (Tavily and Brave in the fallback place)."""
    return ["searxng"] + [e for e in ("tavily", "brave") if keys[e]] + SCRAPED


def ask_engines(env, keys, given):
    current = env.get("SRCHPLEX_ENGINES", "")
    if given is not None:
        order = parse_engines(given)
        return ",".join(order) if order and order != default_order(keys) else ""
    apis = [e for e in ("tavily", "brave") if keys[e]]
    presets = [("default: SearXNG first, the search APIs next, the free built-in engines last",
                default_order(keys))]
    if apis:
        presets.append(("search APIs first (more stable, spends their credits)", apis + ["searxng"] + SCRAPED))
        presets.append(("search APIs last (saves their credits)", ["searxng"] + SCRAPED + apis))
    presets.append(("without SearXNG (it is not installed here)", apis + SCRAPED))
    say("\nSearch engine order for the web search. Engines are asked in turn; the next one only when the "
        "previous one\nfails or finds fewer than 3 results. News follow it too; papers, code and "
        "discussions have their own sources.")
    if current:
        say("  now: %s (SRCHPLEX_ENGINES)" % " → ".join(parse_engines(current)))
    for i, (title, order) in enumerate(presets, 1):
        say("  %d) %s\n       %s" % (i, title, " → ".join(order)))
    say("  %d) your own order" % (len(presets) + 1))
    default = "keep" if current else "1"
    while True:
        answer = ask("Choose", default).lower()
        if answer == "keep":
            return current
        if answer.isdigit() and 1 <= int(answer) <= len(presets):
            order = presets[int(answer) - 1][1]
            break
        if answer.isdigit() and int(answer) == len(presets) + 1:
            say("  engines: " + ", ".join("%d=%s" % (i, e) for i, e in enumerate(ENGINES, 1)))
            say("  type names or numbers in order; engines you leave out are not used")
            order = parse_engines(ask("  order", "searxng brave tavily duckduckgo yandex bing"))
            if order:
                break
            continue
        say("  type a number from the list")
    for api in ("tavily", "brave"):
        if api in order and not keys[api]:
            say("  note: %s has no key, so it is skipped until you add one" % api)
    return "" if order == default_order(keys) else ",".join(order)


def searxng_running(url="http://127.0.0.1:8080"):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        return opener.open(url + "/healthz", timeout=3).status == 200
    except Exception:  # noqa: BLE001
        return False


def install_rules(dry_run):
    target = os.path.join(CONFIG_DIR, "AGENTS.md")
    with open(RULES, encoding="utf-8") as f:
        rules = f.read()
    if os.path.exists(target):
        with open(target, encoding="utf-8") as f:
            current = f.read()
        if current == rules:
            say("Rules for the model: %s is up to date" % target)
            return
        if "srchplex_" in current:
            if not yes("Replace %s with the current Searchplex rules (a backup is kept)?" % target):
                return
            new = rules
        else:
            if not yes("Append the Searchplex rules to your %s?" % target):
                return
            new = current.rstrip() + "\n\n" + rules.replace("# Global rules\n", "", 1).lstrip()
        if not dry_run:
            shutil.copyfile(target, "%s.bak-%s" % (target, time.strftime("%Y%m%d-%H%M%S")))
    else:
        if not yes("Copy the rules for the model to %s?" % target):
            return
        new = rules
    if not dry_run:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(new)
    say("Rules for the model: %s" % target)


# --------------------------------------------------------------------------- #

def main():
    global ASSUME_YES
    ap = argparse.ArgumentParser(prog="install.py", description="Register Searchplex in OpenCode.")
    ap.add_argument("--config", help="OpenCode config (default: ~/.config/opencode/opencode.json)")
    ap.add_argument("--engines", help="search order, e.g. searxng,brave,tavily,duckduckgo,yandex,bing; "
                                      "'default' for Searchplex's own order")
    ap.add_argument("--llm", help="model API address (LLM_BASE_URL), e.g. %s" % DEFAULT_LLM)
    ap.add_argument("--python", default=sys.executable, help="Python that runs Searchplex (default: this one)")
    ap.add_argument("-y", "--yes", action="store_true", help="no questions")
    ap.add_argument("--dry-run", action="store_true", help="print the server entry, change nothing")
    ap.add_argument("--no-searxng", action="store_true", help="do not offer to install SearXNG")
    ap.add_argument("--no-rules", action="store_true", help="do not offer to copy AGENTS.md")
    a = ap.parse_args()
    ASSUME_YES = a.yes
    if sys.version_info < (3, 9):
        sys.exit("ERROR: Searchplex needs Python 3.9+, this is %s" % sys.version.split()[0])

    path = find_config(a.config)
    say("Searchplex for OpenCode\n  config: %s%s" % (path, "" if os.path.exists(path) else " (new)"))
    config, comments = load_config(path)
    servers = servers_of(config)
    entry = servers.get(NAME) if isinstance(servers.get(NAME), dict) else {}
    say("  server \"%s\": %s" % (NAME, "update" if entry else "add"))
    env = dict(entry.get("environment") or {})

    llm = a.llm or ask("\nModel API (LM Studio %s, Ollama http://localhost:11434/v1, or a cloud "
                       "OpenAI-compatible URL)" % DEFAULT_LLM, env.get("LLM_BASE_URL") or DEFAULT_LLM)
    if not re.match(r"^https?://", llm):
        say("  '%s' is not an http(s) address; using %s" % (llm, env.get("LLM_BASE_URL") or DEFAULT_LLM))
        llm = env.get("LLM_BASE_URL") or DEFAULT_LLM
    env["LLM_BASE_URL"] = llm.rstrip("/")
    keys = {e: ask_key(env, e, a.dry_run) for e in ("tavily", "brave")}
    engines = ask_engines(env, keys, None if a.engines in (None, "") else
                          ("" if a.engines == "default" else a.engines))
    if engines:
        env["SRCHPLEX_ENGINES"] = engines
        for var in ("SRCHPLEX_TAVILY", "SRCHPLEX_BRAVE"):  # SRCHPLEX_ENGINES decides; these would only confuse
            env.pop(var, None)
    else:
        env.pop("SRCHPLEX_ENGINES", None)
    entry.update({"type": "local", "command": [a.python, SERVER], "environment": env})
    servers[NAME] = entry

    if a.dry_run:
        say("\nThe server entry (dry run, nothing written):")
        say(json.dumps({NAME: entry}, indent=2, ensure_ascii=False))
        return 0

    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        backup = "%s.bak-%s" % (path, time.strftime("%Y%m%d-%H%M%S"))
        shutil.copyfile(path, backup)
        say("\nBackup: %s" % backup)
        if comments:
            say("  note: the comments in the config are not kept; they stay in the backup")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)
    say("Saved: %s" % path)

    wants_searxng = not engines or "searxng" in engines.split(",")
    if not a.no_searxng and wants_searxng and not searxng_running():
        if yes("\nSearXNG does not answer at http://127.0.0.1:8080. Install it now (a few minutes)?"):
            subprocess.call([a.python, SETUP])
    if not a.no_rules:
        say("")
        install_rules(False)

    say("\nDone. Restart OpenCode.")
    if yes("Check the search engines and the model now (srchplex.py --doctor)?", default=not ASSUME_YES):
        run_env = dict(os.environ, **{k: resolve(v) for k, v in env.items()})
        subprocess.call([a.python, SERVER, "--doctor"], env=run_env)
    else:
        say("Check later: %s %s --doctor" % (os.path.basename(a.python), SERVER))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted, nothing more changed.")
        sys.exit(130)
