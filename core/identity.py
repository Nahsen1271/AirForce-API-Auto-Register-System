"""
IP/UA伪造模块
深度模拟真实浏览器环境，每次请求使用不同的身份
"""
import random
from typing import Dict, Tuple


class IdentityGenerator:
    """身份生成器 - 用于伪造真实的浏览器环境"""
    
    # 常见Chrome版本
    CHROME_VERSIONS = [
        "120.0.0.0", "121.0.0.0", "122.0.0.0", "123.0.0.0", "124.0.0.0",
        "125.0.0.0", "126.0.0.0", "127.0.0.0", "128.0.0.0", "129.0.0.0",
        "130.0.0.0", "131.0.0.0", "132.0.0.0", "133.0.0.0", "134.0.0.0",
        "135.0.0.0", "136.0.0.0", "137.0.0.0", "138.0.0.0", "139.0.0.0",
        "140.0.0.0", "141.0.0.0", "142.0.0.0", "143.0.0.0"
    ]
    
    # 常见操作系统
    OS_LIST = [
        ("Windows NT 10.0; Win64; x64", "Windows"),
        ("Windows NT 11.0; Win64; x64", "Windows"),
        ("Macintosh; Intel Mac OS X 10_15_7", "macOS"),
        ("Macintosh; Intel Mac OS X 11_6_0", "macOS"),
        ("Macintosh; Intel Mac OS X 12_0_0", "macOS"),
        ("Macintosh; Intel Mac OS X 13_0_0", "macOS"),
        ("X11; Linux x86_64", "Linux"),
        ("X11; Ubuntu; Linux x86_64", "Linux"),
    ]
    
    # 常见语言设置
    LANGUAGES = [
        "zh-CN,zh;q=0.9,en;q=0.8",
        "en-US,en;q=0.9",
        "zh-TW,zh;q=0.9,en;q=0.8",
        "ja-JP,ja;q=0.9,en;q=0.8",
        "ko-KR,ko;q=0.9,en;q=0.8",
        "en-GB,en;q=0.9",
        "de-DE,de;q=0.9,en;q=0.8",
        "fr-FR,fr;q=0.9,en;q=0.8",
    ]
    
    # 常见Referer来源
    REFERERS = [
        "https://api.airforce/signup/",
        "https://api.airforce/",
        "https://www.google.com/",
        "https://www.bing.com/",
        "https://github.com/",
        "https://reddit.com/",
    ]
    
    # 随机客户端应用
    CLIENT_APPS = [
        ("CherryStudio/1.7.8", "Cherry Studio", "https://cherry-ai.com"),
        ("NextChat/2.0", "NextChat", "https://nextchat.dev"),
        ("ChatGPT-Next-Web/2.0", "ChatGPT Web", "https://chatgpt.com"),
        ("LobeChat/1.0", "Lobe Chat", "https://lobechat.com"),
        (None, None, None),  # 普通浏览器，不带应用标识
        (None, None, None),
        (None, None, None),
    ]
    
    @classmethod
    def generate_user_agent(cls) -> str:
        """生成随机User-Agent"""
        chrome_version = random.choice(cls.CHROME_VERSIONS)
        os_string, _ = random.choice(cls.OS_LIST)
        
        # 基础UA模板
        ua = f"Mozilla/5.0 ({os_string}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36"
        
        # 随机添加Electron应用标识
        app = random.choice(cls.CLIENT_APPS)
        if app[0]:
            ua = f"Mozilla/5.0 ({os_string}) AppleWebKit/537.36 (KHTML, like Gecko) {app[0]} Chrome/{chrome_version} Electron/28.0.0 Safari/537.36"
        
        return ua
    
    @classmethod
    def generate_sec_ch_ua(cls, chrome_version: str = None) -> str:
        """生成sec-ch-ua头"""
        if not chrome_version:
            chrome_version = random.choice(cls.CHROME_VERSIONS)
        major_version = chrome_version.split('.')[0]
        
        # 随机选择Not A Brand格式
        not_a_brand_formats = [
            '"Not/A)Brand"',
            '"Not A(Brand"',
            '"Not=A?Brand"',
            '"Not.A/Brand"',
        ]
        not_a_brand = random.choice(not_a_brand_formats)
        
        return f'"Google Chrome";v="{major_version}", "Chromium";v="{major_version}", {not_a_brand};v="24"'
    
    @classmethod
    def generate_fake_ip(cls) -> Tuple[str, str]:
        """
        生成伪造的IP相关头
        注意：这只是HTTP头伪造，服务器可能不信任这些头
        返回: (X-Forwarded-For, X-Real-IP)
        """
        # 生成随机IP地址
        def random_ip():
            # 避免保留IP段
            while True:
                ip = f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
                # 排除一些保留段
                first_octet = int(ip.split('.')[0])
                if first_octet not in [10, 127, 169, 172, 192, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239]:
                    return ip
        
        ip = random_ip()
        return ip, ip
    
    @classmethod
    def generate_headers(cls, include_fake_ip: bool = True) -> Dict[str, str]:
        """
        生成完整的伪造请求头
        
        Args:
            include_fake_ip: 是否包含伪造IP头（某些服务器可能不接受）
        
        Returns:
            Dict: 完整的HTTP请求头
        """
        chrome_version = random.choice(cls.CHROME_VERSIONS)
        major_version = chrome_version.split('.')[0]
        os_string, os_platform = random.choice(cls.OS_LIST)
        
        # 构建User-Agent
        app = random.choice(cls.CLIENT_APPS)
        if app[0]:
            user_agent = f"Mozilla/5.0 ({os_string}) AppleWebKit/537.36 (KHTML, like Gecko) {app[0]} Chrome/{chrome_version} Electron/28.0.0 Safari/537.36"
            x_title = app[1]
            http_referer = app[2]
        else:
            user_agent = f"Mozilla/5.0 ({os_string}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36"
            x_title = None
            http_referer = random.choice(cls.REFERERS)
        
        headers = {
            "Accept": "*/*",
            "Accept-Language": random.choice(cls.LANGUAGES),
            "Content-Type": "application/json",
            "Origin": "https://api.airforce",
            "Referer": http_referer or "https://api.airforce/signup/",
            "User-Agent": user_agent,
            "sec-ch-ua": cls.generate_sec_ch_ua(chrome_version),
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": f'"{os_platform}"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": random.choice(["same-origin", "cross-site"]),
        }
        
        # 添加客户端应用标识
        if x_title:
            headers["x-title"] = x_title
            headers["http-referer"] = http_referer
        
        # 添加伪造IP头
        if include_fake_ip:
            xff, xrip = cls.generate_fake_ip()
            headers["X-Forwarded-For"] = xff
            headers["X-Real-IP"] = xrip
            # 随机添加更多代理相关头
            if random.random() > 0.5:
                headers["X-Originating-IP"] = xrip
            if random.random() > 0.7:
                headers["CF-Connecting-IP"] = xrip
        
        return headers
    
    @classmethod
    def get_identity_info(cls, headers: Dict[str, str]) -> str:
        """获取身份信息摘要（用于日志显示）"""
        ua = headers.get("User-Agent", "")
        ip = headers.get("X-Forwarded-For", "N/A")
        
        # 提取浏览器版本
        if "Chrome/" in ua:
            chrome_ver = ua.split("Chrome/")[1].split(" ")[0].split(".")[0]
        else:
            chrome_ver = "?"
        
        # 提取操作系统
        if "Windows" in ua:
            os_name = "Win"
        elif "Mac" in ua:
            os_name = "Mac"
        elif "Linux" in ua:
            os_name = "Linux"
        else:
            os_name = "?"
        
        return f"Chrome{chrome_ver}/{os_name} IP:{ip}"


if __name__ == "__main__":
    print("=" * 60)
    print("Identity Generator Test")
    print("=" * 60)
    
    for i in range(5):
        headers = IdentityGenerator.generate_headers()
        info = IdentityGenerator.get_identity_info(headers)
        print(f"\n[{i+1}] {info}")
        print(f"    UA: {headers['User-Agent'][:80]}...")
