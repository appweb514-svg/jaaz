#!/usr/bin/env python3
"""ComfyUI → RunningHub Proxy - Multi-workflow support"""
import json, os, time, urllib.request, urllib.error, subprocess, asyncio
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import JSONResponse, Response, RedirectResponse, HTMLResponse

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

def fetch_wf_info(wid):
    try:
        r = rh_call("/api/openapi/getJsonApiFormat", {"workflowId": wid})
        p = json.loads(r["data"]["prompt"])
        return {"name": f"WF-{wid[:10]} ({len(p)} nodes)", "nodes": len(p),
                "type": "video" if any("video" in n.get("class_type","").lower() for nid,n in p.items()) else "image"}
    except: return None

app = FastAPI(title="RH Proxy")
known = {}
tasks = {}

@app.get("/api/workflows")
async def wf_list():
    return {"workflows": known, "current": CURRENT}

@app.post("/api/workflows/add")
async def wf_add(req: Request):
    body = await req.json()
    wid = body.get("workflow_id", "")
    if not wid: raise HTTPException(400, "Missing workflow_id")
    name = body.get("name", f"WF-{wid[:10]}")
    info = await asyncio.to_thread(fetch_wf_info, wid)
    if not info: raise HTTPException(400, "Workflow not found on RunningHub")
    info["name"] = f"{name} ({info['nodes']} nodes)"
    known[wid] = info
    global CURRENT
    if not CURRENT: CURRENT = wid
    return {"ok": True, "workflow": wid, "info": info}

@app.post("/api/workflows/switch")
async def wf_switch(req: Request):
    global CURRENT
    body = await req.json()
    wid = body.get("workflow_id", "")
    if wid not in known: raise HTTPException(400, "Unknown workflow")
    CURRENT = wid
    return {"ok": True}

@app.delete("/api/workflows/{wid}")
async def wf_delete(wid: str):
    if wid in known: del known[wid]
    global CURRENT
    if CURRENT == wid: CURRENT = next(iter(known)) if known else None
    return {"ok": True}

@app.get("/api/workflows/{wid}")
async def wf_get(wid: str):
    r = rh_call("/api/openapi/getJsonApiFormat", {"workflowId": wid})
    return json.loads(r["data"]["prompt"])

@app.get("/api/prompt")
async def ping():
    return {"status": "ok", "key_configured": bool(rh_key()), "workflows_count": len(known)}

@app.get("/api/object_info")
async def obj_info():
    return {"CheckpointLoaderSimple": {"input": {"ckpt_name": ("STRING", {"multiline": False})}},
            "LTXVideoTextToVideo": {"input": {"prompt": ("STRING", {"multiline": True}), "width": ("INT", {"default": 960}), "height": ("INT", {"default": 544})}},
            "CLIPTextEncode": {"input": {"text": ("STRING", {"multiline": True}), "clip": ("CLIP",)}}}

@app.post("/prompt")
async def run(req: Request):
    body = await req.json()
    wid = CURRENT or next(iter(known))
    if not wid: raise HTTPException(400, "No workflow configured")
    pid = f"rh_{int(time.time()*1000)}"
    result = rh_call("/task/openapi/create", {"workflowId": wid, "addMetadata": False})
    tasks[pid] = {"task_id": result["data"]["taskId"], "status": "QUEUED", "created": time.time()}
    return {"prompt_id": pid, "number": 1, "workflow": wid}

@app.get("/history/{pid}")
async def history(pid: str):
    t = tasks.get(pid)
    if not t: return {pid: {"status": "error"}}
    try:
        s = rh_call("/task/openapi/status", {"taskId": t["task_id"]})
        st = s.get("data", "RUNNING")
        if st == "SUCCESS":
            o = rh_call("/task/openapi/outputs", {"taskId": t["task_id"]})
            out = {str(i): {"videos": [{"filename": it["fileUrl"], "type": "output"}]} for i, it in enumerate(o.get("data", []))}
            return {pid: {"status": "success", "outputs": {"9": out}}}
        elif st == "FAILED": return {pid: {"status": "error"}}
        else: return {pid: {"status": "running"}}
    except: return {pid: {"status": "running"}}

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
    r = json.loads(subprocess.run(["curl","-s","-X","POST",
        f"{RH_BASE}/task/openapi/upload","-H","Host: www.runninghub.ai",
        "-H","Content-Type: multipart/form-data",
        "-F",f"apiKey={k}","-F",f"file=@{path}"], capture_output=True, text=True, timeout=30).stdout)
    os.remove(path)
    if r.get("code") != 0: raise HTTPException(400, "Upload failed")
    return {"name": r["data"]["fileName"].split("/")[-1], "subfolder": "", "type": "input"}

@app.get("/", response_class=RedirectResponse)
async def root(): return "/webui"

import os as _os
_UI_DIR = _os.path.dirname(_os.path.abspath(__file__))

@app.get("/webui", response_class=HTMLResponse)
async def webui():
    path = _os.path.join(_UI_DIR, "rh_proxy_ui.html")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        return HTMLResponse("<h1>UI file not found</h1>", status_code=404)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8199)
