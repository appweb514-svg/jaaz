"""
RunningHub integration routes for Jaaz
"""
from fastapi import APIRouter, HTTPException, Request
from services.config_service import config_service
import json, os, urllib.request, urllib.error

router = APIRouter(prefix="/runninghub", tags=["runninghub"])

RH_BASE = "https://www.runninghub.ai"

@router.get("/status")
async def get_status():
    """Get RunningHub connection status"""
    # Re-read config from file if needed
    import asyncio
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
    """List workflows from config"""
    settings = config_service.get_config()
    rh = settings.get('runninghub', {})
    wid = rh.get('workflow_id', '')
    return {"workflow_id": wid}

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
