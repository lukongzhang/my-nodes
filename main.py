import requests
import re
import base64
import json
from urllib.parse import urlparse, unquote

SOURCES = [
    "https://raw.githubusercontent.com/crossxx-labs/free-proxy/main/README.md",
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/All_Configs_base64_Sub.txt",
    "https://raw.githubusercontent.com/moez06/V2ray-Configs/main/All_Configs_base64_Sub.txt",
    "https://chromego-sub.netlify.app/sub/merged_proxies_new.yaml",
    "https://raw.githubusercontent.com/Ruk1ng001/freeSub/main/clash.yaml",
    "https://raw.githubusercontent.com/ovmvo/SubShare/refs/heads/main/sub/permanent/mihomo.yaml"
]

def try_base64_decode(text):
    try:
        text = text.strip()
        missing_padding = len(text) % 4
        if missing_padding: text += '=' * (4 - missing_padding)
        return base64.b64decode(text).decode('utf-8', errors='ignore')
    except:
        return text

def parse_any_uri(url):
    """解析多种类型的代理链接"""
    try:
        url = url.strip()
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()
        
        # 基础信息提取
        name = unquote(parsed.fragment) if parsed.fragment else f"{scheme}-{parsed.hostname}"
        server = parsed.hostname
        port = parsed.port or 443
        
        # 1. 处理 VMess (通常是 base64 json)
        if scheme == "vmess":
            v_data = json.loads(try_base64_decode(url[8:]))
            return {
                "name": v_data.get('ps', name), "type": "vmess", "server": v_data['add'],
                "port": v_data['port'], "uuid": v_data['id'], "alterId": v_data['aid'],
                "cipher": "auto", "tls": True if v_data.get('tls') == "tls" else False,
                "servername": v_data.get('sni', v_data['add'])
            }

        # 2. 处理 VLESS / Trojan / SS / Hysteria
        user_info = unquote(parsed.netloc.split('@')[0]) if '@' in parsed.netloc else ""
        params = {k: v[0] for k, v in [p.split('=') for p in parsed.query.split('&')] if '=' in p}
        
        node = {
            "name": name, "type": scheme, "server": server, "port": port,
            "skip-cert-verify": True, "sni": params.get("sni", server)
        }

        if scheme == "vless":
            node.update({"uuid": user_info, "cipher": "auto", "tls": True})
        elif scheme == "trojan":
            node.update({"password": user_info, "sni": params.get("sni", server)})
        elif scheme in ["hysteria", "hysteria2", "hy2"]:
            node["type"] = "hysteria2" if scheme in ["hysteria2", "hy2"] else "hysteria"
            node["password"] = user_info or params.get("auth", "")
        elif scheme == "ss":
            # Shadowsocks 比较复杂，这里做简化处理
            node.update({"cipher": user_info.split(':')[0] if ':' in user_info else "aes-256-gcm", 
                         "password": user_info.split(':')[1] if ':' in user_info else user_info})
            
        return node
    except:
        return None

def main():
    print(">>> 启动全协议万能抓取机器人...")
    all_final_nodes = []
    
    for url in SOURCES:
        try:
            print(f"扫描源: {url}")
            resp = requests.get(url, timeout=15)
            content = resp.text
            
            # 策略 A: 识别 YAML
            if "proxies:" in content:
                blocks = re.split(r'-\s*name:', content)
                for block in blocks[1:]:
                    try:
                        def gv(k):
                            m = re.search(rf'{k}:\s*["\']?(.+?)["\']?\s*(?:\n|$)', block)
                            return m.group(1).strip() if m else ""
                        all_final_nodes.append({
                            "name": block.split('\n')[0].strip('"\' '),
                            "type": gv("type"), "server": gv("server"), "port": gv("port"),
                            "password": gv("password") or gv("uuid") or gv("auth"),
                            "sni": gv("sni") or gv("server")
                        })
                    except: continue

            # 策略 B: 识别 URI (多协议正则)
            uris = re.findall(r'(?:vmess|vless|trojan|ss|hysteria2|hysteria|hy2)://[^\s\'"<>]+', content)
            # 处理 Base64 的订阅内容
            decoded = try_base64_decode(content)
            uris.extend(re.findall(r'(?:vmess|vless|trojan|ss|hysteria2|hysteria|hy2)://[^\s\'"<>]+', decoded))
            
            for uri in set(uris):
                node = parse_any_uri(uri)
                if node: all_final_nodes.append(node)
                
            # 策略 C: 深度递归 (README 中的订阅)
            if "README.md" in url:
                deep_links = re.findall(r'https?://[^\s\'"<>]+?/sub/[^\s\'"<>]+', content)
                for dl in set(deep_links):
                    try:
                        d_resp = requests.get(dl, timeout=10)
                        all_final_nodes.extend([parse_any_uri(u) for u in re.findall(r'(?:vmess|vless|trojan|ss|hy\d?)://[^\s\'"<>]+', try_base64_decode(d_resp.text))])
                    except: continue
        except: continue

    # 写入 YAML
    yaml_lines = ["proxies:"]
    seen = set()
    for n in all_final_nodes:
        if not n or not n.get('server'): continue
        idx = f"{n['server']}:{n['port']}"
        if idx not in seen:
            seen.add(idx)
            yaml_lines.append(f"  - name: \"{n['name']}\"\n    type: {n['type']}\n    server: \"{n['server']}\"\n    port: {n['port']}")
            # 根据类型填入关键认证字段
            if n['type'] == "vmess":
                yaml_lines.append(f"    uuid: {n['uuid']}\n    alterId: {n['alterId']}\n    cipher: auto")
            elif n['type'] == "vless":
                yaml_lines.append(f"    uuid: {n['uuid']}\n    cipher: auto")
            else:
                yaml_lines.append(f"    password: \"{n.get('password', '')}\"")
            yaml_lines.append(f"    sni: \"{n.get('sni', n['server'])}\"\n    skip-cert-verify: true")

    with open("my_sub.yaml", "w", encoding="utf-8") as f:
        f.write("\n".join(yaml_lines))
    print(f"\n>>> 任务结束！全协议节点总计: {len(seen)} 个。")

if __name__ == "__main__":
    main()
