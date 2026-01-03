"""
主窗口UI模块
✅ 大师级UI/UX设计
✅ P2增强：实时速率、进度条、日志过滤、导出功能、统计图表、Key验证
"""
import os
import csv
import time
from pathlib import Path
from datetime import datetime
from collections import deque
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QTextEdit, QSpinBox, QListWidget,
    QFrame, QGroupBox, QSplitter, QMessageBox, QApplication,
    QListWidgetItem, QCheckBox, QProgressBar, QComboBox,
    QTabWidget, QFileDialog, QMenu
)
from PyQt6.QtCore import Qt, QSize, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QIcon, QAction

from core.worker import RegistrationWorker
from core.validator import KeyValidator


# 主题样式
THEMES = {
    "dark": {
        "name": "🌙 深色主题",
        "bg_primary": "#0f172a",
        "bg_secondary": "#1e293b",
        "bg_tertiary": "#334155",
        "text_primary": "#f1f5f9",
        "text_secondary": "#94a3b8",
        "accent_blue": "#3b82f6",
        "accent_green": "#22c55e",
        "accent_red": "#ef4444",
        "accent_yellow": "#f59e0b",
        "accent_purple": "#8b5cf6",
        "border": "#334155",
    },
    "light": {
        "name": "☀️ 浅色主题",
        "bg_primary": "#f8fafc",
        "bg_secondary": "#ffffff",
        "bg_tertiary": "#e2e8f0",
        "text_primary": "#1e293b",
        "text_secondary": "#64748b",
        "accent_blue": "#3b82f6",
        "accent_green": "#22c55e",
        "accent_red": "#ef4444",
        "accent_yellow": "#f59e0b",
        "accent_purple": "#8b5cf6",
        "border": "#e2e8f0",
    },
    "ocean": {
        "name": "🌊 海洋主题",
        "bg_primary": "#0c4a6e",
        "bg_secondary": "#075985",
        "bg_tertiary": "#0369a1",
        "text_primary": "#f0f9ff",
        "text_secondary": "#bae6fd",
        "accent_blue": "#38bdf8",
        "accent_green": "#34d399",
        "accent_red": "#fb7185",
        "accent_yellow": "#fcd34d",
        "accent_purple": "#c4b5fd",
        "border": "#0369a1",
    },
}


