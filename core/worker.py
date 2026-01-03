"""
后台工作线程模块
✅ P0修复：集成SQLite存储、身份伪造
✅ P2增强：账号密码Key详细记录
"""
import time
import json
import os
from pathlib import Path
from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal

from .generator import get_unique_username, generate_password
from .registrar import Registrar, RegistrationResult
from .storage import AccountStorage


class RegistrationWorker(QThread):
    """
    后台注册工作线程
    
    负责执行批量注册任务，并通过信号与UI通信
    """
    
    # 信号定义
    log_signal = pyqtSignal(str, str)  # (消息, 级别: info/success/error/warning)
    progress_signal = pyqtSignal(int, int)  # (当前进度, 总数)
    key_obtained = pyqtSignal(str, str, str)  # (username, password, api_key)
    stats_updated = pyqtSignal(int, int, int)  # (成功数, 失败数, key数)
    finished_signal = pyqtSignal()
    
    def __init__(
        self, 
        data_dir: str,
        interval: float = 5.0,
        target_count: int = 0,  # 0表示无限
        max_retries: int = 3,
        use_email_format: bool = True,
        use_fake_ip: bool = True,
        parent=None
    ):
        """
        初始化工作线程
        
        Args:
            data_dir: 数据保存目录
            interval: 注册间隔（秒）
            target_count: 目标注册数量（0表示无限）
            max_retries: 单次注册最大重试次数
            use_email_format: 是否使用邮箱格式用户名
            use_fake_ip: 是否伪造IP
            parent: 父QObject
        """
        super().__init__(parent)
        
        self.data_dir = Path(data_dir)
        self.interval = interval
        self.target_count = target_count
        self.max_retries = max_retries
        self.use_email_format = use_email_format
        self.use_fake_ip = use_fake_ip
        
        # 状态控制
        self._is_paused = False
        self._is_stopped = False
        
        # 统计数据
        self.success_count = 0
        self.failure_count = 0
        self.key_count = 0
        
        # 确保数据目录存在
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 文件路径
        self.keys_file = self.data_dir / "api_keys.txt"
        self.accounts_txt_file = self.data_dir / "accounts_detail.txt"
        
        # 初始化SQLite存储
        self.storage = AccountStorage(str(self.data_dir / "accounts.db"))
        
        # 初始化注册器（使用身份伪造）
        self.registrar = Registrar(use_fake_ip=use_fake_ip)
        
        # 加载已有的Key数量
        self._load_existing_keys()
    
    def _load_existing_keys(self):
        """加载已有的Key数量"""
        stats = self.storage.get_stats()
        self.key_count = stats.get("total", 0)
    
    def _log(self, message: str, level: str = "info"):
        """发送日志信号"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_signal.emit(f"[{timestamp}] {message}", level)
    
    def _save_key(self, username: str, password: str, api_key: str):
        """保存API Key到文件和数据库"""
        # 保存到SQLite数据库
        self.storage.save_account(username, password, api_key)
        
        # 保存到txt（一行一个key）- 用于API中转站导入
        with open(self.keys_file, 'a', encoding='utf-8') as f:
            f.write(f"{api_key}\n")
        
        # 保存到账号详情文件（用户要求的格式）
        with open(self.accounts_txt_file, 'a', encoding='utf-8') as f:
            f.write(f"账号: {username}\n")
            f.write(f"密码: {password}\n")
            f.write(f"Key: {api_key}\n")
            f.write(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("-" * 50 + "\n\n")
        
        self.key_count += 1
    
    def _update_stats(self):
        """更新统计数据"""
        self.stats_updated.emit(self.success_count, self.failure_count, self.key_count)
    
    def pause(self):
        """暂停注册"""
        self._is_paused = True
        self._log("⏸️ 已暂停注册", "warning")
    
    def resume(self):
        """恢复注册"""
        self._is_paused = False
        self._log("▶️ 已恢复注册", "info")
    
    def stop(self):
        """停止注册"""
        self._is_stopped = True
        self._log("⏹️ 正在停止...", "warning")
    
    def is_paused(self) -> bool:
        """是否暂停中"""
        return self._is_paused
    
    def run(self):
        """主运行循环"""
        self._log("🚀 开始批量注册", "info")
        self._log(f"📡 身份伪造: {'启用' if self.use_fake_ip else '禁用'}", "info")
        current_count = 0
        
        while not self._is_stopped:
            # 检查是否达到目标数量
            if self.target_count > 0 and self.success_count >= self.target_count:
                self._log(f"🎉 已达到目标数量 {self.target_count}，停止注册", "success")
                break
            
            # 处理暂停
            while self._is_paused and not self._is_stopped:
                time.sleep(0.5)
            
            if self._is_stopped:
                break
            
            # 生成账号信息（使用唯一用户名生成器）
            username = get_unique_username(use_email_format=self.use_email_format)
            password = generate_password()
            
            self._log(f"📝 正在注册: {username}", "info")
            
            # 尝试注册（带重试）
            result = None
            for attempt in range(self.max_retries):
                if self._is_stopped:
                    break
                
                result = self.registrar.register_and_get_key(username, password)
                
                # 显示使用的身份信息
                if result.identity_info and attempt == 0:
                    self._log(f"🔒 身份: {result.identity_info}", "info")
                
                if result.success:
                    break
                
                # 如果是用户名重复，重新生成用户名
                if result.error and ("exist" in result.error.lower() or "duplicate" in result.error.lower() or "already" in result.error.lower()):
                    self._log(f"⚠️ 用户名已存在，重新生成...", "warning")
                    username = get_unique_username(use_email_format=self.use_email_format)
                    continue
                
                # 如果是限流，增加等待时间
                if result.error and ("429" in str(result.error) or "rate" in result.error.lower() or "limit" in result.error.lower()):
                    wait_time = (attempt + 1) * 10
                    self._log(f"⚠️ 请求被限流，等待 {wait_time} 秒...", "warning")
                    for _ in range(wait_time * 2):
                        if self._is_stopped:
                            break
                        time.sleep(0.5)
                    continue
                
                # 其他错误，短暂等待后重试
                if attempt < self.max_retries - 1:
                    self._log(f"⚠️ 注册失败，重试中 ({attempt + 2}/{self.max_retries})...", "warning")
                    time.sleep(2)
            
            if self._is_stopped:
                break
            
            # 处理结果
            if result and result.success and result.api_key:
                self.success_count += 1
                self._save_key(username, password, result.api_key)
                self._log(f"✅ 注册成功: {username}", "success")
                self._log(f"🔑 获取Key: {result.api_key[:30]}...", "success")
                self.key_obtained.emit(username, password, result.api_key)
            else:
                self.failure_count += 1
                error_msg = result.error if result else "未知错误"
                self._log(f"❌ 注册失败: {error_msg}", "error")
            
            # 更新统计和进度
            self._update_stats()
            current_count += 1
            if self.target_count > 0:
                self.progress_signal.emit(self.success_count, self.target_count)
            
            # 等待间隔
            if not self._is_stopped:
                self._log(f"⏳ 等待 {self.interval} 秒后继续...", "info")
                for _ in range(int(self.interval * 2)):
                    if self._is_stopped:
                        break
                    time.sleep(0.5)
        
        self._log("🏁 注册任务结束", "info")
        self._log(f"📊 统计: 成功 {self.success_count} | 失败 {self.failure_count} | Keys {self.key_count}", "info")
        self.finished_signal.emit()
