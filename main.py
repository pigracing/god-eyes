import time
from datetime import datetime
from typing import List, Dict

from config_loader import load_config
from checker import run_all_checks
from notifier import send_notification

def format_report(results: List[Dict]) -> str:
    """将检查结果格式化为人类可读的报告（无变化）"""
    ok_count = sum(1 for r in results if r["status"] == "OK")
    error_count = len(results) - ok_count
    
    header = (
        f"📋 API 健康检查报告 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n"
        f"总计: {len(results)} | ✅ 正常: {ok_count} | ❌ 异常: {error_count}\n"
        "--------------------------------------------------\n"
    )
    erro_line = []
    lines = []
    for r in sorted(results, key=lambda x: (x["service_name"], x["status"])):
        status_icon = "✅" if r["status"] == "OK" else "❌"
        line = (
            f"{status_icon} [{r['status']}] {r['service_name']} - "
            f"{r['model_type'].upper()} ({r['model_name']}) | "
            f"延迟: {r['latency_ms']}ms\n"
        )
        if r["status"] == "ERROR":
            line += f"   └── 详情: {r['details']}\n"
            erro_line.append(f"{status_icon} [{r['status']}] {r['service_name']} {r['details']}")
        lines.append(line)
        
    return header + "".join(erro_line)

def main():
    """主循环，定时执行检查和通知（同步版本）"""
    try:
        config = load_config()
    except (FileNotFoundError, ValueError) as e:
        print(f"错误：无法加载配置: {e}")
        return

    interval = config.get("settings", {}).get("check_interval_seconds", 300)
    print("API健康检查服务已启动。")
    print(f"检查周期: {interval} 秒。按 Ctrl+C 退出。")

    while True:
        try:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 开始新一轮检查...")
            
            start_time = time.monotonic()
            results = run_all_checks(config)
            end_time = time.monotonic()
            
            print(f"所有检查完成，耗时 {end_time - start_time:.2f} 秒。")

            report = format_report(results)
            print("\n--- 检查结果清单 ---")
            print(report)
            print("--- 报告结束 ---\n")
            
            send_notification(config, report)

            print(f"等待 {interval} 秒后进行下一轮检查...")
            time.sleep(interval)
            
        except Exception as e:
            print(f"主循环中发生未预料的错误: {e}")
            print(f"将在 {interval} 秒后重试...")
            time.sleep(interval)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n检测到 Ctrl+C，程序关闭。")