#!/usr/bin/env python3
"""Build all TASK5 dashboard pages and the portfolio navigation shell."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "Task5" / "scripts"
DASHBOARD = ROOT / "Task5" / "dashboard"
OUTPUT = DASHBOARD / "index.html"

SHELL = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>Task 5 - Machine-Learning Case Studies</title>
  <style>
    :root{--navy:#17243b;--navy2:#223554;--ink:#172033;--muted:#667085;--line:#e6eaf0;--paper:#f5f7fb;--white:#fff;--orange:#d97706;--green:#2f855a;--blue:#315f9e;--shadow:0 18px 45px rgba(23,36,59,.12)}
    *{box-sizing:border-box}html,body{height:100%;margin:0}body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:var(--paper);color:var(--ink)}
    .app{display:grid;grid-template-columns:286px 1fr;height:100vh;overflow:hidden}.side{position:relative;padding:30px 22px 24px;color:#fff;background:linear-gradient(165deg,var(--navy),var(--navy2) 70%,#2e466c);overflow:auto}.side:after{content:"";position:absolute;width:220px;height:220px;border-radius:50%;right:-105px;bottom:-80px;background:rgba(217,119,6,.18)}
    .eyebrow{font:600 11px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;letter-spacing:.18em;text-transform:uppercase;color:#f2bc6b}.brand{margin:9px 0 8px;font-size:25px;line-height:1.32}.rule{height:1px;margin:24px 0 18px;background:rgba(255,255,255,.13)}
    .nav{display:grid;gap:9px;position:relative;z-index:1}.nav button{width:100%;border:1px solid transparent;border-radius:13px;padding:12px 13px;text-align:left;color:#dce4ef;background:transparent;cursor:pointer;transition:.18s ease}.nav button:hover{background:rgba(255,255,255,.08);color:#fff}.nav button.active{background:#fff;color:var(--navy);box-shadow:0 10px 24px rgba(7,15,28,.22)}.nav strong{display:block;font:650 14px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
    .main{min-width:0;display:flex;flex-direction:column}.top{display:flex;align-items:center;justify-content:space-between;gap:18px;padding:17px 26px;background:rgba(255,255,255,.94);border-bottom:1px solid var(--line)}.crumb{font:600 13px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#475467}.status{display:flex;align-items:center;gap:8px;padding:7px 11px;border-radius:999px;background:#fff7e8;color:#9a5a04;font:600 11px/1 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;border:1px solid #f3d39b}.frame-wrap{flex:1;min-height:0;padding:16px 18px 18px}.frame-card{height:100%;overflow:hidden;border:1px solid var(--line);border-radius:18px;background:#fff;box-shadow:var(--shadow)}iframe{display:block;width:100%;height:100%;border:0;background:#fff}
    @media(max-width:820px){.app{grid-template-columns:1fr;grid-template-rows:auto 1fr;overflow:auto}.side{padding:20px 16px 15px}.brand{font-size:21px}.rule{display:none}.nav{display:flex;gap:8px;overflow-x:auto;margin-top:15px;padding-bottom:2px}.nav button{min-width:150px;padding:10px 12px}.main{min-height:720px}.top{padding:12px 16px}.frame-wrap{padding:10px}.frame-card{border-radius:14px;height:calc(100vh - 230px);min-height:610px}}
  </style>
</head>
<body>
  <div class="app">
    <aside class="side">
      <div class="eyebrow">Quant Portfolio  -  Task 05</div>
      <h1 class="brand">Machine-Learning Case Studies</h1>
      <div class="rule"></div>
      <nav class="nav" aria-label="Task 5 pages">
        <button data-page="overview" data-src="pages/overview.html"><strong>01 Overview</strong></button>
        <button data-page="cancer" data-src="pages/cancer.html"><strong>02 Teaching Case</strong></button>
        <button data-page="finance" data-src="pages/finance.html"><strong>03 Financial Experiments</strong></button>
        <button data-page="catl" data-src="pages/catl.html"><strong>04 CATL Case</strong></button>
      </nav>
    </aside>
    <main class="main">
      <header class="top"><div class="crumb" id="crumb">Task 5 / Overview</div></header>
      <div class="frame-wrap"><div class="frame-card"><iframe id="view" title="TASK5 dashboard" src="pages/overview.html"></iframe></div></div>
    </main>
  </div>
  <script>
    const labels={overview:"Overview",cancer:"Teaching Case",finance:"Financial Experiments",catl:"CATL Case"};
    const buttons=[...document.querySelectorAll(".nav button")],frame=document.getElementById("view"),crumb=document.getElementById("crumb");
    function openPage(page,push=true){const button=buttons.find(x=>x.dataset.page===page)||buttons[0];buttons.forEach(x=>x.classList.toggle("active",x===button));frame.src=button.dataset.src;crumb.textContent="Task 5 / "+labels[button.dataset.page];document.title=labels[button.dataset.page]+" - Task 5 Machine-Learning Case Studies";if(innerWidth>820){document.querySelector(".side").scrollTop=0}else{const nav=document.querySelector(".nav");nav.scrollLeft=Math.max(0,button.offsetLeft-(nav.clientWidth-button.clientWidth)/2)}if(push)history.replaceState(null,"","#"+button.dataset.page)}
    buttons.forEach(button=>button.addEventListener("click",()=>openPage(button.dataset.page)));
    openPage(location.hash.slice(1)||"overview",false);
  </script>
</body>
</html>
'''


def main() -> None:
    DASHBOARD.mkdir(parents=True, exist_ok=True)
    for script in [
        "build_overview_dashboard.py",
        "build_cancer_dashboard.py",
        "build_finance_dashboard.py",
        "build_catl_dashboard.py",
    ]:
        subprocess.run([sys.executable, str(SCRIPT_DIR / script)], cwd=ROOT, check=True)
    OUTPUT.write_text(SHELL, encoding="utf-8")
    print(f"[done] TASK5 dashboard portfolio -> {OUTPUT}")


if __name__ == "__main__":
    main()
