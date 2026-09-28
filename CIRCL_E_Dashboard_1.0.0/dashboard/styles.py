"""Restrained presentation constants and CSS for the CIRCL-E dashboard.

Kept deliberately small: no gradients, glow, animation or marketing hero. The
only DOM-level rules hide Streamlit's own toolbar/footer chrome; they are
version-sensitive cosmetic hooks, so the app still works (showing the toolbar
again) if a Streamlit upgrade stops matching them.
"""
from __future__ import annotations

#: Software product version. This is the *dashboard* version and is deliberately
#: separate from the frozen scientific/model release identifier in the release
#: manifest.
DASHBOARD_VERSION = "1.0.0"

APP_TITLE = "CIRCL-E"
APP_SUBTITLE = "Device identity and circular-economy evidence from one image."

#: Quiet, honest disclosure shown only in About/Technical details.
MODEL_RELEASE_NOTE = "Research/decision-support model release."

DIMENSION_ORDER = ("RRP", "WRO", "CSO", "TPC", "IRP")

CSS = """
<style>
[data-testid="stToolbar"] {visibility: hidden;}
footer {visibility: hidden;}

.block-container {max-width: 1180px; padding-top: 2.0rem; padding-bottom: 2.4rem;}
h3, h4 {margin-top: 0.55rem; margin-bottom: 0.35rem;}
[data-testid="stExpander"] {margin-top: 0.25rem;}
[data-testid="stTabs"] [data-baseweb="tab-list"] {gap: 0.35rem;}

.ce-hero h1 {margin: 0; font-size: 1.9rem; line-height: 1.15;}
.ce-sub {font-size: 0.97rem; opacity: 0.8; margin-top: 0.15rem;}

.ce-card {border:1px solid rgba(128,128,128,0.35); border-radius:10px;
  padding:0.55rem 0.7rem; height:100%;}
.ce-label {font-size:0.68rem; text-transform:uppercase; letter-spacing:0.06em;
  opacity:0.62; margin-bottom:0.16rem;}
.ce-value {font-size:0.98rem; font-weight:600; line-height:1.25; word-break:break-word;
  overflow-wrap:anywhere;}
.ce-value-lg {font-size:1.15rem;}
.ce-meta {font-size:0.72rem; opacity:0.68; margin-top:0.2rem;}

.ce-card-row {display:flex; flex-wrap:wrap; gap:0.5rem; margin-bottom:0.35rem;}
.ce-card-row > .ce-card {flex:1 1 var(--ce-card-min, 9rem); min-width:var(--ce-card-min, 9rem);
  box-sizing:border-box;}

.ce-headline {font-size:1.6rem; font-weight:650; line-height:1.2; word-break:break-word;}
.ce-headline-detail {font-size:0.84rem; opacity:0.72; margin-top:0.2rem;}

.ce-pill {display:inline-block; font-size:0.84rem; font-weight:600;
  padding:0.14rem 0.6rem; border-radius:999px; border:1px solid rgba(128,128,128,0.5);}
.ce-pill-ok {border-color:rgba(46,160,67,0.75); background:rgba(46,160,67,0.13);}
.ce-pill-warn {border-color:rgba(210,153,34,0.85); background:rgba(210,153,34,0.15);}
.ce-pill-bad {border-color:rgba(218,54,51,0.85); background:rgba(218,54,51,0.15);}
.ce-pill-neutral {border-color:rgba(128,128,128,0.5); background:rgba(128,128,128,0.10);}

.ce-muted {font-size:0.79rem; opacity:0.72; margin-top:0.15rem;}
.ce-placeholder {border:1px dashed rgba(128,128,128,0.5); border-radius:10px;
  padding:0.9rem 1.05rem;}
.ce-placeholder-title {font-weight:600; margin-bottom:0.3rem;}
</style>
"""
