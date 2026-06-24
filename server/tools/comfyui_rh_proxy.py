#!/usr/bin/env python3
"""ComfyUI → RunningHub Proxy - Multi-workflow support"""
import json, os, time, urllib.request, urllib.error, subprocess
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import JSONResponse, Response

# --- Config ---
RH_BASE = "https://www.runninghub.ai"
CURRENT = None

def rh_key():
    try: return open('/tmp/rh_key.txt').read().strip()
    except: return ""

def rh_call(ep, payload, timeout=30):
    key = rh_key()
    h = {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "Host": "www.runninghub.ai"}
    payload["apiKey"] = key
    req = urllib.request.Request(f"{RH_BASE}{ep}", data=json.dumps(payload).encode(), headers=h)
    try: return json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    except urllib.error.HTTPError as e: raise HTTPException(502, f"RH {e.code}: {e.read().decode()[:200]}")

# --- App ---
app = FastAPI(title="RH Proxy")

# Pre-load known workflows
known = {}
for wid in ["2069523159090552833"]:
    try:
        r = rh_call("/api/openapi/getJsonApiFormat", {"workflowId": wid})
        p = json.loads(r["data"]["prompt"])
        known[wid] = {"name": f"LTX ({len(p)} nodes)", "nodes": len(p), "type": "video"}
    except: pass

tasks = {}

# --- Multi-workflow API ---

@app.get("/api/workflows")
async def wf_list():
    """List all configured workflows"""
    return {"workflows": known, "current": CURRENT}

@app.post("/api/workflows/add")
async def wf_add(req: Request):
    """Add a workflow from RunningHub by ID"""
    body = await req.json()
    wid = body["workflow_id"]
    name = body.get("name", f"WF-{wid[:10]}")
    r = rh_call("/api/openapi/getJsonApiFormat", {"workflowId": wid})
    p = json.loads(r["data"]["prompt"])
    known[wid] = {"name": f"{name} ({len(p)} nodes)", "nodes": len(p), "type": "video" if any("video" in n.get("class_type","").lower() for nid,n in p.items()) else "image"}
    return {"ok": True, "workflow": wid}

@app.post("/api/workflows/switch")
async def wf_switch(req: Request):
    """Switch active workflow"""
    global CURRENT
    body = await req.json()
    wid = body["workflow_id"]
    if wid not in known: raise HTTPException(400, "Unknown")
    CURRENT = wid
    return {"ok": True, "workflow": wid}

@app.get("/api/workflows/{wid}")
async def wf_get(wid: str):
    """Get workflow structure"""
    r = rh_call("/api/openapi/getJsonApiFormat", {"workflowId": wid})
    return json.loads(r["data"]["prompt"])

# --- ComfyUI API ---

@app.get("/api/prompt")
async def ping(): return {"status": "ok"}

@app.post("/prompt")
async def run(req: Request):
    """Run a workflow on RunningHub"""
    body = await req.json()
    wid = CURRENT or next(iter(known))
    pid = f"rh_{int(time.time()*1000)}"
    
    result = rh_call("/task/openapi/create", {"workflowId": wid, "addMetadata": False})
    tasks[pid] = {"task_id": result["data"]["taskId"], "status": "QUEUED", "created": time.time()}
    return {"prompt_id": pid, "number": 1}

@app.get("/history/{pid}")
async def history(pid: str):
    """Check task status (ComfyUI format)"""
    t = tasks.get(pid)
    if not t: return {pid: {"status": "error"}}
    
    s = rh_call("/task/openapi/status", {"taskId": t["task_id"]})
    st = s.get("data", "RUNNING")
    
    if st == "SUCCESS":
        o = rh_call("/task/openapi/outputs", {"taskId": t["task_id"]})
        out = {str(i): {"videos": [{"filename": it["fileUrl"], "type": "output"}]} for i, it in enumerate(o.get("data", []))}
        return {pid: {"status": "success", "outputs": {"9": out}}}
    elif st == "FAILED":
        return {pid: {"status": "error"}}
    else:
        return {pid: {"status": "running"}}

