import time
import requests
import base64
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

# 一个极小的静音MP3文件的Base64编码，用于STT测试
SILENT_MP3_BASE64 = "SUQzBAAAAAABEVRYWFgAAAASAAAAAPAAADqZmYgAAC1tYW1hYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFh"
SILENT_MP3_BYTES = base64.b64decode(SILENT_MP3_BASE64)

def _check_chat(session: requests.Session, base_url: str, headers: Dict, model: str) -> Dict:
    """检查Chat Completions API"""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Health check"}],
        "max_tokens": 5,
    }
    response = session.post(f"{base_url}/chat/completions", json=payload, headers=headers)
    response.raise_for_status()
    data = response.json()
    if not data.get("choices") or not data["choices"][0].get("message"):
        raise ValueError("无效的Chat API响应格式")
    return {"status_code": response.status_code, "data": data}

def _check_tts(session: requests.Session, base_url: str, headers: Dict, model: str) -> Dict:
    """检查Text-to-Speech API"""
    payload = {"model": model, "input": "Health check", "voice": "alloy"}
    with session.post(f"{base_url}/audio/speech", json=payload, headers=headers, stream=True) as response:
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "audio" not in content_type:
            raise ValueError(f"无效的TTS content-type: {content_type}")
        
        # 确保我们能接收到音频数据
        first_chunk = next(response.iter_content(chunk_size=1024), None)
        if not first_chunk:
            raise ValueError("TTS响应体为空")
    return {"status_code": response.status_code, "content_type": content_type}

def _check_stt(session: requests.Session, base_url: str, headers: Dict, model: str) -> Dict:
    """检查Speech-to-Text API"""
    files = {"file": ("silent.mp3", SILENT_MP3_BYTES, "audio/mpeg")}
    data = {"model": model}
    stt_headers = {k: v for k, v in headers.items() if k.lower() != 'content-type'}
    
    response = session.post(f"{base_url}/audio/transcriptions", files=files, data=data, headers=stt_headers)
    response.raise_for_status()
    data = response.json()
    if "text" not in data:
        raise ValueError("无效的STT API响应格式")
    return {"status_code": response.status_code, "data": data}

def check_api(session: requests.Session, service: Dict, model_info: Dict) -> Dict:
    """调度单个API模型的检查任务（在线程中运行）"""
    start_time = time.monotonic()
    
    service_name = service["name"]
    model_type = model_info["type"]
    model_name = model_info["name"]
    base_url = service["base_url"].rstrip('/')
    
    headers = {
        "Authorization": f"Bearer {service['api_key']}",
        "Content-Type": "application/json",
    }
    
    check_result = {
        "service_name": service_name,
        "model_type": model_type,
        "model_name": model_name,
    }

    try:
        if model_type == "chat":
            _check_chat(session, base_url, headers, model_name)
        elif model_type == "tts":
            _check_tts(session, base_url, headers, model_name)
        elif model_type == "stt":
            _check_stt(session, base_url, headers, model_name)
        else:
            raise ValueError(f"不支持的检查类型: {model_type}")
        
        check_result["status"] = "OK"
        check_result["details"] = "服务工作正常"
        
    except requests.exceptions.HTTPError as e:
        check_result["status"] = "ERROR"
        check_result["details"] = f"HTTP错误: {e.response.status_code} - {e.response.text[:100]}"
    except requests.exceptions.RequestException as e:
        check_result["status"] = "ERROR"
        check_result["details"] = f"请求错误: {type(e).__name__}"
    except Exception as e:
        check_result["status"] = "ERROR"
        check_result["details"] = f"检查失败: {e}"
        
    finally:
        end_time = time.monotonic()
        check_result["latency_ms"] = int((end_time - start_time) * 1000)

    return check_result

def run_all_checks(config: Dict) -> List[Dict]:
    """使用线程池并发执行所有配置的API检查"""
    results = []
    # 使用requests.Session进行连接复用，提高效率
    with requests.Session() as session:
        # 设置全局超时
        session.timeout = 15
        with ThreadPoolExecutor(max_workers=10) as executor:
            # 创建所有检查任务
            futures = []
            for service in config.get("services", []):
                for model_info in service.get("models", []):
                    future = executor.submit(check_api, session, service, model_info)
                    futures.append(future)
            
            # 等待任务完成并收集结果
            for future in as_completed(futures):
                results.append(future.result())
                
    return results