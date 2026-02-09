import requests
import re
import base64
import json
import socket
from urllib.parse import urlparse, unquote
from concurrent.futures import ThreadPoolExecutor # 新增：多线程支持

# ... 前面的代码（SOURCES, check_port, parse_any_uri 等）保持不变 ...

def main():
    print(">>> 启动[并发]存活节点检测模式...")
    all_raw_nodes = []
    
    # 抓取逻辑保持不变
    for url in SOURCES:
        try:
            resp = requests.get(url, timeout=15)
            # ... 提取 YAML 和 URI 的逻辑 (同上一版) ...
            # 此处省略重复抓取逻辑，请保留你现有的抓取部分
        except: continue

    # --- 改进的并发过滤环节 ---
    yaml_lines = ["proxies:"]
    seen = set()
    final_nodes = []

    # 1. 先去重
    unique_nodes = []
    for n in all_raw_nodes:
        if not n or not n.get('server'): continue
        idx = f"{n['type']}:{n['server']}:{n['port']}"
        if idx not in seen:
            seen.add(idx)
            unique_nodes.append(n)

    print(f"\n>>> 原始抓取到 {len(unique_nodes)} 个唯一节点，正在并发检测存活...")

    # 2. 使用线程池同时检测多个节点（速度极快）
    def validate(n):
        if check_port(n['server'], n['port']):
            return n
        return None

    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(validate, unique_nodes))
        final_nodes = [r for r in results if r is not None]

    # 3. 写入 YAML
    for n in final_nodes:
        clean_name = str(n.get('name', 'node')).replace('"', '\\"')
        yaml_lines.append(f"  - name: \"{clean_name}\"\n    type: {n['type']}\n    server: \"{n['server']}\"\n    port: {n['port']}")
        # ... 写入 uuid/password 的逻辑 (同上一版) ...
        yaml_lines.append(f"    sni: \"{n.get('sni', n['server'])}\"\n    skip-cert-verify: true")

    with open("my_sub.yaml", "w", encoding="utf-8") as f:
        f.write("\n".join(yaml_lines))
    print(f"\n>>> 检测完成！保留了 {len(final_nodes)} 个活节点。")
