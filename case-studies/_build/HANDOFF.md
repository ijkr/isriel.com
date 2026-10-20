# Case Studies — build pipeline handoff

Everything in this `_build/` directory is the publishing pipeline for
`www.isriel.com/case-studies/`. GitHub Pages runs Jekyll on this repo, so this
underscore-prefixed directory is **not served** on the web — it exists in the
repo purely so the pipeline travels with the code.

## What the served pages are

Each page under `case-studies/` is a **StatiCrypt encrypted shell**: the real
content is AES-256-encrypted inside the HTML and is decrypted client-side when
the visitor enters the password. There is no server-side anything — it's a
static file on GitHub Pages.

Consequences that matter when editing:

- The plaintext content must **never** be committed to this repo (it's public).
  That means `src/`, `content/`, and `.staticrypt-password` — all gitignored here.
- Crawlers and link-preview bots only ever see the shell, so `noindex` /
  `referrer` meta live in the shell (injected by `pre_publish.py`), not in the
  page content.
- Editing a case study means editing the **markdown source** or the
  **generator**, then rebuilding — never editing files under `case-studies/*.html`
  directly. Those are build artifacts.

## Layout

```
case-studies/
  *.html            ← build artifacts (encrypted shells). Committed. Never hand-edit.
  _build/
    build_site.py   ← markdown → styled HTML → StatiCrypt → hardened build/
    pre_publish.py  ← injects robots/referrer meta into encrypted shells (idempotent)
    content/        ← (gitignored) markdown sources, full statistical detail
    src/            ← (gitignored) generated PLAINTEXT html — never commit
    build/          ← (gitignored) generated encrypted html → copied to case-studies/
    .staticrypt-password  ← (gitignored) the password, or use env var
    HANDOFF.md      ← this file
```

## Setup (local, once)

Requires: Python 3.10+, Node.js (for `npx staticrypt`), `pip install markdown`.

```bash
cd case-studies/_build

# 1. content sources (NOT in the repo — ask Isriel; they live in his private
#    workspace). Expected layout:
#      content/step-one/PDP Redesign Programme - Step One Case Study.md
#      content/step-one/Landing Page CRO - Step One Case Study.md
#      content/step-one/Social Proof Messaging - Step One Case Study.md
#      content/step-one/Tiered Discounting and Pricing - Step One Case Study.md
#      src/nine-entertainment.md        ← this one lives in src/ by design
#    Or point elsewhere:  export CASES_DIR=/path/to/markdown

# 2. password — one of:
echo '<password>' > .staticrypt-password    # chmod 600
#    or:  export STATICRYPT_PASSWORD='<password>'
```

## Build & publish

```bash
python3 build_site.py        # md → src/*.html → build/*.html (encrypted, hardened)
cp build/*.html ../          # publish = copy into case-studies/
git add ../*.html && git commit -m "..." && git push
```

`build_site.py` fails safe: with no password it still builds `src/` but leaves
`build/` untouched and says so.

## Conventions the generator enforces (don't fight them)

- **Stats are written for non-technical readers.** Source markdown keeps full
  statistical notation (p-values, z, χ², SRM, α); `plain_stats()` rewrites it to
  confidence percentages and plain-language flags at build time. If the agent
  changes phrasing rules, change `plain_stats()`, not the markdown.
- **Headline figures are transcribed verbatim** from source documents. Never
  round, never invent. Every figure traces to a named experiment ID.
- Page furniture (hero, stat band, meta grid, contents nav) is data-driven from
  the `PAGES` / `INDEX_ROWS` dicts in `build_site.py` — edit those to change
  standfirsts, stat bands, or to add a new case study.
- Design system: Fraunces display / IBM Plex Sans body / IBM Plex Mono for
  numbers; paper texture background; deep green = wins, oxide red = losses.
- Print stylesheet included (A4). No dates in generated page bodies.
- StatiCrypt version is pinned (`STATICRYPT_VERSION = "3.5.4"` in build_site.py).

## Adding a new case study

1. Write the markdown in `content/` (numbered `## 1. Section` headings — the
   contents nav and section numerals are generated from them).
2. Add a `dict(...)` entry to `PAGES` and a row to `INDEX_ROWS` in `build_site.py`.
3. Build, copy, push. StatiCrypt encrypts every `src/*.html` it finds.

## Verifying a build

- `head build/index.html` → should start `<html class="staticrypt-html">` and
  contain `name="robots" content="noindex,nofollow,noarchive,noimageindex"`.
- After pushing, load `https://www.isriel.com/case-studies/` — you should get
  the password form titled "Protected — Case Studies", not content.