class StatCard(QFrame):
    """统计数据卡片组件"""
    
    def __init__(self, icon: str, title: str, value: str = "0", color: str = "#3b82f6", parent=None):
        super().__init__(parent)
        self.icon = icon
        self.color = color
        self._setup_ui(title, value)
    
    def _setup_ui(self, title: str, value: str):
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # 图标和标题行
        header = QHBoxLayout()
        self.icon_label = QLabel(self.icon)
        self.icon_label.setStyleSheet(f"font-size: 18px;")
        header.addWidget(self.icon_label)
        
        self.title_label = QLabel(title)
        self.title_label.setObjectName("stat_title")
        header.addWidget(self.title_label)
        header.addStretch()
        layout.addLayout(header)
        
        # 数值
        self.value_label = QLabel(value)
        self.value_label.setObjectName("stat_value")
        self.value_label.setStyleSheet(f"color: {self.color}; font-size: 28px; font-weight: bold;")
        layout.addWidget(self.value_label)
    
    def set_value(self, value):
        """更新数值"""
        self.value_label.setText(str(value))
    
    def apply_theme(self, theme: dict):
        """应用主题"""
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {theme['bg_secondary']};
                border-radius: 12px;
                border: 1px solid {theme['border']};
            }}
        """)
        self.title_label.setStyleSheet(f"color: {theme['text_secondary']}; font-size: 13px;")


class MainWindow(QMainWindow):
    """主窗口 - 大师级UI设计"""
    
    def __init__(self):
        super().__init__()
        
        # 当前主题
        self.current_theme_name = "dark"
        self.theme = THEMES[self.current_theme_name]
        
        # 设置窗口属性
        self.setWindowTitle("🚀 AirForce API Auto Register v2.0")
        self.setMinimumSize(1100, 800)
        self.resize(1200, 850)
        
        # 数据目录
        self.data_dir = Path(__file__).parent.parent / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 工作线程
        self.worker = None
        
        # 速率计算
        self.rate_history = deque(maxlen=60)
        
        # 日志历史
        self.all_logs = []
        
        # 创建UI
        self._setup_ui()
        
        # 应用初始主题
        self._apply_theme()
        
        # 加载已有的Keys
        self._load_existing_keys()
        
        # 启动速率计算定时器
        self.rate_timer = QTimer()
        self.rate_timer.timeout.connect(self._update_rate)
        self.rate_timer.start(1000)
    
    def _setup_ui(self):
        """设置UI布局"""
        # 中央容器
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # === 顶部标题栏 ===
        header_layout = QHBoxLayout()
        
        title_label = QLabel("🚀 AirForce API Auto Register")
        title_label.setObjectName("main_title")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # 主题切换
        self.theme_combo = QComboBox()
        for key, value in THEMES.items():
            self.theme_combo.addItem(value["name"], key)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        header_layout.addWidget(QLabel("主题:"))
        header_layout.addWidget(self.theme_combo)
        
        main_layout.addLayout(header_layout)
        
        # === 统计卡片区 ===
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(12)
        
        self.success_card = StatCard("✅", "成功注册", "0", "#22c55e")
        self.failure_card = StatCard("❌", "失败次数", "0", "#ef4444")
        self.keys_card = StatCard("🔑", "获取Keys", "0", "#3b82f6")
        self.rate_card = StatCard("⚡", "注册速率", "0/min", "#8b5cf6")
        self.status_card = StatCard("📡", "运行状态", "待机", "#f59e0b")
        
        for card in [self.success_card, self.failure_card, self.keys_card, self.rate_card, self.status_card]:
            stats_layout.addWidget(card)
        
        main_layout.addLayout(stats_layout)
        
        # === 控制面板区 ===
        control_group = QGroupBox("⚙️ 控制面板")
        control_group.setObjectName("control_group")
        control_layout = QHBoxLayout(control_group)
        control_layout.setSpacing(20)
        
        # 注册间隔
        interval_layout = QVBoxLayout()
        interval_label = QLabel("⏱️ 注册间隔")
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 120)
        self.interval_spin.setValue(5)
        self.interval_spin.setSuffix(" 秒")
        self.interval_spin.setToolTip("每次注册之间的等待时间（建议5秒以上防止限流）")
        interval_layout.addWidget(interval_label)
        interval_layout.addWidget(self.interval_spin)
        control_layout.addLayout(interval_layout)
        
        # 目标数量
        target_layout = QVBoxLayout()
        target_label = QLabel("🎯 目标数量")
        self.target_spin = QSpinBox()
        self.target_spin.setRange(0, 100000)
        self.target_spin.setValue(0)
        self.target_spin.setSpecialValueText("无限")
        self.target_spin.setToolTip("要注册的账号数量（0表示无限）")
        target_layout.addWidget(target_label)
        target_layout.addWidget(self.target_spin)
        control_layout.addLayout(target_layout)
        
        # 选项
        options_layout = QVBoxLayout()
        self.email_format_cb = QCheckBox("📧 邮箱格式用户名")
        self.email_format_cb.setChecked(True)
        self.email_format_cb.setToolTip("使用邮箱格式确保用户名唯一（推荐）")
        
        self.fake_ip_cb = QCheckBox("🔒 IP/UA伪造")
        self.fake_ip_cb.setChecked(True)
        self.fake_ip_cb.setToolTip("每次请求使用不同的IP和浏览器身份")
        
        options_layout.addWidget(self.email_format_cb)
        options_layout.addWidget(self.fake_ip_cb)
        control_layout.addLayout(options_layout)
        
        control_layout.addStretch()
        
        # 按钮组
        btn_layout = QVBoxLayout()
        btn_row1 = QHBoxLayout()
        
        self.start_btn = QPushButton("▶ 开始注册")
        self.start_btn.setObjectName("startBtn")
        self.start_btn.setMinimumWidth(120)
        self.start_btn.clicked.connect(self._on_start)
        
        self.pause_btn = QPushButton("⏸ 暂停")
        self.pause_btn.setObjectName("pauseBtn")
        self.pause_btn.setMinimumWidth(100)
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self._on_pause)
        
        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.setMinimumWidth(100)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop)
        
        btn_row1.addWidget(self.start_btn)
        btn_row1.addWidget(self.pause_btn)
        btn_row1.addWidget(self.stop_btn)
        btn_layout.addLayout(btn_row1)
        
        control_layout.addLayout(btn_layout)
        
        main_layout.addWidget(control_group)
        
        # === 进度条 ===
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("main_progress")
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setMinimumHeight(25)
        main_layout.addWidget(self.progress_bar)
        
        # === 主内容区（标签页）===
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("main_tabs")
        
        # Tab 1: 日志
        log_tab = QWidget()
        log_layout = QVBoxLayout(log_tab)
        
        # 日志过滤器
        log_filter_layout = QHBoxLayout()
        log_filter_layout.addWidget(QLabel("📋 日志级别:"))
        self.log_filter_combo = QComboBox()
        self.log_filter_combo.addItems(["全部", "信息", "成功", "警告", "错误"])
        self.log_filter_combo.currentTextChanged.connect(self._filter_logs)
        log_filter_layout.addWidget(self.log_filter_combo)
        log_filter_layout.addStretch()
        
        clear_log_btn = QPushButton("🗑️ 清空日志")
        clear_log_btn.clicked.connect(self._clear_logs)
        log_filter_layout.addWidget(clear_log_btn)
        log_layout.addLayout(log_filter_layout)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(200)
        log_layout.addWidget(self.log_text)
        
        self.tab_widget.addTab(log_tab, "📋 实时日志")
        
        # Tab 2: Keys列表
        keys_tab = QWidget()
        keys_layout = QVBoxLayout(keys_tab)
        
        self.keys_list = QListWidget()
        self.keys_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.keys_list.customContextMenuRequested.connect(self._show_key_context_menu)
        keys_layout.addWidget(self.keys_list)
        
        # 按钮行
        keys_btn_layout = QHBoxLayout()
        
        copy_btn = QPushButton("📋 复制所有")
        copy_btn.clicked.connect(self._copy_all_keys)
        keys_btn_layout.addWidget(copy_btn)
        
        validate_btn = QPushButton("🔍 验证选中")
        validate_btn.clicked.connect(self._validate_selected_key)
        keys_btn_layout.addWidget(validate_btn)
        
        export_txt_btn = QPushButton("📁 导出TXT")
        export_txt_btn.clicked.connect(self._open_keys_file)
        keys_btn_layout.addWidget(export_txt_btn)
        
        export_csv_btn = QPushButton("📊 导出CSV")
        export_csv_btn.clicked.connect(self._export_to_csv)
        keys_btn_layout.addWidget(export_csv_btn)
        
        keys_layout.addLayout(keys_btn_layout)
        
        self.tab_widget.addTab(keys_tab, "🔑 API Keys")
        
        # Tab 3: 帮助
        help_tab = QWidget()
        help_layout = QVBoxLayout(help_tab)
        
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setHtml("""
        <h2>🚀 AirForce API 自动注册系统 v2.0</h2>
        <hr>
        
        <h3>📖 使用说明</h3>
        <ol>
            <li><b>设置参数</b>：调整注册间隔（建议5秒以上）和目标数量</li>
            <li><b>选择选项</b>：
                <ul>
                    <li>📧 邮箱格式：使用邮箱作为用户名，确保亿万次不重复</li>
                    <li>🔒 IP/UA伪造：每次请求使用不同身份，模拟真实用户</li>
                </ul>
            </li>
            <li><b>点击开始</b>：系统将自动批量注册并保存Key</li>
        </ol>
        
        <h3>📂 数据文件说明</h3>
        <ul>
            <li><b>api_keys.txt</b>：纯Key列表，一行一个，可直接导入API中转站</li>
            <li><b>accounts_detail.txt</b>：账号详情（账号/密码/Key），方便溯源</li>
            <li><b>accounts.db</b>：SQLite数据库，支持大量数据</li>
        </ul>
        
        <h3>⚠️ 注意事项</h3>
        <ul>
            <li>注册间隔过短可能触发限流（429错误）</li>
            <li>系统会自动处理用户名重复和限流错误</li>
            <li>所有数据本地保存，请妥善保管</li>
        </ul>
        
        <h3>🔧 技术特性</h3>
        <ul>
            <li>✅ 线程安全的用户名生成器（支持并发）</li>
            <li>✅ SQLite存储（优化大量数据性能）</li>
            <li>✅ IP/UA伪造（模拟真实浏览器环境）</li>
            <li>✅ 自动错误重试（指数退避策略）</li>
        </ul>
        """)
        help_layout.addWidget(help_text)
        
        self.tab_widget.addTab(help_tab, "❓ 帮助")
        
        main_layout.addWidget(self.tab_widget, 1)
        
        # 添加欢迎日志
        self._add_log("🎉 欢迎使用 AirForce API 自动注册系统 v2.0", "success")
        self._add_log(f"📁 数据保存位置: {self.data_dir}", "info")
        self._add_log("💡 提示: 建议注册间隔设置为5秒以上，避免被限流", "info")
    
    def _get_stylesheet(self) -> str:
        """生成主题样式表"""
        t = self.theme
        return f"""
            QMainWindow {{
                background-color: {t['bg_primary']};
            }}
            QWidget {{
                color: {t['text_primary']};
                font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif;
            }}
            #main_title {{
                font-size: 26px;
                font-weight: bold;
                color: {t['text_primary']};
            }}
            QGroupBox {{
                font-size: 14px;
                font-weight: bold;
                border: 1px solid {t['border']};
                border-radius: 10px;
                margin-top: 12px;
                padding-top: 12px;
                background-color: {t['bg_secondary']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
                color: {t['text_secondary']};
            }}
            QPushButton {{
                background-color: {t['accent_blue']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                min-height: 36px;
            }}
            QPushButton:hover {{
                background-color: {t['accent_blue']}dd;
            }}
            QPushButton:pressed {{
                background-color: {t['accent_blue']}aa;
            }}
            QPushButton:disabled {{
                background-color: {t['bg_tertiary']};
                color: {t['text_secondary']};
            }}
            #startBtn {{
                background-color: {t['accent_green']};
            }}
            #startBtn:hover {{
                background-color: {t['accent_green']}dd;
            }}
            #pauseBtn {{
                background-color: {t['accent_yellow']};
            }}
            #pauseBtn:hover {{
                background-color: {t['accent_yellow']}dd;
            }}
            #stopBtn {{
                background-color: {t['accent_red']};
            }}
            #stopBtn:hover {{
                background-color: {t['accent_red']}dd;
            }}
            QSpinBox, QComboBox {{
                background-color: {t['bg_secondary']};
                border: 1px solid {t['border']};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
                min-width: 100px;
                min-height: 20px;
            }}
            QSpinBox:focus, QComboBox:focus {{
                border-color: {t['accent_blue']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            QTextEdit {{
                background-color: {t['bg_primary']};
                border: 1px solid {t['border']};
                border-radius: 8px;
                padding: 12px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 13px;
            }}
            QListWidget {{
                background-color: {t['bg_primary']};
                border: 1px solid {t['border']};
                border-radius: 8px;
                padding: 8px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
            }}
            QListWidget::item {{
                padding: 8px 10px;
                border-radius: 4px;
                margin: 2px 0;
            }}
            QListWidget::item:selected {{
                background-color: {t['bg_tertiary']};
            }}
            QListWidget::item:hover {{
                background-color: {t['bg_secondary']};
            }}
            QCheckBox {{
                font-size: 13px;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border-radius: 4px;
                border: 2px solid {t['border']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {t['accent_blue']};
                border-color: {t['accent_blue']};
            }}
            #main_progress {{
                border: none;
                border-radius: 12px;
                text-align: center;
                background-color: {t['bg_secondary']};
                font-weight: bold;
            }}
            #main_progress::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {t['accent_blue']}, stop:1 {t['accent_purple']});
                border-radius: 11px;
            }}
            QTabWidget::pane {{
                border: 1px solid {t['border']};
                border-radius: 8px;
                background-color: {t['bg_secondary']};
            }}
            QTabBar::tab {{
                background-color: {t['bg_tertiary']};
                color: {t['text_secondary']};
                padding: 10px 20px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }}
            QTabBar::tab:selected {{
                background-color: {t['bg_secondary']};
                color: {t['text_primary']};
            }}
            QTabBar::tab:hover {{
                background-color: {t['bg_secondary']};
            }}
            QScrollBar:vertical {{
                background-color: {t['bg_primary']};
                width: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {t['bg_tertiary']};
                border-radius: 6px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {t['accent_blue']};
            }}
        """
    
    def _apply_theme(self):
        """应用当前主题"""
        self.setStyleSheet(self._get_stylesheet())
        
        # 更新统计卡片
        for card in [self.success_card, self.failure_card, self.keys_card, self.rate_card, self.status_card]:
            card.apply_theme(self.theme)
    
    def _on_theme_changed(self, index: int):
        """主题切换"""
        theme_key = self.theme_combo.currentData()
        self.current_theme_name = theme_key
        self.theme = THEMES[theme_key]
        self._apply_theme()
        self._add_log(f"🎨 已切换到 {THEMES[theme_key]['name']}", "info")
    
    def _add_log(self, message: str, level: str = "info"):
        """添加日志消息"""
        colors = {
            "info": self.theme["accent_blue"],
            "success": self.theme["accent_green"],
            "error": self.theme["accent_red"],
            "warning": self.theme["accent_yellow"]
        }
        color = colors.get(level, self.theme["text_primary"])
        
        # 保存到历史
        self.all_logs.append((message, level))
        
        # 检查过滤
        filter_map = {"全部": "all", "信息": "info", "成功": "success", "警告": "warning", "错误": "error"}
        current_filter = filter_map.get(self.log_filter_combo.currentText(), "all")
        
        if current_filter != "all" and level != current_filter:
            return
        
        # HTML格式化消息
        html = f'<span style="color: {color};">{message}</span><br>'
        
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)
        self.log_text.insertHtml(html)
        
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _clear_logs(self):
        """清空日志"""
        self.log_text.clear()
        self.all_logs.clear()
    
    def _filter_logs(self):
        """过滤日志"""
        self.log_text.clear()
        filter_map = {"全部": "all", "信息": "info", "成功": "success", "警告": "warning", "错误": "error"}
        current_filter = filter_map.get(self.log_filter_combo.currentText(), "all")
        
        for message, level in self.all_logs:
            if current_filter == "all" or level == current_filter:
                colors = {
                    "info": self.theme["accent_blue"],
                    "success": self.theme["accent_green"],
                    "error": self.theme["accent_red"],
                    "warning": self.theme["accent_yellow"]
                }
                color = colors.get(level, self.theme["text_primary"])
                html = f'<span style="color: {color};">{message}</span><br>'
                self.log_text.insertHtml(html)
    
    def _update_rate(self):
        """更新注册速率"""
        now = time.time()
        # 清理60秒前的数据
        while self.rate_history and now - self.rate_history[0] > 60:
            self.rate_history.popleft()
        
        if len(self.rate_history) >= 1:
            time_span = max(1, now - self.rate_history[0]) if self.rate_history else 60
            count = len(self.rate_history)
            rate = (count / time_span) * 60
            self.rate_card.set_value(f"{rate:.1f}/min")
        else:
            self.rate_card.set_value("0/min")
    
    def _load_existing_keys(self):
        """加载已有的Keys"""
        keys_file = self.data_dir / "api_keys.txt"
        if keys_file.exists():
            with open(keys_file, 'r', encoding='utf-8') as f:
                for line in f:
                    key = line.strip()
                    if key:
                        self._add_key_to_list(key)
            
            count = self.keys_list.count()
            if count > 0:
                self._add_log(f"📂 已加载 {count} 个已保存的Keys", "info")
                self.keys_card.set_value(count)
    
    def _add_key_to_list(self, api_key: str):
        """添加Key到列表"""
        item = QListWidgetItem(api_key)
        item.setForeground(QColor(self.theme["accent_green"]))
        self.keys_list.addItem(item)
        self.keys_list.scrollToBottom()
    
    def _show_key_context_menu(self, position):
        """显示Key右键菜单"""
        menu = QMenu()
        copy_action = menu.addAction("📋 复制")
        validate_action = menu.addAction("🔍 验证")
        
        action = menu.exec(self.keys_list.mapToGlobal(position))
        
        if action == copy_action:
            item = self.keys_list.currentItem()
            if item:
                QApplication.clipboard().setText(item.text())
                self._add_log("📋 已复制Key到剪贴板", "success")
        elif action == validate_action:
            self._validate_selected_key()
    
    def _validate_selected_key(self):
        """验证选中的Key"""
        item = self.keys_list.currentItem()
        if not item:
            self._add_log("⚠️ 请先选择一个Key", "warning")
            return
        
        key = item.text()
        self._add_log(f"🔍 正在验证Key: {key[:20]}...", "info")
        
        is_valid, msg = KeyValidator.validate_key(key)
        if is_valid:
            item.setForeground(QColor(self.theme["accent_green"]))
            self._add_log(f"✅ Key有效: {msg}", "success")
        else:
            item.setForeground(QColor(self.theme["accent_red"]))
            self._add_log(f"❌ Key无效: {msg}", "error")
    
    def _on_start(self):
        """开始注册"""
        if self.worker and self.worker.isRunning():
            return
        
        # 创建工作线程
        self.worker = RegistrationWorker(
            data_dir=str(self.data_dir),
            interval=self.interval_spin.value(),
            target_count=self.target_spin.value(),
            use_email_format=self.email_format_cb.isChecked(),
            use_fake_ip=self.fake_ip_cb.isChecked()
        )
        
        # 连接信号
        self.worker.log_signal.connect(self._add_log)
        self.worker.stats_updated.connect(self._update_stats)
        self.worker.key_obtained.connect(self._on_key_obtained)
        self.worker.progress_signal.connect(self._update_progress)
        self.worker.finished_signal.connect(self._on_finished)
        
        # 更新UI状态
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.interval_spin.setEnabled(False)
        self.target_spin.setEnabled(False)
        self.email_format_cb.setEnabled(False)
        self.fake_ip_cb.setEnabled(False)
        self.status_card.set_value("运行中")
        self.status_card.value_label.setStyleSheet(f"color: {self.theme['accent_green']}; font-size: 28px; font-weight: bold;")
        
        # 显示进度条
        if self.target_spin.value() > 0:
            self.progress_bar.setVisible(True)
            self.progress_bar.setMaximum(self.target_spin.value())
            self.progress_bar.setValue(0)
        
        # 启动线程
        self.worker.start()
    
    def _update_progress(self, current: int, total: int):
        """更新进度条"""
        self.progress_bar.setValue(current)
        percent = (current / total * 100) if total > 0 else 0
        self.progress_bar.setFormat(f"{current}/{total} ({percent:.1f}%)")
    
    def _on_pause(self):
        """暂停/恢复"""
        if not self.worker:
            return
        
        if self.worker.is_paused():
            self.worker.resume()
            self.pause_btn.setText("⏸ 暂停")
            self.status_card.set_value("运行中")
            self.status_card.value_label.setStyleSheet(f"color: {self.theme['accent_green']}; font-size: 28px; font-weight: bold;")
        else:
            self.worker.pause()
            self.pause_btn.setText("▶ 继续")
            self.status_card.set_value("已暂停")
            self.status_card.value_label.setStyleSheet(f"color: {self.theme['accent_yellow']}; font-size: 28px; font-weight: bold;")
    
    def _on_stop(self):
        """停止注册"""
        if not self.worker:
            return
        
        self.worker.stop()
        self.stop_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
    
    def _on_finished(self):
        """注册任务完成"""
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("⏸ 暂停")
        self.stop_btn.setEnabled(False)
        self.interval_spin.setEnabled(True)
        self.target_spin.setEnabled(True)
        self.email_format_cb.setEnabled(True)
        self.fake_ip_cb.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_card.set_value("已停止")
        self.status_card.value_label.setStyleSheet(f"color: {self.theme['text_secondary']}; font-size: 28px; font-weight: bold;")
        
        self.worker = None
    
    def _update_stats(self, success: int, failure: int, keys: int):
        """更新统计数据"""
        self.success_card.set_value(success)
        self.failure_card.set_value(failure)
        self.keys_card.set_value(keys)
    
    def _on_key_obtained(self, username: str, password: str, api_key: str):
        """获取到新Key"""
        self._add_key_to_list(api_key)
        self.rate_history.append(time.time())
    
    def _copy_all_keys(self):
        """复制所有Keys"""
        keys = []
        for i in range(self.keys_list.count()):
            keys.append(self.keys_list.item(i).text())
        
        if keys:
            QApplication.clipboard().setText('\n'.join(keys))
            self._add_log(f"📋 已复制 {len(keys)} 个Keys到剪贴板", "success")
        else:
            self._add_log("⚠️ 没有可复制的Keys", "warning")
    
    def _open_keys_file(self):
        """打开Keys文件"""
        keys_file = self.data_dir / "api_keys.txt"
        if keys_file.exists():
            os.startfile(str(keys_file))
        else:
            self._add_log("⚠️ Keys文件不存在", "warning")
    
    def _export_to_csv(self):
        """导出到CSV"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出账号信息", 
            str(self.data_dir / f"accounts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"),
            "CSV Files (*.csv)"
        )
        
        if not file_path:
            return
        
        try:
            if hasattr(self, 'worker') and self.worker and hasattr(self.worker, 'storage'):
                self.worker.storage.export_csv(file_path)
            else:
                # 从数据库导出
                from core.storage import AccountStorage
                storage = AccountStorage(str(self.data_dir / "accounts.db"))
                storage.export_csv(file_path)
            
            self._add_log(f"📊 已导出到: {file_path}", "success")
        except Exception as e:
            self._add_log(f"❌ 导出失败: {e}", "error")
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, '确认退出',
                '注册任务正在运行中，确定要退出吗？',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.worker.stop()
                self.worker.wait(3000)
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
