"""`skill web` — read-only local dashboard over the repo's own data
(registry, manifests, results JSONL). Stdlib only; binds to localhost."""

from __future__ import annotations

import json
import pathlib
import re
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .evals.results import all_runs, run_summary
from .manifest import load_all

SAFE = re.compile(r"^[A-Za-z0-9._-]+$")


def _catalog(repo_root: pathlib.Path) -> dict:
    skills = []
    for m in load_all(repo_root):
        runs = all_runs(repo_root, m.name)
        # The most recent run isn't always the most informative (triggers-only
        # runs have no comparisons) — merge the latest of each kind.
        latest = None
        for p in reversed(runs):
            s = run_summary(p)
            if latest is None:
                latest = s
            else:
                if not latest["comparisons"] and s["comparisons"]:
                    latest["comparisons"] = s["comparisons"]
                    latest["cases"] = s["cases"]
                if latest["triggers"] is None and s["triggers"] is not None:
                    latest["triggers"] = s["triggers"]
            if latest["comparisons"] and latest["triggers"] is not None:
                break
        skills.append({
            "name": m.name, "description": m.description, "version": m.version,
            "owner": m.owner, "status": m.status, "tags": m.tags,
            "execution_cases": len(m.execution_cases()),
            "has_triggers": m.triggers_file() is not None,
            "run_count": len(runs), "latest": latest,
        })
    return {"repo": str(repo_root), "skills": skills}


def _skill_detail(repo_root: pathlib.Path, name: str) -> dict | None:
    for m in load_all(repo_root):
        if m.name == name:
            return {
                "name": m.name, "description": m.description, "version": m.version,
                "owner": m.owner, "status": m.status, "tags": m.tags,
                "body": m.body,
                "runs": [run_summary(p) for p in reversed(all_runs(repo_root, name))],
            }
    return None


class Handler(BaseHTTPRequestHandler):
    repo_root: pathlib.Path  # set by serve()

    def do_GET(self):  # noqa: N802
        try:
            if self.path == "/" or self.path == "/index.html":
                self._send(200, PAGE, "text/html; charset=utf-8")
            elif self.path == "/api/catalog":
                self._json(_catalog(self.repo_root))
            elif self.path.startswith("/api/skill/"):
                name = self.path.rsplit("/", 1)[-1]
                if not SAFE.match(name):
                    return self._json({"error": "bad name"}, 400)
                detail = _skill_detail(self.repo_root, name)
                self._json(detail or {"error": "not found"}, 200 if detail else 404)
            else:
                self._send(404, "not found", "text/plain")
        except Exception as e:  # surface errors to the page, not a dead socket
            self._json({"error": str(e)}, 500)

    def _json(self, obj, status=200):
        self._send(status, json.dumps(obj), "application/json")

    def _send(self, status, body: str, ctype: str):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


def serve(repo_root: pathlib.Path, port: int = 7787, open_browser: bool = True) -> None:
    Handler.repo_root = repo_root
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}"
    print(f"skilldeck dashboard: {url}  (ctrl-c to stop)")
    if open_browser:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


