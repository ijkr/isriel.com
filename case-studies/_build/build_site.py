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
# Fixed salt across ALL pages so StatiCrypt's "Remember me" login works
# site-wide (log in once, every page auto-decrypts). The salt is embedded in
# the public encrypted pages anyway, so keeping it here is no exposure.
# Change it (32 hex chars) only if you want to invalidate every remembered login.
STATICRYPT_SALT = "9f06d8831857273deb9aac6941d81d20"
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
        slug="step-one-liquid-pdp",
        source=None,
        title="Rebuilding the PDP in Liquid &mdash; Step One",
        hero_title="Re-platforming the PDP<br><em>without losing a conversion</em>",
        eyebrow="Step One Life &nbsp;·&nbsp; AU &nbsp;·&nbsp; Aug 2026 &nbsp;·&nbsp; 2 tests",
        standfirst=("The product page ran on an iFrame \u201cIslands\u201d architecture \u2014 slow and fragile. "
                    "The rebuild in native Shopify Liquid was gated behind two sequential A/B validations "
                    "(Men\u2019s, then Women\u2019s) with a maintain-or-improve bar. <strong>Both migrations deployed "
                    "with zero commercial regression</strong> \u2014 and the tests caught a +39.9% desktop \u201cwin\u201d "
                    "that was pure instrumentation artefact."),
        stats=[("+5.1%", "CVR, Men\u2019s Liquid PDP (nothing significantly worse anywhere)", "win"),
               ("+7.4%", "RPV, Men\u2019s \u2014 climbing all test", "win"),
               ("94.8", "Women\u2019s SKU index post-migration \u2014 friction closed from ~85", "win"),
               ("2", "categories migrated behind A/B validation, both shipped", "neutral")],
        meta=[("Role", "CRO Lead + Ecom Ops \u2014 migration gating, test design, per-device/SKU/channel analysis"),
              ("Programme scale", "2 sequential tests, ~95K visitors combined, full device/channel/SKU cuts"),
              ("Primary metric owned", "Non-inferiority across CVR, RPV, ATC, CTR"),
              ("Status", "Men\u2019s and Women\u2019s Liquid PDPs both deployed. Per-device splits flagged unreliable pending audit.")],
        client="Step One Life",
    ),
    dict(
        slug="step-one-visual-mobile-menu",
        source=None,
        title="Visual Mobile Menu &mdash; Step One",
        hero_title="Replacing the text menu<br>with <em>product imagery</em>",
        eyebrow="Step One Life &nbsp;·&nbsp; AU &nbsp;·&nbsp; Jul\u2013Aug 2026",
        standfirst=("The mobile menu was a text list for a product chosen by colour and style. An image-led "
                    "menu lifted add-to-cart significantly and conversion with it \u2014 while clickthrough "
                    "fell significantly, the signature of a <strong>shorter path, not a weaker one</strong>."),
        stats=[("+5.1%", "conversion rate (5.82% \u2192 6.11%)", "win"),
               ("+4.6%", "add-to-cart rate \u2014 statistically significant", "win"),
               ("\u22126.7%", "clickthrough \u2014 significant, and correctly read as navigation efficiency", "neutral"),
               ("+A$6,625", "revenue over the read window", "win")],
        meta=[("Role", "CRO Lead + Ecom Ops \u2014 hypothesis, analysis, rollout call"),
              ("Programme scale", "~67K visitors, mobile-only surface, new/returning and channel cuts"),
              ("Primary metric owned", "Conversion rate, with ATC as the behavioural corroboration"),
              ("Status", "Winner; Paid Social and SMS carried as watch items for paid traffic")],
        client="Step One Life",
    ),
    dict(
        slug="step-one-quick-buy",
        source=None,
        title="Quick Buy, Tested Twice, Killed Twice &mdash; Step One",
        hero_title="The shortcut that<br><em>cost 17% of conversions</em>",
        eyebrow="Step One Life &nbsp;·&nbsp; US &nbsp;·&nbsp; Jul 2026 &nbsp;·&nbsp; 2 iterations",
        standfirst=("Quick-buy on the home page was supposed to shorten the path to purchase. It cut "
                    "clickthroughs significantly and conversion with it \u2014 so the component was rethought "
                    "around the diagnosed SKU-mix problem and tested again. <strong>Same result. "
                    "Stopped in 4 days and abandoned</strong>, because significance wouldn\u2019t have changed "
                    "the decision."),
        stats=[("\u221217.2%", "CVR, iteration 1", "loss"),
               ("\u221218.1%", "CVR, iteration 2 \u2014 after the diagnosed fix", "loss"),
               ("\u221212.4%", "clickthrough, statistically significant in both", "loss"),
               ("88", "Boxer Brief unit index \u2014 the tile steered buyers off the hero SKU", "loss")],
        meta=[("Role", "CRO Lead + Ecom Ops \u2014 hypothesis, kill call, iteration design, second kill call"),
              ("Programme scale", "2 tests, ~5.3K visitors, US home page and men\u2019s landing page"),
              ("Primary metric owned", "Conversion rate, with CTR as leading indicator"),
              ("Status", "Concept abandoned after two iterations \u2014 not extended, not re-skinned")],
        client="Step One Life",
    ),
    dict(
        slug="step-one-founder-story",
        source=None,
        title="The Founder Story Tile &mdash; Step One",
        hero_title="Right asset,<br><em>wrong audience</em>",
        eyebrow="Step One Life &nbsp;·&nbsp; US &nbsp;·&nbsp; May 2026",
        standfirst=("A \u201cMeet the Founder\u201d tile on the PDP lifted conversion for first-time visitors "
                    "(<strong>+5.7%</strong>) while actively hurting returning customers and CRM traffic "
                    "(<strong>\u221244% RPV on SMS</strong>). The aggregate hid the mechanism; the segment read "
                    "turned a no-rollout into a targeting brief."),
        stats=[("+5.7%", "CVR among new visitors \u2014 the tile works for cold audiences", "win"),
               ("\u22127.5%", "CVR among returning visitors", "loss"),
               ("\u221244.4%", "RPV on SMS traffic \u2014 the highest-intent cohort", "loss"),
               ("+9.7%", "CVR on direct traffic \u2014 brand-aware, not yet loyal", "win")],
        meta=[("Role", "CRO Lead + Ecom Ops \u2014 hypothesis, segment analysis, follow-up design"),
              ("Programme scale", "~31K visitors, US PDP, visitor-type and channel segmentation"),
              ("Primary metric owned", "Conversion rate, read against RPV/AOV value metrics"),
              ("Status", "No rollout as-is; segment-targeted variant (new visitors only, CRM-suppressed) designed as follow-up")],
        client="Step One Life",
    ),
    dict(
        slug="step-one-trust-signals",
        source=None,
        title="Trust Signals on the Lead Image &mdash; Step One",
        hero_title="How much trust signal<br><em>is enough</em>",
        eyebrow="Step One Life &nbsp;·&nbsp; US &nbsp;·&nbsp; Oct 2025 &nbsp;·&nbsp; 3-variant ladder",
        standfirst=("The PDP lead image carried only product; the trust assets sat below the fold. "
                    "A three-variant ladder \u2014 Trustpilot, +render, +USP icons \u2014 asked how much signal "
                    "pays, not just whether it works. <strong>+8.5% conversion</strong>, implemented, "
                    "with the AU replication queued."),
        stats=[("+8.5%", "conversion rate, winning variant", "win"),
               ("3", "variants laddered by information density", "neutral"),
               ("15", "days, US storefront", "neutral"),
               ("AU", "replication queued on the trusted stack", "neutral")],
        meta=[("Role", "CRO Lead + Ecom Ops \u2014 ladder test design, cross-market replication plan"),
              ("Programme scale", "Control + 3 variants, US PDP lead image"),
              ("Primary metric owned", "Conversion rate"),
              ("Status", "Implemented in the US; AU rerun queued (US result from a CRO tool under trial \u2014 treated as directional until replicated)")],
        client="Step One Life",
    ),
    dict(
        slug="step-one-payment-methods",
        source=None,
        title="Payment Methods on the PDP &mdash; Step One",
        hero_title="Financing anxiety,<br><em>answered upstream of the cart</em>",
        eyebrow="Step One Life &nbsp;·&nbsp; UK &nbsp;·&nbsp; Oct 2025",
        standfirst=("Instalment options existed but were invisible at the point of decision. Making payment "
                    "types visible on the PDP lifted UK conversion <strong>+5.6%</strong> \u2014 and generated "
                    "its own follow-up: relocate the logos to the side cart and test whether the win survives "
                    "the move."),
        stats=[("+5.6%", "conversion rate, UK PDP", "win"),
               ("10", "days to the call (11\u201320 Oct 2025)", "neutral"),
               ("1", "follow-up spawned \u2014 side-cart relocation test", "neutral")],
        meta=[("Role", "CRO Lead + Ecom Ops \u2014 hypothesis, analysis, iteration pipeline"),
              ("Programme scale", "UK storefront, PDP surface"),
              ("Primary metric owned", "Conversion rate"),
              ("Status", "Implemented; side-cart relocation follow-up queued")],
        client="Step One Life",
    ),
    dict(
        slug="step-one-bundle-builder",
        source=None,
        title="Mixed-Colours Bundle Builder &mdash; Step One",
        hero_title="Killing the page-hops<br><em>inside the bundle journey</em>",
        eyebrow="Step One Life &nbsp;·&nbsp; AU + UK &nbsp;·&nbsp; Oct 2025",
        standfirst=("Building a mixed-colour pack meant adding one colour, changing pages, adding the next. "
                    "A single-surface bundle builder won <strong>+19.1% in AU and +5.6% in the UK in the "
                    "same week</strong> \u2014 the cross-market replication that turns a result into a mechanic."),
        stats=[("+19.1%", "CVR, AU (24\u201329 Oct 2025)", "win"),
               ("+5.6%", "CVR, UK (27\u201331 Oct 2025)", "win"),
               ("2", "markets, same week, same verdict", "win")],
        meta=[("Role", "CRO Lead + Ecom Ops \u2014 hypothesis, dual-market analysis, rollout"),
              ("Programme scale", "2 storefronts in parallel, theme-level component"),
              ("Primary metric owned", "Conversion rate"),
              ("Status", "Implemented in both markets; desktop caveat logged with session-recording follow-up; upsell and orientation iterations queued")],
        client="Step One Life",
    ),
    dict(
        slug="nine-intro-offer-pricing",
        source=None,  # markdown authored in src/
        title="Intro Offer Pricing &mdash; Nine Entertainment",
        hero_title="Calibrating intro pricing<br>to <em>each masthead's market</em>",
        eyebrow="Nine Entertainment &nbsp;·&nbsp; SMH, The Age &amp; AFR &nbsp;·&nbsp; Nov&ndash;Dec 2023",
        standfirst=("SMH and The Age were the only publishers not advertising a discounted intro offer, "
                    "and the AFR's was the most expensive in its market. A three-channel flash-sale "
                    "programme &mdash; paywall, email and landing page &mdash; acquired "
                    "<strong>2,751 subscriptions</strong> and found that different price points win on "
                    "different paywall types."),
        stats=[("2,751", "subscriptions acquired in the flash-sale window", "win"),
               ("+129%", "conversion on the winning metered-paywall offer", "win"),
               ("$26K", "annualised revenue from the $1/week paywall test", "win"),
               ("3", "channels tested independently, then coordinated", "neutral")],
        meta=[("Role", "CRO &amp; Experimentation Lead &mdash; hypothesis &rarr; build &rarr; run &rarr; analyse across paywall, email and landing page"),
              ("Programme scale", "4 email offers, 5 paywall price points, metered vs subscriber-only paywalls, 3 mastheads"),
              ("Primary metric owned", "Conversion rate, measured per channel before coordination"),
              ("Status", "75% of SMH/The Age acquisition target; 83% of AFR target")],
        client="Nine Entertainment",
    ),
    dict(
        slug="nine-personalised-retention",
        source=None,
        title="Personalised Pricing &amp; Retention &mdash; Nine Entertainment",
        hero_title="Pricing the renewal<br>before the <em>cancellation decision</em>",
        eyebrow="Nine Entertainment &nbsp;·&nbsp; All mastheads &nbsp;·&nbsp; FY22&ndash;FY24",
        standfirst=("26% of subscribers cancelled the moment their promotion ended. A churn-propensity "
                    "model tiered every subscriber 1&ndash;10 and priced their renewal accordingly &mdash; "
                    "until its precision problems forced the right call: <strong>abandon model-led "
                    "targeting for randomised testing</strong>."),
        stats=[("26%", "of subscribers cancelled the moment their promotion ended", "loss"),
               ("14,600&ndash;20,000", "subscribers retained in the modelled scenario", "win"),
               ("$400K&ndash;$530K", "projected additional annual revenue", "win"),
               ("1&ndash;10", "churn-propensity score segmenting every subscriber", "neutral")],
        meta=[("Role", "CRO &amp; Experimentation Lead &mdash; retention pricing strategy across all mastheads"),
              ("Programme scale", "3 risk tiers, D-6 transactional eDM + SMS renewal comms, Starter vs Premium Digital churn patterns"),
              ("Key decision", "Pivoted from a 5&ndash;10% precision-limited propensity model to randomised A/B testing on flash-sale cohorts"),
              ("Status", "Modelled at $400K&ndash;$530K annual revenue; retention pricing adopted over acquisition spend")],
        client="Nine Entertainment",
    ),
    dict(
        slug="nine-social-ribbon",
        source=None,
        title="Social Ribbon: Removing the Timer &mdash; Nine Entertainment",
        hero_title="The 30-second timer<br><em>costing conversions</em>",
        eyebrow="Nine Entertainment &nbsp;·&nbsp; AFR &nbsp;·&nbsp; CRO-30.0-2312",
        standfirst=("One variable: the social ribbon's auto-dismissing 30-second timer was removed, "
                    "letting the offer persist until the reader actively dismisses it. "
                    "<strong>+33% conversion</strong> &mdash; removing artificial expiry friction beat "
                    "manufactured urgency."),
        stats=[("+33%", "conversion lift with the timer removed", "win"),
               ("+26%", "clickthrough lift &mdash; 293 incremental clicks", "win"),
               ("$6K", "annualised incremental revenue", "win"),
               ("947K", "visitors over 21 days", "neutral")],
        meta=[("Role", "CRO &amp; Experimentation Lead &mdash; single-variable paywall-surface test"),
              ("Programme scale", "21 days, 947K visitors, AFR social ribbon on the Piano platform"),
              ("Primary metric owned", "Conversion rate and clickthrough rate"),
              ("Status", "Winner; recommendation carried into the next social ribbon template build")],
        client="Nine Entertainment",
    ),
    dict(
        slug="nine-multi-package-paywall",
        source=None,
        title="Multi-Package Paywall &mdash; Nine Entertainment",
        hero_title="Three prices instead of<br><em>take-it-or-leave-it</em>",
        eyebrow="Nine Entertainment &nbsp;·&nbsp; SMH &amp; The Age &nbsp;·&nbsp; CRO-73/74.0-2404",
        standfirst=("A single-package paywall offered one price as take-it-or-leave-it. Replacing it "
                    "with three simultaneous options let readers self-select to their own price "
                    "sensitivity: <strong>+70% conversions at SMH, +102% at The Age</strong>, both at "
                    "100% winning probability."),
        stats=[("+70%", "SMH conversions (622 &rarr; 1,058)", "win"),
               ("+102%", "The Age conversions (324 &rarr; 654)", "win"),
               ("+122%", "SMH revenue", "win"),
               ("765", "incremental sales across both mastheads", "win")],
        meta=[("Role", "CRO &amp; Experimentation Lead &mdash; paywall-structure test, two mastheads in parallel"),
              ("Programme scale", "Single-package vs three-package paywall, SMH &amp; The Age, Piano platform"),
              ("Primary metric owned", "Conversion rate, with revenue as the commercial read"),
              ("Status", "Winner on both mastheads; follow-up recommended: retest without Premium Digital on offer")],
        client="Nine Entertainment",
    ),
]

