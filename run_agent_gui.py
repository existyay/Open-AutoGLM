#!/usr/bin/env python3
"""Phone Agent GUI - AI手机自动化助手 v2.0"""

import os
import sys
import json
import threading
import queue
import time
from datetime import datetime
from pathlib import Path

os.environ['PYTHONIOENCODING'] = 'utf-8'

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

# 应用目录和配置文件
APP_DIR = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent
CONFIG_FILE = APP_DIR / "phone_agent_config.json"

# 统一颜色主题
COLORS = {
    'bg_dark': '#0f0f1a', 'bg': '#1a1a2e', 'bg_light': '#252540',
    'card': '#2d2d4a', 'card_hover': '#363660',
    'accent': '#6366f1', 'accent_hover': '#818cf8', 'accent2': '#8b5cf6', 'accent3': '#06b6d4',
    'text': '#f1f5f9', 'text2': '#94a3b8', 'text3': '#64748b',
    'success': '#22c55e', 'error': '#ef4444', 'warn': '#f59e0b',
    'border': '#3f3f5a', 'log_bg': '#0d0d14',
}

# 统一字体
FONTS = {
    'normal': ('Microsoft YaHei UI', 10),
    'bold': ('Microsoft YaHei UI', 10, 'bold'),
    'title': ('Microsoft YaHei UI', 24, 'bold'),
    'subtitle': ('Microsoft YaHei UI', 11),
    'small': ('Microsoft YaHei UI', 9),
    'mono': ('Consolas', 10),
    'mono_bold': ('Consolas', 11, 'bold'),
}


