"""ADB utility functions for subprocess handling."""

import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import List, Optional, Any

# 全局ADB路径缓存
_ADB_PATH: Optional[str] = None
_ADB_INITIALIZED: bool = False


def get_bundled_adb_dir() -> Path:
    """
    获取打包应用中的ADB工具目录。
    
    对于打包后的EXE，ADB工具可能在以下位置：
    1. EXE同目录下的 platform-tools 文件夹
    2. EXE内部打包的资源中（需要解压）
    3. 系统PATH中
    """
    if getattr(sys, 'frozen', False):
        # 打包后的EXE环境
        exe_dir = Path(sys.executable).parent
        
        # 优先检查EXE同目录下的platform-tools
        platform_tools = exe_dir / "platform-tools"
        if platform_tools.exists() and (platform_tools / "adb.exe").exists():
            return platform_tools
        
        # 检查_internal目录（PyInstaller onefile模式的临时解压目录）
        internal_dir = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else exe_dir
        internal_adb = internal_dir / "platform-tools"
        if internal_adb.exists() and (internal_adb / "adb.exe").exists():
            return internal_adb
    else:
        # 开发环境
        project_dir = Path(__file__).parent.parent.parent
        platform_tools = project_dir / "platform-tools"
        if platform_tools.exists():
            return platform_tools
    
    return None


def get_adb_executable() -> str:
    """
    获取ADB可执行文件的完整路径。
    
    按以下优先级查找：
    1. 打包的EXE内嵌的ADB
    2. EXE同目录下的platform-tools
    3. 系统环境变量中的ADB
    4. 常见安装路径
    
    Returns:
        ADB可执行文件路径
    """
    global _ADB_PATH, _ADB_INITIALIZED
    
    if _ADB_INITIALIZED and _ADB_PATH:
        return _ADB_PATH
    
    _ADB_INITIALIZED = True
    
    # 1. 检查打包的ADB
    bundled_dir = get_bundled_adb_dir()
    if bundled_dir:
        adb_exe = bundled_dir / ("adb.exe" if sys.platform == 'win32' else "adb")
        if adb_exe.exists():
            _ADB_PATH = str(adb_exe)
            # 确保ADB服务启动
            _start_adb_server(_ADB_PATH)
            return _ADB_PATH
    
    # 2. 检查常见路径
    common_paths = [
        Path(r"C:\platform-tools\adb.exe"),
        Path(os.environ.get("ANDROID_HOME", "")) / "platform-tools" / "adb.exe",
        Path(os.environ.get("ANDROID_SDK_ROOT", "")) / "platform-tools" / "adb.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Android" / "Sdk" / "platform-tools" / "adb.exe",
    ]
    
    for adb_path in common_paths:
        if adb_path.exists():
            _ADB_PATH = str(adb_path)
            return _ADB_PATH
    
    # 3. 检查系统PATH
    adb_in_path = shutil.which("adb")
    if adb_in_path:
        _ADB_PATH = adb_in_path
        return _ADB_PATH
    
    # 4. 默认使用"adb"，让系统去找
    _ADB_PATH = "adb"
    return _ADB_PATH


def _start_adb_server(adb_path: str) -> None:
    """启动ADB服务器"""
    try:
        subprocess.run(
            [adb_path, "start-server"],
            capture_output=True,
            timeout=10,
            **get_subprocess_flags()
        )
    except Exception:
        pass  # 忽略启动失败


def get_subprocess_flags() -> dict:
    """
    Get platform-specific subprocess flags to prevent window popups on Windows.
    
    Returns:
        Dictionary of kwargs to pass to subprocess.run()
    """
    kwargs: dict = {}
    if sys.platform == 'win32':
        # Prevent console window popup on Windows
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
    return kwargs


def run_adb_command(
    args: List[str],
    capture_output: bool = True,
    text: bool = True,
    timeout: Optional[int] = None,
    encoding: str = "utf-8",
    errors: str = "replace",
    **kwargs
) -> subprocess.CompletedProcess:
    """
    Run an ADB command with proper Windows handling.
    
    自动使用正确的ADB路径（内嵌或系统）
    
    Args:
        args: Command arguments list (e.g., ["adb", "devices"])
        capture_output: Whether to capture stdout/stderr
        text: Whether to decode output as text
        timeout: Command timeout in seconds
        encoding: Text encoding
        errors: Error handling mode
        **kwargs: Additional subprocess.run arguments
        
    Returns:
        CompletedProcess instance
    """
    # 替换第一个参数（adb）为正确的路径
    if args and args[0] == "adb":
        args = [get_adb_executable()] + args[1:]
    
    # Merge with platform-specific flags
    run_kwargs = get_subprocess_flags()
    run_kwargs.update({
        'capture_output': capture_output,
        'text': text,
        'encoding': encoding,
        'errors': errors,
    })
    if timeout is not None:
        run_kwargs['timeout'] = timeout
    run_kwargs.update(kwargs)
    
    return subprocess.run(args, **run_kwargs)


def get_adb_prefix(device_id: str | None) -> list:
    """
    Get ADB command prefix with optional device specifier.
    
    自动使用正确的ADB路径
    
    Args:
        device_id: Optional device ID for multi-device setups
        
    Returns:
        List of command prefix arguments
    """
    adb_exe = get_adb_executable()
    if device_id:
        return [adb_exe, "-s", device_id]
    return [adb_exe]


def check_adb_available() -> tuple[bool, str]:
    """
    检查ADB是否可用。
    
    Returns:
        (是否可用, 状态消息)
    """
    try:
        adb_exe = get_adb_executable()
        result = subprocess.run(
            [adb_exe, "version"],
            capture_output=True,
            text=True,
            timeout=5,
            encoding="utf-8",
            errors="replace",
            **get_subprocess_flags()
        )
        if result.returncode == 0:
            version = result.stdout.split('\n')[0] if result.stdout else "已安装"
            return True, version
        return False, "ADB返回错误"
    except FileNotFoundError:
        return False, "未找到ADB工具"
    except Exception as e:
        return False, f"ADB错误: {e}"


def get_connected_devices() -> list[str]:
    """
    获取已连接的设备列表。
    
    Returns:
        设备ID列表
    """
    try:
        adb_exe = get_adb_executable()
        result = subprocess.run(
            [adb_exe, "devices"],
            capture_output=True,
            text=True,
            timeout=5,
            encoding="utf-8",
            errors="replace",
            **get_subprocess_flags()
        )
        devices = []
        for line in result.stdout.strip().split('\n')[1:]:
            if line.strip() and 'device' in line:
                device_id = line.split()[0]
                devices.append(device_id)
        return devices
    except Exception:
        return []
