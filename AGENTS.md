# AGENTS.md

This file provides guidance to AI coding agents when working with code in this repository.

## What this is

A standalone script that downloads the Miele Outlet UK pricelist PDF, parses it with
`pypdf`, and lets a user filter/query the results (by name, grade, max price) and
optionally check whether each product's page is still live. Output is a table
(`tabulate`) or JSON. There is no package/install step — it's meant to be run directly,
e.g. via `uv run miele_outlet_scrape.py` or `pipx run miele_outlet_scrape.py`, which
pick up the inline PEP 723 dependency block at the top of the file.

## Commands

```bash
# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

# Test
python3 -m pytest
python3 -m pytest tests/test_miele_outlet_scrape.py -v -k parse_pdf   # subset

# Lint
ruff check .
```

`pyproject.toml` sets `pythonpath = "."` for pytest, so `import miele_outlet_scrape`
works from `tests/` without installing the module.

## Structure

- `miele_outlet_scrape.py` — the entire tool: PDF download (`load_pdf`), regex-based
  parsing of the pricelist text (`parse_pdf`), filtering (`filter_products`), a
  per-product live-status check (`check_product_status`), and a CLI (`argparse`) under
  `if __name__ == "__main__":`.
- `tests/` — pytest suite. Network calls (`requests.get`) and PDF parsing
  (`PdfReader`/`load_pdf`) are mocked with stdlib `unittest.mock`; the `__main__` CLI
  block itself is not covered (it's argument wiring and table/locale formatting, not
  logic worth testing in isolation).

## Conventions

- No comments except where a genuine non-obvious constraint exists.
- There is no PyPI `requests` dependency in this project despite the `requests.get(...)`
  calls throughout the file — `import requests` is actually
  `from curl_cffi import requests`, a drop-in-compatible module that also supports
  `impersonate=`. Don't add the real `requests` package back as a dependency; if you
  need something it doesn't have, it's probably on `curl_cffi`'s version already.
- `load_pdf()`'s URL is a Miele365 SharePoint anonymous share link
  (`https://miele365.sharepoint.com/:b:/s/GBOutlet/...`) with `?download=1` appended —
  without that param the same link 302s to an HTML document-library view page instead
  of the raw PDF. A plain `requests.get(url)` (no `impersonate` needed) is enough
  (no manual `Session`/cookie jar needed): SharePoint's redirect chain sets a
  `FedAuth` cookie and requests follows redirects within a single call, carrying
  cookies along automatically. If this URL
  ever starts 401ing or timing out again, it's moved — ask for (or find) the current
  share link from Miele's outlet team/portal and re-append `?download=1` (or
  `&download=1` if it already has a query string); don't assume it's a network/sandbox
  block before checking that first, since a stale URL and a blocked host look identical
  from a timeout/error alone.
- The pricelist's "Product Sheet" column is a hyperlink caption that `extract_text()`
  inlines right before `Outlet <grade> Stock` on every row — `parse_pdf()` strips
  `\s*Product Sheet\s*$` off the raw description before the GB/EU1 split. If a future
  PDF layout change makes rows look wrong again, check the raw
  `page.extract_text()` output first (see the live-verification steps used while
  fixing this — reproduced via a quick `load_pdf()` + `extract_text()` call) before
  assuming the regex itself is broken.
- The GB/EU1 split (`re.split(r"(GB|EU1)\b", description)`) deliberately has no `\b`
  before the marker: some rows glue it straight onto a truncated word with no space
  (e.g. `"...stainless steGB Fully integrated..."`), and a leading boundary stops the
  split from firing at all on those rows. Don't add one without re-testing against
  that exact case.
- `check_product_status()` passes `impersonate="chrome"` because
  `www.miele.co.uk` runs Akamai bot detection (`Server: AkamaiGHost`) that returns a
  blanket `403` to a normal client regardless of whether the product is genuinely
  live. Confirmed it's TLS-fingerprint-based, not header-based: a browser-like
  `User-Agent` alone didn't help, and even `httpx` with `http2=True` (matching
  `curl`'s HTTP/2 negotiation) still got `403`. Only a client that replicates a real
  browser's TLS/HTTP2 fingerprint (`curl_cffi`, or the similar `tls-client`) gets
  through. `load_pdf()` doesn't pass `impersonate` — SharePoint isn't behind the
  same kind of bot detection, so a plain request is enough there.
- Keep the PEP 723 inline dependency block at the top of `miele_outlet_scrape.py` in
  sync with `requirements.txt` — the former is what makes the script runnable
  standalone via `uv run`/`pipx run`; the latter is what CI and `requirements-dev.txt`
  install from. `requirements-dev.txt` adds test tooling only, via `-r requirements.txt`.
- `locale.setlocale` is called only inside the `__main__` table-printing branch, not at
  import time — importing the module (e.g. in tests) must not depend on the
  `en_GB.UTF-8` locale being installed on the machine running it.
- After editing any `.md` file, run markdownlint before committing — rules live in
  `.markdownlint.jsonc`. If Node/`npx` is available, run it with the same globs the
  `Lint` workflow uses (`.github/workflows/lint.yml`'s `markdownlint` job). If Node
  isn't available locally, push and check the `markdownlint` job in CI instead.
- No release-please/versioning setup here — this is a script, not a published package,
  so there's no version number to bump.
