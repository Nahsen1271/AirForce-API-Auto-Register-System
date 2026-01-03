"""
注册器模块 - 处理API调用
✅ 集成IP/UA伪造，每次请求使用不同身份
"""
import httpx
import json
from typing import Tuple, Optional
from dataclasses import dataclass
from .identity import IdentityGenerator


@dataclass
class RegistrationResult:
    """注册结果"""
    success: bool
    username: str
    password: str
    token: Optional[str] = None
    api_key: Optional[str] = None
    user_id: Optional[str] = None
    error: Optional[str] = None
    identity_info: Optional[str] = None  # 用于显示使用的身份


class Registrar:
    """
    无痕注册器
    
    ✅ 每次请求使用新的HTTP会话，不保留Cookie
    ✅ 每次请求使用随机UA和伪造IP
    """
    
    # API端点
    SIGNUP_URL = "https://api.airforce/auth/signup"
    USER_INFO_URL = "https://api.airforce/api/me"
    
    def __init__(self, timeout: float = 30.0, use_fake_ip: bool = True):
        """
        初始化注册器
        
        Args:
            timeout: 请求超时时间（秒）
            use_fake_ip: 是否使用伪造IP头
        """
        self.timeout = timeout
        self.use_fake_ip = use_fake_ip
    
    def _create_client(self, headers: dict = None) -> httpx.Client:
        """
        创建新的HTTP客户端（无Cookie继承）
        
        Returns:
            httpx.Client: 新的HTTP客户端
        """
        if headers is None:
            headers = IdentityGenerator.generate_headers(include_fake_ip=self.use_fake_ip)
        
        return httpx.Client(
            headers=headers,
            timeout=self.timeout,
            follow_redirects=True,
        )
    
    def register(self, username: str, password: str) -> RegistrationResult:
        """
        注册新账号
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            RegistrationResult: 注册结果
        """
        # 为这次注册生成新的身份
        headers = IdentityGenerator.generate_headers(include_fake_ip=self.use_fake_ip)
        identity_info = IdentityGenerator.get_identity_info(headers)
        
        result = RegistrationResult(
            success=False,
            username=username,
            password=password,
            identity_info=identity_info
        )
        
        try:
            # 创建新的HTTP客户端
            with self._create_client(headers) as client:
                # 发送注册请求
                response = client.post(
                    self.SIGNUP_URL,
                    json={"username": username, "password": password}
                )
                
                # 解析响应
                if response.status_code == 200 or response.status_code == 201:
                    # 注册成功
                    data = response.json()
                    
                    # 尝试从响应中获取token
                    token = None
                    
                    # 方式1: 从响应体获取
                    if "token" in data:
                        token = data["token"]
                    elif "access_token" in data:
                        token = data["access_token"]
                    
                    # 方式2: 从Cookie获取
                    if not token:
                        for cookie in response.cookies.jar:
                            if "token" in cookie.name.lower():
                                token = cookie.value
                                break
                    
                    # 方式3: 从响应头获取
                    if not token:
                        auth_header = response.headers.get("Authorization", "")
                        if auth_header.startswith("Bearer "):
                            token = auth_header[7:]
                    
                    # 方式4: 检查Set-Cookie头
                    if not token:
                        set_cookie = response.headers.get("Set-Cookie", "")
                        if "token=" in set_cookie:
                            for part in set_cookie.split(";"):
                                if part.strip().startswith("token="):
                                    token = part.strip()[6:]
                                    break
                    
                    result.success = True
                    result.token = token
                    
                    # 如果响应中直接包含api_key
                    if "api_key" in data:
                        result.api_key = data["api_key"]
                    if "id" in data:
                        result.user_id = data["id"]
                    
                elif response.status_code == 400:
                    # 请求错误（如用户名已存在）
                    try:
                        error_data = response.json()
                        result.error = error_data.get("error", error_data.get("message", "Registration failed"))
                    except:
                        result.error = f"Registration failed: HTTP {response.status_code}"
                        
                elif response.status_code == 429:
                    result.error = "Rate limited - too many requests"
                    
                else:
                    result.error = f"Unknown error: HTTP {response.status_code}"
                    
        except httpx.TimeoutException:
            result.error = "Request timeout"
        except httpx.ConnectError:
            result.error = "Connection failed"
        except Exception as e:
            result.error = f"Request error: {str(e)}"
        
        return result
    
    def get_api_key(self, token: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        获取API Key
        
        Args:
            token: JWT Token
            
        Returns:
            Tuple[bool, Optional[str], Optional[str]]: (成功标志, api_key, 错误信息)
        """
        try:
            # 使用新的身份请求
            headers = IdentityGenerator.generate_headers(include_fake_ip=self.use_fake_ip)
            
            with self._create_client(headers) as client:
                # 添加Authorization头
                auth_headers = {"Authorization": f"Bearer {token}"}
                
                # 发送请求
                response = client.get(self.USER_INFO_URL, headers=auth_headers)
                
                if response.status_code == 200:
                    data = response.json()
                    api_key = data.get("api_key")
                    if api_key:
                        return True, api_key, None
                    else:
                        return False, None, "api_key not found in response"
                else:
                    return False, None, f"Get user info failed: HTTP {response.status_code}"
                    
        except Exception as e:
            return False, None, f"Request error: {str(e)}"
    
    def register_and_get_key(self, username: str, password: str) -> RegistrationResult:
        """
        完整的注册流程：注册账号并获取API Key
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            RegistrationResult: 包含完整信息的注册结果
        """
        # 第一步：注册
        result = self.register(username, password)
        
        if not result.success:
            return result
        
        # 如果注册响应中已经包含api_key，直接返回
        if result.api_key:
            return result
        
        # 第二步：获取API Key（如果有token）
        if result.token:
            success, api_key, error = self.get_api_key(result.token)
            if success:
                result.api_key = api_key
            else:
                # 获取key失败，但注册成功
                result.error = f"Registered but failed to get Key: {error}"
        else:
            result.error = "Registered but no token received, cannot get API Key"
        
        return result


if __name__ == "__main__":
    # 测试代码
    from generator import get_unique_username, generate_password
    
    registrar = Registrar()
    username = get_unique_username()
    password = generate_password()
    
    print(f"Testing registration:")
    print(f"  Username: {username}")
    print(f"  Password: {password}")
    
    result = registrar.register_and_get_key(username, password)
    print(f"\nResult:")
    print(f"  Success: {result.success}")
    print(f"  Identity: {result.identity_info}")
    print(f"  API Key: {result.api_key}")
    print(f"  Error: {result.error}")
