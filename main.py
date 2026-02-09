import requests
import re
import base64
import json
import socket
from urllib.parse import urlparse, unquote

SOURCES = [
    "https://raw.githubusercontent.com/crossxx-labs/free-proxy/main/README.md",
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/All_Configs_base64_Sub.txt",
    "https://raw.githubusercontent.com/moez06/V2ray-Configs/main/All_Configs_base64_Sub.txt",
    "https://chromego-sub.netlify.app/sub/merged_proxies_new.yaml",
    "https://raw.githubusercontent.com/Ruk1ng001/freeSub/main/clash.yaml",
    "https://raw.githubusercontent.com/ovmvo/SubShare/refs/heads/main/sub/permanent/mihomo.yaml"
]

def check_port(host, port):
    """检测节点服务器端口是否开放"""
    try:
        # 尝试建立 TCP 连接，超时时间设为 2 秒
        with socket.create_connection((host, int(port)), timeout=2):
            return True
    except:
        return False

def try_base64_decode(text):
    try:
        text = text.strip()
        missing_padding = len(text) % 4
        if missing_padding: text += '=' * (4 - missing_padding)
        return base64.b64decode(text).decode('utf-8', errors='ignore')
    except:
        return text

def parse_any_uri(url):
    try:
        url = url.strip()
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()
        name = unquote(parsed.fragment) if parsed.fragment else f"{scheme}-{parsed.hostname}"
        server = parsed.hostname
        port = parsed.port or 443
        
        if scheme == "vmess":
            try:
                v_data = json.loads(try_base64_decode(url[8:]))
                return {
                    "name": v_data.get('ps', name), "type": "vmess", "server": v_data['add'],
                    "port": v_data['port'], "uuid": v_data.get('id', ''), "alterId": v_data.get('aid', 0),
                    "cipher": "auto", "tls": True if v_data.get('tls') == "tls" else False,
                    "sni": v_data.get('sni', v_data['add'])
                }
            except: return None

        user_info = unquote(parsed.netloc.split('@')[0]) if '@' in parsed.netloc else ""
        params = {k: v[0] for k, v in [p.split('=') for p in parsed.query.split('&')] if '=' in p}
        
        node = {
            "name": name, "type": scheme, "server": server, "port": port,
            "skip-cert-verify": True, "sni": params.get("sni", server)
        }

        if scheme == "vless":
            node.update({"uuid": user_info, "cipher": "auto", "tls": True})
        elif scheme == "trojan":
            node.update({"password": user_info})
        elif scheme in ["hysteria", "hysteria2", "hy2"]:
            node["type"] = "hysteria2" if scheme in ["hysteria2", "hy2"] else "hysteria"
            node["password"] = user_info or params.get("auth", "")
        elif scheme == "ss":
            node.update({"cipher": user_info.split(':')[0] if ':' in user_info else "aes-256-gcm", 
                         "password": user_info.split(':')[1] if ':' in user_info else user_info})
        return node
    except:
        return None

def main():
    print(">>> 启动存活节点检测模式...")
    all_raw_nodes = []
    
    for url in SOURCES:
        try:
            print(f"扫描源: {url}")
            resp = requests.get(url, timeout=15)
            content = resp.text
            
            # YAML 提取
            if "proxies:" in content:
                blocks = re.split(r'-\s*name:', content)
                for block in blocks[1:]:
                    try:
                        def gv(k):
                            m = re.search(rf'{k}:\s*["\']?(.+?)["\']?\s*(?:\n|$)', block)
                            return m.group(1).strip() if m else ""
                        all_raw_nodes.append({
                            "name": block.split('\n')[0].strip('"\' '),
                            "type": gv("type"), "server": gv("server"), "port": gv("port"),
                            "password": gv("password") or gv("uuid") or gv("auth"),
                            "uuid": gv("uuid") or gv("password"),
                            "sni": gv("sni") or gv("server"),
                            "alterId": gv("alterId") or 0
                        })
                    except: continue

            # URI 提取
            uris = re.findall(r'(?:vmess|vless|trojan|ss|hysteria2|hysteria|hy2)://[^\s\'"<>]+', content)
            decoded = try_base64_decode(content)
            uris.extend(re.findall(r'(?:vmess|vless|trojan|ss|hysteria2|hysteria|hy2)://[^\s\'"<>]+', decoded))
            for uri in set(uris):
                node = parse_any_uri(uri)
                if node: all_raw_nodes.append(node)
        except: continue

    # --- 关键过滤环节 ---
    yaml_lines = ["proxies:"]
    seen = set()
    alive_count = 0
    
    print(f"\n>>> 原始抓取到 {len(all_raw_nodes)} 个节点，正在进行存活检测 (请耐心等待)...")

    for n in all_raw_nodes:
        if not n or not n.get('server'): continue
        idx = f"{n['type']}:{n['server']}:{n['port']}"
        if idx not in seen:
            seen.add(idx)
            # 进行端口检测
            if check_port(n['server'], n['port']):
                alive_count += 1
                clean_name = str(n.get('name', 'node')).replace('"', '\\"')
                yaml_lines.append(f"  - name: \"{clean_name}\"\n    type: {n['type']}\n    server: \"{n['server']}\"\n    port: {n['port']}")
                if n['type'] == "vmess":
                    yaml_lines.append(f"    uuid: \"{n.get('uuid', '')}\"\n    alterId: {n.get('alterId', 0)}\n    cipher: auto")
                elif n['type'] == "vless":
                    yaml_lines.append(f"    uuid: \"{n.get('uuid', '')}\"\n    cipher: auto")
                else:
                    yaml_lines.append(f"    password: \"{n.get('password', '')}\"")
                yaml_lines.append(f"    sni: \"{n.get('sni', n['server'])}\"\n    skip-cert-verify: true")

    with open("my_sub.yaml", "w", encoding="utf-8") as f:
        f.write("\n".join(yaml_lines))
    print(f"\n>>> 检测完成！丢弃了 {len(seen) - alive_count} 个死节点，保留了 {alive_count} 个活节点。")

if __name__ == "__main__":
    main()
