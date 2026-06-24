"""
FastAPI app that plugs into Jaaz, adding RunningHub video/image generation.
Run: uvicorn runninghub_plugin:app --host 0.0.0.0 --port 8765
"""
import json
import os
import time
import asyncio
import urllib.request
import urllib.error
from typing import Optional
from pydantic import BaseModel

try:
    from fastapi import FastAPI, UploadFile, File, HTTPException, Query
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
except ImportError:
    import subprocess
    subprocess.run(["pip", "install", "fastapi", "uvicorn", "python-multipart", "aiofiles", "-q"])
    from fastapi import FastAPI, UploadFile, File, HTTPException, Query
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles

# ---------- RunningHub API Client ----------
def get_rh_key() -> str:
    try:
        with open('/tmp/rh_key.txt') as f:
            return f.read().strip()
    except: pass
    return ""

RH_BASE = "https://www.runninghub.ai"
RH_HEADERS = {"Content-Type": "application/json", "Host": "www.runninghub.ai"}

def rh_request(endpoint: str, payload: dict, timeout: int = 30) -> dict:
    key = get_rh_key()
    headers = {**RH_HEADERS, "Authorization": f"Bearer {key}"}
    payload["apiKey"] = key
    data = json.dumps(payload).encode()
    req = urllib.request.Request(f"{RH_BASE}{endpoint}", data=data, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"RH {e.code}: {e.read().decode()[:200]}")

# ---------- FastAPI App ----------
app = FastAPI(title="RunningHub Media Studio", version="0.1.0")

# ---------- Models ----------
class GenerateRequest(BaseModel):
    workflow_id: str = "2069523159090552833"
    prompt: Optional[str] = ""
    image_url: Optional[str] = ""
    wait: bool = True

class TaskStatus(BaseModel):
    task_id: str

# ---------- Routes ----------

@app.get("/")
async def root():
    return {"name": "RunningHub Media Studio", "status": "ok"}

@app.post("/generate/video")
async def generate_video(req: GenerateRequest):
    """Generate video via RunningHub"""
    node_info = []
    if req.prompt:
        # Find text node - get from workflow JSON
        wf = rh_request("/api/openapi/getJsonApiFormat", {"workflowId": req.workflow_id})
        prompt_data = json.loads(wf["data"]["prompt"])
        # Find first LTXVideoTextToVideo node
        for nid, node in prompt_data.items():
            if "TextToVideo" in node.get("class_type", ""):
                node_info.append({"nodeId": nid, "fieldName": "prompt", "fieldValue": req.prompt})
                break
    
    result = rh_request("/task/openapi/create", {
        "workflowId": req.workflow_id,
        "nodeInfoList": node_info,
        "addMetadata": False
    }, timeout=30)
    
    if not req.wait:
        return {"task_id": result["data"]["taskId"], "status": "QUEUED"}
    
    task_id = result["data"]["taskId"]
    
    # Poll
    for _ in range(60):
        status = rh_request("/task/openapi/status", {"taskId": task_id}, timeout=10)
        s = status.get("data", "")
        if s == "SUCCESS":
            outputs = rh_request("/task/openapi/outputs", {"taskId": task_id})
            return {
                "task_id": task_id,
                "status": "SUCCESS",
                "outputs": outputs.get("data", []),
                "coins": [o.get("consumeCoins", "?") for o in outputs.get("data", [])]
            }
        elif s == "FAILED":
            return {"task_id": task_id, "status": "FAILED"}
        time.sleep(5)
    
    return {"task_id": task_id, "status": "TIMEOUT"}

