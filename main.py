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

def parse_uri(url):
    """同时支持 hysteria:// 和 hysteria2://"""
    try:
        url = url.strip()
        parsed = urlparse(url)
        # 自动识别类型
        node_type = "hysteria" if url.startswith("hysteria://") else "hysteria2"
        
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
            
        name = unquote(parsed.fragment) if parsed.fragment else f"{node_type}-{server}"
        if not password or not server: return None
        
        return {
            "name": name, "type": node_type, "server": server, 
            "port": port, "password": password, "sni": params.get("sni", server)
        }
    except:
        return None

def extract_from_content(text):
    nodes = []
    # 修改正则，使其兼容 hysteria 和 hysteria2
    uris = re.findall(r'(?:hysteria2|hysteria|hy2)://[^\s\'"<>]+', text)
    decoded = try_base64_decode(text)
    if decoded != text:
        uris.extend(re.findall(r'(?:hysteria2|hysteria|hy2)://[^\s\'"<>]+', decoded))
    
    for uri in set(uris):
        n = parse_uri(uri)
        if n: nodes.append(n)
    return nodes

def main():
    print(">>> 启动双类型(Hy1 & Hy2)深度抓取...")
    all_final_nodes = []
    
    for url in SOURCES:
        try:
            print(f"扫描: {url}")
            resp = requests.get(url, timeout=15)
            content = resp.text
            
            # 1. 提取 YAML
            if "proxies:" in content:
                blocks = re.split(r'-\s*name:', content)
                for block in blocks[1:]:
                    # 同时匹配 hysteria 和 hysteria2
                    type_match = re.search(r'type:\s*(hysteria2|hysteria|hy2|hy)', block, re.I)
                    if type_match:
                        raw_type = type_match.group(1).lower()
                        real_type = "hysteria" if raw_type in ["hysteria", "hy"] else "hysteria2"
                        try:
                            def gv(k):
                                m = re.search(rf'{k}:\s*["\']?(.+?)["\']?\s*(?:\n|$)', block)
                                return m.group(1).strip() if m else ""
                            all_final_nodes.append({
                                "name": block.split('\n')[0].strip('"\' '),
                                "type": real_type,
                                "server": gv("server"), "port": gv("port"),
                                "password": gv("password") or gv("auth"),
                                "sni": gv("sni") or gv("server")
                            })
                        except: continue

            # 2. 提取 URI
            all_final_nodes.extend(extract_from_content(content))

            # 3. 递归抓取
            if "README.md" in url:
                # 寻找包含 hysteria1/2 的订阅链接
                deep_links = re.findall(r'https?://[^\s\'"<>]+?/sub/(?:hysteria2|hysteria|hy2|hy)/\d+', content)
                for dl in set(deep_links):
                    try:
                        deep_content = requests.get(dl, timeout=10).text
                        all_final_nodes.extend(extract_from_content(deep_content))
                    except: continue

        except: continue

    # 4. 写入文件
    yaml_lines = ["proxies:"]
    seen = set()
    for n in all_final_nodes:
        if not n.get('server'): continue
        # 唯一标识加入类型，防止同服务器双协议被去重
        idx = f"{n['type']}:{n['server']}:{n['port']}"
        if idx not in seen:
            seen.add(idx)
            clean_name = n['name'].replace('"', '\\"')
            yaml_lines.append(f"  - name: \"{clean_name}\"")
            yaml_lines.append(f"    type: {n['type']}")
            yaml_lines.append(f"    server: \"{n['server']}\"")
            yaml_lines.append(f"    port: {n['port']}")
            yaml_lines.append(f"    password: \"{n['password']}\"")
            yaml_lines.append(f"    sni: \"{n['sni']}\"")
            yaml_lines.append(f"    skip-cert-verify: true")

    with open("my_sub.yaml", "w", encoding="utf-8") as f:
        f.write("\n".join(yaml_lines))
    print(f"\n>>> 任务完成！共计抓取 {len(seen)} 个节点。")

if __name__ == "__main__":
    main()
