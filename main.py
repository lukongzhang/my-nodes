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

def extract_from_content(text):
    """从任何文本中提取 hy2 节点（包括解密 Base64）"""
    nodes = []
    # 尝试直接找
    uris = re.findall(r'(?:hysteria2|hy2)://[^\s\'"<>]+', text)
    # 尝试解密后再找
    decoded = try_base64_decode(text)
    if decoded != text:
        uris.extend(re.findall(r'(?:hysteria2|hy2)://[^\s\'"<>]+', decoded))
    
    for uri in set(uris):
        n = parse_hy2_uri(uri)
        if n: nodes.append(n)
    return nodes

def main():
    print(">>> 深度抓取模式启动...")
    all_final_nodes = []
    
    for url in SOURCES:
        try:
            print(f"正在扫描源: {url}")
            resp = requests.get(url, timeout=15)
            content = resp.text
            
            # 1. 提取 YAML 里的节点
            if "proxies:" in content:
                from_yaml = re.split(r'-\s*name:', content)
                for block in from_yaml[1:]:
                    if re.search(r'type:\s*(?:hysteria2|hy2)', block, re.I):
                        try:
                            def gv(k):
                                m = re.search(rf'{k}:\s*["\']?(.+?)["\']?\s*(?:\n|$)', block)
                                return m.group(1).strip() if m else ""
                            all_final_nodes.append({
                                "name": block.split('\n')[0].strip('"\' '),
                                "server": gv("server"), "port": gv("port"),
                                "password": gv("password") or gv("auth"),
                                "sni": gv("sni") or gv("server")
                            })
                        except: continue

            # 2. 提取文本里的 URI
            all_final_nodes.extend(extract_from_content(content))

            # 3. 【核心修复】深度递归：找 README 里的订阅链接并点进去
            if "README.md" in url:
                # 寻找 crossxx 这种典型的订阅格式：http.../sub/hysteria/...
                deep_links = re.findall(r'https?://[^\s\'"<>]+?/sub/(?:hysteria|hy2)/\d+', content)
                for dl in set(deep_links):
                    print(f"  --> 发现深度订阅地址，正在进入: {dl}")
                    try:
                        deep_resp = requests.get(dl, timeout=10)
                        all_final_nodes.extend(extract_from_content(deep_resp.text))
                    except: continue

        except Exception as e:
            print(f"扫描失败: {e}")

    # 4. 写入文件
    yaml_lines = ["proxies:"]
    seen = set()
    for n in all_final_nodes:
        if not n.get('server'): continue
        idx = f"{n['server']}:{n['port']}"
        if idx not in seen:
            seen.add(idx)
            clean_name = n['name'].replace('"', '\\"')
            yaml_lines.append(f"  - name: \"{clean_name}\"")
            yaml_lines.append(f"    type: hysteria2\n    server: \"{n['server']}\"\n    port: {n['port']}\n    password: \"{n['password']}\"\n    sni: \"{n['sni']}\"\n    skip-cert-verify: true")

    with open("my_sub.yaml", "w", encoding="utf-8") as f:
        f.write("\n".join(yaml_lines))
    print(f"\n>>> 任务完成！共计 {len(seen)} 个节点。")

if __name__ == "__main__":
    main()
