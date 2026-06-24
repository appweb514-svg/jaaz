"""
ComfyUI API Proxy → RunningHub
Makes Jaaz think it's talking to local ComfyUI but actually uses RunningHub
"""
import json
import os
import time
import asyncio
from typing import Optional
from urllib.parse import urlencode

try:
    from fastapi import FastAPI, HTTPException, Request, UploadFile, File, WebSocket, WebSocketDisconnect
    from fastapi.responses import JSONResponse, Response, StreamingResponse
except ImportError:
    import subprocess
    subprocess.run(["pip", "install", "fastapi", "uvicorn", "python-multipart", "-q"])
    from fastapi import FastAPI, HTTPException, Request, UploadFile, File, WebSocket, WebSocketDisconnect
    from fastapi.responses import JSONResponse, Response, StreamingResponse

import httpx

# ---------- RunningHub Client ----------
def get_rh_key() -> str:
    try:
        with open('/tmp/rh_key.txt') as f:
            return f.read().strip()
    except: pass
    return ""

RH_BASE = "https://www.runninghub.ai"
RH_H = {"Content-Type": "application/json", "Host": "www.runninghub.ai"}

def rh_call(endpoint: str, payload: dict, timeout: int = 30) -> dict:
    import urllib.request, urllib.error
    key = get_rh_key()
    headers = {**RH_H, "Authorization": f"Bearer {key}"}
    payload["apiKey"] = key
    data = json.dumps(payload).encode()
    req = urllib.request.Request(f"{RH_BASE}{endpoint}", data=data, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err = e.read().decode()[:200]
        raise HTTPException(502, f"RH Error {e.code}: {err}")

# A simple in-memory task store
tasks = {}

# ---------- FastAPI App ----------
app = FastAPI(title="ComfyUI → RunningHub Proxy")

# ComfyUI models that RunningHub supports via our workflow
SUPPORTED_NODES = {
    "CheckpointLoaderSimple": {"input": {"ckpt_name": ["STRING"]}},
    "LTXVideoTextToVideo": {"input": {"prompt": ["STRING"], "model": ["MODEL"], "width": ["INT"], "height": ["INT"], "frames": ["INT"], "steps": ["INT"]}},
    "LTXVideoModelLoader": {"input": {"model_name": ["STRING"]}},
    "VAELoader": {"input": {"vae_name": ["STRING"]}},
    "CLIPTextEncode": {"input": {"text": ["STRING"], "clip": ["CLIP"]}},
    "KSampler": {"input": {"seed": ["INT"], "steps": ["INT"], "cfg": ["FLOAT"], "model": ["MODEL"], "positive": ["CONDITIONING"], "negative": ["CONDITIONING"], "latent_image": ["LATENT"]}},
    "EmptyLatentImage": {"input": {"width": ["INT"], "height": ["INT"], "batch_size": ["INT"]}},
    "VAEDecode": {"input": {"samples": ["LATENT"], "vae": ["VAE"]}},
    "VAEEncode": {"input": {"pixels": ["IMAGE"], "vae": ["VAE"]}},
    "SaveImage": {"input": {"images": ["IMAGE"]}},
    "LoadImage": {"input": {"image": ["STRING"]}},
}

WORKFLOW_ID = "2069523159090552833"
TASK_PREFIX = "rh_"
_task_counter = 0

@app.get("/api/prompt")
async def check_running():
    return JSONResponse(content={"status": "ok"})

@app.get("/api/object_info")
async def object_info():
    """Return supported node types (mimicking ComfyUI)"""
    return JSONResponse(content=SUPPORTED_NODES)

@app.post("/prompt")
async def queue_prompt(request: Request):
    """Receive ComfyUI workflow, execute on RunningHub"""
    body = await request.json()
    workflow = body.get("prompt", {})
    
    prompt_id = f"{TASK_PREFIX}{int(time.time()*1000)}"
    
    # Extract prompt text from workflow nodes
    prompt_text = ""
    for nid, node in workflow.items():
        ct = node.get("class_type", "")
        inputs = node.get("inputs", {})
        if "TextToVideo" in ct:
            prompt_text = inputs.get("prompt", inputs.get("text", ""))
            break
        elif "CLIPTextEncode" == ct:
            prompt_text = inputs.get("text", "")
            break
    
    # Just submit directly to RunningHub with a generic prompt override
    try:
        result = rh_call("/task/openapi/create", {
            "workflowId": WORKFLOW_ID,
            "addMetadata": False
        })
        task_id = result["data"]["taskId"]
        tasks[prompt_id] = {"task_id": task_id, "status": "QUEUED", "outputs": [], "created": time.time()}
    except Exception as e:
        tasks[prompt_id] = {"task_id": "", "status": "FAILED", "error": str(e)}
    
    return JSONResponse(content={"prompt_id": prompt_id, "number": 1})


@app.get("/history/{prompt_id}")
async def get_history(prompt_id: str):
    """Return execution history (ComfyUI format)"""
    task = tasks.get(prompt_id)
    if not task:
        return JSONResponse(content={})
    
    # Check RunningHub status
    try:
        status = rh_call("/task/openapi/status", {"taskId": task["task_id"]})
        s = status.get("data", "")
        task["status"] = s
        
        if s == "SUCCESS":
            outputs = rh_call("/task/openapi/outputs", {"taskId": task["task_id"]})
            task["outputs"] = outputs.get("data", [])
            
            # Return in ComfyUI format
            output = {}
            for i, o in enumerate(task["outputs"]):
                output[str(i)] = {"videos": [{"filename": o["fileUrl"], "type": "output", "format": o.get("fileType", "mp4")}]}
            
            return JSONResponse(content={
                prompt_id: {
                    "status": "success",
                    "outputs": {"9": output} if output else {},
                }
            })
        elif s == "FAILED":
            return JSONResponse(content={
                prompt_id: {"status": "error"}
            })
        else:
            # RUNNING / QUEUED
            return JSONResponse(content={
                prompt_id: {"status": "running"}
            })
    except:
        return JSONResponse(content={
            prompt_id: {"status": "running"}
        })

@app.get("/view")
async def view_file(filename: str = "", type: str = "", subfolder: str = "", **kwargs):
    """Proxy file download from RunningHub to ComfyUI format"""
    if filename.startswith("http"):
        async with httpx.AsyncClient() as client:
            resp = await client.get(filename)
            return Response(content=resp.content, media_type=resp.headers.get("content-type", "video/mp4"))
    return Response(content="", status_code=404)

@app.post("/upload/image")
async def upload_image(file: UploadFile = File(...), image: UploadFile = File(None), subfolder: str = "jaaz"):
    """Upload image to RunningHub, return in ComfyUI format"""
    upload_file = file or image
    if not upload_file:
        raise HTTPException(400, "No file")
    
    import subprocess, os as _os
    key = get_rh_key()
    path = f"/tmp/rh_proxy_{int(time.time())}.png"
    content = await upload_file.read()
    with open(path, "wb") as f:
        f.write(content)
    
    result = subprocess.run([
        "curl", "-s", "-X", "POST",
        f"{RH_BASE}/task/openapi/upload",
        "-H", "Host: www.runninghub.ai",
        "-H", f"Authorization: Bearer {_os.environ.get('RH_KEY','') or open('/tmp/rh_key.txt').read().strip()}",
        "-F", f"apiKey={key}",
        "-F", f"file=@{path}"
    ], capture_output=True, text=True, timeout=30)
    
    _os.remove(path)
    data = json.loads(result.stdout)
    if data.get("code") != 0:
        raise HTTPException(400, f"Upload failed: {data.get('msg')}")
    
    return JSONResponse(content={
        "name": data["data"]["fileName"].split("/")[-1],
        "subfolder": "",
        "type": "input"
    })

@app.get("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            await ws.receive_text()
            await ws.send_json({"type": "status", "data": {"sid": "rh-proxy", "status": "connected"}})
    except:
        pass

if __name__ == "__main__":
    import uvicorn
    print("🎬 ComfyUI → RunningHub Proxy on http://0.0.0.0:8199")
    uvicorn.run(app, host="0.0.0.0", port=8199)
