import requests
import re
import base64
import json
import socket
import yaml
import logging
from urllib.parse import urlparse, unquote, parse_qs
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class NodeCollector:
    def __init__(self, sources, max_workers=20):
        self.sources = sources
        self.max_workers = max_workers
        self.session = self._create_session()
        
    def _create_session(self):
        session = requests.Session()
        retry = Retry(total=3, backoff_factor=1)
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        session.headers.update({'User-Agent': 'Mozilla/5.0'})
        return session
    
    def fetch_source(self, url):
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            logger.warning(f"获取 {url} 失败: {e}")
            return None
    
    def decode_base64_urls(self, text):
        """尝试解码可能的base64内容"""
        try:
            text = text.strip()
            # 补全base64填充
            missing_padding = len(text) % 4
            if missing_padding:
                text += '=' * (4 - missing_padding)
            decoded = base64.b64decode(text).decode('utf-8', errors='ignore')
            return decoded
        except:
            return text
    
    def parse_uri(self, uri):
        """安全的URI解析"""
        try:
            uri = uri.strip()
            if not uri.startswith(('vmess://', 'vless://', 'trojan://', 'ss://', 'hysteria')):
                return None
                
            parsed = urlparse(uri)
            scheme = parsed.scheme.lower()
            
            # 处理vmess协议
            if scheme == 'vmess':
                return self._parse_vmess(uri, parsed)
            
            # 处理其他协议
            return self._parse_generic(uri, parsed, scheme)
        except Exception as e:
            logger.debug(f"解析URI失败 {uri[:50]}...: {e}")
            return None
    
    def _parse_vmess(self, uri, parsed):
        """解析vmess协议"""
        try:
            # 移除"vmess://"前缀
            encoded = uri[8:]
            decoded = self.decode_base64_urls(encoded)
            v_data = json.loads(decoded)
            
            node = {
                'name': v_data.get('ps', 'vmess-node'),
                'type': 'vmess',
                'server': v_data.get('add'),
                'port': int(v_data.get('port', 443)),
                'uuid': v_data.get('id'),
                'aid': v_data.get('aid', 0),
                'sni': v_data.get('sni', v_data.get('add')),
                'tls': v_data.get('tls') == 'tls'
            }
            return node if node['server'] and node['port'] else None
        except:
            return None
    
    def _parse_generic(self, uri, parsed, scheme):
        """解析通用协议"""
        try:
            # 解析参数
            params = parse_qs(parsed.query)
            user_info = unquote(parsed.username or '') if parsed.username else ''
            
            node = {
                'name': unquote(parsed.fragment or f'{scheme}-node'),
                'type': scheme,
                'server': parsed.hostname,
                'port': parsed.port or 443,
                'sni': params.get('sni', [parsed.hostname])[0] if parsed.hostname else ''
            }
            
            # 协议特定字段
            if scheme == 'vless':
                node['uuid'] = user_info
            elif scheme == 'trojan':
                node['password'] = user_info
            elif scheme in ['hysteria', 'hysteria2', 'hy2']:
                node['type'] = 'hysteria2' if scheme in ['hysteria2', 'hy2'] else 'hysteria'
                node['password'] = user_info or params.get('auth', [''])[0]
            elif scheme == 'ss':
                if ':' in user_info:
                    node['cipher'], node['password'] = user_info.split(':', 1)
                else:
                    node['password'] = user_info
                    node['cipher'] = 'chacha20-ietf-poly1305'
            
            return node if node['server'] and node['port'] else None
        except:
            return None
    
    def check_node(self, node):
        """检查节点可用性"""
        if not node or 'server' not in node or 'port' not in node:
            return None
            
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((node['server'], int(node['port'])))
            sock.close()
            return node if result == 0 else None
        except:
            return None
    
    def collect_nodes(self):
        """收集所有节点"""
        all_nodes = []
        
        for source in self.sources:
            logger.info(f"处理源: {source}")
            content = self.fetch_source(source)
            if not content:
                continue
            
            # 提取URI
            uris = re.findall(r'(?:vmess|vless|trojan|ss|hysteria[2]?)://[^\s\'"<>]+', content)
            
            # 尝试解码可能的base64内容
            decoded = self.decode_base64_urls(content)
            if decoded != content:
                uris.extend(re.findall(r'(?:vmess|vless|trojan|ss|hysteria[2]?)://[^\s\'"<>]+', decoded))
            
            # 解析URI
            for uri in set(uris):
                node = self.parse_uri(uri)
                if node:
                    all_nodes.append(node)
        
        # 去重
        unique_nodes = []
        seen = set()
        for node in all_nodes:
            key = f"{node['server']}:{node['port']}"
            if key not in seen:
                seen.add(key)
                unique_nodes.append(node)
        
        return unique_nodes
    
    def check_nodes(self, nodes):
        """并发检查节点"""
        alive_nodes = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.check_node, node): node for node in nodes}
            
            for future in as_completed(futures):
                result = future.result()
                if result:
                    alive_nodes.append(result)
        
        return alive_nodes
    
    def save_yaml(self, nodes, filename='my_sub.yaml'):
        """保存为YAML格式"""
        proxies = []
        
        for node in nodes:
            proxy = {
                'name': node.get('name', 'unnamed'),
                'type': node['type'],
                'server': node['server'],
                'port': node['port'],
                'skip-cert-verify': True,
                'sni': node.get('sni', node['server'])
            }
            
            # 协议特定字段
            if node['type'] == 'vmess':
                proxy.update({
                    'uuid': node.get('uuid', ''),
                    'alterId': node.get('aid', 0),
                    'cipher': 'auto'
                })
            elif node['type'] == 'vless':
                proxy['uuid'] = node.get('uuid', '')
            elif 'password' in node:
                proxy['password'] = node['password']
            
            proxies.append(proxy)
        
        # 使用yaml库确保格式正确
        with open(filename, 'w', encoding='utf-8') as f:
            yaml.dump({'proxies': proxies}, f, allow_unicode=True, sort_keys=False)
        
        logger.info(f"保存了 {len(proxies)} 个节点到 {filename}")

def main():
    SOURCES = [
        "https://raw.githubusercontent.com/crossxx-labs/free-proxy/main/README.md",
        "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/All_Configs_base64_Sub.txt",
        "https://raw.githubusercontent.com/moez06/V2ray-Configs/main/All_Configs_base64_Sub.txt",
        "https://chromego-sub.netlify.app/sub/merged_proxies_new.yaml",
        "https://raw.githubusercontent.com/Ruk1ng001/freeSub/main/clash.yaml",
        "https://raw.githubusercontent.com/ovmvo/SubShare/refs/heads/main/sub/permanent/mihomo.yaml"
    ]
    
    collector = NodeCollector(SOURCES, max_workers=20)
    
    # 收集节点
    logger.info("开始收集节点...")
    all_nodes = collector.collect_nodes()
    logger.info(f"收集到 {len(all_nodes)} 个节点")
    
    # 检查节点
    logger.info("开始检查节点可用性...")
    alive_nodes = collector.check_nodes(all_nodes)
    logger.info(f"可用节点: {len(alive_nodes)}/{len(all_nodes)}")
    
    # 保存结果
    collector.save_yaml(alive_nodes)
    logger.info("完成!")

if __name__ == '__main__':
    main()
