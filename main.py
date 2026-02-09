# 简单直接的节点收集程序
import requests
import re

print("🚀 启动节点收集程序...")

# 使用可靠的订阅源
sources = [
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/All_Configs_base64_Sub.txt",
    "https://raw.githubusercontent.com/moez06/V2ray-configs/main/All_Configs_base64_Sub.txt",
    "https://sub.sharecentre.online/sub",  # 这个源通常有很多节点
]

all_links = []

for url in sources:
    print(f"\n📥 尝试: {url}")
    try:
        response = requests.get(url, timeout=20)
        print(f"  状态码: {response.status_code}")
        print(f"  内容长度: {len(response.text)} 字符")
        
        if response.status_code == 200:
            content = response.text
            
            # 方法1：直接搜索 "vmess://"
            if "vmess://" in content:
                # 提取所有vmess链接
                lines = content.split('\n')
                for line in lines:
                    if "vmess://" in line:
                        # 清理链接
                        link = line.strip()
                        # 去除前后的引号或空格
                        link = link.replace('"', '').replace("'", "").strip()
                        if link.startswith("vmess://"):
                            all_links.append(link)
                            print(f"  找到: {link[:60]}...")
            
            # 方法2：正则查找
            patterns = [
                r'vmess://[A-Za-z0-9+/=\-_]+',
                r'vless://[A-Za-z0-9%\-_\.:@]+',
                r'trojan://[A-Za-z0-9%\-_\.:@]+'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content)
                if matches:
                    for match in matches:
                        if match not in all_links:
                            all_links.append(match)
                    print(f"  正则找到 {len(matches)} 个 {pattern.split(':')[0]} 链接")
    
    except Exception as e:
        print(f"  ❌ 错误: {str(e)[:50]}")

print(f"\n📊 结果统计:")
print(f"总共找到: {len(all_links)} 个链接")

if all_links:
    # 去重
    unique_links = []
    seen = set()
    for link in all_links:
        if link not in seen:
            seen.add(link)
            unique_links.append(link)
    
    print(f"去重后: {len(unique_links)} 个唯一链接")
    
    # 保存到文件
    with open('nodes.txt', 'w', encoding='utf-8') as f:
        for link in unique_links:
            f.write(link + '\n')
    
    print("✅ 成功保存到 nodes.txt")
    
    # 显示一些示例
    print("\n📋 链接示例:")
    for i, link in enumerate(unique_links[:3]):
        print(f"{i+1}. {link[:80]}...")
    
else:
    print("⚠️  没有找到标准格式的链接")
    print("正在从其他源获取...")
    
    # 备用方案：从已知的好用源获取
    try:
        backup_url = "https://raw.githubusercontent.com/mianfeifq/share/main/README.md"
        print(f"尝试备用源: {backup_url}")
        resp = requests.get(backup_url, timeout=15)
        
        if resp.status_code == 200:
            # 这个源通常有很多链接
            backup_content = resp.text
            backup_links = re.findall(r'vmess://[A-Za-z0-9+/=]+', backup_content)
            
            if backup_links:
                print(f"从备用源找到 {len(backup_links)} 个链接")
                with open('nodes.txt', 'w', encoding='utf-8') as f:
                    for link in backup_links[:20]:  # 只取前20个
                        f.write(link + '\n')
                print("✅ 从备用源保存了链接")
            else:
                # 最后方案：创建测试文件
                create_test_file()
        else:
            create_test_file()
            
    except:
        create_test_file()

def create_test_file():
    """创建测试文件"""
    print("创建测试节点文件...")
    test_links = [
        "vmess://eyJhZGQiOiJ2bS5leGFtcGxlLmNvbSIsInBvcnQiOiI0NDMiLCJpZCI6IjEyMzQ1Njc4OTAtMTIzNC01Njc4LTkwMTItMzQ1Njc4OTAxMiIsImFpZCI6IjAiLCJuZXQiOiJ3cyIsInR5cGUiOiJub25lIiwiaG9zdCI6IiIsInBhdGgiOiIiLCJ0bHMiOiJ0bHMifQ==",
        "vmess://eyJhZGQiOiJub2RlMS5mcmVlcHJveHkub3JnIiwicG9ydCI6IjgwODAiLCJpZCI6ImFiY2RlZmdoaWprbG1ub3BxcnN0dXZ3IiwgImFpZCI6IjAiLCJuZXQiOiJ0Y3AiLCJ0eXBlIjoibm9uZSIsInBzIjoiVGVzdCBOb2RlIDEifQ==",
        "vmess://eyJhZGQiOiJmcmVlLnZwbi5jb20iLCJwb3J0IjoiNDQzIiwiaWQiOiI1Njc4OTAxMi0zNDU2LTc4OTAtMTIzNDU2Nzg5MDEyIiwiYWlkIjoiMCIsIm5ldCI6IndzIiwidHlwZSI6Im5vbmUiLCJob3N0IjoiIiwicGF0aCI6IiIsInRscyI6InRscyJ9"
    ]
    
    with open('nodes.txt', 'w', encoding='utf-8') as f:
        for link in test_links:
            f.write(link + '\n')
    
    print("✅ 已创建测试 nodes.txt 文件")

print("\n✨ 程序执行完成！")
