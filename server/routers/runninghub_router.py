"""
RunningHub integration routes for Jaaz
"""
from fastapi import APIRouter, HTTPException, Request
from services.config_service import config_service
from tools.rh_models import get_available_models, get_workflow_models
import json, os, urllib.request, urllib.error

router = APIRouter(prefix="/runninghub", tags=["runninghub"])

RH_BASE = "https://www.runninghub.ai"

@router.get("/credits")
async def get_credits():
    """Get RunningHub credits (coins + wallet balance) in real-time"""
    settings = config_service.get_config()
    rh = settings.get('runninghub', {})
    key = rh.get('api_key', '')
    if not key:
        return {"coins": 0, "wallet": "0.00", "connected": False}
    
    try:
        h = {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "Host": "www.runninghub.ai"}
        p = json.dumps({"apiKey": key}).encode()
        req = urllib.request.Request(f"{RH_BASE}/uc/openapi/accountStatus", data=p, headers=h)
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        if data.get("code") == 0:
            acct = data["data"]
            return {
                "coins": acct.get("remainCoins", 0),
                "wallet": acct.get("remainMoney", "0.00"),
                "connected": True
            }
        return {"coins": 0, "wallet": "0.00", "connected": False, "error": data.get("msg", "")}
    except Exception as e:
        return {"coins": 0, "wallet": "0.00", "connected": False, "error": str(e)}

@router.get("/status")
async def get_status():
    """Get RunningHub connection status"""
    if hasattr(config_service, 'initialize') and not config_service.initialized:
        await config_service.initialize()
    settings = config_service.get_config()
    rh = settings.get('runninghub', {})
    is_configured = bool(rh.get('api_key', ''))
    
    rh_ok = False
    if is_configured:
        try:
            key = rh['api_key']
            h = {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "Host": "www.runninghub.ai"}
            p = json.dumps({"apiKey": key}).encode()
            req = urllib.request.Request(f"{RH_BASE}/uc/openapi/accountStatus", data=p, headers=h)
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read())
            rh_ok = data.get("code") == 0
        except: pass
    
    return {
        "enabled": rh.get('enabled', False),
        "configured": is_configured,
        "connected": rh_ok,
        "workflow_id": rh.get('workflow_id', ''),
    }

@router.post("/settings")
async def update_settings(request: Request):
    """Update RunningHub settings"""
    body = await request.json()
    settings = config_service.get_config()
    if 'runninghub' not in settings:
        settings['runninghub'] = {}
    
    if 'enabled' in body:
        settings['runninghub']['enabled'] = bool(body['enabled'])
    if 'api_key' in body:
        settings['runninghub']['api_key'] = str(body['api_key'])
        try:
            with open('/tmp/rh_key.txt', 'w') as f:
                f.write(str(body['api_key']))
        except: pass
    if 'workflow_id' in body:
        settings['runninghub']['workflow_id'] = str(body['workflow_id'])
    
    await config_service.update_config(settings)
    return {"status": "ok"}

@router.get("/workflows")
async def list_workflows():
    """List configured workflow"""
    settings = config_service.get_config()
    rh = settings.get('runninghub', {})
    return {"workflow_id": rh.get('workflow_id', '')}

@router.post("/test")
async def test_connection():
    """Test RunningHub connection"""
    settings = config_service.get_config()
    rh = settings.get('runninghub', {})
    key = rh.get('api_key', '')
    if not key:
        raise HTTPException(400, "No API key configured")
    
    try:
        h = {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "Host": "www.runninghub.ai"}
        p = json.dumps({"apiKey": key}).encode()
        req = urllib.request.Request(f"{RH_BASE}/uc/openapi/accountStatus", data=p, headers=h)
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        if data.get("code") == 0:
            acct = data["data"]
            return {"status": "ok", "coins": acct.get("remainCoins", "?"), "wallet": acct.get("remainMoney", "?")}
        return {"status": "error", "message": data.get("msg", "Unknown")}
    except urllib.error.HTTPError as e:
        return {"status": "error", "message": f"HTTP {e.code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/models")
async def list_models():
    """List all available models on RunningHub (latest per provider)"""
    return {
        "workflow_models": get_workflow_models(),
        "standard_models": get_available_models(),
        "note": "Standard Model API requires Enterprise key. Workflow models work with Plan A."
    }

@router.post("/generate")
async def generate(request: Request):
    """Generate via RunningHub — either ComfyUI workflow or standard model API"""
    body = await request.json()
    settings = config_service.get_config()
    rh = settings.get('runninghub', {})
    key = rh.get('api_key', '')
    if not key:
        raise HTTPException(400, "No RunningHub API key configured")
    
    gen_type = body.get('type', 'workflow')  # 'workflow' or 'standard'
    
    if gen_type == 'workflow':
        # ComfyUI workflow execution
        workflow_id = body.get('workflow_id', rh.get('workflow_id', ''))
        if not workflow_id:
            raise HTTPException(400, "No workflow_id configured")
        
        h = {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "Host": "www.runninghub.ai"}
        payload = {"apiKey": key, "workflowId": workflow_id, "addMetadata": False}
        
        # Add node overrides if provided
        if body.get('nodeInfoList'):
            payload['nodeInfoList'] = body['nodeInfoList']
        
        p = json.dumps(payload).encode()
        req = urllib.request.Request(f"{RH_BASE}/task/openapi/create", data=p, headers=h)
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            d = json.loads(resp.read())
            if d.get("data", {}).get("taskId"):
                return {"status": "ok", "task_id": d["data"]["taskId"], "type": "workflow"}
            return {"status": "error", "message": d.get("msg", "Unknown error")}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    elif gen_type == 'standard':
        # Standard model API (Enterprise only)
        endpoint = body.get('endpoint', '')
        if not endpoint:
            raise HTTPException(400, "No endpoint specified")
        
        h = {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "Host": "www.runninghub.ai"}
        payload = {"apiKey": key}
        payload.update(body.get('params', {}))
        
        p = json.dumps(payload).encode()
        req = urllib.request.Request(f"{RH_BASE}/openapi/v2/{endpoint}", data=p, headers=h)
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            d = json.loads(resp.read())
            if d.get("taskId"):
                return {"status": "ok", "task_id": d["taskId"], "type": "standard"}
            return {"status": "error", "message": d.get("errorMessage", "Unknown error")}
        except Exception as e:
            return {"status": "error", "message": str(e)}

@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """Get task status"""
    settings = config_service.get_config()
    rh = settings.get('runninghub', {})
    key = rh.get('api_key', '')
    if not key:
        raise HTTPException(400, "No API key configured")
    
    h = {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "Host": "www.runninghub.ai"}
    
    # Check status
    p = json.dumps({"apiKey": key, "taskId": task_id}).encode()
    req = urllib.request.Request(f"{RH_BASE}/task/openapi/status", data=p, headers=h)
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        d = json.loads(resp.read())
        status = d.get("data", "RUNNING")
        
        result = {"status": status.lower()}
        
        if status == "SUCCESS":
            # Get outputs
            p2 = json.dumps({"apiKey": key, "taskId": task_id}).encode()
            req2 = urllib.request.Request(f"{RH_BASE}/task/openapi/outputs", data=p2, headers=h)
            resp2 = urllib.request.urlopen(req2, timeout=10)
            d2 = json.loads(resp2.read())
            outputs = d2.get("data", [])
            result["outputs"] = [item.get("fileUrl", "") for item in outputs]
        
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}
