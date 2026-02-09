# 简单的节点收集程序 - 第1版
import requests
import re

print("开始收集节点链接...")

# 几个免费的节点源
sources = [
    "https://raw.githubusercontent.com/crossxx-labs/free-proxy/main/README.md",
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/All_Configs_base64_Sub.txt"
]

# 收集所有链接
all_links = []

for url in sources:
    print(f"正在获取: {url}")
    try:
        # 发送网络请求
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            content = response.text
            # 查找vmess链接
            links = re.findall(r'vmess://[A-Za-z0-9+/=]+', content)
            all_links.extend(links)
            print(f"  找到 {len(links)} 个vmess链接")
    except Exception as e:
        print(f"  错误: {e}")

print(f"\n总共找到 {len(all_links)} 个链接")

# 去重
unique_links = list(set(all_links))
print(f"去重后剩下 {len(unique_links)} 个链接")

# 保存到文件
with open('nodes.txt', 'w', encoding='utf-8') as f:
    for link in unique_links:
        f.write(link + '\n')

print("✅ 完成！已保存到 nodes.txt")
