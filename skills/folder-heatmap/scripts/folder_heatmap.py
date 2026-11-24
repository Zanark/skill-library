"""Generate a local, review-only directory-size treemap using the standard library."""

import argparse
import csv
import heapq
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import time
import webbrowser
from datetime import datetime


def scan(root):
    root = Path(root).absolute()
    info = root.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
        raise ValueError(f"Scan root must not be a link or reparse point: {root}")
    if not stat.S_ISDIR(info.st_mode):
        raise ValueError(f"Scan root must be a directory: {root}")
    nodes = []
    errors = []
    skipped = []
    started = datetime.now().astimezone().isoformat()
    stack = [(str(root), -1)]
    last_progress = time.monotonic()
    while stack:
        path, parent = stack.pop()
        index = len(nodes)
        node = dict(name=os.path.basename(path), parent=parent, size=0,
                    direct=0, files=0, directFiles=0, children=[], largest=[])
        nodes.append(node)
        if parent >= 0:
            nodes[parent]["children"].append(index)
        try:
            with os.scandir(path) as entries:
                for entry in entries:
                    try:
                        info = entry.stat(follow_symlinks=False)
                        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                            skipped.append(dict(path=entry.path, reason="Reparse point/link not followed"))
                        elif stat.S_ISDIR(info.st_mode):
                            stack.append((entry.path, index))
                        elif stat.S_ISREG(info.st_mode):
                            size = info.st_size
                            node["direct"] += size
                            node["directFiles"] += 1
                            candidate = (size, entry.name)
                            if len(node["largest"]) < 20:
                                heapq.heappush(node["largest"], candidate)
                            elif candidate > node["largest"][0]:
                                heapq.heapreplace(node["largest"], candidate)
                    except OSError as exc:
                        errors.append(dict(path=entry.path, error=str(exc)))
        except OSError as exc:
            errors.append(dict(path=path, error=str(exc)))
        if time.monotonic() - last_progress > 20:
            print(f"Scanned {len(nodes):,} folders; currently {path}", flush=True)
            last_progress = time.monotonic()
    for node in reversed(nodes):
        node["size"] += node["direct"]
        node["files"] += node["directFiles"]
        node["largest"].sort(reverse=True)
        if node["parent"] >= 0:
            parent = nodes[node["parent"]]
            parent["size"] += node["size"]
            parent["files"] += node["files"]
    return dict(root=str(root), started=started,
                finished=datetime.now().astimezone().isoformat(),
                nodes=nodes, errors=errors, skipped=skipped)


HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'">
<title>Folder heatmap | Space review</title>
<style>
:root{color-scheme:dark;font:15px system-ui,sans-serif;background:#10151d;color:#e5edf7}
*{box-sizing:border-box}body{max-width:1600px;margin:auto;padding:28px}
h1{font-size:30px;margin:6px 0}h2{font-size:19px}p{line-height:1.55}
.muted{color:#a7b6c8}.cards{display:flex;gap:14px;flex-wrap:wrap;margin:22px 0}
.card{background:#1b2533;border:1px solid #344155;padding:16px 22px;border-radius:10px;flex:1}
.value{display:block;font-size:27px;font-weight:700;margin-bottom:4px}
button,input,select{font:inherit;background:#1b2533;color:inherit;border:1px solid #52647b;border-radius:6px;padding:8px 12px}
button{cursor:pointer}button:hover{background:#30445e}button:disabled{opacity:.4;cursor:default}
.toolbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:14px 0}
#path{overflow-wrap:anywhere;flex:1;font-family:Consolas,monospace;font-size:14px}
#map{height:530px;position:relative;background:#0b1017;border-radius:9px;overflow:hidden}
.tile{position:absolute;border:2px solid #10151d;border-radius:6px;padding:10px;overflow:hidden;text-align:left;line-height:1.5;color:white}
.tile strong{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.tile small{display:block;color:#f0f3f8}.tile:hover{filter:brightness(1.15);z-index:1;outline:2px solid white}
.tile.tiny{padding:0;border-width:1px}
.note{padding:13px 17px;border-left:3px solid #e6b96c;background:#241f19;border-radius:4px}
.scroll{overflow:auto;max-height:620px;border:1px solid #344155;border-radius:8px}
table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}
th,td{padding:10px 12px;text-align:right;border-bottom:1px solid #2d3849}
th:first-child,td:first-child{text-align:left;overflow-wrap:anywhere}
th{position:sticky;top:0;background:#1b2533;z-index:1}td button{border:0;padding:0;background:none;color:#9fd7ff;text-align:left}
th button{border:0;background:none;padding:0;text-align:inherit;font-weight:700;width:100%;white-space:nowrap}
th button:focus-visible{outline:2px solid #9fd7ff;outline-offset:4px}
td button:hover{background:none;text-decoration:underline}.bar{height:5px;background:#ed945c;border-radius:4px;margin-top:5px}
details{margin-top:20px}summary{cursor:pointer}pre{white-space:pre-wrap;overflow-wrap:anywhere}
#selection{font-weight:600;color:#ffd2a0}
@media(max-width:650px){body{padding:14px}#map{height:430px}.card{padding:12px}.value{font-size:23px}th,td{padding:9px 7px}}
</style></head><body>
<div class="muted">LOCAL STORAGE / REVIEW ONLY</div><h1>Folder space heatmap</h1>
<p class="muted">Bigger tiles mean more file bytes. Warmer tiles identify larger items in the current folder.
Click a folder to drill down; use the table to reach even the smallest folders. No deletion controls.</p>
<div class="cards">
<div class="card"><span id="total" class="value"></span>Total file size</div>
<div class="card"><span id="folders" class="value"></span>Folders scanned</div>
<div class="card"><span id="files" class="value"></span>Files counted</div>
<div class="card"><span id="issues" class="value"></span>Read errors / skipped links</div>
</div>
<p class="note">Read-only, non-atomic snapshot including hidden folders, .git, dependencies and build outputs.
Sizes are logical file bytes (GiB = 1,073,741,824 bytes), not allocated disk space or guaranteed deletion savings.
Hard-linked copies are counted per path. Junctions, symlinks and other reparse points are excluded to avoid crossing directory boundaries.
Other sessions may change files during or after the scan.</p>
<p id="timestamp" class="muted"></p>
<div class="toolbar"><button id="home">Home</button><button id="up">Up one folder</button><span id="path"></span></div>
<div id="map" aria-label="Interactive folder-size treemap"></div>
<p id="selection" aria-live="polite"></p>
<div class="toolbar"><h2 style="margin-right:auto">Items in this folder</h2>
<input id="filter" type="search" placeholder="Filter names or full paths" aria-label="Filter names or full paths">
<select id="scope" aria-label="Search scope"><option value="current">Current folder</option><option value="all">All folders</option></select>
</div>
<p id="tableNote" class="muted"></p>
<p class="muted">Default: size descending. Click a new column once for ascending, again for descending. Clicking the active descending column switches to ascending.</p>
<div class="scroll"><table id="folderTable"><thead><tr>
<th scope="col"><button data-sort="name">Folder / item</button></th>
<th scope="col"><button data-sort="size">Size</button></th>
<th scope="col"><button data-sort="percent">% of parent</button></th>
<th scope="col"><button data-sort="files">Files</button></th>
</tr></thead><tbody id="rows"></tbody></table></div>
<h2>Largest files directly in this folder</h2>
<p class="muted">Up to 20 files, not a recursive list. Navigate into subfolders to inspect their largest direct files.</p>
<div class="scroll"><table id="fileTable"><thead><tr>
<th scope="col"><button data-sort="name">Full file path</button></th>
<th scope="col"><button data-sort="size">Size</button></th>
</tr></thead><tbody id="fileRows"></tbody></table></div>
<details><summary id="errorSummary"></summary><pre id="errorList"></pre></details>
<details><summary id="skipSummary"></summary><pre id="skipList"></pre></details>
<script id="snapshot" type="application/json">__DATA__</script>
<script>
'use strict';
const data=JSON.parse(document.getElementById('snapshot').textContent), nodes=data.nodes;
const $=id=>document.getElementById(id);
let current=0;
const folderSort={key:'size',direction:-1}, fileSort={key:'size',direction:-1};
const fmt=n=>{if(n===0)return '0 B';const u=['B','KiB','MiB','GiB','TiB'];const i=Math.min(4,Math.floor(Math.log(n)/Math.log(1024)));return (n/1024**i).toLocaleString(undefined,{maximumFractionDigits:2})+' '+u[i]};
const paths=nodes.map((n,i)=>i===0?data.root:'');
const separator=data.root.includes('\\')?'\\':'/';
const join=(base,name)=>base.replace(/[\\/]$/,'')+separator+name;
for(let i=1;i<nodes.length;i++)paths[i]=join(paths[nodes[i].parent],nodes[i].name);
document.title=nodes[0].name+' | Folder space review';
function sortItems(list,state){
 return list.sort((a,b)=>{
  const result=state.key==='name'?a.name.localeCompare(b.name):a[state.key]-b[state.key];
  return state.direction*result||a.name.localeCompare(b.name);
 });
}
function updateHeaders(id,state){
 for(const b of $(id).querySelectorAll('th button[data-sort]')){
  const active=b.dataset.sort===state.key;
  b.parentElement.setAttribute('aria-sort',active?(state.direction===1?'ascending':'descending'):'none');
  b.textContent=b.dataset.label+(active?(state.direction===1?' [asc]':' [desc]'):'');
 }
}
function items(id){
 const n=nodes[id], result=n.children.map(i=>({id:i,name:nodes[i].name,size:nodes[i].size,files:nodes[i].files}));
 if(n.directFiles)result.push({id:-1,name:'[Files directly in this folder]',size:n.direct,files:n.directFiles});
 return result.sort((a,b)=>b.size-a.size||a.name.localeCompare(b.name));
}
function navigate(id){current=id;$('filter').value='';$('scope').value='current';render()}
function table(){
 const all=$('scope').value==='all', q=$('filter').value.toLowerCase();
 let list=all?nodes.map((n,i)=>({id:i,name:paths[i],size:n.size,files:n.files})):items(current);
 list=list.filter(x=>x.name.toLowerCase().includes(q)).map(x=>{
  const parent=all?(x.id===0?nodes[0]:nodes[nodes[x.id].parent]):nodes[current];
  return {...x,percent:parent.size?100*x.size/parent.size:0};
 });
 sortItems(list,folderSort);updateHeaders('folderTable',folderSort);
 $('tableNote').textContent=(all?'All-folder results overlap: parents include their descendants. Do not add these rows together. ':'Folder totals include every descendant. Direct files are a separate item. ')+
 'Showing '+Math.min(1000,list.length).toLocaleString()+' of '+list.length.toLocaleString()+' matching items; sorted before limiting. Use filters to reach omitted rows.';
 const fragment=document.createDocumentFragment();
 for(const x of list.slice(0,1000)){
  const tr=document.createElement('tr'), name=document.createElement('td');
  if(x.id>=0){const b=document.createElement('button');b.textContent=x.name;b.title=paths[x.id];b.onclick=()=>navigate(x.id);name.append(b)}
  else name.textContent=x.name;
  tr.append(name);
  const pct=x.percent;
  for(const v of [fmt(x.size),pct.toFixed(2)+'%',x.files.toLocaleString()]){const td=document.createElement('td');td.textContent=v;tr.append(td)}
  const bar=document.createElement('div');bar.className='bar';bar.style.width=Math.max(0,Math.min(100,pct))+'%';name.append(bar);fragment.append(tr);
 }
 $('rows').replaceChildren(fragment);
}
function draw(){
 const map=$('map');map.replaceChildren();
 const list=items(current).filter(x=>x.size>0), max=list[0]?.size||1;
 function layout(entries,x,y,w,h){
  if(!entries.length)return;
  if(entries.length===1){
   const item=entries[0], b=document.createElement('button');
   b.className='tile'+(w<85||h<52?' tiny':'');b.style.cssText=`left:${x}px;top:${y}px;width:${Math.max(0,w)}px;height:${Math.max(0,h)}px;background:hsl(${36-30*Math.sqrt(item.size/max)} 57% ${30+9*(1-item.size/max)}%)`;
   b.title=(item.id<0?join(paths[current],'[direct files]'):paths[item.id])+'\n'+fmt(item.size)+' | '+item.size.toLocaleString()+' bytes';
   b.setAttribute('aria-label',item.name+', '+fmt(item.size));
   if(w>=85&&h>=52){const name=document.createElement('strong');name.textContent=item.name;b.append(name);const size=document.createElement('small');size.textContent=fmt(item.size)+' / '+(100*item.size/nodes[current].size).toFixed(1)+'%';b.append(size)}
   b.onclick=()=>{if(item.id>=0)navigate(item.id);else{$('selection').textContent=fmt(item.size)+' in '+item.files.toLocaleString()+' direct files. Largest direct files are listed below.';$('fileRows').scrollIntoView({behavior:'smooth',block:'center'})}};
   map.append(b);return;
  }
  const total=entries.reduce((s,e)=>s+e.size,0);let split=1,acc=entries[0].size;
  while(split<entries.length-1 && Math.abs(acc+entries[split].size-total/2)<Math.abs(acc-total/2)){acc+=entries[split].size;split++}
  const f=acc/total;
  if(w>=h){layout(entries.slice(0,split),x,y,w*f,h);layout(entries.slice(split),x+w*f,y,w*(1-f),h)}
  else{layout(entries.slice(0,split),x,y,w,h*f);layout(entries.slice(split),x,y+h*f,w,h*(1-f))}
 }
 layout(list,0,0,map.clientWidth,map.clientHeight);
 if(!list.length){const p=document.createElement('p');p.textContent='No counted file bytes in this folder. See the table and read-error list for details.';map.append(p)}
}
function fileTable(){
 const list=nodes[current].largest.map(([size,name])=>({size,name}));
 sortItems(list,fileSort);updateHeaders('fileTable',fileSort);
 const fragment=document.createDocumentFragment();
 for(const {size,name} of list){const tr=document.createElement('tr');for(const v of [join(paths[current],name),fmt(size)]){const td=document.createElement('td');td.textContent=v;tr.append(td)}fragment.append(tr)}
 $('fileRows').replaceChildren(fragment);
}
function render(){
 const n=nodes[current];$('path').textContent=paths[current];$('up').disabled=current===0;
 $('selection').textContent=fmt(n.size)+' | '+n.files.toLocaleString()+' files | '+n.children.length.toLocaleString()+' immediate subfolders';
 fileTable();table();draw();
}
$('total').textContent=fmt(nodes[0].size);$('folders').textContent=nodes.length.toLocaleString();$('files').textContent=nodes[0].files.toLocaleString();$('issues').textContent=data.errors.length+' / '+data.skipped.length;
$('timestamp').textContent='Scan started: '+data.started+' | Finished: '+data.finished;
$('errorSummary').textContent='Read errors ('+data.errors.length+')'+(data.errors.length?' - totals may be incomplete':'');
$('errorList').textContent=data.errors.map(e=>e.path+'\n'+e.error).join('\n\n')||'None recorded.';
$('skipSummary').textContent='Excluded reparse points / links ('+data.skipped.length+')';
$('skipList').textContent=data.skipped.map(e=>e.path+'\n'+e.reason).join('\n\n')||'None recorded.';
$('home').onclick=()=>navigate(0);$('up').onclick=()=>{if(current)navigate(nodes[current].parent)};
$('filter').oninput=table;$('scope').onchange=table;
for(const [id,state,redraw] of [['folderTable',folderSort,table],['fileTable',fileSort,fileTable]]){
 for(const b of $(id).querySelectorAll('th button[data-sort]')){
  b.dataset.label=b.textContent;
  b.onclick=()=>{
   const key=b.dataset.sort;
   state.direction=state.key===key?-state.direction:1;
   state.key=key;redraw();
  };
 }
}
let resize;window.addEventListener('resize',()=>{clearTimeout(resize);resize=setTimeout(draw,100)});
render();
</script></body></html>"""


def save(data, output):
    output = Path(output).resolve()
    root = Path(data["root"]).resolve()
    if output == root or root in output.parents:
        raise ValueError("Report output must be outside the scanned directory to avoid counting its own reports.")
    nodes = data["nodes"]
    if not nodes or nodes[0]["size"] != sum(n["direct"] for n in nodes):
        raise ValueError("Snapshot byte totals do not reconcile.")
    if nodes[0]["files"] != sum(n["directFiles"] for n in nodes):
        raise ValueError("Snapshot file counts do not reconcile.")
    for node in nodes:
        if node["size"] != node["direct"] + sum(nodes[i]["size"] for i in node["children"]):
            raise ValueError("Snapshot child byte totals do not reconcile.")
    output.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(data, ensure_ascii=True, separators=(",", ":"))
    (output / "snapshot.json").write_text(encoded, encoding="utf-8")
    (output / "index.html").write_text(
        HTML.replace("__DATA__", encoded.replace("<", "\\u003c")), encoding="utf-8")
    paths = []
    with (output / "folder-sizes.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Full path", "Total bytes", "GiB", "Recursive file count",
                         "Direct file bytes", "Direct file count"])
        for i, node in enumerate(nodes):
            path = data["root"] if i == 0 else str(Path(paths[node["parent"]]) / node["name"])
            paths.append(path)
            writer.writerow([path, node["size"], f'{node["size"] / 1024**3:.6f}',
                             node["files"], node["direct"], node["directFiles"]])
    return dict(report=str(output / "index.html"), bytes=nodes[0]["size"],
                          gib=round(nodes[0]["size"] / 1024**3, 2),
                          folders=len(nodes), files=nodes[0]["files"],
                          errors=len(data["errors"]), skipped=len(data["skipped"]),
                          largestFolders=[dict(name=nodes[i]["name"],
                                               gib=round(nodes[i]["size"] / 1024**3, 2))
                                          for i in sorted(nodes[0]["children"],
                                                          key=lambda i: nodes[i]["size"],
                                                          reverse=True)[:10]],
                          largestRootFiles=nodes[0]["largest"])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Directory to scan; defaults to the current directory.")
    parser.add_argument("--output", type=Path, help="Report directory outside the scan root. Reuse it to refresh.")
    parser.add_argument("--open", action="store_true", help="Open the completed local HTML report in the default browser.")
    args = parser.parse_args(argv)
    root = args.root.absolute()
    output = args.output or (Path(tempfile.gettempdir()) / "folder-heatmap" /
                             datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
    try:
        resolved_output = output.resolve()
        resolved_root = root.resolve()
        if resolved_output == resolved_root or resolved_root in resolved_output.parents:
            raise ValueError("Report output must be outside the scanned directory.")
        data = scan(root)
        result = save(data, output)
        result["status"] = "partial" if data["errors"] else "complete"
        print(json.dumps(result, indent=2), flush=True)
        if args.open and not webbrowser.open(Path(result["report"]).as_uri()):
            raise RuntimeError(f"Could not open browser; open the report manually: {result['report']}")
        return 2 if data["errors"] else 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Folder heatmap failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
