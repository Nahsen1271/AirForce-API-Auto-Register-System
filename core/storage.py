"""
SQLite账号存储管理器
✅ P0修复：大量数据时性能优化
"""
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime
from typing import List, Dict, Optional


class AccountStorage:
    """账号存储管理器 - 使用SQLite"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    api_key TEXT,
                    status TEXT DEFAULT 'active',
                    validated INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_username ON accounts(username)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON accounts(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_api_key ON accounts(api_key)")
    
    @contextmanager
    def _get_conn(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def save_account(self, username: str, password: str, api_key: str) -> bool:
        """保存账号"""
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO accounts (username, password, api_key) VALUES (?, ?, ?)",
                    (username, password, api_key)
                )
            return True
        except Exception:
            return False
    
    def get_all_accounts(self) -> List[Dict]:
        """获取所有账号"""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT username, password, api_key, status, created_at FROM accounts ORDER BY created_at DESC"
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def get_all_keys(self) -> List[str]:
        """获取所有API Key"""
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT api_key FROM accounts WHERE api_key IS NOT NULL")
            return [row['api_key'] for row in cursor.fetchall()]
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        with self._get_conn() as conn:
            total = conn.execute("SELECT COUNT(*) as c FROM accounts").fetchone()['c']
            validated = conn.execute("SELECT COUNT(*) as c FROM accounts WHERE validated = 1").fetchone()['c']
            today = datetime.now().strftime("%Y-%m-%d")
            today_count = conn.execute(
                "SELECT COUNT(*) as c FROM accounts WHERE date(created_at) = ?", (today,)
            ).fetchone()['c']
            
            return {
                "total": total,
                "validated": validated,
                "today": today_count
            }
    
    def update_validation_status(self, api_key: str, is_valid: bool):
        """更新Key验证状态"""
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE accounts SET validated = ?, status = ? WHERE api_key = ?",
                (1 if is_valid else 0, 'valid' if is_valid else 'invalid', api_key)
            )
    
    def export_keys(self, output_file: str):
        """导出所有Key到文件"""
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT api_key FROM accounts WHERE api_key IS NOT NULL")
            with open(output_file, 'w', encoding='utf-8') as f:
                for row in cursor:
                    f.write(f"{row['api_key']}\n")
    
    def export_accounts_txt(self, output_file: str):
        """导出账号详情到txt文件（用户要求的格式）"""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT username, password, api_key, created_at FROM accounts ORDER BY created_at DESC"
            )
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("AirForce API 账号信息导出\n")
                f.write(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n\n")
                
                for row in cursor:
                    f.write(f"账号: {row['username']}\n")
                    f.write(f"密码: {row['password']}\n")
                    f.write(f"Key: {row['api_key']}\n")
                    f.write(f"创建时间: {row['created_at']}\n")
                    f.write("-" * 40 + "\n\n")
    
    def export_csv(self, output_file: str):
        """导出到CSV"""
        import csv
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT username, password, api_key, status, created_at FROM accounts"
            )
            with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['Username', 'Password', 'API Key', 'Status', 'Created At'])
                writer.writerows(cursor.fetchall())
