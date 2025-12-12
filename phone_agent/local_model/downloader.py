"""
模型下载模块
支持从HuggingFace和ModelScope下载模型
"""

import os
import sys
import json
import hashlib
import threading
import time
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Callable, Dict, Any, List
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


@dataclass
class ModelInfo:
    """模型信息"""
    name: str
    repo_id: str
    source: str  # 'huggingface' or 'modelscope'
    size_gb: float
    files: List[str]
    quantization: str
    description: str


class DownloadProgress:
    """下载进度跟踪"""
    
    def __init__(self, total_size: int = 0):
        self.total_size = total_size
        self.downloaded_size = 0
        self.current_file = ""
        self.current_file_size = 0
        self.current_file_downloaded = 0
        self.speed = 0.0  # MB/s
        self.eta = 0  # 秒
        self.status = "waiting"  # waiting, downloading, completed, error
        self.error_message = ""
        self._last_time = time.time()
        self._last_downloaded = 0
        
    def update(self, downloaded: int):
        """更新进度"""
        self.current_file_downloaded = downloaded
        current_time = time.time()
        time_diff = current_time - self._last_time
        
        if time_diff >= 1.0:  # 每秒更新一次速度
            size_diff = downloaded - self._last_downloaded
            self.speed = size_diff / (1024 * 1024 * time_diff)  # MB/s
            
            if self.speed > 0:
                remaining = self.current_file_size - downloaded
                self.eta = int(remaining / (self.speed * 1024 * 1024))
            
            self._last_time = current_time
            self._last_downloaded = downloaded
            
    @property
    def percent(self) -> float:
        """获取当前文件下载百分比"""
        if self.current_file_size <= 0:
            return 0.0
        return min(100.0, (self.current_file_downloaded / self.current_file_size) * 100)
        
    @property
    def total_percent(self) -> float:
        """获取总体下载百分比"""
        if self.total_size <= 0:
            return 0.0
        total_downloaded = self.downloaded_size + self.current_file_downloaded
        return min(100.0, (total_downloaded / self.total_size) * 100)


