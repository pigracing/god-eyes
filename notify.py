import requests
from typing import Dict, Any

def send_notification(config: Dict, report: str):
    """发送检查报告到指定的通知API（同步版本）"""
    notify_config = config.get("notification")
    if not notify_config or not notify_config.get("url"):
        print("未配置通知API，跳过发送。")
        return

    url = notify_config["url"]
    n_channel = notify_config.get("n_channel")
    api_key = notify_config.get("api_key")
    timeout = notify_config.get("timeout", 10)
    
    if n_channel == "bark":
        try:
            response = requests.get(url+"/"+report,timeout=timeout)
            response.raise_for_status()
            print(f"通知已成功发送到 {url}")
        except requests.exceptions.RequestException as e:
            print(f"错误：发送通知失败: {e}")
        except requests.exceptions.HTTPError as e:
            print(f"错误: 通知API返回错误状态 {e.response.status_code}: {e.response.text}")
    else:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {"content": report}
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
            response.raise_for_status()
            print(f"通知已成功发送到 {url}")
        except requests.exceptions.RequestException as e:
            print(f"错误：发送通知失败: {e}")
        except requests.exceptions.HTTPError as e:
            print(f"错误: 通知API返回错误状态 {e.response.status_code}: {e.response.text}")