class AnimatedButton(tk.Canvas):
    """带动画效果的按钮"""
    def __init__(self, parent, text, command, bg_color, hover_color, fg_color='white', 
                 width=120, height=40, radius=8, font=FONTS['bold'], **kwargs):
        parent_bg = kwargs.pop('bg', None) or parent.cget('bg') if hasattr(parent, 'cget') else COLORS['bg_dark']
        super().__init__(parent, width=width, height=height, highlightthickness=0, bg=parent_bg, **kwargs)
        
        self.command, self.bg_color, self.hover_color = command, bg_color, hover_color
        self.fg_color, self.radius, self.text, self.font = fg_color, radius, text, font
        self._disabled = False
        self._draw_button(bg_color)
        self.bind('<Enter>', lambda e: self._draw_button(hover_color) if not self._disabled else None)
        self.bind('<Leave>', lambda e: self._draw_button(bg_color) if not self._disabled else None)
        self.bind('<Button-1>', lambda e: self.command() if not self._disabled and self.command else None)
        
    def _draw_button(self, color):
        self.delete('all')
        w, h, r = self.winfo_reqwidth(), self.winfo_reqheight(), self.radius
        # 圆角矩形
        for x, y, s, e in [(0, 0, 90, 90), (w-r*2, 0, 0, 90), (0, h-r*2, 180, 90), (w-r*2, h-r*2, 270, 90)]:
            self.create_arc(x, y, x+r*2, y+r*2, start=s, extent=e, fill=color, outline=color)
        self.create_rectangle(r, 0, w-r, h, fill=color, outline=color)
        self.create_rectangle(0, r, w, h-r, fill=color, outline=color)
        self.create_text(w//2, h//2, text=self.text, fill=self.fg_color, font=self.font)
        
    def configure(self, **kwargs):
        if 'state' in kwargs:
            self._disabled = kwargs['state'] == tk.DISABLED
            self._draw_button('#4a4a5e' if self._disabled else self.bg_color)
        if 'text' in kwargs:
            self.text = kwargs['text']
            self._draw_button('#4a4a5e' if self._disabled else self.bg_color)


class StatusIndicator(tk.Canvas):
    """状态指示灯"""
    STATUS_COLORS = {
        'ok': ('#22c55e', '#16a34a'), 'error': ('#ef4444', '#dc2626'),
        'warn': ('#f59e0b', '#d97706'), 'unknown': ('#6b7280', '#4b5563')
    }
    
    def __init__(self, parent, size=12, **kwargs):
        parent_bg = kwargs.pop('bg', None) or (parent.cget('bg') if hasattr(parent, 'cget') else COLORS['card'])
        super().__init__(parent, width=size+4, height=size+4, highlightthickness=0, bg=parent_bg)
        self.size = size
        self.set_status('unknown')
        
    def set_status(self, status):
        self.delete('all')
        outer, inner = self.STATUS_COLORS.get(status, self.STATUS_COLORS['unknown'])
        self.create_oval(2, 2, self.size+2, self.size+2, fill=inner, outline='')
        self.create_oval(4, 4, self.size, self.size, fill=outer, outline='')


class PhoneAgentGUI:
    DEFAULT_CONFIG = {
        "mode": "api", "api_key": "", "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "autoglm-phone", "local_model_path": "", "local_port": 8000, "lang": "cn", "max_steps": 100
    }
    
    def __init__(self, root):
        self.root = root
        self.root.title("📱 Phone Agent - AI手机自动化助手 v2.0")
        self.root.geometry("1050x850")
        self.root.minsize(950, 750)
        
        self.agent = None
        self.is_running = False
        self.output_queue = queue.Queue()
        self.config = self._load_config()
        self.step_count = 0
        self.start_time = None
        
        self._setup_theme()
        self._create_widgets()
        self._check_output_queue()
        self.root.after(500, self.check_adb_status)
        
    def _load_config(self):
        config = self.DEFAULT_CONFIG.copy()
        if CONFIG_FILE.exists():
            try:
                config.update(json.loads(CONFIG_FILE.read_text(encoding='utf-8')))
            except Exception:
                pass
        return config
        
    def save_config(self):
        try:
            CONFIG_FILE.write_text(json.dumps(self.config, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception as e:
            self.log(f"保存配置失败: {e}", "error")
            
    def _setup_theme(self):
        """设置主题颜色"""
        self.colors = COLORS
        self.root.configure(bg=COLORS['bg_dark'])
        
        style = ttk.Style()
        style.theme_use('clam')
        
        # 批量配置样式
        styles = [
            ('TFrame', {'background': COLORS['bg']}),
            ('Dark.TFrame', {'background': COLORS['bg_dark']}),
            ('Card.TFrame', {'background': COLORS['card']}),
            ('TLabel', {'background': COLORS['bg'], 'foreground': COLORS['text'], 'font': FONTS['normal']}),
            ('Dark.TLabel', {'background': COLORS['bg_dark']}),
            ('Card.TLabel', {'background': COLORS['card']}),
            ('Title.TLabel', {'font': FONTS['title'], 'foreground': COLORS['accent']}),
            ('Subtitle.TLabel', {'font': FONTS['subtitle'], 'foreground': COLORS['text2']}),
            ('Small.TLabel', {'font': FONTS['small'], 'foreground': COLORS['text3']}),
            ('TLabelframe', {'background': COLORS['bg'], 'bordercolor': COLORS['border']}),
            ('TLabelframe.Label', {'background': COLORS['bg'], 'foreground': COLORS['accent2'], 'font': FONTS['bold']}),
            ('TEntry', {'fieldbackground': COLORS['card'], 'foreground': COLORS['text'], 'insertcolor': COLORS['text'], 'padding': 8}),
            ('TCombobox', {'fieldbackground': COLORS['card'], 'foreground': COLORS['text'], 'padding': 5}),
            ('TRadiobutton', {'background': COLORS['bg'], 'foreground': COLORS['text'], 'font': FONTS['normal']}),
            ('TButton', {'padding': (15, 8), 'font': FONTS['normal']}),
        ]
        for name, opts in styles:
            style.configure(name, **opts)
        style.map('TRadiobutton', background=[('active', COLORS['bg_light'])])
        
    def _create_widgets(self):
        main = ttk.Frame(self.root, style='Dark.TFrame')
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        
        self._create_header(main)
        self._create_status_panel(main)
        
        content = ttk.Frame(main, style='Dark.TFrame')
        content.pack(fill=tk.BOTH, expand=True, pady=(15, 0))
        
        left_panel = ttk.Frame(content, style='Dark.TFrame', width=400)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 15))
        left_panel.pack_propagate(False)
        
        self._create_config_panel(left_panel)
        self._create_task_panel(left_panel)
        
        right_panel = ttk.Frame(content, style='Dark.TFrame')
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._create_log_panel(right_panel)
        
    def _create_header(self, parent):
        header = ttk.Frame(parent, style='Dark.TFrame')
        header.pack(fill=tk.X, pady=(0, 15))
        
        title_frame = ttk.Frame(header, style='Dark.TFrame')
        title_frame.pack(side=tk.LEFT)
        ttk.Label(title_frame, text="📱 Phone Agent", style='Title.TLabel',
                 background=COLORS['bg_dark']).pack(anchor=tk.W)
        ttk.Label(title_frame, text="使用自然语言控制手机，AI自动完成各种任务", 
                 style='Subtitle.TLabel', background=COLORS['bg_dark']).pack(anchor=tk.W)
        
        version_frame = ttk.Frame(header, style='Dark.TFrame')
        version_frame.pack(side=tk.RIGHT)
        ttk.Label(version_frame, text="v2.0 | Powered by AutoGLM", 
                 style='Small.TLabel', background=COLORS['bg_dark']).pack(anchor=tk.E)
                 
    def _create_status_panel(self, parent):
        """创建状态面板"""
        C = COLORS
        status_frame = tk.Frame(parent, bg=C['card'], highlightthickness=1, highlightbackground=C['border'])
        status_frame.pack(fill=tk.X)
        
        inner = tk.Frame(status_frame, bg=C['card'])
        inner.pack(fill=tk.X, padx=20, pady=15)
        
        # 状态项通用创建函数
        def create_status_item(parent, title, is_indicator=True):
            frame = tk.Frame(parent, bg=C['card'])
            frame.pack(side=tk.LEFT, padx=(0, 40))
            tk.Label(frame, text=title, font=FONTS['small'], fg=C['text3'], bg=C['card']).pack(anchor=tk.W)
            row = tk.Frame(frame, bg=C['card'])
            row.pack(anchor=tk.W, pady=(3, 0))
            indicator = StatusIndicator(row, bg=C['card']) if is_indicator else None
            if indicator:
                indicator.pack(side=tk.LEFT)
            return frame, row, indicator
        
        # ADB状态
        _, adb_row, self.adb_indicator = create_status_item(inner, "ADB 状态")
        self.adb_status = tk.Label(adb_row, text="检测中...", font=FONTS['mono'], fg=C['warn'], bg=C['card'])
        self.adb_status.pack(side=tk.LEFT, padx=(5, 0))
        
        # 设备状态
        _, device_row, self.device_indicator = create_status_item(inner, "连接设备")
        self.device_status = tk.Label(device_row, text="检测中...", font=FONTS['mono'], fg=C['warn'], bg=C['card'])
        self.device_status.pack(side=tk.LEFT, padx=(5, 0))
        
        # 运行状态
        run_frame, _, _ = create_status_item(inner, "运行状态", False)
        self.run_status = tk.Label(run_frame, text="⏸ 空闲", font=FONTS['bold'], fg=C['text2'], bg=C['card'])
        self.run_status.pack(anchor=tk.W, pady=(3, 0))
        
        # 步骤计数
        step_frame, _, _ = create_status_item(inner, "执行步骤", False)
        self.step_label = tk.Label(step_frame, text="0 / 100", font=FONTS['mono_bold'], fg=C['accent3'], bg=C['card'])
        self.step_label.pack(anchor=tk.W, pady=(3, 0))
        
        # 刷新按钮
        AnimatedButton(inner, "🔄 刷新", self.check_adb_status, C['card_hover'], C['accent'], width=90, height=32).pack(side=tk.RIGHT)
        
    def _create_config_panel(self, parent):
        """创建配置面板"""
        C = COLORS
        config_frame = tk.Frame(parent, bg=C['card'], highlightthickness=1, highlightbackground=C['border'])
        config_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 标题栏
        title_bar = tk.Frame(config_frame, bg=C['accent2'])
        title_bar.pack(fill=tk.X)
        tk.Label(title_bar, text="⚙️ 配置设置", font=FONTS['bold'], fg='white', bg=C['accent2'], pady=8).pack(anchor=tk.W, padx=15)
        
        inner = tk.Frame(config_frame, bg=C['card'])
        inner.pack(fill=tk.X, padx=15, pady=15)
        
        # 模式选择
        mode_frame = tk.Frame(inner, bg=C['card'])
        mode_frame.pack(fill=tk.X, pady=(0, 15))
        tk.Label(mode_frame, text="运行模式", font=FONTS['bold'], fg=C['text'], bg=C['card']).pack(anchor=tk.W)
        
        self.mode_var = tk.StringVar(value=self.config['mode'])
        mode_btns = tk.Frame(mode_frame, bg=C['card'])
        mode_btns.pack(fill=tk.X, pady=(8, 0))
        ttk.Radiobutton(mode_btns, text="☁️ API模式", variable=self.mode_var, value="api", command=self.on_mode_change).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Radiobutton(mode_btns, text="💻 本地模式", variable=self.mode_var, value="local", command=self.on_mode_change).pack(side=tk.LEFT)
        
        # API配置
        self.api_config_frame = tk.Frame(inner, bg=C['card'])
        self.api_config_frame.pack(fill=tk.X)
        self._create_input_row(self.api_config_frame, "API Key", "api_key", show="*", has_toggle=True)
        self._create_input_row(self.api_config_frame, "Base URL", "base_url")
        
        # Model选择
        model_row = tk.Frame(self.api_config_frame, bg=C['card'])
        model_row.pack(fill=tk.X, pady=(0, 8))
        tk.Label(model_row, text="模型", font=FONTS['small'], fg=C['text2'], bg=C['card']).pack(anchor=tk.W)
        self.model_var = tk.StringVar(value=self.config['model'])
        ttk.Combobox(model_row, textvariable=self.model_var, values=["autoglm-phone", "glm-4v-plus", "glm-4v"], width=35).pack(fill=tk.X, pady=(3, 0))
        
        # 本地模型配置框架
        self.local_config_frame = tk.Frame(inner, bg=C['card'])
        self._create_local_model_panel(self.local_config_frame)
        
        # 保存按钮
        save_row = tk.Frame(inner, bg=C['card'])
        save_row.pack(fill=tk.X, pady=(15, 0))
        AnimatedButton(save_row, "💾 保存配置", self.save_current_config, C['accent'], C['accent_hover'], width=100, height=35).pack(side=tk.RIGHT)
        
        self.on_mode_change()
        
    def _create_input_row(self, parent, label, config_key, show=None, has_toggle=False):
        """创建输入行"""
        C = COLORS
        row = tk.Frame(parent, bg=C['card'])
        row.pack(fill=tk.X, pady=(0, 8))
        tk.Label(row, text=label, font=FONTS['small'], fg=C['text2'], bg=C['card']).pack(anchor=tk.W)
        
        entry_row = tk.Frame(row, bg=C['card'])
        entry_row.pack(fill=tk.X, pady=(3, 0))
        
        var = tk.StringVar(value=self.config.get(config_key, ''))
        setattr(self, f'{config_key}_var', var)
        entry = ttk.Entry(entry_row, textvariable=var, show=show or '')
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        setattr(self, f'{config_key}_entry', entry)
        
        if has_toggle:
            def toggle():
                entry.configure(show='' if entry.cget('show') == '*' else '*')
            tk.Button(entry_row, text="👁", command=toggle, bg=C['card_hover'], fg=C['text'], relief=tk.FLAT, padx=8).pack(side=tk.LEFT, padx=(5, 0))
            
    def _create_task_panel(self, parent):
        """创建任务输入面板"""
        C = COLORS
        task_frame = tk.Frame(parent, bg=C['card'], highlightthickness=1, highlightbackground=C['border'])
        task_frame.pack(fill=tk.BOTH, expand=True)
        
        title_bar = tk.Frame(task_frame, bg=C['accent'])
        title_bar.pack(fill=tk.X)
        tk.Label(title_bar, text="📝 任务描述", font=FONTS['bold'], fg='white', bg=C['accent'], pady=8).pack(anchor=tk.W, padx=15)
        
        inner = tk.Frame(task_frame, bg=C['card'])
        inner.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        self.task_text = tk.Text(inner, height=5, wrap=tk.WORD, font=FONTS['subtitle'],
                                bg=C['bg_light'], fg=C['text'], insertbackground=C['accent'],
                                relief=tk.FLAT, padx=12, pady=10, highlightthickness=1,
                                highlightbackground=C['border'], highlightcolor=C['accent'])
        self.task_text.pack(fill=tk.BOTH, expand=True)
        self.task_text.bind('<Control-Return>', lambda e: self.run_task())
        
        tk.Label(inner, text="💡 示例: 打开微信发消息给张三 | Ctrl+Enter 快速执行",
                font=FONTS['small'], fg=C['text3'], bg=C['card']).pack(anchor=tk.W, pady=(8, 0))
        
        btn_frame = tk.Frame(inner, bg=C['card'])
        btn_frame.pack(fill=tk.X, pady=(15, 0))
        
        self.run_btn = AnimatedButton(btn_frame, "▶ 执行任务", self.run_task, C['success'], '#16a34a', 
                                      width=120, height=42, font=FONTS['bold'])
        self.run_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_btn = AnimatedButton(btn_frame, "⏹ 停止", self.stop_task, C['error'], '#dc2626', width=80, height=42)
        self.stop_btn.configure(state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT)
        
    def _create_log_panel(self, parent):
        """创建日志面板"""
        C = COLORS
        log_frame = tk.Frame(parent, bg=C['card'], highlightthickness=1, highlightbackground=C['border'])
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        title_bar = tk.Frame(log_frame, bg=C['accent3'])
        title_bar.pack(fill=tk.X)
        tk.Label(title_bar, text="📋 执行日志", font=FONTS['bold'], fg='white', bg=C['accent3'], pady=8).pack(side=tk.LEFT, padx=15)
        tk.Button(title_bar, text="🗑 清空", command=self.clear_log, bg=C['accent3'], fg='white',
                 relief=tk.FLAT, font=FONTS['small'], activebackground='#0891b2', activeforeground='white').pack(side=tk.RIGHT, padx=10, pady=5)
        
        log_container = tk.Frame(log_frame, bg=C['log_bg'])
        log_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        self.log_text = scrolledtext.ScrolledText(log_container, wrap=tk.WORD, font=FONTS['mono'],
                                                   bg=C['log_bg'], fg=C['text'], insertbackground=C['accent'],
                                                   relief=tk.FLAT, padx=15, pady=12, cursor='arrow')
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 配置日志标签样式
        log_tags = [
            ('time', C['text3'], FONTS['small']), ('info', C['text'], None), ('success', C['success'], None),
            ('error', C['error'], None), ('warn', C['warn'], None), ('step', C['accent'], FONTS['mono_bold']),
            ('model', C['accent2'], FONTS['mono']), ('action', C['accent3'], FONTS['mono']),
            ('thinking', '#a78bfa', ('Consolas', 10, 'italic')), ('separator', C['border'], None)
        ]
        for tag, color, font in log_tags:
            self.log_text.tag_configure(tag, foreground=color, font=font if font else FONTS['mono'])
        
    def on_mode_change(self):
        """切换模式时更新界面"""
        if self.mode_var.get() == "api":
            self.local_config_frame.pack_forget()
            self.api_config_frame.pack(fill=tk.X)
        else:
            self.api_config_frame.pack_forget()
            self.local_config_frame.pack(fill=tk.X, pady=(10, 0))
            
    def _create_local_model_panel(self, parent):
        """创建本地模型配置面板"""
        C = COLORS
        
        # 环境检测区
        env_frame = tk.Frame(parent, bg=C['card'])
        env_frame.pack(fill=tk.X, pady=(0, 10))
        tk.Label(env_frame, text="系统环境", font=FONTS['bold'], fg=C['text'], bg=C['card']).pack(anchor=tk.W)
        
        self.env_status_frame = tk.Frame(env_frame, bg=C['bg_light'])
        self.env_status_frame.pack(fill=tk.X, pady=(5, 0))
        self.env_status_label = tk.Label(self.env_status_frame, text="点击检测按钮检测环境",
                                         font=FONTS['small'], fg=C['text2'], bg=C['bg_light'],
                                         wraplength=320, justify=tk.LEFT, padx=10, pady=8)
        self.env_status_label.pack(fill=tk.X)
        
        AnimatedButton(env_frame, "🔍 检测环境", self.detect_environment, C['accent3'], '#0891b2', width=100, height=30).pack(anchor=tk.W, pady=(8, 0))
        
        # 模型下载区
        model_frame = tk.Frame(parent, bg=C['card'])
        model_frame.pack(fill=tk.X, pady=(10, 0))
        tk.Label(model_frame, text="本地模型", font=FONTS['bold'], fg=C['text'], bg=C['card']).pack(anchor=tk.W)
        
        # 模型选择行
        model_select_frame = tk.Frame(model_frame, bg=C['card'])
        model_select_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.local_model_var = tk.StringVar(value="AutoGLM-Phone-9B")
        self.model_combo = ttk.Combobox(model_select_frame, textvariable=self.local_model_var, width=28,
                    values=["AutoGLM-Phone-9B", "📁 选择本地模型..."])
        self.model_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.model_combo.bind('<<ComboboxSelected>>', self._on_model_selected)
        
        # 自定义模型路径（默认隐藏）
        self.custom_model_frame = tk.Frame(model_frame, bg=C['card'])
        self.custom_model_path = tk.StringVar()
        tk.Label(self.custom_model_frame, text="模型路径:", font=FONTS['small'], fg=C['text2'], bg=C['card']).pack(side=tk.LEFT)
        self.custom_model_entry = ttk.Entry(self.custom_model_frame, textvariable=self.custom_model_path, width=25)
        self.custom_model_entry.pack(side=tk.LEFT, padx=(5, 5), fill=tk.X, expand=True)
        AnimatedButton(self.custom_model_frame, "📂", self._browse_model_folder, C['accent2'], C['accent'], width=30, height=24).pack(side=tk.LEFT)
        
        # 下载进度
        self.download_progress_frame = tk.Frame(model_frame, bg=C['card'])
        self.download_progress_frame.pack(fill=tk.X, pady=(8, 0))
        self.download_progress = ttk.Progressbar(self.download_progress_frame, mode='determinate')
        self.download_status_label = tk.Label(self.download_progress_frame, text="", font=FONTS['small'], fg=C['text2'], bg=C['card'])
        
        # 按钮
        btn_frame = tk.Frame(model_frame, bg=C['card'])
        btn_frame.pack(fill=tk.X, pady=(8, 0))
        self.download_btn = AnimatedButton(btn_frame, "⬇️ 下载模型", self.download_model, C['accent'], C['accent_hover'], width=100, height=30)
        self.download_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.start_server_btn = AnimatedButton(btn_frame, "🚀 启动服务", self.start_local_server, C['success'], '#16a34a', width=100, height=30)
        self.start_server_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.stop_server_btn = AnimatedButton(btn_frame, "⏹ 停止", self.stop_local_server, C['error'], '#dc2626', width=70, height=30)
        self.stop_server_btn.configure(state=tk.DISABLED)
        self.stop_server_btn.pack(side=tk.LEFT)
        
        self.server_status_label = tk.Label(model_frame, text="🔴 服务未启动", font=FONTS['small'], fg=C['text2'], bg=C['card'])
        self.server_status_label.pack(anchor=tk.W, pady=(8, 0))
        
        # 端口设置
        port_frame = tk.Frame(model_frame, bg=C['card'])
        port_frame.pack(fill=tk.X, pady=(8, 0))
        tk.Label(port_frame, text="服务端口:", font=FONTS['small'], fg=C['text2'], bg=C['card']).pack(side=tk.LEFT)
        self.local_port_var = tk.StringVar(value=str(self.config.get('local_port', 8000)))
        ttk.Entry(port_frame, textvariable=self.local_port_var, width=8).pack(side=tk.LEFT, padx=(5, 0))
        
    def detect_environment(self):
        """检测系统环境"""
        def check():
            try:
                from phone_agent.local_model import EnvironmentDetector
                info = EnvironmentDetector().detect()
                
                lines = [f"🖥️ 系统: {info.os_name}", f"🐍 Python: {info.python_version}",
                        f"💾 内存: {info.ram_total / 1024:.1f} GB"]
                
                # Git 环境检测
                if info.git_info:
                    if info.git_info.git_available:
                        git_status = f"✅ Git: {info.git_info.git_version or '已安装'}"
                        if info.git_info.lfs_available:
                            git_status += f" | LFS: {info.git_info.lfs_version or '已安装'}"
                        else:
                            git_status += " | ❌ LFS未安装"
                        lines.append(git_status)
                    else:
                        lines.append("❌ Git: 未安装 (需要安装Git和Git LFS)")
                
                if info.cuda_available:
                    lines.append(f"🎮 CUDA: {info.cuda_version or '可用'}")
                    lines.extend(f"🖼️ GPU: {gpu.name} ({gpu.memory_total / 1024:.1f}GB)" for gpu in info.gpus)
                else:
                    lines.append("❌ CUDA: 不可用")
                    
                lines.extend([f"💡 推荐: {info.recommended_model}", f"   {info.reason}"])
                
                # 根据环境状态设置颜色
                can_download = info.git_info and info.git_info.git_available and info.git_info.lfs_available
                color = COLORS['success'] if (info.can_run_local and can_download) else COLORS['warn']
                self.root.after(0, lambda: self.env_status_label.configure(text="\n".join(lines), fg=color))
            except Exception as e:
                self.root.after(0, lambda: self.env_status_label.configure(text=f"❌ 检测失败: {e}", fg=COLORS['error']))
                
        self.env_status_label.configure(text="🔄 正在检测环境...", fg=COLORS['warn'])
        threading.Thread(target=check, daemon=True).start()
    
    def _on_model_selected(self, event=None):
        """模型选择变化时的处理"""
        selection = self.local_model_var.get()
        if selection == "📁 选择本地模型...":
            self.custom_model_frame.pack(fill=tk.X, pady=(5, 0))
            self.download_btn.configure(state=tk.DISABLED)
        else:
            self.custom_model_frame.pack_forget()
            self.download_btn.configure(state=tk.NORMAL)
    
    def _browse_model_folder(self):
        """浏览并选择本地模型文件夹"""
        from tkinter import filedialog
        folder = filedialog.askdirectory(title="选择模型文件夹")
        if folder:
            self.custom_model_path.set(folder)
            # 验证是否是有效的模型目录
            model_path = Path(folder)
            config_file = model_path / "config.json"
            if config_file.exists():
                self.server_status_label.configure(text=f"✅ 已选择模型: {model_path.name}", fg=COLORS['success'])
            else:
                self.server_status_label.configure(text="⚠️ 未找到config.json，可能不是有效的模型目录", fg=COLORS['warn'])
    
    def _get_model_path(self):
        """获取当前选择的模型路径"""
        selection = self.local_model_var.get()
        if selection == "📁 选择本地模型...":
            return self.custom_model_path.get()
        return selection
        
    def download_model(self):
        """下载模型"""
        model_name = self.local_model_var.get()
        
        def download():
            try:
                from phone_agent.local_model import ModelDownloader
                downloader = ModelDownloader()
                
                if downloader.is_model_downloaded(model_name):
                    self.root.after(0, lambda: self._update_download_status("✅ 模型已存在，无需下载", 100))
                    return
                    
                self.root.after(0, lambda: self._show_download_progress(True))
                self.root.after(0, lambda: self.download_btn.configure(state=tk.DISABLED))
                
                success = downloader.download_model(model_name, 
                    lambda p: self.root.after(0, lambda: self._update_download_status(f"📥 {p.current_file} ({p.percent:.1f}%)", p.percent)),
                    'ModelScope' not in model_name)
                
                self.root.after(0, lambda: self._update_download_status(
                    "✅ 下载完成!" if success else f"❌ 下载失败: {downloader.progress.error_message}", 100 if success else 0))
            except Exception as e:
                self.root.after(0, lambda: self._update_download_status(f"❌ 下载失败: {e}", 0))
            finally:
                self.root.after(0, lambda: self.download_btn.configure(state=tk.NORMAL))
                
        threading.Thread(target=download, daemon=True).start()
        
    def _show_download_progress(self, show):
        if show:
            self.download_progress.pack(fill=tk.X)
            self.download_status_label.pack(anchor=tk.W, pady=(5, 0))
        else:
            self.download_progress.pack_forget()
            self.download_status_label.pack_forget()
            
    def _update_download_status(self, status, percent):
        self.download_status_label.configure(text=status)
        self.download_progress['value'] = percent
        
    def start_local_server(self):
        """启动本地推理服务"""
        model_path = self._get_model_path()
        port = int(self.local_port_var.get())
        
        # 检查是否选择了自定义模型路径
        if self.local_model_var.get() == "📁 选择本地模型..." and not model_path:
            messagebox.showwarning("提示", "请先选择模型文件夹")
            return
        
        def start():
            try:
                from phone_agent.local_model import LocalModelManager
                self.local_model_manager = LocalModelManager()
                
                self.root.after(0, lambda: (self.server_status_label.configure(text="🟡 正在启动服务...", fg=COLORS['warn']),
                                            self.start_server_btn.configure(state=tk.DISABLED)))
                
                if self.local_model_manager.start_server(model_path, port):
                    api_base = self.local_model_manager.get_api_base()
                    self.root.after(0, lambda: (self.server_status_label.configure(text=f"🟢 服务运行中: {api_base}", fg=COLORS['success']),
                                                self.stop_server_btn.configure(state=tk.NORMAL)))
                    self.log("✅ 本地推理服务已启动", "success")
                else:
                    self.root.after(0, lambda: (self.server_status_label.configure(text="🔴 启动失败", fg=COLORS['error']),
                                                self.start_server_btn.configure(state=tk.NORMAL)))
                    self.log("❌ 本地推理服务启动失败", "error")
            except Exception as e:
                self.root.after(0, lambda: (self.server_status_label.configure(text=f"🔴 错误: {e}", fg=COLORS['error']),
                                            self.start_server_btn.configure(state=tk.NORMAL)))
                self.log(f"❌ 启动失败: {e}", "error")
                
        threading.Thread(target=start, daemon=True).start()
        
    def stop_local_server(self):
        """停止本地推理服务"""
        try:
            if hasattr(self, 'local_model_manager') and self.local_model_manager:
                self.local_model_manager.stop_server()
            self.server_status_label.configure(text="🔴 服务已停止", fg=COLORS['text2'])
            self.start_server_btn.configure(state=tk.NORMAL)
            self.stop_server_btn.configure(state=tk.DISABLED)
            self.log("⏹ 本地推理服务已停止", "info")
        except Exception as e:
            self.log(f"停止服务失败: {e}", "error")
            
    def save_current_config(self):
        """保存当前配置"""
        self.config.update({'mode': self.mode_var.get(), 'api_key': self.api_key_var.get(),
                           'base_url': self.base_url_var.get(), 'model': self.model_var.get()})
        self.save_config()
        self.log("✅ 配置已保存", "success")
        
    def check_adb_status(self):
        """检查ADB状态"""
        def check():
            try:
                from phone_agent.adb.utils import check_adb_available, get_connected_devices
                available, version = check_adb_available()
                self.root.after(0, lambda: self._update_adb_status(available, version))
                if available:
                    devices = get_connected_devices()
                    self.root.after(0, lambda: self._update_device_status(bool(devices), devices[0] if devices else "未连接设备"))
            except Exception as e:
                self.root.after(0, lambda: self._update_adb_status(False, str(e)))
        threading.Thread(target=check, daemon=True).start()
        
    def _update_adb_status(self, ok, text):
        display = text[:25] if len(text) > 25 else text
        self.adb_indicator.set_status('ok' if ok else 'error')
        self.adb_status.configure(text=display, fg=COLORS['success'] if ok else COLORS['error'])
            
    def _update_device_status(self, ok, text):
        self.device_indicator.set_status('ok' if ok else 'error')
        self.device_status.configure(text=f"{'✅' if ok else '❌'} {text}", fg=COLORS['success'] if ok else COLORS['error'])
            
    def run_task(self):
        """运行任务"""
        task = self.task_text.get('1.0', tk.END).strip()
        if not task:
            return messagebox.showwarning("警告", "请输入任务描述")
        if self.mode_var.get() == "api" and not self.api_key_var.get().strip():
            return messagebox.showwarning("警告", "请输入API Key")
            
        self.is_running, self.step_count, self.start_time = True, 0, time.time()
        self.run_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)
        self.run_status.configure(text="🔄 运行中", fg=COLORS['success'])
        self.step_label.configure(text=f"0 / {self.config.get('max_steps', 100)}")
        
        self._log_separator()
        self.log("🚀 开始执行任务", "step")
        self.log(f"📋 任务内容: {task}", "info")
        self.log(f"🤖 使用模型: {self.model_var.get()}", "model")
        self.log(f"🔗 API地址: {self.base_url_var.get()}", "info")
        self._log_separator()
        
        threading.Thread(target=self._execute_task, args=(task,), daemon=True).start()
        
    def _execute_task(self, task):
        """执行任务（在后台线程中）"""
        try:
            from phone_agent import PhoneAgent
            from phone_agent.model import ModelConfig
            from phone_agent.agent import AgentConfig
            
            mode = self.mode_var.get()
            if mode == "api":
                model_config = ModelConfig(api_key=self.api_key_var.get().strip(),
                                          base_url=self.base_url_var.get().strip(),
                                          model_name=self.model_var.get().strip())
            else:
                port = getattr(self, 'local_port_var', None)
                model_config = ModelConfig(api_key="local", base_url=f"http://localhost:{port.get() if port else '8000'}/v1",
                                          model_name="local-model")
                
            agent_config = AgentConfig(lang=self.config.get('lang', 'cn'),
                                       max_steps=self.config.get('max_steps', 100), verbose=False)
            
            self.agent = PhoneAgent(model_config=model_config, agent_config=agent_config,
                                   log_callback=self._agent_log_callback)
            self.output_queue.put(("log", "info", "✅ Agent 初始化完成"))
            
            result = self.agent.run(task)
            elapsed = time.time() - self.start_time
            self.output_queue.put(("log", "separator", None))
            self.output_queue.put(("log", "success", f"🎉 任务完成!"))
            self.output_queue.put(("log", "success", f"📊 执行结果: {result}"))
            self.output_queue.put(("log", "info", f"⏱️ 总耗时: {elapsed:.1f}秒, 共 {self.step_count} 步"))
        except Exception as e:
            import traceback
            self.output_queue.put(("log", "error", f"❌ 执行出错: {e}"))
            self.output_queue.put(("log", "error", traceback.format_exc()))
        finally:
            self.output_queue.put(("done", None, None))
            
    def _agent_log_callback(self, event_type, data):
        """Agent日志回调函数"""
        q = self.output_queue
        
        if event_type == "step_start":
            self.step_count = data.get('step', self.step_count + 1)
            q.put(("update_step", self.step_count, self.config.get('max_steps', 100)))
            q.put(("log", "separator", None))
            q.put(("log", "step", f"📍 第 {self.step_count} 步"))
        elif event_type == "screenshot":
            q.put(("log", "info", "📸 截取屏幕截图"))
        elif event_type == "current_app":
            q.put(("log", "info", f"📱 当前应用: {data.get('app', 'unknown')}"))
        elif event_type == "model_request":
            q.put(("log", "model", f"🤖 调用大模型: {data.get('model', 'unknown')}"))
            q.put(("log", "info", "   ├─ 发送请求中..."))
        elif event_type == "model_response":
            q.put(("log", "model", f"   └─ 响应完成 (耗时: {data.get('time', 0):.1f}s)"))
        elif event_type == "thinking":
            thinking = data.get('content', '')[:200] + ("..." if len(data.get('content', '')) > 200 else "")
            q.put(("log", "thinking", "💭 模型思考:"))
            for line in thinking.split('\n')[:5]:
                if line.strip():
                    q.put(("log", "thinking", f"   {line.strip()}"))
        elif event_type == "action":
            action = data.get('action', {})
            q.put(("log", "action", f"🎯 执行动作: {action.get('_metadata', action.get('type', 'unknown'))}"))
            if 'coordinate' in action:
                q.put(("log", "info", f"   ├─ 坐标: ({action['coordinate'][0]}, {action['coordinate'][1]})"))
            if 'text' in action:
                q.put(("log", "info", f"   ├─ 文本: {action['text'][:50]}{'...' if len(action['text']) > 50 else ''}"))
            if 'direction' in action:
                q.put(("log", "info", f"   ├─ 方向: {action['direction']}"))
            if 'message' in action:
                q.put(("log", "info", f"   └─ 消息: {action['message']}"))
        elif event_type == "action_result":
            q.put(("log", "success" if data.get('success') else "error", 
                   f"   {'✅ 动作执行成功' if data.get('success') else '❌ 动作执行失败: ' + data.get('message', '')}"))
        elif event_type == "finish":
            q.put(("log", "success", f"🏁 {data.get('message', '任务完成')}"))
            
    def stop_task(self):
        """停止任务"""
        self.is_running = False
        if self.agent:
            try:
                self.agent.stop()
            except Exception:
                pass
        self.log("⏹ 任务已停止", "warn")
        self.run_btn.configure(state=tk.NORMAL)
        self.stop_btn.configure(state=tk.DISABLED)
        self.run_status.configure(text="⏸ 空闲", fg=COLORS['text2'])
        
    def log(self, message, tag="info"):
        """添加日志"""
        self.log_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] ", "time")
        self.log_text.insert(tk.END, f"{message}\n", tag)
        self.log_text.see(tk.END)
        
    def _log_separator(self):
        self.log_text.insert(tk.END, "─" * 60 + "\n", "separator")
        self.log_text.see(tk.END)
        
    def clear_log(self):
        self.log_text.delete('1.0', tk.END)
        
    def _check_output_queue(self):
        """检查输出队列"""
        try:
            while True:
                msg = self.output_queue.get_nowait()
                if msg[0] == "log":
                    self._log_separator() if msg[1] == "separator" else self.log(msg[2], msg[1])
                elif msg[0] == "update_step":
                    self.step_label.configure(text=f"{msg[1]} / {msg[2]}")
                elif msg[0] == "done":
                    self.is_running = False
                    self.run_btn.configure(state=tk.NORMAL)
                    self.stop_btn.configure(state=tk.DISABLED)
                    self.run_status.configure(text="⏸ 空闲", fg=COLORS['text2'])
        except queue.Empty:
            pass
        self.root.after(100, self._check_output_queue)


def main():
    """主程序入口 - 确保单实例运行"""
    import multiprocessing
    
    # 关键：PyInstaller打包后必须调用freeze_support防止多窗口
    if hasattr(sys, 'frozen'):
        multiprocessing.freeze_support()
        # 设置multiprocessing的启动方式为spawn（Windows默认）
        try:
            multiprocessing.set_start_method('spawn', force=True)
        except RuntimeError:
            pass
    
    root = tk.Tk()
    root.protocol("WM_DELETE_WINDOW", lambda: root.quit())
    
    try:
        icon_path = APP_DIR / "icon.ico"
        if icon_path.exists():
            root.iconbitmap(icon_path)
    except Exception:
        pass
    
    gui = PhoneAgentGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
