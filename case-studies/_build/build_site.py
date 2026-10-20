#!/usr/bin/env python3
"""
Build the protected case-study microsite for isriels domain.

  md/markdown  ->  src/*.html (plaintext, NEVER committed)
               ->  build/*.html (StatiCrypt AES-256, safe to publish on a public repo)

Design: editorial "Decide/Learn" surface. Fraunces display + IBM Plex Sans body,
IBM Plex Mono for every number. Paper background, deep-green accent for wins,
oxide for losses. Headline figures are transcribed verbatim from the source
documents - do not round or invent.
"""
import os, re, html, datetime, subprocess, sys, shutil, base64

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
BUILD = os.path.join(ROOT, "build")
_SERVER_CASES = "/opt/data/workspace/job-search/03-case-studies"
CASES = os.environ.get("CASES_DIR") or (
    _SERVER_CASES if os.path.isdir(_SERVER_CASES) else os.path.join(ROOT, "content"))
STATICRYPT_VERSION = "3.5.4"
TODAY = datetime.date.today().strftime("%d %b %Y")

# ---------------------------------------------------------------- design system
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300..700;1,9..144,300..600&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');
:root{
  --paper:#fbf9f3; --paper-2:#f3eee2; --sheet:#fffefb; --ink:#16181c; --ink-2:#3b3f47;
  --muted:#6b6f78; --line:#dfd9cc; --line-2:#eae5da;
  --accent:#0b5c4d; --accent-soft:#e3ece8; --loss:#96331f; --loss-soft:#f2e5e1;
  --display:'Fraunces',Iowan Old Style,Palatino,Georgia,serif;
  --sans:'IBM Plex Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,sans-serif;
  --mono:'IBM Plex Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;background-color:#f7f3ea}
body{margin:0;background:transparent;color:var(--ink);
  font:400 17px/1.68 var(--sans);font-synthesis-weight:none;
  -webkit-font-smoothing:antialiased}
/* ---- paper stock. The texture must be a FIXED, viewport-sized layer: a background
   on <html>/<body> is positioned against the root box and leaves an untextured band
   whenever the document is shorter than the viewport. z-index:-1 keeps it beneath
   both the text and the opaque cards. ---- */
body::before{content:'';position:fixed;inset:0;z-index:-1;pointer-events:none;
  background-color:#f7f3ea;
  background-image:
    repeating-linear-gradient(46deg,  rgba(122,98,64,.075) 0 1px, transparent 1px 3px),
    repeating-linear-gradient(-44deg, rgba(122,98,64,.065) 0 1px, transparent 1px 4px),
    repeating-linear-gradient(0deg,   rgba(140,112,72,.07)  0 1px, transparent 1px 5px),
    radial-gradient(closest-side at 12% 16%, rgba(150,116,68,.10), transparent 80%),
    radial-gradient(closest-side at 88% 10%, rgba(122,98,64,.09), transparent 78%),
    radial-gradient(closest-side at 76% 82%, rgba(150,116,68,.10), transparent 80%),
    radial-gradient(closest-side at 16% 90%, rgba(122,98,64,.09), transparent 78%),
    radial-gradient(closest-side at 50% 48%, rgba(255,255,252,.52), transparent 58%),
    radial-gradient(125% 105% at 50% 42%, rgba(255,254,250,0) 42%, rgba(142,112,74,.16) 100%),
    radial-gradient(135% 105% at 50% -12%, #fffefa 0%, var(--paper) 46%, var(--paper-2) 100%)}
/* fine tooth: two-layer dot screen, offset so it doesn't moire */
body::after{content:'';position:fixed;inset:0;z-index:-1;pointer-events:none;
  mix-blend-mode:multiply;opacity:.5;
  background-image:
    radial-gradient(circle at 50% 50%, rgba(108,86,54,.30) 0 .5px, rgba(0,0,0,0) 1px),
    radial-gradient(circle at 50% 50%, rgba(108,86,54,.20) 0 .5px, rgba(0,0,0,0) 1px);
  background-size:3px 3px, 3px 3px;background-position:0 0, 1.5px 1.5px}
.page{max-width:1120px;margin:0 auto;padding:0 32px 96px}
.col{max-width:720px}
a{color:var(--accent);text-decoration:none;border-bottom:1px solid rgba(11,92,77,.28)}
a:hover{border-bottom-color:var(--accent)}

/* ---- masthead ---- */
.top{border-bottom:1px solid var(--line);margin-bottom:64px}
.top .in{max-width:1120px;margin:0 auto;padding:18px 32px;display:flex;
  align-items:baseline;justify-content:space-between;gap:20px;flex-wrap:wrap}
.brand{font:500 15px/1 var(--sans);letter-spacing:.01em}
.brand b{font-family:var(--display);font-weight:600;font-size:16px}
.top nav{font:400 12.5px/1 var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.top nav a{color:var(--muted);border:0}
.top nav a:hover{color:var(--accent)}

/* ---- hero ---- */
.eyebrow{font:500 12.5px/1.5 var(--mono);letter-spacing:.13em;text-transform:uppercase;
  color:var(--accent);margin:0 0 20px}
h1{font:400 clamp(34px,4.6vw,58px)/1.06 var(--display);letter-spacing:-.015em;margin:0 0 22px;
  font-variation-settings:'opsz' 120;text-wrap:balance}
h1 em{font-style:italic;font-weight:300}
.standfirst{font:300 21px/1.5 var(--sans);color:var(--ink-2);max-width:760px;margin:0 0 40px}
.standfirst strong{font-weight:500;color:var(--ink)}
.clientline{font:400 15px/1.5 var(--sans);color:var(--muted);margin:0 0 6px}

/* ---- meta grid ---- */
.meta{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));
  gap:0;border-top:1px solid var(--line);border-left:1px solid var(--line);margin:0 0 56px}
.meta div{border-right:1px solid var(--line);border-bottom:1px solid var(--line);padding:16px 20px}
.meta dt{font:500 11.5px/1 var(--mono);letter-spacing:.11em;text-transform:uppercase;
  color:var(--muted);margin:0 0 9px}
.meta dd{margin:0;font:400 15.5px/1.5 var(--sans);color:var(--ink-2)}

/* ---- stat band ---- */
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
  border-top:1.5px solid var(--ink);border-bottom:1.5px solid var(--ink);
  margin:0 0 64px;background:var(--sheet)}
.stats div{padding:26px 24px;border-right:1px solid var(--line-2)}
.stats div:last-child{border-right:0}
.stats .v{font:500 clamp(26px,3vw,36px)/1 var(--mono);letter-spacing:-.02em;color:var(--accent);
  display:block;margin:0 0 12px;font-variant-numeric:tabular-nums}
.stats .k{font:400 13.5px/1.45 var(--sans);color:var(--muted);margin:0}
.stats .loss .v{color:var(--loss)}
.stats .neutral .v{color:var(--ink)}

/* ---- contents ---- */
.contents{border:1px solid var(--line);background:var(--sheet);padding:22px 26px;margin:0 0 64px}
.contents p{font:500 11.5px/1 var(--mono);letter-spacing:.11em;text-transform:uppercase;
  color:var(--muted);margin:0 0 14px}
.contents ol{margin:0;padding:0;list-style:none;columns:2;column-gap:40px}
.contents li{font:400 15px/1.9 var(--sans);break-inside:avoid}
.contents a{border:0;color:var(--ink-2)}
.contents a:hover{color:var(--accent)}

/* ---- body ---- */
h2{font:400 clamp(25px,2.5vw,33px)/1.15 var(--display);letter-spacing:-.01em;
  margin:72px 0 18px;padding-top:26px;border-top:1px solid var(--line);
  display:flex;gap:16px;align-items:baseline}
h2 .num{font:500 13px/1 var(--mono);color:var(--accent);letter-spacing:.06em;
  padding-top:8px;flex:0 0 auto}
h2:first-of-type{margin-top:0}
h3{font:500 18.5px/1.35 var(--sans);margin:38px 0 10px;color:var(--ink);letter-spacing:-.005em}
h3 code{font-size:15px}
p{margin:0 0 20px;max-width:720px}
li{max-width:700px}
ul,ol{padding-left:22px;margin:0 0 22px}
li{margin:7px 0}
strong{font-weight:600}
em{font-style:italic}
hr{border:0;border-top:1px solid var(--line);margin:56px 0}
blockquote{margin:30px 0;padding:4px 0 4px 26px;border-left:2px solid var(--accent);
  font:300 italic clamp(19px,2.1vw,24px)/1.48 var(--display);color:var(--ink);
  max-width:760px}
blockquote p{margin:0}
code{font:400 14.5px/1.4 var(--mono);background:var(--accent-soft);color:#0a4b3f;
  padding:2px 6px;border-radius:3px;white-space:nowrap}

/* tables break out of the reading column */
.tw{width:100%;overflow-x:auto;margin:0 0 28px}
table{border-collapse:collapse;font:400 14.5px/1.45 var(--sans);min-width:660px;
  font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:10px 14px;border-bottom:1px solid var(--line-2);vertical-align:top}
thead th{border-bottom:1.5px solid var(--ink);font:500 11.5px/1.3 var(--mono);
  letter-spacing:.08em;text-transform:uppercase;color:var(--muted);padding-bottom:8px}
tbody tr:first-child td{border-top:1.5px solid var(--ink)}
tbody tr:hover td{background:var(--sheet)}
td strong{font-weight:600}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:7px;
  vertical-align:1px}
