#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phone Agent 打包脚本
使用PyInstaller将应用打包成独立EXE文件（包含ADB工具）
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# 设置Windows控制台为UTF-8编码
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 项目根目录
ROOT_DIR = Path(__file__).parent
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build"


def find_adb_tools() -> Path:
    """查找ADB工具目录"""
    adb_paths = [
        Path(r"C:\platform-tools"),
        ROOT_DIR / "platform-tools",
        Path(os.environ.get("ANDROID_HOME", "")) / "platform-tools",
        Path(os.environ.get("ANDROID_SDK_ROOT", "")) / "platform-tools",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Android" / "Sdk" / "platform-tools",
    ]
    
    for adb_path in adb_paths:
        if adb_path.exists() and (adb_path / "adb.exe").exists():
            return adb_path
    return None


def check_pyinstaller():
    """检查PyInstaller是否已安装"""
    try:
        import PyInstaller
        print(f"✅ PyInstaller 版本: {PyInstaller.__version__}")
        return True
    except ImportError:
        print("❌ PyInstaller 未安装")
        return False


def install_pyinstaller():
    """安装PyInstaller"""
    print("📦 正在安装 PyInstaller...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller", "-q"])
    print("✅ PyInstaller 安装完成")


def create_spec_file(include_adb: bool = True):
    """创建PyInstaller spec文件"""
    
    # 查找ADB工具
    adb_path = find_adb_tools() if include_adb else None
    adb_datas = ""
    if adb_path:
        adb_datas = f"    (r'{adb_path}', 'platform-tools'),\n"
        print(f"✅ 将嵌入 ADB 工具: {adb_path}")
    else:
        print("⚠️  未找到 ADB 工具，EXE将依赖系统PATH中的ADB")
    
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
import os
import sys

block_cipher = None

# 获取项目路径
project_path = os.path.dirname(os.path.abspath(SPEC))

# 收集数据文件（包括ADB工具）
datas = [
    (os.path.join(project_path, 'phone_agent'), 'phone_agent'),
    (os.path.join(project_path, 'resources'), 'resources'),
{adb_datas}]

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
    hooksconfig={{}},
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
'''
    
    spec_path = ROOT_DIR / "PhoneAgent.spec"
    with open(spec_path, 'w', encoding='utf-8') as f:
        f.write(spec_content)
    print(f"✅ 已创建 spec 文件: {spec_path}")
    return spec_path


def build_exe(include_adb: bool = True):
    """构建EXE文件"""
    print("\n🔨 开始构建 EXE...")
    print("=" * 50)
    
    # 检查并安装PyInstaller
    if not check_pyinstaller():
        install_pyinstaller()
    
    # 创建spec文件（包含ADB）
    spec_path = create_spec_file(include_adb=include_adb)
    
    # 清理旧的构建文件
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    
    # 运行PyInstaller
    print("\n📦 正在打包...")
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(spec_path), "--clean"],
        cwd=str(ROOT_DIR),
        capture_output=False
    )
    
    if result.returncode == 0:
        exe_path = DIST_DIR / "PhoneAgent.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print("\n" + "=" * 50)
            print("✅ 构建成功!")
            print(f"📁 输出文件: {exe_path}")
            print(f"📊 文件大小: {size_mb:.1f} MB")
            if include_adb:
                print("\n💡 此EXE已内置ADB工具，无需额外安装!")
            print("\n💡 使用说明:")
            print("   1. 将 PhoneAgent.exe 复制到任意位置")
            print("   2. 连接手机并启用 USB 调试")
            print("   3. 双击运行 PhoneAgent.exe")
            return True
    
    print("\n❌ 构建失败，请检查错误信息")
    return False


def build_standalone():
    """构建完全独立的一体化版本（推荐）"""
    print("\n🔨 开始构建完全独立版本...")
    print("=" * 50)
    
    # 检查ADB工具
    adb_path = find_adb_tools()
    if not adb_path:
        print("❌ 未找到ADB工具！")
        print("请先下载 Android Platform Tools:")
        print("   https://developer.android.com/studio/releases/platform-tools")
        print("   并解压到 C:\\platform-tools 或项目目录下的 platform-tools")
        return False
    
    print(f"✅ 找到 ADB 工具: {adb_path}")
    
    # 构建包含ADB的EXE
    if not build_exe(include_adb=True):
        return False
    
    exe_path = DIST_DIR / "PhoneAgent.exe"
    size_mb = exe_path.stat().st_size / (1024 * 1024)
    
    print("\n" + "=" * 50)
    print("🎉 完全独立版本构建成功!")
    print("=" * 50)
    print(f"\n📁 输出文件: {exe_path}")
    print(f"📊 文件大小: {size_mb:.1f} MB")
    print("\n✨ 特点:")
    print("   ✅ 内置 ADB 工具")
    print("   ✅ 无需安装 Python")
    print("   ✅ 无需配置环境变量")
    print("   ✅ 双击即可运行")
    print("\n📋 使用步骤:")
    print("   1. 将 PhoneAgent.exe 复制到任意位置")
    print("   2. 手机通过USB连接电脑")
    print("   3. 手机开启USB调试（开发者选项）")
    print("   4. 双击运行 PhoneAgent.exe")
    print("   5. 输入智谱AI的API Key")
    print("   6. 输入任务描述，点击执行")
    
    return True


def build_with_adb():
    """构建包含ADB的版本（旧方法，保留兼容）"""
    print("\n🔨 开始构建带ADB的完整版本...")
    
    # 首先构建基础EXE（带ADB）
    if not build_exe(include_adb=True):
        return False
    
    # 创建完整发布目录
    release_dir = DIST_DIR / "PhoneAgent_Full"
    release_dir.mkdir(exist_ok=True)
    
    # 复制EXE
    shutil.copy(DIST_DIR / "PhoneAgent.exe", release_dir)
    
    # 也复制一份ADB到外部目录（备用）
    adb_path = find_adb_tools()
    if adb_path:
        adb_dest = release_dir / "platform-tools"
        shutil.copytree(adb_path, adb_dest, dirs_exist_ok=True)
        print(f"✅ 已复制备用 ADB 工具: {adb_path}")
    else:
        print("⚠️  未找到 ADB 工具")
    
    # 创建启动脚本
    launcher_content = '''@echo off