PAGE = r"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>skilldeck</title>
<style>
:root{
  color-scheme:light;
  --page:#f9f9f7; --surface:#fcfcfb; --ink:#0b0b0b; --ink-2:#52514e; --muted:#898781;
  --grid:#e1e0d9; --baseline:#c3c2b7; --border:rgba(11,11,11,.10);
  --good:#0ca30c; --good-text:#006300; --critical:#d03b3b; --tie:#898781;
}
:root[data-theme="dark"]{
  color-scheme:dark;
  --page:#0d0d0d; --surface:#1a1a19; --ink:#ffffff; --ink-2:#c3c2b7; --muted:#898781;
  --grid:#2c2c2a; --baseline:#383835; --border:rgba(255,255,255,.10);
  --good-text:#0ca30c; --critical:#e66767;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    color-scheme:dark;
    --page:#0d0d0d; --surface:#1a1a19; --ink:#ffffff; --ink-2:#c3c2b7; --muted:#898781;
    --grid:#2c2c2a; --baseline:#383835; --border:rgba(255,255,255,.10);
    --good-text:#0ca30c; --critical:#e66767;
  }
}
*{box-sizing:border-box;margin:0}
body{font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;background:var(--page);color:var(--ink)}
header{display:flex;align-items:baseline;gap:12px;padding:14px 20px;border-bottom:1px solid var(--grid)}
header h1{font-size:16px;font-weight:650}
header .repo{color:var(--muted);font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1}
header button{background:none;border:1px solid var(--border);border-radius:6px;color:var(--ink-2);padding:3px 10px;cursor:pointer;font:inherit;font-size:12px}
.layout{display:flex;min-height:calc(100vh - 49px)}
nav{width:280px;flex-shrink:0;border-right:1px solid var(--grid);padding:12px}
nav .sk{display:block;width:100%;text-align:left;background:none;border:0;border-radius:8px;padding:10px 12px;cursor:pointer;color:var(--ink);font:inherit}
nav .sk:hover{background:var(--surface)}
nav .sk.on{background:var(--surface);outline:1px solid var(--border)}
nav .sk .nm{font-weight:600}
nav .sk .mt{color:var(--muted);font-size:12px}
main{flex:1;padding:20px 24px;max-width:960px;min-width:0}
.badge{display:inline-flex;align-items:center;gap:5px;font-size:11px;color:var(--ink-2);border:1px solid var(--border);border-radius:999px;padding:1px 8px;vertical-align:2px}
.badge .dot{width:7px;height:7px;border-radius:50%;background:var(--baseline)}
.badge.verified .dot{background:var(--good)}
h2{font-size:20px;font-weight:650;margin-bottom:2px}
.desc{color:var(--ink-2);max-width:70ch}
.meta{color:var(--muted);font-size:12px;margin:4px 0 18px}
.tiles{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:22px}
.tile{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:12px 16px;min-width:150px}
.tile .lb{font-size:12px;color:var(--ink-2)}
.tile .vl{font-size:26px;font-weight:600;margin-top:2px}
.tile .dl{font-size:12px;color:var(--muted);margin-top:2px}
.tile .vl.up{color:var(--good-text)} .tile .vl.down{color:var(--critical)}
h3{font-size:13px;font-weight:650;color:var(--ink-2);text-transform:uppercase;letter-spacing:.04em;margin:22px 0 8px}
table{border-collapse:collapse;width:100%;background:var(--surface);border:1px solid var(--border);border-radius:10px;overflow:hidden}
th{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);text-align:left;font-weight:600}
th,td{padding:8px 12px;border-bottom:1px solid var(--grid)}
tr:last-child td{border-bottom:0}
td{font-variant-numeric:tabular-nums}
.wlt{display:flex;align-items:center;gap:8px}
.wlt .bar{display:flex;gap:2px;width:120px;height:10px}
.wlt .seg{border-radius:2px}
.wlt .seg.w{background:var(--good)} .wlt .seg.l{background:var(--critical)} .wlt .seg.t{background:var(--tie)}
.wlt .tx{font-size:12px;color:var(--ink-2);white-space:nowrap}
.fail{color:var(--ink-2);font-size:13px;padding:2px 0}
.fail b{color:var(--critical);font-weight:600;font-size:11px;letter-spacing:.03em}
details{margin-top:6px}
summary{cursor:pointer;color:var(--muted);font-size:12px}
.case-r{font-size:13px;padding:6px 0;border-bottom:1px solid var(--grid)}
.case-r:last-child{border-bottom:0}
.case-r .oc{font-weight:600}
.case-r .oc.win{color:var(--good-text)} .case-r .oc.loss{color:var(--critical)} .case-r .oc.tie{color:var(--muted)}
.case-r .rs{color:var(--muted)}
pre.body{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:16px;white-space:pre-wrap;font:12.5px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--ink-2);overflow-x:auto}
.empty{color:var(--muted);padding:24px 0}
</style></head><body>
<header><h1>skilldeck</h1><span class="repo" id="repo"></span>
<button id="theme">theme</button></header>
<div class="layout"><nav id="nav"></nav><main id="main"><div class="empty">loading…</div></main></div>
<script>
const $=(s,el)=>(el||document).querySelector(s);
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
let CAT=null,CUR=null;
const root=document.documentElement;
$("#theme").onclick=()=>{
  const dark=matchMedia("(prefers-color-scheme: dark)").matches;
  const now=root.dataset.theme||(dark?"dark":"light");
  root.dataset.theme=now==="dark"?"light":"dark";
};
const pct=v=>v==null?"–":Math.round(v*100)+"%";
const lift=v=>(v>0?"+":"")+Math.round(v*100)+"%";
const stamp=f=>{const m=f.match(/^(\d{4})(\d\d)(\d\d)T(\d\d)(\d\d)/);return m?`${m[1]}-${m[2]}-${m[3]} ${m[4]}:${m[5]}Z`:f};
function wlt(c){
  const n=c.win+c.loss+c.tie||1;
  const seg=(k,v)=>v?`<div class="seg ${k}" style="flex:${v}" title="${v}"></div>`:"";
  return `<div class="wlt"><div class="bar">${seg("w",c.win)}${seg("l",c.loss)}${seg("t",c.tie)}</div>
    <span class="tx">${c.win}W ${c.loss}L ${c.tie}T</span></div>`;
}
async function load(){
  CAT=await (await fetch("/api/catalog")).json();
  $("#repo").textContent=CAT.repo;
  renderNav();
  if(CAT.skills.length) select(CUR||CAT.skills[0].name);
  else $("#main").innerHTML='<div class="empty">no skills yet — try <code>skill new my-skill</code></div>';
}
function renderNav(){
  $("#nav").innerHTML=CAT.skills.map(s=>{
    const lb=s.latest&&s.latest.comparisons["candidate-vs-baseline"];
    return `<button class="sk${s.name===CUR?" on":""}" onclick="select('${s.name}')">
      <div class="nm">${esc(s.name)}</div>
      <div class="mt">${s.version} · ${s.status} · ${s.execution_cases} cases · ${s.run_count} runs${lb?` · ${lift(lb.net_lift)}`:""}</div>
    </button>`}).join("");
}
async function select(name){
  CUR=name; renderNav();
  const d=await (await fetch("/api/skill/"+name)).json();
  const cvb=(d.runs.find(r=>r.comparisons["candidate-vs-baseline"])||{comparisons:{}}).comparisons["candidate-vs-baseline"];
  const tr=(d.runs.find(r=>r.triggers)||{}).triggers;
  const tiles=[];
  if(cvb){const cls=cvb.net_lift>0?"up":cvb.net_lift<0?"down":"";
    const n=cvb.win+cvb.loss+cvb.tie;
    tiles.push(`<div class="tile"><div class="lb">Net lift vs baseline</div>
      <div class="vl ${cls}">${lift(cvb.net_lift)}</div>
      <div class="dl">${n} comparisons · p=${cvb.p.toFixed(3)}</div></div>`);}
  if(tr){tiles.push(`<div class="tile"><div class="lb">Trigger recall</div><div class="vl">${pct(tr.recall)}</div>
      <div class="dl">${tr.fn} missed of ${tr.tp+tr.fn}</div></div>`);
    tiles.push(`<div class="tile"><div class="lb">Trigger precision</div><div class="vl">${pct(tr.precision)}</div>
      <div class="dl">${tr.fp} false fire${tr.fp===1?"":"s"}</div></div>`);}
  const runs=d.runs.map(r=>{
    const c=r.comparisons["candidate-vs-baseline"];
    const t=r.triggers;
    const fails=(t?t.failures.map(f=>`<div class="fail"><b>${f.kind}</b> ${esc(f.prompt)}</div>`).join(""):"");
    const cases=r.cases.length?`<details><summary>${r.cases.length} case results</summary>${
      r.cases.map(x=>`<div class="case-r"><span class="oc ${x.outcome}">${x.outcome}</span>
        ${esc(x.case)} rep${x.rep} · ${esc(x.comparison)} · ${esc(x.decided_by)}
        ${x.reason?`<div class="rs">${esc(x.reason)}</div>`:""}</div>`).join("")}</details>`:"";
    const pv=r.meta.provenance||{};
    const at=pv.commit?("@"+pv.commit.slice(0,7)+(pv.dirty?"+dirty":"")):"?";
    return `<tr><td>${stamp(r.file)}</td><td>v${esc(r.meta.version||"?")} <span style="color:var(--muted)">${at}</span></td><td>${esc(r.meta.model||"–")}</td><td>${r.meta.k??"–"}</td>
      <td>${t?pct(t.recall)+" / "+pct(t.precision):"–"}</td>
      <td>${c?wlt(c):"–"}</td><td>${c?lift(c.net_lift):"–"}</td></tr>
      ${fails||cases?`<tr><td colspan="7">${fails}${cases}</td></tr>`:""}`;
  }).join("");
  $("#main").innerHTML=`
    <h2>${esc(d.name)} <span class="badge ${d.status}"><span class="dot"></span>${d.status}</span></h2>
    <div class="desc">${esc(d.description)}</div>
    <div class="meta">v${d.version} · ${esc(d.owner)} · ${d.tags.map(esc).join(", ")||"no tags"}</div>
    ${tiles.length?`<div class="tiles">${tiles.join("")}</div>`:'<div class="empty">no eval runs yet — <code>skill evals '+esc(d.name)+'</code></div>'}
    ${d.runs.length?`<h3>Eval runs</h3><table>
      <tr><th>Run</th><th>Skill</th><th>Model</th><th>k</th><th>Triggers R / P</th><th>Outcomes</th><th>Net lift</th></tr>
      ${runs}</table>`:""}
    <h3>Skill</h3><pre class="body">${esc(d.body)}</pre>`;
}
load();
</script></body></html>
"""