INDEX_STATS = [("15", "case studies &mdash; two employers, 4 mastheads", "neutral"),
               ("77", "documented experiments behind them", "neutral"),
               ("60%+", "documented win rate across both programmes", "win"),
               ("7", "storefronts / mastheads / markets", "neutral")]

INDEX_ROWS = [
    ("step-one-pdp-redesign", "PDP Redesign Programme", "Step One",
     "AU + UK · Jan–Jun 2026", "UX & Layout", "+17.6% CVR", "&gt;99.99% confidence",
     "Six iterations rebuilding the product detail page. The UK rollout is the strongest result in the programme."),
    ("step-one-landing-page-cro", "Landing Page CRO", "Step One",
     "AU · Jan–Feb 2026", "Value Proposition", "+42.8% CVR", "&gt;99.99% confidence",
     "Removing price from above the fold on campaign landing pages — the largest single effect in the programme."),
    ("step-one-social-proof", "Social Proof Messaging", "Step One",
     "US · AU · UK · Dec 2025–Jan 2026", "Social Proof", "+28.1% CVR", "&gt;99.99% confidence",
     "One treatment, three storefronts, run in parallel to test whether a claim travels."),
    ("step-one-tiered-discounting", "Tiered Discounting &amp; Pack Pricing", "Step One",
     "AU / UK / US · Feb–Jun 2026", "Pricing", "+A$30,894", "incremental revenue",
     "Unit-based tiers replaced with spend thresholds across 9 experiments, with a quantified discount-efficiency finding."),
    ("step-one-liquid-pdp", "Rebuilding the PDP in Liquid", "Step One",
     "AU · Aug 2026", "Technical CRO", "0 regressions", "2 migrations shipped",
     "An iFrame PDP re-platformed to native Liquid, gated behind two A/B validations — and a +39.9% desktop 'win' exposed as an instrumentation artefact."),
    ("step-one-visual-mobile-menu", "Visual Mobile Menu", "Step One",
     "AU · Jul–Aug 2026", "Navigation & Mobile", "+5.1% CVR", "ATC +4.6% sig",
     "An image-led mobile menu. Clickthrough fell significantly — the signature of a shorter path, not a weaker one."),
    ("step-one-quick-buy", "Quick Buy, Tested Twice, Killed Twice", "Step One",
     "US · Jul 2026", "Friction Reduction", "−17% CVR", "concept abandoned",
     "Quick-buy cut conversion in both iterations. Stopped in 4 days — significance wouldn't have changed the decision."),
    ("step-one-founder-story", "The Founder Story Tile", "Step One",
     "US · May 2026", "Value Proposition", "+5.7% new", "−44% RPV on SMS",
     "Right asset, wrong audience: a PDP founder tile that converts cold visitors while taxing loyal ones. The segment read became a targeting brief."),
    ("step-one-trust-signals", "Trust Signals on the Lead Image", "Step One",
     "US · Oct 2025", "Trust Signals", "+8.5% CVR", "3-variant ladder",
     "Trustpilot → +render → +USP icons: a laddered test that asked how much trust signal pays, not just whether it works."),
    ("step-one-payment-methods", "Payment Methods on the PDP", "Step One",
     "UK · Oct 2025", "Payment & Anxiety", "+5.6% CVR", "implemented",
     "Financing anxiety answered upstream of the cart — payment visibility at the point of decision, not checkout."),
    ("step-one-bundle-builder", "Mixed-Colours Bundle Builder", "Step One",
     "AU + UK · Oct 2025", "Friction Reduction", "+19.1% CVR", "won both markets",
     "Killing the page-hops inside the bundle journey — +19.1% in AU, +5.6% in the UK, same week, same verdict."),
    ("nine-intro-offer-pricing", "Intro Offer Pricing", "Nine Entertainment",
     "SMH · The Age · AFR · Nov–Dec 2023", "Pricing", "2,751", "subscriptions acquired",
     "A three-channel flash-sale programme across paywall, email and landing page — different price points win on different paywall types."),
    ("nine-personalised-retention", "Personalised Pricing &amp; Retention", "Nine Entertainment",
     "All mastheads · FY22–FY24", "Pricing", "$400–530K", "modelled annual revenue",
     "Churn-propensity-tiered renewal pricing — and the pivot to randomised testing when the model's precision fell short."),
    ("nine-social-ribbon", "Social Ribbon: Removing the Timer", "Nine Entertainment",
     "AFR · CRO-30.0-2312", "Friction Reduction", "+33%", "conversion",
     "One variable — the 30-second auto-dismiss timer removed. Expiry friction was costing engagement, not creating urgency."),
    ("nine-multi-package-paywall", "Multi-Package Paywall", "Nine Entertainment",
     "SMH · The Age · CRO-73/74.0-2404", "Pricing", "+102%", "The Age conversions",
     "Three prices instead of take-it-or-leave-it: +70% conversions at SMH, +102% at The Age, both at 100% winning probability."),
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
    for slug, title, client, period, category, metric, sub, blurb in INDEX_ROWS:
        b_cls = "b-" + re.sub(r"[^a-z0-9]+", "-", category.lower()).strip("-")
        cards.append(f"""<a class="card" href="{slug}.html">
  <div class="c-top"><span class="c-client">{client}</span><span class="c-period">{period}</span></div>
  <div class="c-badge {b_cls}"><span class="b-dot"></span>{category}</div>
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
.card{display:flex;flex-direction:column;border-right:1px solid var(--line);border-bottom:1px solid var(--line);
  padding:26px 26px 22px;background:var(--sheet);border-bottom-color:var(--line)}
.card:hover{background:#fdfcf7}
.card{border-bottom:1px solid var(--line)!important}
.c-top{display:flex;justify-content:space-between;gap:12px;font:500 11.5px/1.3 var(--mono);
  letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin-bottom:14px}
.c-client{color:var(--accent)}
.c-badge{display:inline-flex;align-items:center;gap:6.5px;font:500 10.5px/1 var(--mono);
  letter-spacing:.08em;text-transform:uppercase;color:var(--ink-2);background:var(--paper-2);
  border:1px solid var(--line);padding:4px 8px;border-radius:2px;margin-bottom:14px;
  width:fit-content}
.b-dot{width:6.5px;height:6.5px;border-radius:50%;display:inline-block;flex:0 0 6.5px}
.b-pricing .b-dot{background:#b8860b}
.b-trust-signals .b-dot{background:#0b5c4d}
.b-social-proof .b-dot{background:#1d4ed8}
.b-ux-layout .b-dot{background:#6d28d9}
.b-friction-reduction .b-dot{background:#c2410c}
.b-value-proposition .b-dot{background:#9f1239}
.b-navigation-mobile .b-dot{background:#0f766e}
.b-payment-anxiety .b-dot{background:#92400e}
.b-technical-cro .b-dot{background:#475569}
.c-title{font:400 25px/1.15 var(--display);letter-spacing:-.01em;margin:0 0 12px;color:var(--ink)}
.c-blurb{font:400 15px/1.55 var(--sans);color:var(--muted);margin:0 0 20px;max-width:52ch;flex-grow:1}
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
    npx_bin = "npx.cmd" if sys.platform == "win32" else "npx"
    use_shell = sys.platform == "win32"
    for f in sorted(glob.glob(os.path.join(SRC, "*.html"))):
        subprocess.run(
            [npx_bin, "--yes", f"staticrypt@{STATICRYPT_VERSION}", f,
             "-d", BUILD, "--short", "-s", STATICRYPT_SALT,
             "--remember", "30",
             "--template-title", "Protected — Case Studies"],
            check=True, env=env, shell=use_shell,
            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        print(f"  encrypted {os.path.basename(f)}")
    subprocess.run([sys.executable, os.path.join(ROOT, "pre_publish.py")], check=True)
    return True


# ------------------------------------------------------------------------ main
def main():
    os.makedirs(SRC, exist_ok=True)
    made = [build_index()]
    for p in PAGES:
        src = os.path.join(CASES, p["source"]) if p["source"] else os.path.join(SRC, p["slug"] + ".md")
        if os.path.exists(src):
            made.append(build_page(p))
        else:
            print(f"  skip (source missing) {p['slug']}")
    for f in made:
        print(f"  built {os.path.relpath(f, ROOT)}  ({os.path.getsize(f):,} bytes)")
    if encrypt_all():
        print(f"  publish build/*.html -> case-studies/ (never src/)")
    return made


if __name__ == "__main__":
    main()
