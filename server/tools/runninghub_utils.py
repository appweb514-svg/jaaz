"""
RunningHub API client for Jaaz
Replaces local ComfyUI with RunningHub cloud ComfyUI
"""
import json
import time
import asyncio
import urllib.request
import urllib.error
import os
from typing import Optional

# Read API key
def get_runninghub_key() -> str:
    """Get RunningHub API key from env file or key file"""
    try:
        with open('/tmp/rh_key.txt') as f:
            return f.read().strip()
    except:
        pass
    try:
        with open(os.path.expanduser('~/.hermes/.env')) as f:
            for line in f:
                if 'RUNNINGHUB_API_KEY' in line and '=' in line:
                    parts = line.strip().split('=', 1)
                    if len(parts) == 2 and len(parts[1]) > 5:
                        return parts[1]
    except:
        pass
    return ""

BASE_URL = "https://www.runninghub.ai"
HEADERS = {"Content-Type": "application/json", "Host": "www.runninghub.ai"}

async def execute_workflow(
    workflow: dict,
    workflow_id: str = "",
    wait: bool = True,
    timeout: int = 300
) -> dict:
    """
    Execute a ComfyUI workflow on RunningHub.
    
    Args:
        workflow: The full workflow JSON
        workflow_id: RunningHub workflow ID (optional, uses workflow JSON otherwise)
        wait: Whether to wait for completion
        timeout: Max wait time in seconds
    
    Returns:
        dict with 'outputs' list of file URLs and 'status'
    """
    api_key = get_runninghub_key()
    if not api_key:
        raise ValueError("RunningHub API key not found")
    
    headers = {**HEADERS, "Authorization": f"Bearer {api_key}"}
    
    # Convert workflow to string if needed
    workflow_str = json.dumps(workflow) if isinstance(workflow, dict) else workflow
    
    # Build request payload
    payload = {
        "apiKey": api_key,
        "workflow": workflow_str,
        "addMetadata": False
    }
    if workflow_id:
        payload["workflowId"] = workflow_id
    
    # Submit task
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/task/openapi/create",
        data=data, headers=headers
    )
    
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()[:300]
        raise RuntimeError(f"RunningHub API error {e.code}: {error_body}")
    
    if result.get("code") != 0:
        raise RuntimeError(f"RunningHub error: {result.get('msg', 'Unknown')}")
    
    task_id = result["data"]["taskId"]
    
    if not wait:
        return {"task_id": task_id, "status": "QUEUED"}
    
    # Poll for completion
    start = time.time()
    while time.time() - start < timeout:
        status_payload = json.dumps({
            "apiKey": api_key,
            "taskId": task_id
        }).encode()
        status_req = urllib.request.Request(
            f"{BASE_URL}/task/openapi/status",
            data=status_payload, headers=headers
        )
        try:
            status_resp = urllib.request.urlopen(status_req, timeout=10)
            status_data = json.loads(status_resp.read())
        except Exception as e:
            await asyncio.sleep(5)
            continue
        
        s = status_data.get("data", "")
        if s == "SUCCESS":
            # Get outputs
            out_payload = json.dumps({
                "apiKey": api_key,
                "taskId": task_id
            }).encode()
            out_req = urllib.request.Request(
                f"{BASE_URL}/task/openapi/outputs",
                data=out_payload, headers=headers
            )
            out_resp = urllib.request.urlopen(out_req, timeout=10)
            out_data = json.loads(out_resp.read())
            
            outputs = []
            for item in out_data.get("data", []):
                outputs.append({
                    "url": item["fileUrl"],
                    "type": item["fileType"],
                    "node_id": item.get("nodeId", ""),
                    "coins": item.get("consumeCoins", "?")
                })
            
            return {
                "task_id": task_id,
                "status": "SUCCESS",
                "outputs": outputs,
                "elapsed": time.time() - start
            }
        
        elif s == "FAILED":
            return {
                "task_id": task_id,
                "status": "FAILED",
                "error": "Workflow execution failed"
            }
        
        await asyncio.sleep(3)
    
    return {
        "task_id": task_id,
        "status": "TIMEOUT",
        "error": f"Execution timed out after {timeout}s"
    }


async def upload_image(image_path: str, filename: Optional[str] = None) -> str:
    """
    Upload an image to RunningHub for use in workflows.
    Returns the fileName reference to use in nodeInfoList.
    """
    import subprocess as sp
    
    api_key = get_runninghub_key()
    if not api_key:
        raise ValueError("RunningHub API key not found")
    
    result = sp.run([
        "curl", "-s", "-X", "POST",
        f"{BASE_URL}/task/openapi/upload",
        "-H", f"Authorization: Bearer {api_key}",
        "-H", "Host: www.runninghub.ai",
        "-F", f"apiKey={api_key}",
        "-F", f"file=@{image_path}"
    ], capture_output=True, text=True, timeout=30)
    
    data = json.loads(result.stdout)
    if data.get("code") != 0:
        raise RuntimeError(f"Upload failed: {data.get('msg', 'Unknown')}")
    
    return data["data"]["fileName"]


async def check_server_running() -> bool:
    """Check if RunningHub API is accessible"""
    api_key = get_runninghub_key()
    if not api_key:
        return False
    try:
        headers = {**HEADERS, "Authorization": f"Bearer {api_key}"}
        payload = json.dumps({"apiKey": api_key, "taskId": "0"}).encode()
        req = urllib.request.Request(
            f"{BASE_URL}/task/openapi/status",
            data=payload, headers=headers
        )
        resp = urllib.request.urlopen(req, timeout=5)
        return True
    except:
        return False
