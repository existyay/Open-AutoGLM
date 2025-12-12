"""本地模型管理器 - 整合环境检测、模型下载和服务管理"""

import sys
import json
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, Any, List

from phone_agent.local_model.environment import EnvironmentDetector, SystemInfo
from phone_agent.local_model.downloader import ModelDownloader, DownloadProgress, VLLMServerManager


@dataclass
class LocalModelConfig:
    """本地模型配置"""
    model_name: str
    model_path: str
    quantization: str = "fp16"
    port: int = 8000
    gpu_memory_utilization: float = 0.9
    max_model_len: int = 8192


class LocalModelManager:
    """本地模型管理器 - 简洁高效实现"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.base_dir = Path.home() / '.autoglm'
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        self.config_path = Path(config_path) if config_path else self.base_dir / 'config.json'
        self.environment = EnvironmentDetector()
        self.downloader = ModelDownloader(str(self.base_dir / 'models'))
        self.server: Optional[VLLMServerManager] = None
        
        self._config = self._load_config()
        self._status_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
        
    def _load_config(self) -> Dict[str, Any]:
        if self.config_path.exists():
            try:
                return json.loads(self.config_path.read_text(encoding='utf-8'))
            except Exception:
                pass
        return {}
        
    def _save_config(self):
        try:
            self.config_path.write_text(json.dumps(self._config, indent=2, ensure_ascii=False), encoding='utf-8')
        except Exception:
            pass
            
    def set_status_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        self._status_callback = callback
        
    def _notify_status(self, event: str, data: Dict[str, Any] = None):
        if self._status_callback:
            try:
                self._status_callback(event, data or {})
            except Exception:
                pass
                
    def check_environment(self) -> SystemInfo:
        self._notify_status('environment_check_start')
        info = self.environment.detect()
        self._notify_status('environment_check_done', self.environment.to_dict())
        return info
        
    def get_recommended_setup(self) -> Dict[str, Any]:
        """获取推荐配置方案"""
        if not self.environment.system_info:
            self.check_environment()
            
        info = self.environment.system_info
        
        if not info.can_run_local:
            return {
                'can_run_local': False, 'reason': info.reason,
                'recommended_model': 'API_MODE', 'recommended_quantization': 'none',
                'steps': [{'step': 1, 'description': '使用云端API模式', 'action': 'use_api'},
                         {'step': 2, 'description': '配置API密钥', 'action': 'config_api_key'}]
            }
            
        # 构建安装步骤
        steps, step_num = [], 1
        
        # 检查依赖并添加安装步骤
        dep_checks = [
            ('torch', lambda: __import__('torch').cuda.is_available(), 
             'install_pytorch', self.environment.get_torch_install_command()),
            ('vllm', lambda: __import__('vllm'), 'install_vllm', 'pip install vllm'),
            ('transformers', lambda: __import__('transformers'), 'install_transformers', 'pip install transformers'),
        ]
        
        for name, check_fn, action, cmd in dep_checks:
            try:
                check_fn()
            except (ImportError, RuntimeError):
                steps.append({'step': step_num, 'description': f'安装{name}', 'action': action, 'command': cmd})
                step_num += 1
                
        # 下载模型
        if not self.downloader.is_model_downloaded(info.recommended_model):
            steps.append({'step': step_num, 'description': f'下载模型: {info.recommended_model}', 
                         'action': 'download_model', 'model': info.recommended_model})
            step_num += 1
            
        steps.append({'step': step_num, 'description': '启动本地推理服务', 'action': 'start_server'})
        
        return {
            'can_run_local': True, 'reason': info.reason,
            'recommended_model': info.recommended_model, 'recommended_quantization': info.recommended_quantization,
            'steps': steps
        }
        
    def _pip_install(self, packages: List[str]) -> bool:
        """安装pip包"""
        for pkg in packages:
            try:
                __import__(pkg.split('[')[0])  # 处理 pkg[extras] 格式
            except ImportError:
                proc = subprocess.Popen(
                    [sys.executable, '-m', 'pip', 'install', pkg, '-q'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                )
                proc.wait(timeout=120)
                if proc.returncode != 0:
                    return False
        return True
        
    def install_dependencies(self, progress_callback: Optional[Callable[[str, float], None]] = None) -> bool:
        """安装必要的依赖"""
        try:
            if progress_callback:
                progress_callback('检查环境...', 0.05)
                
            if not self.environment.system_info:
                self.check_environment()
            
            print("📦 开始安装依赖...")
                
            # 安装PyTorch
            if progress_callback:
                progress_callback('安装PyTorch...', 0.1)
            
            torch_cmd = self.environment.get_torch_install_command()
            print(f"📝 执行: {torch_cmd}")
            proc = subprocess.Popen(
                torch_cmd.split(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            stdout, stderr = proc.communicate(timeout=120)
            if proc.returncode != 0:
                error_msg = f"安装PyTorch失败: {stderr}"
                print(f"❌ {error_msg}")
                raise Exception(error_msg)
            print("✅ PyTorch 安装成功")
                
            # 安装其他依赖
            if progress_callback:
                progress_callback('安装vLLM和其他依赖...', 0.5)
            
            deps = ['vllm', 'transformers', 'accelerate', 'sentencepiece', 'requests']
            for dep in deps:
                print(f"📦 安装 {dep}...")
                proc = subprocess.Popen(
                    [sys.executable, '-m', 'pip', 'install', dep, '-q'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                )
                stdout, stderr = proc.communicate(timeout=60)
                if proc.returncode != 0:
                    error_msg = f"安装{dep}失败: {stderr}"
                    print(f"⚠️  {error_msg}")
                    # 继续尝试安装其他依赖
                else:
                    print(f"✅ {dep} 安装成功")
                
            if progress_callback:
                progress_callback('安装完成', 1.0)
            print("✅ 所有依赖安装完成")
            return True
            
        except Exception as e:
            error_msg = f'安装依赖失败: {str(e)}'
            self._notify_status('install_error', {'error': error_msg})
            print(f"❌ {error_msg}")
            return False
            
    def download_model(self, model_name: str = None,
                       progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
                       use_mirror: bool = True) -> bool:
        """下载模型"""
        if not model_name:
            if not self.environment.system_info:
                self.check_environment()
            model_name = self.environment.system_info.recommended_model
            
        if model_name == 'API_MODE':
            return False
            
        self._notify_status('download_start', {'model': model_name})
        success = self.downloader.download_model(model_name, progress_callback, use_mirror)
        
        if success:
            self._config.update({'last_model': model_name, 
                               'model_path': str(self.downloader.get_model_path(model_name))})
            self._save_config()
            self._notify_status('download_complete', {'model': model_name})
        else:
            self._notify_status('download_error', {'model': model_name, 
                               'error': self.downloader.progress.error_message})
        return success
        
    def start_server(self, model_name: str = None, port: int = 8000,
                     gpu_memory_utilization: float = 0.9) -> bool:
        """启动本地推理服务"""
        try:
            model_name = model_name or self._config.get('last_model')
            if not model_name:
                error_msg = '未指定模型'
                self._notify_status('server_error', {'error': error_msg})
                print(f"❌ {error_msg}")
                return False
                
            model_path = str(self.downloader.get_model_path(model_name))
            if not self.downloader.is_model_downloaded(model_name):
                error_msg = f'模型未下载: {model_name}'
                self._notify_status('server_error', {'error': error_msg})
                print(f"❌ {error_msg}")
                return False
            
            print(f"📝 即将启动服务: 模型={model_name}, 端口={port}, 模型路径={model_path}")
            self._notify_status('server_starting', {'model': model_name, 'port': port})
            
            self.server = VLLMServerManager(model_path, port)
            
            if self.server.start(gpu_memory_utilization=gpu_memory_utilization):
                self._config['server_port'] = port
                self._config['last_model'] = model_name
                self._save_config()
                api_base = self.server.get_api_base()
                self._notify_status('server_started', {'model': model_name, 'port': port, 'api_base': api_base})
                print(f"✅ 服务已启动: {api_base}")
                return True
            else:
                error_msg = '服务启动失败'
                self._notify_status('server_error', {'error': error_msg})
                print(f"❌ {error_msg}")
                return False
                
        except Exception as e:
            error_msg = f'启动服务异常: {str(e)}'
            self._notify_status('server_error', {'error': error_msg})
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return False
        
    def stop_server(self):
        """停止推理服务"""
        try:
            if self.server:
                self.server.stop()
            self._notify_status('server_stopped')
        except Exception as e:
            print(f"⚠️  停止服务时出错: {e}")
            
    def is_server_running(self) -> bool:
        return self.server is not None and self.server.is_running()
        
    def get_api_base(self) -> Optional[str]:
        return self.server.get_api_base() if self.is_server_running() else None
        
    def get_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        if not self.environment.system_info:
            self.check_environment()
        return {
            'environment': self.environment.to_dict(),
            'models_downloaded': self.downloader.get_downloaded_models(),
            'server_running': self.is_server_running(),
            'api_base': self.get_api_base(),
            'config': self._config
        }
        
    def auto_setup(self, progress_callback: Optional[Callable[[str, float, str], None]] = None) -> bool:
        """自动设置：检测环境、安装依赖、下载模型、启动服务"""
        try:
            # 1. 检测环境
            if progress_callback:
                progress_callback('检测环境', 0.05, '正在检测系统配置...')
            self.check_environment()
            
            if not self.environment.system_info.can_run_local:
                if progress_callback:
                    progress_callback('检测完成', 1.0, self.environment.system_info.reason)
                return False
                
            # 2. 安装依赖
            if progress_callback:
                progress_callback('安装依赖', 0.1, '正在安装必要的依赖包...')
            if not self.install_dependencies(lambda m, p: progress_callback('安装依赖', 0.1 + p * 0.2, m) if progress_callback else None):
                return False
                
            # 3. 下载模型
            model_name = self.environment.system_info.recommended_model
            if not self.downloader.is_model_downloaded(model_name):
                if progress_callback:
                    progress_callback('下载模型', 0.3, f'正在下载 {model_name}...')
                if not self.download_model(model_name, 
                    lambda dp: progress_callback('下载模型', 0.3 + dp.total_percent / 100 * 0.5, 
                               f'{dp.current_file} ({dp.percent:.1f}%)') if progress_callback else None):
                    return False
            elif progress_callback:
                progress_callback('下载模型', 0.8, '模型已存在，跳过下载')
                
            # 4. 启动服务
            if progress_callback:
                progress_callback('启动服务', 0.85, '正在启动推理服务...')
            if not self.start_server(model_name):
                return False
                
            if progress_callback:
                progress_callback('完成', 1.0, f'本地服务已启动: {self.get_api_base()}')
            return True
            
        except Exception as e:
            if progress_callback:
                progress_callback('错误', 1.0, str(e))
            return False


def quick_setup() -> LocalModelManager:
    """快速设置本地模型"""
    manager = LocalModelManager()
    print("🔍 检测系统环境...")
    manager.check_environment()
    manager.environment.print_summary()
    
    if not manager.environment.system_info.can_run_local:
        print("❌ 当前环境不支持本地运行，请使用API模式")
        return manager
        
    print("\n📋 推荐设置步骤:")
    for step in manager.get_recommended_setup()['steps']:
        print(f"  {step['step']}. {step['description']}")
    return manager


if __name__ == '__main__':
    quick_setup()