class ModelDownloader:
    """模型下载器"""
    
    # 预定义模型列表 - 仅使用ModelScope源
    AVAILABLE_MODELS = {
        'AutoGLM-Phone-9B': ModelInfo(
            name='AutoGLM-Phone-9B',
            repo_id='ZhipuAI/AutoGLM-Phone-9B',
            source='modelscope',
            size_gb=18.0,
            files=[],
            quantization='fp16',
            description='官方完整模型 (FP16精度，需要16GB+显存)'
        ),
    }
    
    # ModelScope Git Clone URL
    MODELSCOPE_GIT_URL = "https://www.modelscope.cn/ZhipuAI/AutoGLM-Phone-9B.git"
    
    def __init__(self, model_dir: Optional[str] = None):
        """
        初始化下载器
        
        Args:
            model_dir: 模型存储目录，默认为 ~/.autoglm/models
        """
        if model_dir:
            self.model_dir = Path(model_dir)
        else:
            self.model_dir = Path.home() / '.autoglm' / 'models'
            
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.progress = DownloadProgress()
        self._stop_flag = False
        self._download_thread: Optional[threading.Thread] = None
        self._progress_callback: Optional[Callable[[DownloadProgress], None]] = None
        
    def get_model_path(self, model_name: str) -> Path:
        """获取模型本地路径"""
        return self.model_dir / model_name.replace('/', '_')
        
    def is_model_downloaded(self, model_name: str) -> bool:
        """检查模型是否已下载"""
        model_path = self.get_model_path(model_name)
        if not model_path.exists():
            return False
            
        # 检查是否有必要的文件
        required_files = ['config.json', 'tokenizer.json']
        for f in required_files:
            if not (model_path / f).exists():
                return False
                
        # 检查是否有模型权重文件
        weight_patterns = ['*.safetensors', '*.bin', '*.gguf']
        for pattern in weight_patterns:
            if list(model_path.glob(pattern)):
                return True
                
        return False
        
    def get_downloaded_models(self) -> List[str]:
        """获取已下载的模型列表"""
        downloaded = []
        if self.model_dir.exists():
            for path in self.model_dir.iterdir():
                if path.is_dir() and self.is_model_downloaded(path.name):
                    downloaded.append(path.name)
        return downloaded
        
    def download_model(self, model_name: str, 
                       progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
                       use_mirror: bool = True) -> bool:
        """
        下载模型
        
        Args:
            model_name: 模型名称（从AVAILABLE_MODELS中选择）
            progress_callback: 进度回调函数
            use_mirror: 是否使用镜像源（已弃用，统一使用ModelScope）
            
        Returns:
            是否下载成功
        """
        self._progress_callback = progress_callback
        self._stop_flag = False
        
        if model_name not in self.AVAILABLE_MODELS:
            self.progress.status = "error"
            self.progress.error_message = f"未知模型: {model_name}"
            return False
            
        model_path = self.get_model_path(model_name)
        
        try:
            self.progress.status = "downloading"
            self.progress.current_file = "准备使用 Git LFS 下载..."
            self._notify_progress()
            
            # 统一使用 git clone 从 ModelScope 下载
            success = self._download_via_git_clone(model_path)
                
            if success:
                self.progress.status = "completed"
                self._notify_progress()
                return True
            else:
                return False
                
        except Exception as e:
            self.progress.status = "error"
            self.progress.error_message = str(e)
            self._notify_progress()
            return False
    
    def _download_via_git_clone(self, save_path: Path) -> bool:
        """使用 git clone 从 ModelScope 下载模型"""
        import shutil
        
        # 检查 git 和 git-lfs 是否可用
        try:
            result = subprocess.run(
                ['git', '--version'],
                capture_output=True, text=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            if result.returncode != 0:
                self.progress.status = "error"
                self.progress.error_message = "Git 未安装，请先安装 Git"
                self._notify_progress()
                return False
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self.progress.status = "error"
            self.progress.error_message = "Git 未安装，请先安装 Git: https://git-scm.com/downloads"
            self._notify_progress()
            return False
        
        # 检查 git-lfs
        try:
            result = subprocess.run(
                ['git', 'lfs', 'version'],
                capture_output=True, text=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            if result.returncode != 0:
                self.progress.status = "error"
                self.progress.error_message = "Git LFS 未安装，请先安装: git lfs install"
                self._notify_progress()
                return False
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self.progress.status = "error"
            self.progress.error_message = "Git LFS 未安装，请运行: git lfs install"
            self._notify_progress()
            return False
        
        # 如果目标目录已存在，先删除
        if save_path.exists():
            try:
                shutil.rmtree(save_path)
            except Exception as e:
                self.progress.status = "error"
                self.progress.error_message = f"无法删除旧目录: {e}"
                self._notify_progress()
                return False
        
        # 确保父目录存在
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.progress.current_file = f"正在从 ModelScope 克隆模型 (约18GB)..."
        self._notify_progress()
        print(f"📥 执行: git clone {self.MODELSCOPE_GIT_URL}")
        
        try:
            # 使用 git clone 下载
            process = subprocess.Popen(
                ['git', 'clone', self.MODELSCOPE_GIT_URL, str(save_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
                cwd=str(save_path.parent)
            )
            
            # 实时读取输出
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    line = line.strip()
                    if line:
                        # 解析 git 进度信息
                        if 'Receiving objects:' in line or 'Resolving deltas:' in line:
                            self.progress.current_file = line
                            self._notify_progress()
                        elif '%' in line:
                            self.progress.current_file = line
                            self._notify_progress()
                        print(line)
            
            if process.returncode == 0:
                self.progress.current_file = "✅ 模型下载完成!"
                self._notify_progress()
                print("✅ Git clone 成功")
                return True
            else:
                self.progress.status = "error"
                self.progress.error_message = f"Git clone 失败，返回码: {process.returncode}"
                self._notify_progress()
                return False
                
        except Exception as e:
            self.progress.status = "error"
            self.progress.error_message = f"Git clone 异常: {str(e)}"
            self._notify_progress()
            return False
            
    def download_model_async(self, model_name: str,
                             progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
                             use_mirror: bool = True):
        """异步下载模型"""
        self._download_thread = threading.Thread(
            target=self.download_model,
            args=(model_name, progress_callback, use_mirror),
            daemon=True
        )
        self._download_thread.start()
        
    def stop_download(self):
        """停止下载"""
        self._stop_flag = True
        if self._download_thread and self._download_thread.is_alive():
            self._download_thread.join(timeout=5)
            
    def _notify_progress(self):
        """通知进度更新"""
        if self._progress_callback:
            try:
                self._progress_callback(self.progress)
            except Exception:
                pass
            
    def delete_model(self, model_name: str) -> bool:
        """删除已下载的模型"""
        import shutil
        
        model_path = self.get_model_path(model_name)
        if model_path.exists():
            try:
                shutil.rmtree(model_path)
                return True
            except Exception:
                return False
        return True
        
    def get_model_size(self, model_name: str) -> int:
        """获取模型大小（字节）"""
        model_path = self.get_model_path(model_name)
        if not model_path.exists():
            return 0
            
        total_size = 0
        for f in model_path.rglob('*'):
            if f.is_file():
                total_size += f.stat().st_size
        return total_size


class VLLMServerManager:
    """vLLM服务管理器"""
    
    def __init__(self, model_path: str, port: int = 8000):
        self.model_path = model_path
        self.port = port
        self.process: Optional[object] = None
        self._is_running = False
        self._startup_timeout = 30  # 启动超时时间（秒）
        
    def start(self, gpu_memory_utilization: float = 0.9,
              max_model_len: int = 8192) -> bool:
        """启动vLLM服务"""
        try:
            import subprocess
            import requests
            
            # 检查模型路径是否存在
            if not Path(self.model_path).exists():
                print(f"❌ 模型路径不存在: {self.model_path}")
                return False
            
            cmd = [
                sys.executable, '-m', 'vllm.entrypoints.openai.api_server',
                '--model', self.model_path,
                '--port', str(self.port),
                '--gpu-memory-utilization', str(gpu_memory_utilization),
                '--max-model-len', str(max_model_len),
                '--trust-remote-code',
            ]
            
            print(f"📝 启动命令: {' '.join(cmd)}")
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            
            print(f"⏳ 等待vLLM服务启动 (最多{self._startup_timeout}秒)...")
            
            # 检查进程是否立即崩溃
            time.sleep(2)
            if self.process.poll() is not None:
                stderr = self.process.stderr.read() if self.process.stderr else ""
                stdout = self.process.stdout.read() if self.process.stdout else ""
                error_msg = f"进程立即退出\nSTDOUT: {stdout}\nSTDERR: {stderr}"
                print(f"❌ {error_msg}")
                return False
            
            # 轮询检查服务是否启动
            for attempt in range(self._startup_timeout):
                try:
                    response = requests.get(f"http://localhost:{self.port}/v1/models", timeout=2)
                    if response.status_code == 200:
                        print(f"✅ vLLM服务已启动 (耗时{attempt}秒)")
                        self._is_running = True
                        return True
                except Exception:
                    pass
                
                time.sleep(1)
                
                # 再次检查进程是否还在运行
                if self.process.poll() is not None:
                    stderr = self.process.stderr.read() if self.process.stderr else ""
                    stdout = self.process.stdout.read() if self.process.stdout else ""
                    error_msg = f"启动过程中进程退出\nSTDOUT: {stdout}\nSTDERR: {stderr}"
                    print(f"❌ {error_msg}")
                    return False
            
            print(f"❌ 启动超时({self._startup_timeout}秒)，服务未响应")
            self.stop()
            return False
                
        except ImportError as e:
            print(f"❌ 缺少依赖: {e}")
            print("请安装: pip install vllm requests")
            return False
        except Exception as e:
            print(f"❌ 启动vLLM服务失败: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    def stop(self):
        """停止vLLM服务"""
        if self.process:
            try:
                if self.process.poll() is None:  # 进程仍在运行
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        print("⚠️  进程未在规定时间内停止，强制杀死...")
                        self.process.kill()
                        self.process.wait()
            except Exception as e:
                print(f"⚠️  停止进程时出错: {e}")
            finally:
                self.process = None
        self._is_running = False
        print("✅ vLLM服务已停止")
        
    def is_running(self) -> bool:
        """检查服务是否运行中"""
        if self.process is None:
            return False
        
        # 检查进程是否仍在运行
        poll_result = self.process.poll()
        if poll_result is not None:
            self._is_running = False
            return False
        
        # 尝试ping API检查是否真正可用
        try:
            import requests
            response = requests.get(f"http://localhost:{self.port}/v1/models", timeout=2)
            return response.status_code == 200
        except Exception:
            return False
        
    def get_api_base(self) -> str:
        """获取API基础URL"""
        return f"http://localhost:{self.port}/v1"


if __name__ == '__main__':
    # 测试下载器
    downloader = ModelDownloader()
    
    print("可用模型:")
    for name, info in downloader.AVAILABLE_MODELS.items():
        print(f"  - {name}: {info.description}")
        
    print(f"\n已下载模型: {downloader.get_downloaded_models()}")