@app.post("/generate/image-to-video")
async def image_to_video(file: UploadFile = File(...)):
    """Upload image and generate video"""
    # Save uploaded file
    import aiofiles
    upload_path = f"/tmp/rh_upload_{int(time.time())}_{file.filename}"
    async with aiofiles.open(upload_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    # Upload to RunningHub
    import subprocess
    key = get_rh_key()
    import os as _os
    result = subprocess.run([
        "curl", "-s", "-X", "POST",
        f"{RH_BASE}/task/openapi/upload",
        "-H", "Host: www.runninghub.ai",
        "-H", f"Authorization: Bearer {_os.environ.get('RH_KEY','') or open('/tmp/rh_key.txt').read().strip()}",
        "-F", f"apiKey={key}",
        "-F", f"file=@{upload_path}"
    ], capture_output=True, text=True, timeout=30)
    
    os.remove(upload_path)
    upload_data = json.loads(result.stdout)
    if upload_data.get("code") != 0:
        raise HTTPException(status_code=400, detail=f"Upload failed: {upload_data.get('msg')}")
    
    fn = upload_data["data"]["fileName"]
    
    # Run workflow with image input
    wf_result = rh_request("/task/openapi/create", {
        "workflowId": "2069523159090552833",
        "nodeInfoList": [{"nodeId": "98", "fieldName": "image", "fieldValue": fn}],
        "addMetadata": False
    }, timeout=30)
    
    task_id = wf_result["data"]["taskId"]
    
    # Poll
    for _ in range(60):
        status = rh_request("/task/openapi/status", {"taskId": task_id}, timeout=10)
        s = status.get("data", "")
        if s == "SUCCESS":
            outputs = rh_request("/task/openapi/outputs", {"taskId": task_id})
            return {
                "task_id": task_id,
                "status": "SUCCESS",
                "outputs": outputs.get("data", []),
                "coins": [o.get("consumeCoins", "?") for o in outputs.get("data", [])]
            }
        elif s == "FAILED":
            return {"task_id": task_id, "status": "FAILED"}
        time.sleep(5)
    
    return {"task_id": task_id, "status": "TIMEOUT"}

@app.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """Check task status"""
    status = rh_request("/task/openapi/status", {"taskId": task_id})
    if status.get("data") == "SUCCESS":
        outputs = rh_request("/task/openapi/outputs", {"taskId": task_id})
        return {"status": "SUCCESS", "outputs": outputs.get("data", [])}
    return {"status": status.get("data", "UNKNOWN")}

@app.get("/account")
async def get_account():
    """Get RunningHub account info"""
    result = rh_request("/uc/openapi/accountStatus", {})
    return result

@app.get("/webui")
async def web_ui():
    """Simple media creation UI"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>🎬 RunningHub Media Studio</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-950 text-white min-h-screen">
        <div class="max-w-4xl mx-auto p-6">
            <h1 class="text-4xl font-bold mb-2">🎬 RunningHub Media Studio</h1>
            <p class="text-gray-400 mb-8">Powered by RunningHub + LTX 2.3</p>
            
            <div class="grid md:grid-cols-2 gap-6 mb-8">
                <!-- Text to Video -->
                <div class="bg-gray-900 rounded-xl p-6 border border-gray-800">
                    <h2 class="text-xl font-semibold mb-4">📝 Texte → Vidéo</h2>
                    <textarea id="prompt" rows="3" class="w-full bg-gray-800 rounded-lg p-3 text-white border border-gray-700 mb-3" placeholder="Un chat orange qui joue dans l'herbe..."></textarea>
                    <button onclick="generateVideo()" class="bg-purple-600 hover:bg-purple-700 px-6 py-2 rounded-lg font-semibold transition">Générer</button>
                    <div id="textResult" class="mt-4"></div>
                </div>
                
                <!-- Image to Video -->
                <div class="bg-gray-900 rounded-xl p-6 border border-gray-800">
                    <h2 class="text-xl font-semibold mb-4">🖼️ Image → Vidéo</h2>
                    <input type="file" id="imageInput" accept="image/*" class="w-full bg-gray-800 rounded-lg p-3 text-white border border-gray-700 mb-3">
                    <button onclick="imageToVideo()" class="bg-purple-600 hover:bg-purple-700 px-6 py-2 rounded-lg font-semibold transition">Générer</button>
                    <div id="imgResult" class="mt-4"></div>
                </div>
            </div>

            <div class="bg-gray-900 rounded-xl p-6 border border-gray-800 mb-8">
                <h2 class="text-xl font-semibold mb-4">📋 Tâches récentes</h2>
                <div id="recentTasks" class="text-gray-400 text-sm">Aucune tâche pour l'instant</div>
            </div>
        </div>

        <script>
            async function generateVideo() {
                const prompt = document.getElementById('prompt').value;
                const result = document.getElementById('textResult');
                result.innerHTML = '<div class="animate-pulse text-purple-400">⏳ Génération en cours...</div>';
                
                const resp = await fetch('/generate/video', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({prompt, wait: true})
                });
                const data = await resp.json();
                
                if (data.status === 'SUCCESS' && data.outputs?.length) {
                    const url = data.outputs[0].fileUrl;
                    result.innerHTML = `<video controls class="w-full rounded-lg mt-2"><source src="${url}" type="video/mp4"></video>
                        <p class="text-green-400 mt-2">✅ ${data.coins?.[0] || '?'} RH coins</p>`;
                } else {
                    result.innerHTML = `<p class="text-red-400">❌ ${data.status}</p>`;
                }
            }

            async function imageToVideo() {
                const file = document.getElementById('imageInput').files[0];
                if (!file) return alert('Sélectionne une image');
                const result = document.getElementById('imgResult');
                result.innerHTML = '<div class="animate-pulse text-purple-400">⏳ Génération en cours...</div>';
                
                const form = new FormData();
                form.append('file', file);
                const resp = await fetch('/generate/image-to-video', {method: 'POST', body: form});
                const data = await resp.json();
                
                if (data.status === 'SUCCESS' && data.outputs?.length) {
                    const url = data.outputs[0].fileUrl;
                    result.innerHTML = `<video controls class="w-full rounded-lg mt-2"><source src="${url}" type="video/mp4"></video>
                        <p class="text-green-400 mt-2">✅ ${data.coins?.[0] || '?'} RH coins</p>`;
                } else {
                    result.innerHTML = `<p class="text-red-400">❌ ${data.status}</p>`;
                }
            }
        </script>
    </body>
    </html>
    """, media_type="text/html; charset=utf-8")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)