.dot.win{background:var(--accent)}
.dot.loss{background:var(--loss)}
.mark{color:#b8860b;font-size:15px}

/* ---- footer ---- */
footer{margin-top:88px;padding-top:26px;border-top:1.5px solid var(--ink);
  font:400 13.5px/1.6 var(--mono);color:var(--muted);display:flex;
  justify-content:space-between;gap:18px;flex-wrap:wrap}
footer a{color:var(--muted);border:0}

@media(max-width:720px){
  .page{padding:0 20px 64px}
  .top .in{padding:14px 20px}
  .contents ol{columns:1}
  h2{gap:10px}
  .stats div{border-right:0;border-bottom:1px solid var(--line-2)}
}
@media print{
  @page{size:A4;margin:14mm}
  html{background:#fff}
  body{background:#fff;font-size:10.5pt}
  body::before,body::after{display:none}
  .top,.contents,footer nav{display:none}
  a{color:inherit;border:0}
  h2{page-break-after:avoid}
  table,tr,blockquote{page-break-inside:avoid}
}
"""

SHELL = """<!doctype html>
<html lang="en-AU">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
<div class="top"><div class="in">
  <div class="brand"><b>Isriel Robinson</b> &nbsp;&middot;&nbsp; CRO &amp; Experimentation</div>
  <nav><a href="index.html">All case studies</a></nav>
</div></div>
<div class="page">
{body}
<footer>
  <span>Isriel Robinson &middot; {client}</span>
  <span>Private &mdash; not for distribution</span>
</footer>
</div>
</body>
</html>
"""

# ------------------------------------------------------------- page definitions
def meta_block(items):
    cells = "".join(
        f'<div><dt>{html.escape(k)}</dt><dd>{v}</dd></div>' for k, v in items)
    return f'<dl class="meta">{cells}</dl>'


def stat_block(items):
    cells = []
    for v, k, kind in items:
        cls = "" if kind == "win" else f' class="{kind}"' if kind else ""
        cells.append(f'<div{cls}><span class="v">{v}</span><p class="k">{k}</p></div>')
    return f'<div class="stats">{"".join(cells)}</div>'


PAGES = [
    dict(
        slug="step-one-pdp-redesign",
        source="step-one/PDP Redesign Programme - Step One Case Study.md",
        title="PDP Redesign Programme &mdash; Step One",
        hero_title="Rebuilding the product page<br>into a <em>stepped, modular</em> experience",
        eyebrow="Step One Life &nbsp;·&nbsp; AU + UK &nbsp;·&nbsp; Jan &ndash; Jun 2026",
        standfirst=("Six iterations across two markets to fix three structural problems on the "
                    "product detail page. The UK rollout returned a <strong>definitive +17.6% "
                    "conversion rate</strong> on flat order value &mdash; and the programme's other "
                    "result was a conversion &ldquo;win&rdquo; I refused to ship."),
        stats=[("+17.6%", "UK conversion rate lift, &gt;99.99% confidence", "win"),
               ("+£7,243", "incremental UK revenue in a six-day window", "win"),
               ("6", "iterations across 2 markets, ~85,000 visitors", "neutral"),
               ("&minus;A$9,151", "revenue lost by the iteration I killed", "loss")],
        meta=[("Role", "CRO Lead + Ecom Ops &mdash; sole owner: hypothesis &rarr; design &rarr; build &rarr; run &rarr; analyse &rarr; ship"),
              ("Programme scale", "6 iterations across 2 markets, ~85,000 visitors, strongest confidence in the CRO programme (&gt;99.99%)"),
              ("Primary metric owned", "Conversion Rate, with RPV as the commercial guardrail"),
              ("Status", "UK rolled out at +17.6% CVR. AU iterated to v3 and is now running with a paid-search-targeted follow-up.")],
        client="Step One Life",
    ),
    dict(
        slug="step-one-landing-page-cro",
        source="step-one/Landing Page CRO - Step One Case Study.md",
        title="Landing Page CRO &mdash; Step One",
        hero_title="Removing price from<br><em>above the fold</em>",
        eyebrow="Step One Life &nbsp;·&nbsp; AU &nbsp;·&nbsp; Jan &ndash; Feb 2026",
        standfirst=("A deliberately blunt intervention on campaign landing pages: take the number "
                    "out of the above-the-fold experience and let the value proposition work first. "
                    "It produced <strong>+42.8% conversion at &gt;99.99% confidence</strong> &mdash; the largest "
                    "single effect in the programme."),
        stats=[("+42.8%", "conversion rate lift, &gt;99.99% confidence", "win"),
               ("+35.6%", "revenue per visitor", "win"),
               ("+A$4,781", "more revenue from 203 fewer visitors", "win"),
               ("&minus;5.8%", "average order value &mdash; the accepted trade-off", "loss")],
        meta=[("Role", "CRO Lead + Ecom Ops &mdash; designed, built and tested the landing pages"),
              ("Programme scale", "2 landing page tests, ~9,400 visitors, the largest single lift in the CRO programme"),
              ("Primary metric owned", "Conversion Rate, with AOV as the explicit trade-off guardrail"),
              ("Status", "Sticker Shock shipped. The competitor-funnel variant was rejected.")],
        client="Step One Life",
    ),
    dict(
        slug="step-one-social-proof",
        source="step-one/Social Proof Messaging - Step One Case Study.md",
        title="Social Proof Messaging &mdash; Step One",
        hero_title="One message,<br><em>three markets</em>",
        eyebrow="Step One Life &nbsp;·&nbsp; US · AU · UK &nbsp;·&nbsp; Dec 2025 &ndash; Jan 2026",
        standfirst=("The same PDP banner treatment &mdash; &ldquo;X+ Million Sold&rdquo; replacing a "
                    "generic USP strip &mdash; run as three parallel tests to find out whether a "
                    "social-proof claim travels. <strong>US: +28.1% conversion at &gt;99.99% confidence.</strong>"),
        stats=[("+28.1%", "US conversion rate, &gt;99.99% confidence", "win"),
               ("+26.0%", "US revenue per visitor", "win"),
               ("+23.3%", "US add-to-cart rate", "win"),
               ("3", "storefronts, ~111,000 visitors, one treatment", "neutral")],
        meta=[("Role", "CRO Lead + Ecom Ops &mdash; sole owner: hypothesis &rarr; build &rarr; run &rarr; analyse &rarr; ship"),
              ("Programme scale", "3 tests, one treatment, three storefronts, ~111,000 visitors"),
              ("Primary metric owned", "Conversion Rate, with RPV as the commercial guardrail"),
              ("Status", "US rolled out on a definitive result. AU shipped mobile-first with a desktop watch-list. UK held as directional.")],
        client="Step One Life",
    ),
    dict(
        slug="step-one-tiered-discounting",
        source="step-one/Tiered Discounting and Pricing - Step One Case Study.md",
        title="Tiered Discounting &amp; Pack Pricing &mdash; Step One",
        hero_title="Re-architecting<br><em>discounting and pack pricing</em>",
        eyebrow="Step One Life &nbsp;·&nbsp; AU / UK / US &nbsp;·&nbsp; Feb &ndash; Jun 2026",
        standfirst=("Moving the discount architecture from unit-based tiers to spend thresholds, "
                    "across three storefronts and two currencies. The commercial finding arrived "
                    "where the RPV read couldn't see it: <strong>£21,136 less promotional cost</strong> "
                    "on the same orders."),
        stats=[("+A$30,894", "incremental AU revenue inside the test windows", "win"),
               ("&minus;£21,136", "UK promotional cost given away, 5,400 orders", "win"),
               ("9", "completed experiments, ~776,000 visitors", "neutral"),
               ("+5.5%", "AU revenue per visitor &mdash; the headline metric owned", "win")],
        meta=[("Role", "CRO Lead + Ecom Ops &mdash; sole owner: hypothesis &rarr; build &rarr; run &rarr; analyse &rarr; ship"),
              ("Programme scale", "9 completed experiments, ~776,000 visitors, 3 storefronts, 2 currencies"),
              ("Primary metric owned", "Revenue Per Visitor (RPV)"),
              ("Status", "AU model shipped and re-confirmed post price-increase. UK concluded with a quantified margin finding. US pack structure tested and held.")],
        client="Step One Life",
    ),
    dict(
        slug="nine-entertainment",
        source=None,  # markdown authored in src/
        title="Nine Entertainment &mdash; CRO Case Studies",
        hero_title="Paywalls, pricing and<br><em>68 experiments in a year</em>",
        eyebrow="Nine Entertainment &nbsp;·&nbsp; SMH, The Age, Brisbane Times &amp; AFR &nbsp;·&nbsp; FY24",
        standfirst=("Full-lifecycle ownership of onsite experimentation across four mastheads on the "
                    "Piano platform: <strong>68 A/B tests, 43 conclusive winners (63% win rate)</strong>, "
                    "and 1,391 incremental subscriptions from conclusive results."),
        stats=[("43/68", "tests produced positive lift &mdash; 63% win rate", "win"),
               ("47%", "average uplift from positive tests", "win"),
               ("1,391", "incremental subscriptions from conclusive winners", "win"),
               ("+102%", "The Age conversions, multi-package paywall", "win")],
        meta=[("Role", "CRO &amp; Experimentation Lead &mdash; full lifecycle across 4 mastheads"),
              ("Programme scale", "68 A/B tests in FY24 on the Piano platform; paywall optimisation, intro offer pricing, personalised pricing, social ribbons and meters"),
              ("Analysis depth", "Audience segments (anon, registered, direct), device-level, metered vs subscriber-only paywalls"),
              ("Reporting", "Campaign performance at a glance, test-level deep dives, programme-level summary to Subscriptions &amp; Marketing and Product")],
        client="Nine Entertainment",
    ),
]

INDEX_STATS = [("5", "case studies &mdash; two employers, 4 mastheads", "neutral"),
               ("77", "documented experiments behind them", "neutral"),
               ("60%+", "documented win rate across both programmes", "win"),
               ("7", "storefronts / mastheads / markets", "neutral")]

INDEX_ROWS = [
    ("step-one-pdp-redesign", "PDP Redesign Programme", "Step One Life",
     "AU + UK · Jan–Jun 2026", "+17.6% CVR", "&gt;99.99% confidence",
     "Six iterations rebuilding the product detail page. The UK rollout is the strongest result in the programme."),
    ("step-one-landing-page-cro", "Landing Page CRO", "Step One Life",
     "AU · Jan–Feb 2026", "+42.8% CVR", "&gt;99.99% confidence",
     "Removing price from above the fold on campaign landing pages — the largest single effect in the programme."),
    ("step-one-social-proof", "Social Proof Messaging", "Step One Life",
     "US · AU · UK · Dec 2025–Jan 2026", "+28.1% CVR", "&gt;99.99% confidence",
     "One treatment, three storefronts, run in parallel to test whether a claim travels."),
    ("step-one-tiered-discounting", "Tiered Discounting &amp; Pack Pricing", "Step One Life",
     "AU / UK / US · Feb–Jun 2026", "+A$30,894", "incremental revenue",
     "Unit-based tiers replaced with spend thresholds across 9 experiments, with a quantified discount-efficiency finding."),
    ("nine-entertainment", "Paywalls, Pricing &amp; Programmes", "Nine Entertainment",
     "SMH · The Age · BT · AFR · FY24", "63% win rate", "43/68 tests",
     "Intro offer pricing, multi-package paywalls, social ribbons and a personalised retention-pricing strategy."),
]


# --------------------------------------------------- p-value -> plain language
def _conf(p):
    """Confidence phrasing for a p-value, written for a non-technical reader."""
    if p >= 0.10:
        return "not significant"
    conf = (1.0 - p) * 100.0
    if conf >= 99.99:
        return "&gt;99.99% confidence"
    return f"{conf:.2f}".rstrip("0").rstrip(".") + "% confidence"


_PV = re.compile(r"(?<![\w?&/=])p\s*=\s*(\d*\.?\d+(?:[eE][+-]?\d+)?)")
_PLT = re.compile(r"(?<![\w?&/=])p\s*<\s*(\d*\.?\d+(?:[eE][+-]?\d+)?)")


def plain_stats(t):
    """Swap p-value notation for confidence percentages. Applied at build time so
    the source markdown keeps the full statistical detail."""
    def eq(m):
        v = float(m.group(1))
        return _conf(v) if 0.0 <= v <= 1.0 else m.group(0)

    def lt(m):
        v = float(m.group(1))
        if not (0.0 <= v <= 1.0):
            return m.group(0)
        conf = (1.0 - v) * 100.0
        if conf >= 99.99:
            return "&gt;99.99% confidence"
        return "&gt;" + f"{conf:.2f}".rstrip("0").rstrip(".") + "% confidence"

    t = _PV.sub(eq, t)
    t = _PLT.sub(lt, t)

    # ---- strip test-statistic notation, keep the plain-language verdict ------
    # "✅ z = −11.17, >99.99% confidence"  -> "✅ >99.99% confidence"
    # "❌ z = −0.80, not significant"      -> "❌ not significant"
    t = re.sub(r"(?<![A-Za-z0-9_])[zt]\s*=\s*[-\u2212\u2013]?\d+(?:\.\d+)?\s*,?\s*", "", t)
    # "χ² = 5.4 ⚠ moderate SRM" -> "⚠ moderate SRM"  (statistic dropped, verdict kept)
    t = re.sub(r"[\u03c7\u03a7]\s*\u00b2\s*=\s*\d+(?:\.\d+)?\s*,?\s*", "", t)

    # ---- name the quality flags in words, not acronyms ----------------------
    t = t.replace("moderate SRM flag", "moderate traffic-imbalance flag")
    t = t.replace("minor SRM flag", "slight traffic-imbalance flag")
    t = t.replace("moderate SRM", "moderate traffic imbalance")
    t = t.replace("minor SRM", "minor traffic imbalance")
    t = t.replace("SRM", "traffic imbalance")
    t = t.replace("\u2705 balanced", "\u2705 balanced split")
    t = t.replace("\u2705 clean 50/50", "\u2705 clean 50/50 split")

    # ---- alpha and win-probability phrasing ---------------------------------
    t = t.replace("Standard \u03b1 = 0.05", "Standard 95% confidence threshold")
    t = t.replace("Standard &alpha; = 0.05", "Standard 95% confidence threshold")
    t = t.replace("\u03b1 = 0.05", "95% confidence threshold")
    t = t.replace("&alpha; = 0.05", "95% confidence threshold")
    t = t.replace("zero-inflated z-test for RPV", "zero-inflated test on revenue per visitor")
    t = t.replace("two-proportion z-test for CVR and ATC rate",
                  "two-proportion significance test on conversion rate and add-to-cart rate")
    t = t.replace("win probability", "probability of improvement")
    t = t.replace("win prob", "probability of improvement")
    t = t.replace("win chance", "probability of improvement")

    # ---- tidy the artefacts the strips leave behind -------------------------
    t = re.sub(r"\(\s*,\s*", "(", t)
    t = re.sub(r",\s*,", ",", t)
    t = re.sub(r"\(\s*\)", "", t)
    t = re.sub(r"\s+([,.;])", r"\1", t)
    t = re.sub(r"[ \t]{2,}", " ", t)
    # "✅ >99.9%" reads as a verdict; give it the same label as its neighbours
    t = t.replace("\u2705 >99.9%", "\u2705 >99.9% confidence")
    return t


# ------------------------------------------------------------------- md -> html
def to_body(md_text):
    """Markdown -> styled body HTML. Verbatim content; only presentation is added."""
    import markdown as mdlib
    t = plain_stats(md_text)
    # strip the source doc's own H1/H2/meta header - the shell supplies the hero
    t = re.sub(r"\A#.*?\n(?:\*\*[^\n]*\n)*\n*---\n", "", t, flags=re.S)
    # source-doc trailing italics block -> footer note styling
    t = t.replace("✅", '<span class="dot win"></span>').replace("❌", '<span class="dot loss"></span>')
    t = t.replace("⭐", '<span class="mark">★</span>')
    conv = mdlib.Markdown(extensions=["tables", "sane_lists", "attr_list", "toc"],
                          extension_configs={"toc": {"slugify": lambda v, s: re.sub(
                              r"[^a-z0-9]+", "-", v.lower()).strip("-")}})
    out = conv.convert(t)
    # numbered section headings -> display numeral (headings carry ids from the toc extension)
    out = re.sub(r"<h2([^>]*)>(\d+)\.\s*",
                 lambda m: f'<h2{m.group(1)}><span class="num">{int(m.group(2)):02d}</span>'
                           '<span class="t">', out)
    out = re.sub(r"</h2>", "</span></h2>", out)
    # wrap tables for horizontal scroll
    out = out.replace("<table>", '<div class="tw"><table>').replace("</table>", "</table></div>")
    return out


def contents_nav(md_text):
    heads = re.findall(r"^##\s+(\d+)\.\s*(.+)$", md_text, flags=re.M)
    if not heads:
        return ""
    items = "".join(
        f'<li><a href="#{re.sub(r"[^a-z0-9]+", "-", f"{h[0]}. {h[1]}".lower()).strip("-")}">'
        f'{h[0]}. {h[1]}</a></li>' for h in heads)
    return f'<div class="contents"><p>Contents</p><ol>{items}</ol></div>'


def build_page(p):
    src = os.path.join(CASES, p["source"]) if p["source"] else os.path.join(SRC, p["slug"] + ".md")
    md_text = open(src, encoding="utf-8").read()
    body = "\n".join([
        f'<p class="eyebrow">{p["eyebrow"]}</p>',
        f'<h1>{p["hero_title"]}</h1>',
        f'<p class="standfirst">{p["standfirst"]}</p>',
        stat_block(p["stats"]),
        meta_block(p["meta"]),
        contents_nav(md_text),
        to_body(md_text),
    ])
    out = SHELL.format(title=re.sub("<[^>]+>", "", p["title"]), css=CSS, body=body,
                       client=p["client"])
    os.makedirs(SRC, exist_ok=True)
    dest = os.path.join(SRC, p["slug"] + ".html")
    open(dest, "w", encoding="utf-8").write(out)
    return dest


def build_index():
    cards = []
    for slug, title, client, period, metric, sub, blurb in INDEX_ROWS:
        cards.append(f"""<a class="card" href="{slug}.html">
  <div class="c-top"><span class="c-client">{client}</span><span class="c-period">{period}</span></div>
  <h3 class="c-title">{title}</h3>
  <p class="c-blurb">{blurb}</p>
  <div class="c-foot"><span class="c-metric">{metric}</span><span class="c-sub">{sub}</span></div>
</a>""")
    extra_css = """
.hero{padding-top:8px}
.lede{font:300 22px/1.5 var(--sans);color:var(--ink-2);max-width:760px;margin:0 0 48px}
.lede strong{font-weight:500;color:var(--ink)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:0;
  border-top:1.5px solid var(--ink);border-left:1px solid var(--line)}
.card{display:block;border-right:1px solid var(--line);border-bottom:1px solid var(--line);
  padding:26px 26px 22px;background:var(--sheet);border-bottom-color:var(--line)}
.card:hover{background:#fdfcf7}
.card{border-bottom:1px solid var(--line)!important}
.c-top{display:flex;justify-content:space-between;gap:12px;font:500 11.5px/1.3 var(--mono);
  letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin-bottom:16px}
.c-client{color:var(--accent)}
.c-title{font:400 25px/1.15 var(--display);letter-spacing:-.01em;margin:0 0 12px;color:var(--ink)}
.c-blurb{font:400 15px/1.55 var(--sans);color:var(--muted);margin:0 0 20px;max-width:52ch}
.c-foot{display:flex;align-items:baseline;gap:12px;border-top:1px solid var(--line-2);padding-top:14px}
.c-metric{font:500 22px/1 var(--mono);color:var(--accent);letter-spacing:-.02em}
.c-sub{font:400 12.5px/1.3 var(--mono);letter-spacing:.04em;color:var(--muted)}
.note{max-width:720px;margin:56px 0 0;font:400 15px/1.6 var(--sans);color:var(--muted)}
"""
    body = "\n".join([
        '<div class="hero">',
        '<p class="eyebrow">Private portfolio &nbsp;·&nbsp; CRO &amp; Experimentation</p>',
        '<h1>Case studies:<br><em>what was tested,<br>and what actually happened</em></h1>',
        '<p class="lede">Fifteen years of conversion-rate and ecommerce operations work, written up as '
        'the experiments themselves &mdash; hypotheses, statistics, the tests that failed, and the ones '
        'I killed rather than reported. <strong>Every figure traces to a named experiment ID.</strong></p>',
        stat_block(INDEX_STATS),
        '</div>',
        f'<div class="cards">{"".join(cards)}</div>',
        '<p class="note">Confidential: these documents contain commercially sensitive performance data '
        'for former employers and are shared for recruitment evaluation only. Not for distribution, '
        'republication or reference.</p>',
    ])
    out = SHELL.format(title="Case Studies — Isriel Robinson", css=CSS + extra_css,
                       body=body, client="Private portfolio")
    dest = os.path.join(SRC, "index.html")
    open(dest, "w", encoding="utf-8").write(out)
    return dest


# -------------------------------------------------------------------- encrypt
def _password():
    pw = os.environ.get("STATICRYPT_PASSWORD", "").strip()
    if pw:
        return pw
    pwfile = os.path.join(ROOT, ".staticrypt-password")
    if os.path.exists(pwfile):
        return open(pwfile, encoding="utf-8").read().strip()
    return None


def encrypt_all():
    """StatiCrypt-encrypt every src/*.html into build/. Requires the password
    via STATICRYPT_PASSWORD env or a .staticrypt-password file (never committed)."""
    import glob
    pw = _password()
    if not pw:
        print("  !! no StatiCrypt password (STATICRYPT_PASSWORD env or "
              ".staticrypt-password file) - build/ NOT regenerated")
        return False
    os.makedirs(BUILD, exist_ok=True)
    for stale in glob.glob(os.path.join(BUILD, "*.html")):
        os.remove(stale)
    env = dict(os.environ, STATICRYPT_PASSWORD=pw)
    for f in sorted(glob.glob(os.path.join(SRC, "*.html"))):
        subprocess.run(
            ["npx", "--yes", f"staticrypt@{STATICRYPT_VERSION}", f,
             "-d", BUILD, "--short",
             "--template-title", "Protected — Case Studies"],
            check=True, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        print(f"  encrypted {os.path.basename(f)}")
    subprocess.run([sys.executable, os.path.join(ROOT, "pre_publish.py")], check=True)
    return True


# ------------------------------------------------------------------------ main
def main():
    os.makedirs(SRC, exist_ok=True)
    made = [build_index()]
    for p in PAGES:
        made.append(build_page(p))
    for f in made:
        print(f"  built {os.path.relpath(f, ROOT)}  ({os.path.getsize(f):,} bytes)")
    if encrypt_all():
        print(f"  publish build/*.html -> case-studies/ (never src/)")
    return made


if __name__ == "__main__":
    main()
