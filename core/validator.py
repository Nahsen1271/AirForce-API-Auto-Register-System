"""
API Key验证器
验证Key是否有效，使用OpenAI兼容格式
"""
import httpx
from typing import Tuple, Optional
from .identity import IdentityGenerator


class KeyValidator:
    """API Key验证器"""
    
    CHAT_API_URL = "https://api.airforce/v1/chat/completions"
    
    # 验证用的最小请求
    VALIDATION_PAYLOAD = {
        "model": "mimo-v2-flash",
        "messages": [
            {"role": "system", "content": "test"},
            {"role": "user", "content": "hi"}
        ],
        "stream": False,
        "max_tokens": 5
    }
    
    @classmethod
    def validate_key(cls, api_key: str, timeout: float = 15.0) -> Tuple[bool, Optional[str]]:
        """
        验证API Key是否有效
        
        Args:
            api_key: 要验证的API Key
            timeout: 超时时间
            
        Returns:
            Tuple[bool, Optional[str]]: (是否有效, 错误信息或成功响应)
        """
        try:
            # 生成随机请求头
            headers = IdentityGenerator.generate_headers(include_fake_ip=True)
            headers["Authorization"] = f"Bearer {api_key}"
            
            with httpx.Client(timeout=timeout) as client:
                response = client.post(
                    cls.CHAT_API_URL,
                    headers=headers,
                    json=cls.VALIDATION_PAYLOAD
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # 检查是否有有效响应
                    if "choices" in data and len(data["choices"]) > 0:
                        content = data["choices"][0].get("message", {}).get("content", "")
                        return True, f"Valid - Response: {content[:50]}..."
                    return True, "Valid - Got response"
                
                elif response.status_code == 401:
                    return False, "Invalid API Key"
                
                elif response.status_code == 429:
                    return True, "Valid - Rate limited (but key works)"
                
                else:
                    return False, f"HTTP {response.status_code}"
                    
        except httpx.TimeoutException:
            return False, "Timeout"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    @classmethod
    def quick_validate(cls, api_key: str) -> bool:
        """快速验证（只返回布尔值）"""
        is_valid, _ = cls.validate_key(api_key, timeout=10.0)
        return is_valid


if __name__ == "__main__":
    # 测试验证
    test_key = "sk-air-test123"
    print(f"Testing key: {test_key[:20]}...")
    is_valid, msg = KeyValidator.validate_key(test_key)
    print(f"Valid: {is_valid}, Message: {msg}")
