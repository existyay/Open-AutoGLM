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
    
    # 预定义模型列表
    AVAILABLE_MODELS = {
        'AutoGLM-Phone-9B': ModelInfo(
            name='AutoGLM-Phone-9B',
            repo_id='zai-org/AutoGLM-Phone-9B',
            source='huggingface',
            size_gb=18.0,
            files=[],  # 将动态获取
            quantization='fp16',
            description='官方完整模型 (FP16精度，需要16GB+显存)'
        ),
        'AutoGLM-Phone-9B-Multilingual': ModelInfo(
            name='AutoGLM-Phone-9B-Multilingual',
            repo_id='zai-org/AutoGLM-Phone-9B-Multilingual',
            source='huggingface',
            size_gb=18.0,
            files=[],
            quantization='fp16',
            description='官方多语言模型 (FP16精度，需要16GB+显存)'
        ),
        'AutoGLM-Phone-9B-ModelScope': ModelInfo(
            name='AutoGLM-Phone-9B',
            repo_id='ZhipuAI/AutoGLM-Phone-9B',
            source='modelscope',
            size_gb=18.0,
            files=[],
            quantization='fp16',
            description='官方完整模型 (ModelScope源，国内推荐)'
        ),
    }
    
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
            use_mirror: 是否使用镜像源（国内加速）
            
        Returns:
            是否下载成功
        """
        self._progress_callback = progress_callback
        self._stop_flag = False
        
        if model_name not in self.AVAILABLE_MODELS:
            self.progress.status = "error"
            self.progress.error_message = f"未知模型: {model_name}"
            return False
            
        model_info = self.AVAILABLE_MODELS[model_name]
        model_path = self.get_model_path(model_name)
        
        try:
            self.progress.status = "downloading"
            self.progress.current_file = "准备下载..."
            self._notify_progress()
            
            if model_info.source == 'huggingface':
                success = self._download_from_huggingface(
                    model_info.repo_id, model_path, use_mirror
                )
            else:
                success = self._download_from_modelscope(
                    model_info.repo_id, model_path
                )
                
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
                
    def _download_from_huggingface(self, repo_id: str, save_path: Path, 
                                    use_mirror: bool = True) -> bool:
        """从HuggingFace下载模型"""
        try:
            # 尝试使用 huggingface_hub
            from huggingface_hub import snapshot_download, hf_hub_download
            
            # 设置镜像
            if use_mirror:
                os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
                
            self.progress.current_file = f"下载模型: {repo_id}"
            self._notify_progress()
            
            # 使用 snapshot_download 下载整个仓库
            snapshot_download(
                repo_id=repo_id,
                local_dir=str(save_path),
                local_dir_use_symlinks=False,
                resume_download=True,
            )
            
            return True
            
        except ImportError:
            self.progress.current_file = "正在安装 huggingface_hub..."
            self._notify_progress()
            
            # 安装 huggingface_hub
            import subprocess
            subprocess.run(
                [sys.executable, '-m', 'pip', 'install', 'huggingface_hub'],
                capture_output=True
            )
            
            # 重试
            return self._download_from_huggingface(repo_id, save_path, use_mirror)
            
        except Exception as e:
            self.progress.status = "error"
            self.progress.error_message = f"HuggingFace下载失败: {str(e)}"
            self._notify_progress()
            return False
            
    def _download_from_modelscope(self, repo_id: str, save_path: Path) -> bool:
        """从ModelScope下载模型"""
        try:
            from modelscope import snapshot_download
            
            self.progress.current_file = f"下载模型: {repo_id}"
            self._notify_progress()
            
            snapshot_download(
                repo_id,
                cache_dir=str(save_path.parent),
                local_dir=str(save_path),
            )
            
            return True
            
        except ImportError:
            self.progress.current_file = "正在安装 modelscope..."
            self._notify_progress()
            
            import subprocess
            subprocess.run(
                [sys.executable, '-m', 'pip', 'install', 'modelscope'],
                capture_output=True
            )
            
            return self._download_from_modelscope(repo_id, save_path)
            
        except Exception as e:
            self.progress.status = "error"
            self.progress.error_message = f"ModelScope下载失败: {str(e)}"
            self._notify_progress()
            return False
            
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
        
    def start(self, gpu_memory_utilization: float = 0.9,
              max_model_len: int = 8192) -> bool:
        """启动vLLM服务"""
        try:
            import subprocess
            
            cmd = [
                sys.executable, '-m', 'vllm.entrypoints.openai.api_server',
                '--model', self.model_path,
                '--port', str(self.port),
                '--gpu-memory-utilization', str(gpu_memory_utilization),
                '--max-model-len', str(max_model_len),
                '--trust-remote-code',
            ]
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            
            # 等待服务启动
            time.sleep(10)
            
            if self.process.poll() is None:
                self._is_running = True
                return True
            else:
                return False
                
        except Exception as e:
            print(f"启动vLLM服务失败: {e}")
            return False
            
    def stop(self):
        """停止vLLM服务"""
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=10)
            self.process = None
        self._is_running = False
        
    def is_running(self) -> bool:
        """检查服务是否运行中"""
        if self.process is None:
            return False
        return self.process.poll() is None
        
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
