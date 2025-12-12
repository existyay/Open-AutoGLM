# -*- mode: python ; coding: utf-8 -*-
import os
import sys

block_cipher = None

# 获取项目路径
project_path = os.path.dirname(os.path.abspath(SPEC))

# 收集数据文件（包括ADB工具）
datas = [
    (os.path.join(project_path, 'phone_agent'), 'phone_agent'),
    (os.path.join(project_path, 'resources'), 'resources'),
    (r'C:\platform-tools', 'platform-tools'),
]

# 隐藏导入
hiddenimports = [
    'openai',
    'PIL',
    'PIL.Image',
    'phone_agent',
    'phone_agent.agent',
    'phone_agent.model',
    'phone_agent.model.client',
    'phone_agent.adb',
    'phone_agent.adb.connection',
    'phone_agent.adb.device',
    'phone_agent.adb.input',
    'phone_agent.adb.screenshot',
    'phone_agent.adb.utils',
    'phone_agent.config',
    'phone_agent.config.apps',
    'phone_agent.config.prompts',
    'phone_agent.config.prompts_zh',
    'phone_agent.config.prompts_en',
    'phone_agent.config.i18n',
    'phone_agent.actions',
    'phone_agent.actions.handler',
    'phone_agent.local_model',
    'phone_agent.local_model.environment',
    'phone_agent.local_model.downloader',
    'phone_agent.local_model.manager',
    'tkinter',
    'tkinter.ttk',
    'tkinter.scrolledtext',
    'tkinter.filedialog',
    'tkinter.messagebox',
    'queue',
    'threading',
    'json',
    'base64',
    'io',
    'httpx',
    'httpcore',
    'anyio',
    'certifi',
    'idna',
    'sniffio',
    'h11',
    'distro',
    'jiter',
    'pydantic',
    'pydantic_core',
    'typing_extensions',
    'annotated_types',
]

a = Analysis(
    [os.path.join(project_path, 'run_agent_gui.py')],
    pathex=[project_path],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'torch',
        'tensorflow',
        'transformers',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PhoneAgent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可以设置图标路径
)

# 注意: 打包为单个EXE文件而非目录
# 这有助于防止多进程问题