chcp 65001 > nul
cd /d "%~dp0"

REM 设置ADB路径
if exist "%~dp0platform-tools\\adb.exe" (
    set PATH=%~dp0platform-tools;%PATH%
)

REM 启动PhoneAgent
start "" "%~dp0PhoneAgent.exe"
'''
    
    with open(release_dir / "启动PhoneAgent.bat", 'w', encoding='utf-8') as f:
        f.write(launcher_content)
    
    # 创建README
    readme_content = '''# Phone Agent - AI手机自动化助手

## 🎉 完全独立版本

此版本已内置所有依赖，无需安装任何环境！

## 使用说明

1. 确保手机已连接到电脑并启用USB调试
2. 直接双击运行 "PhoneAgent.exe"
3. 在界面中输入API Key（智谱AI）
4. 输入任务描述，点击"执行任务"

## 关于ADB工具

EXE已内置ADB工具，无需额外配置。
外部的platform-tools文件夹为备用，可删除。

## 获取API Key

1. 访问 https://open.bigmodel.cn/
2. 注册并创建API Key
3. 复制API Key到程序中

## 常见问题

Q: 提示找不到设备？
A: 检查USB连接，确保手机开启USB调试

Q: 执行任务失败？
A: 检查API Key是否正确，网络是否正常

## 支持的任务示例

- 打开微信发送消息给张三
- 打开抖音刷5个视频
- 打开淘宝搜索手机壳
- 打开地图导航到最近的星巴克
'''
    
    with open(release_dir / "README.txt", 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print("\n" + "=" * 50)
    print("✅ 完整版本构建成功!")
    print(f"📁 输出目录: {release_dir}")
    print("\n📦 发布包内容:")
    for item in release_dir.iterdir():
        if item.is_file():
            size = item.stat().st_size / 1024
            print(f"   - {item.name} ({size:.1f} KB)")
        else:
            print(f"   - {item.name}/ (文件夹)")
    
    return True


def main():
    print("=" * 50)
    print("   Phone Agent 打包工具")
    print("=" * 50)
    print("\n请选择打包模式:")
    print("1. 🚀 完全独立版 - 单个EXE内置ADB（推荐）")
    print("2. 📦 完整发布包 - EXE + 外部ADB备份")
    print("3. ⚡ 基础版 - 仅EXE（需系统安装ADB）")
    print("4. 退出")
    
    choice = input("\n请输入选择 (1/2/3/4): ").strip()
    
    if choice == "1":
        build_standalone()
    elif choice == "2":
        build_with_adb()
    elif choice == "3":
        build_exe(include_adb=False)
    elif choice == "4":
        print("👋 再见!")
    else:
        print("❌ 无效选择")


if __name__ == "__main__":
    main()
