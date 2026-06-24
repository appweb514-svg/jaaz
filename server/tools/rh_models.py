"""
RunningHub model catalog — latest models available via ComfyUI workflows
Standard Model API is Enterprise-only, so all generation goes through /task/openapi/create
"""
import json, urllib.request, urllib.error

RH_BASE = "https://www.runninghub.ai"

# Latest models per provider (curated — only latest versions)
RH_MODELS = {
    "video": {
        "LTX 2.3": {
            "id": "ltx-2.3",
            "provider": "Lightricks",
            "type": "text-to-video",
            "workflow_id": "2069523159090552833",
            "params": ["prompt", "image", "duration", "resolution"],
            "cost_coins": 55,
            "description": "Fast video generation, good quality"
        },
    },
    "image": {
        "RH Image G": {
            "id": "rhart-image-g",
            "provider": "RunningHub",
            "type": "text-to-image",
            "endpoint": "/openapi/v2/rhart-image-g/text-to-image",
            "params": ["prompt", "size"],
            "description": "RunningHub image generation"
        },
        "Qwen Image 2": {
            "id": "qwen-image-2",
            "provider": "Alibaba",
            "type": "text-to-image",
            "endpoint": "/openapi/v2/alibaba/qwen-image-2",
            "params": ["prompt"],
            "description": "Alibaba Qwen image generation"
        },
    }
}

# All available standard model endpoints (Enterprise-only, for reference)
STANDARD_MODELS_AVAILABLE = {
    "video": {
        "Kling": [
            {"name": "Kling O3 Pro", "endpoints": ["text-to-video", "image-to-video", "reference-to-video", "video-edit"]},
            {"name": "Kling O3 Std", "endpoints": ["text-to-video", "image-to-video", "reference-to-video", "video-edit"]},
            {"name": "Kling O3 4K", "endpoints": ["text-to-video", "image-to-video", "reference-to-video"]},
            {"name": "Kling O1", "endpoints": ["text-to-video", "image-to-video", "start-to-end"]},
            {"name": "Kling V3 Pro", "endpoints": ["image-to-video"]},
            {"name": "Kling V3 Std", "endpoints": ["image-to-video"]},
            {"name": "Kling V3 4K", "endpoints": ["image-to-video", "text-to-video"]},
        ],
        "Wan": [
            {"name": "Wan 2.7", "endpoints": ["image-to-video"]},
            {"name": "Wan 2.6", "endpoints": ["reference-to-video"]},
            {"name": "Wan 2.2", "endpoints": ["start-to-end"]},
        ],
        "Vidu": [
            {"name": "Vidu Q3 Pro", "endpoints": ["text-to-video", "image-to-video", "start-to-end", "reference-to-video"]},
            {"name": "Vidu Q3 Turbo", "endpoints": ["text-to-video", "image-to-video", "start-to-end"]},
            {"name": "Vidu Q2 Pro", "endpoints": ["text-to-video", "image-to-video", "start-to-end", "reference-to-video"]},
        ],
        "Seedance": [
            {"name": "Seedance 2.0 Global", "endpoints": ["image-to-video"]},
            {"name": "Seedance 2.0 Global Fast", "endpoints": ["image-to-video"]},
            {"name": "Seedance V1.5 Pro", "endpoints": ["image-to-video"]},
        ],
        "Hailuo": [
            {"name": "Hailuo 2.3 Pro", "endpoints": ["image-to-video"]},
            {"name": "Hailuo 2.3 Fast", "endpoints": ["image-to-video"]},
            {"name": "Hailuo 2.3 Std", "endpoints": ["image-to-video"]},
        ],
        "Google Veo": [
            {"name": "Veo 3.1 Pro", "endpoints": ["image-to-video", "start-end-to-video", "reference-to-video"]},
            {"name": "Veo 3.1 Fast", "endpoints": ["image-to-video", "start-end-to-video"]},
            {"name": "Veo 3.1 Lite", "endpoints": ["image-to-video"]},
        ],
        "Sora": [
            {"name": "Sora 2", "endpoints": ["text-to-video", "image-to-video"]},
        ],
        "RH Video": [
            {"name": "RH Video S", "endpoints": ["text-to-video", "image-to-video", "text-to-video-pro", "image-to-video-pro"]},
            {"name": "RH Video G", "endpoints": ["text-to-video", "image-to-video", "edit-video", "video-extend"]},
            {"name": "RH Video V3", "endpoints": ["video"]},
        ],
        "Pixverse": [
            {"name": "Pixverse V6", "endpoints": ["text-to-video", "image-to-video", "extend", "transition"]},
        ],
        "Skyreels": [
            {"name": "Skyreels V4", "endpoints": ["text-to-video-fast", "text-to-video-std", "image-to-video-fast", "image-to-video-std"]},
        ],
    },
    "image": {
        "RH Image": [
            {"name": "RH Image G 2", "endpoints": ["text-to-image", "image-to-image"]},
            {"name": "RH Image N Pro", "endpoints": ["text-to-image", "edit"]},
            {"name": "RH Image X", "endpoints": ["text-to-image", "edit"]},
            {"name": "RH Image V1", "endpoints": ["text-to-image", "edit"]},
            {"name": "Z Image Turbo", "endpoints": ["text-to-image", "image-to-image"]},
        ],
        "Midjourney": [
            {"name": "MJ V8.1", "endpoints": ["text-to-image"]},
            {"name": "MJ V7", "endpoints": ["text-to-image"]},
            {"name": "MJ Niji 7", "endpoints": ["text-to-image"]},
        ],
        "Qwen": [
            {"name": "Qwen Image 2", "endpoints": ["text-to-image", "edit"]},
        ],
        "Seedream": [
            {"name": "Seedream V5 Lite", "endpoints": ["text-to-image", "image-to-image"]},
            {"name": "Seedream V4", "endpoints": ["text-to-image", "image-to-image"]},
        ],
    },
    "audio": {
        "Suno": [
            {"name": "Suno V5", "endpoints": ["custom", "single"]},
            {"name": "Suno V4", "endpoints": ["music"]},
        ],
        "TTS": [
            {"name": "Speech-02 HD", "endpoints": ["text-to-audio"]},
            {"name": "Speech-02 Turbo", "endpoints": ["text-to-audio"]},
            {"name": "Voice Clone", "endpoints": ["text-to-audio"]},
        ],
    },
    "3d": {
        "Hitem3D": [
            {"name": "Hitem3D V2.1", "endpoints": ["image-to-3d", "multi-image-to-3d"]},
            {"name": "Hitem3D V2", "endpoints": ["image-to-3d", "multi-image-to-3d"]},
            {"name": "Hunyuan3D V3", "endpoints": ["3d"]},
        ],
    }
}

def get_available_models():
    """Returns curated list of latest models per category"""
    return STANDARD_MODELS_AVAILABLE

def get_workflow_models():
    """Returns models available via ComfyUI workflows (Plan A compatible)"""
    return RH_MODELS
