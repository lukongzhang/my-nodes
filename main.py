import requests
import re
import base64
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

def parse_hy2_uri(url):
    try:
        url = url.strip()
        parsed = urlparse(url)
        password = ""
        if '@' in parsed.netloc:
            password = unquote(parsed.netloc.split('@')[0])
        host_port = parsed.netloc.split('@')[-1]
        server = host_port.split(':')[0] if ':' in host_port else host_port
        port = host_port.split(':')[1] if ':' in host_port else "443"
        params = {}
        if parsed.query:
            for p in parsed.query.split('&'):
                if '=' in p:
                    k, v = p.split('=', 1)
                    params[k] = v
        if not password and 'auth' in params:
            password = params['auth']
        name = unquote(parsed.fragment) if parsed.fragment else f"Hy2-{server}"
        if not password or not server: return None
        return {"name": name, "server": server, "port": port, "password": password, "sni": params.get("sni", server)}
    except:
        return None

def extract_from_yaml(content):
    nodes = []
    proxy_blocks = re.split(r'-\s*name:', content)
    for block in proxy_blocks[1:]:
        if re.search(r'type:\s*(?:hysteria2|hy2)', block, re.I):
            try:
                def get_val(key):
                    m = re.search(rf'{key}:\s*["\']?(.+?)["\']?\s*(?:\n|$)', block)
                    return m.group(1).strip() if m else ""
                server = get_val("server")
                port = get_val("port")
                password = get_val("password") or get_val("auth")
                name = block.split('\n')[0].strip('"\' ')
                sni = get_val("sni") or server
                if server and port and password:
                    nodes.append({"name": name, "server": server, "port": port, "password": password, "sni": sni})
            except:
                continue
    return nodes

def main():
    print(">>> 正在生成标准 YAML 格式...")
    all_final_nodes = []
    for url in SOURCES:
        try:
            resp = requests.get(url, timeout=15)
            content = resp.text
            uris = re.findall(r'(?:hysteria2|hy2)://[^\s\'"<>]+', content)
            uris.extend(re.findall(r'(?:hysteria2|hy2)://[^\s\'"<>]+', try_base64_decode(content)))
            for uri in set(uris):
                node = parse_hy2_uri(uri)
                if node: all_final_nodes.append(node)
            all_final_nodes.extend(extract_from_yaml(content))
        except:
            continue

    yaml_lines = ["proxies:"]
    seen = set()
    for n in all_final_nodes:
        idx = f"{n['server']}:{n['port']}"
        if idx not in seen:
            seen.add(idx)
            # 关键修复：所有字符串值都强制加上双引号，并转义内部的双引号
            clean_name = n['name'].replace('"', '\\"')
            clean_pass = n['password'].replace('"', '\\"')
            yaml_lines.append(f"  - name: \"{clean_name}\"")
            yaml_lines.append(f"    type: hysteria2")
            yaml_lines.append(f"    server: \"{n['server']}\"")
            yaml_lines.append(f"    port: {n['port']}")
            yaml_lines.append(f"    password: \"{clean_pass}\"")
            yaml_lines.append(f"    sni: \"{n['sni']}\"")
            yaml_lines.append(f"    skip-cert-verify: true")

    with open("my_sub.yaml", "w", encoding="utf-8") as f:
        f.write("\n".join(yaml_lines))
    print(f">>> 修复版已完成，共计 {len(seen)} 个节点。")

if __name__ == "__main__":
    main()