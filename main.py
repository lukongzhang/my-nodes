import requests
import re
import base64
import json
import socket
from urllib.parse import urlparse, unquote
from concurrent.futures import ThreadPoolExecutor

SOURCES = [
    "https://raw.githubusercontent.com/crossxx-labs/free-proxy/main/README.md",
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/All_Configs_base64_Sub.txt",
    "https://raw.githubusercontent.com/moez06/V2ray-Configs/main/All_Configs_base64_Sub.txt",
    "https://chromego-sub.netlify.app/sub/merged_proxies_new.yaml",
    "https://raw.githubusercontent.com/Ruk1ng001/freeSub/main/clash.yaml",
    "https://raw.githubusercontent.com/ovmvo/SubShare/refs/heads/main/sub/permanent/mihomo.yaml"
]

def check_port(host, port):
    try:
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
        if not url: return None
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()
        name = unquote(parsed.fragment) if parsed.fragment else f"{scheme}-{parsed.hostname}"
        
        if scheme == "vmess":
            try:
                v_str = url[8:]
                v_data = json.loads(try_base64_decode(v_str))
                return {
                    "name": v_data.get('ps', name), "type": "vmess", "server": v_data['add'],
                    "port": v_data['port'], "uuid": v_data.get('id', ''), "aid": v_data.get('aid', 0),
                    "sni": v_data.get('sni', v_data['add']), "tls": True if v_data.get('tls') == "tls" else False
                }
            except: return None

        user_info = unquote(parsed.netloc.split('@')[0]) if '@' in parsed.netloc else ""
        params = {k: v[0] for k, v in [p.split('=') for p in parsed.query.split('&')] if '=' in p}
        
        node = {"name": name, "type": scheme, "server": parsed.hostname, "port": parsed.port or 443, "sni": params.get("sni", parsed.hostname)}

        if scheme == "vless":
            node.update({"uuid": user_info, "tls": True})
        elif scheme == "trojan":
            node.update({"password": user_info})
        elif scheme in ["hysteria", "hysteria2", "hy2"]:
            node["type"] = "hysteria2" if scheme in ["hysteria2", "hy2"] else "hysteria"
            node["password"] = user_info or params.get("auth", "")
        elif scheme == "ss":
            node.update({"cipher": user_info.split(':')[0] if ':' in user_info else "aes-256-gcm", "password": user_info.split(':')[1] if ':' in user_info else user_info})
        return node
    except:
        return None

def main():
    print(">>> 正在抓取并过滤节点...")
    raw_nodes = []
    for url in SOURCES:
        try:
            content = requests.get(url, timeout=15).text
            # 基础文本解析
            uris = re.findall(r'(?:vmess|vless|trojan|ss|hy\d?)://[^\s\'"<>]+', content)
            uris.extend(re.findall(r'(?:vmess|vless|trojan|ss|hy\d?)://[^\s\'"<>]+', try_base64_decode(content)))
            for u in set(uris):
                n = parse_any_uri(u)
                if n: raw_nodes.append(n)
        except: continue

    # 并发测速检测
    seen = set()
    unique_nodes = []
    for n in raw_nodes:
        if not n.get('server'): continue
        key = f"{n['server']}:{n['port']}"
        if key not in seen:
            seen.add(key)
            unique_nodes.append(n)

    print(f">>> 开始检测 {len(unique_nodes)} 个节点...")
    with ThreadPoolExecutor(max_workers=30) as executor:
        alive_nodes = list(filter(None, executor.map(lambda n: n if check_port(n['server'], n['port']) else None, unique_nodes)))

    # 写入 YAML (加强引号保护)
    with open("my_sub.yaml", "w", encoding="utf-8") as f:
        f.write("proxies:\n")
        for n in alive_nodes:
            # 强制清理名字中的非法字符并包裹引号
            safe_name = str(n['name']).replace('"', '').replace(':', ' ').strip()
            f.write(f"  - name: \"{safe_name}\"\n")
            f.write(f"    type: {n['type']}\n")
            f.write(f"    server: \"{n['server']}\"\n")
            f.write(f"    port: {n['port']}\n")
            f.write(f"    skip-cert-verify: true\n")
            f.write(f"    sni: \"{n.get('sni', n['server'])}\"\n")
            
            if n['type'] == "vmess":
                f.write(f"    uuid: \"{n.get('uuid', '')}\"\n    alterId: {n.get('aid', 0)}\n    cipher: auto\n")
            elif n['type'] == "vless":
                f.write(f"    uuid: \"{n.get('uuid', '')}\"\n    cipher: auto\n")
            else:
                f.write(f"    password: \"{n.get('password', '')}\"\n")
    
    print(f">>> 完成！保留活节点: {len(alive_nodes)} 个")

if __name__ == "__main__":
    main()