@app.get("/view")
async def view(filename="", type="", subfolder=""):
    if filename.startswith("http"):
        import httpx
        async with httpx.AsyncClient() as c:
            r = await c.get(filename)
            return Response(content=r.content, media_type=r.headers.get("content-type", "video/mp4"))
    return Response(status_code=404)

@app.post("/upload/image")
async def upload(file: UploadFile = File(None), image: UploadFile = File(None)):
    f = file or image
    if not f: raise HTTPException(400, "No file")
    path = f"/tmp/rh_up_{time.time()}.png"
    with open(path, "wb") as fh: fh.write(await f.read())
    k = rh_key()
    # Use curl to avoid auth issues
    r = json.loads(subprocess.run(["curl","-s","-X","POST",
        f"{RH_BASE}/task/openapi/upload","-H","Host: www.runninghub.ai",
        "-H","Content-Type: multipart/form-data",
        "-F",f"apiKey={k}","-F",f"file=@{path}"], capture_output=True, text=True, timeout=30).stdout)
    os.remove(path)
    if r.get("code") != 0: raise HTTPException(400, "Upload failed")
    return {"name": r["data"]["fileName"].split("/")[-1], "subfolder": "", "type": "input"}

# --- Web UI ---
from fastapi.responses import HTMLResponse

@app.get("/webui", response_class=HTMLResponse)
async def webui():
    return """
    <!DOCTYPE html>
    <html><head><title>RunningHub Proxy</title>
    <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-gray-950 text-white min-h-screen p-6">
    <div class="max-w-4xl mx-auto">
        <h1 class="text-3xl font-bold mb-2">🎬 RunningHub Proxy</h1>
        <p class="text-gray-400 mb-6">Multi-workflow ComfyUI proxy</p>
        
        <div class="bg-gray-900 rounded-xl p-4 border border-gray-800 mb-6">
            <h2 class="font-semibold mb-3">Workflows</h2>
            <div id="wflist" class="space-y-2"></div>
            <div class="mt-3 flex gap-2">
                <input id="wid" class="bg-gray-800 rounded px-3 py-2 text-sm flex-1 border border-gray-700" placeholder="Workflow ID">
                <input id="wname" class="bg-gray-800 rounded px-3 py-2 text-sm flex-1 border border-gray-700" placeholder="Nom">
                <button onclick="add()" class="bg-purple-600 px-4 py-2 rounded text-sm">+</button>
            </div>
        </div>
        <div class="bg-gray-900 rounded-xl p-4 border border-gray-800">
            <h2 class="font-semibold mb-3">Génération</h2>
            <textarea id="prompt" rows="2" class="w-full bg-gray-800 rounded p-3 text-sm border border-gray-700" placeholder="Prompt..."></textarea>
            <button onclick="gen()" class="bg-purple-600 hover:bg-purple-700 px-6 py-2 rounded-lg mt-2">Lancer</button>
            <div id="res" class="mt-4"></div>
        </div>
    </div>
    <script>
    async function load() {
        let r = await fetch('/api/workflows')
        let d = await r.json()
        document.getElementById('wflist').innerHTML = Object.entries(d.workflows).map(([id,w]) =>
            `<div class="flex justify-between items-center bg-gray-800 rounded px-4 py-2 ${id==d.current?'border border-purple-500':''}">
                <span>${w.name} <span class="text-xs text-gray-500">${id.slice(0,12)}...</span></span>
                <button onclick="sw('${id}')" class="text-purple-400 text-sm ${id==d.current?'hidden':''}">Utiliser</button>
            </div>`
        ).join('')
    }
    async function add() {
        await fetch('/api/workflows/add', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({workflow_id: document.getElementById('wid').value, name: document.getElementById('wname').value || ''})})
        load()
    }
    async function sw(id) {
        await fetch('/api/workflows/switch', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({workflow_id: id})})
        load()
    }
    async function gen() {
        let p = document.getElementById('prompt').value
        let r = await fetch('/prompt', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({prompt:{}})})
        let d = await r.json()
        document.getElementById('res').innerHTML = `<p class="text-purple-400">Envoyé: ${d.prompt_id}</p>`
    }
    load()
    </script></body></html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8199)
