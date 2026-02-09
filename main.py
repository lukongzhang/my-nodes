# 增强版节点收集程序
import requests
import re
import base64

print("🚀 开始收集节点链接...")

# 使用更多的订阅源
sources = [
    "https://raw.githubusercontent.com/crossxx-labs/free-proxy/main/README.md",
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/All_Configs_base64_Sub.txt",
    "https://raw.githubusercontent.com/moez06/V2ray-configs/main/All_Configs_base64_Sub.txt",
    "https://chromego-sub.netlify.app/sub/merged_proxies_new.yaml",
    "https://raw.githubusercontent.com/Ruk1ng001/freeSub/main/clash.yaml"
]

# 收集所有链接
all_links = []

for url in sources:
    print(f"\n📥 正在获取: {url}")
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            content = response.text
            
            # 方法1：直接查找各种链接
            patterns = [
                r'vmess://[A-Za-z0-9+/=]+',          # vmess链接
                r'vless://[^\s\'"<>]+',              # vless链接
                r'trojan://[^\s\'"<>]+',             # trojan链接
                r'ss://[^\s\'"<>]+',                 # ss链接
                r'hy2://[^\s\'"<>]+',                # hysteria2链接
                r'hysteria://[^\s\'"<>]+'            # hysteria链接
            ]
            
            found_count = 0
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    all_links.extend(matches)
                    found_count += len(matches)
                    print(f"  找到 {len(matches)} 个 {pattern.split(':')[0]} 链接")
            
            # 方法2：尝试解码base64内容
            try:
                # 如果内容是base64编码的
                if len(content) % 4 == 0 and re.match(r'^[A-Za-z0-9+/=]+$', content.strip()):
                    decoded = base64.b64decode(content).decode('utf-8', errors='ignore')
                    for pattern in patterns:
                        matches = re.findall(pattern, decoded, re.IGNORECASE)
                        if matches:
                            all_links.extend(matches)
                            print(f"  Base64解码后找到 {len(matches)} 个链接")
            except:
                pass
            
            if found_count == 0:
                print(f"  ⚠️  这个源没有找到标准格式链接")
                
    except Exception as e:
        print(f"  ❌ 获取失败: {e}")

print(f"\n📊 统计结果:")
print(f"总共找到 {len(all_links)} 个链接")

# 去重
if all_links:
    unique_links = list(set(all_links))
    print(f"去重后剩下 {len(unique_links)} 个唯一链接")
    
    # 保存到文件
    with open('nodes.txt', 'w', encoding='utf-8') as f:
        for link in unique_links:
            f.write(link + '\n')
    
    print("✅ 成功保存到 nodes.txt")
    
    # 显示前5个链接作为示例
    print("\n📋 示例链接（前5个）:")
    for i, link in enumerate(unique_links[:5]):
        print(f"{i+1}. {link[:80]}...")
else:
    print("❌ 没有找到任何节点链接！")
    print("正在创建测试文件...")
    
    # 创建测试文件，确保至少有个文件
    test_nodes = [
        "vmess://eyJhZGQiOiIxLjEuMS4xIiwicG9ydCI6IjQ0MyIsImlkIjoiMTIzNCIsImFpZCI6IjAiLCJuZXQiOiJ0Y3AiLCJ0eXBlIjoibm9uZSIsInBzIjoi5Yqg5ou/5pWwIiwiYWx0ZXJuYXRlSG9zdCI6IiIsIm9ic2VydmUiOiJub25lIn0=",
        "vmess://eyJhZGQiOiIyLjIuMi4yIiwicG9ydCI6IjQ0MyIsImlkIjoiNTY3OCIsImFpZCI6IjAiLCJuZXQiOiJ0Y3AiLCJ0eXBlIjoibm9uZSIsInBzIjoi5Yqg5ou/5pWwIiwic25pIjoiZXhhbXBsZS5jb20ifQ=="
    ]
    
    with open('nodes.txt', 'w', encoding='utf-8') as f:
        for node in test_nodes:
            f.write(node + '\n')
    
    print("✅ 已创建包含测试节点的 nodes.txt")
