"""环境检测模块 - 检测系统CUDA、显存、Python版本等配置"""

import os
import sys
import platform
import subprocess
from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict, Any

# Windows下隐藏控制台窗口
_SUBPROCESS_FLAGS = {'creationflags': subprocess.CREATE_NO_WINDOW} if sys.platform == 'win32' else {}


@dataclass
class GPUInfo:
    """GPU信息"""
    name: str
    memory_total: int  # MB
    memory_free: int = 0
    compute_capability: str = ""
    driver_version: str = ""


@dataclass
class GitInfo:
    """Git环境信息"""
    git_available: bool
    git_version: Optional[str] = None
    lfs_available: bool = False
    lfs_version: Optional[str] = None


@dataclass
class SystemInfo:
    """系统环境信息"""
    os_name: str
    os_version: str
    python_version: str
    cpu_cores: int
    ram_total: int  # MB
    cuda_available: bool
    cuda_version: Optional[str]
    gpus: List[GPUInfo]
    recommended_model: str
    recommended_quantization: str
    can_run_local: bool
    reason: str
    cudnn_version: Optional[str] = None
    git_info: Optional[GitInfo] = None


class EnvironmentDetector:
    """环境检测器 - 简洁高效实现"""
    
    def __init__(self):
        self.system_info: Optional[SystemInfo] = None
        
    def detect(self) -> SystemInfo:
        """一次性检测所有系统环境信息"""
        os_name, os_version = platform.system(), platform.version()
        python_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        
        cuda_available, cuda_version, gpus = self._detect_gpu_environment()
        ram_total = self._get_ram_total()
        git_info = self._detect_git_environment()
        
        model, quant, can_run, reason = self._get_recommendation(cuda_available, gpus, ram_total)
        
        self.system_info = SystemInfo(
            os_name=os_name, os_version=os_version, python_version=python_ver,
            cpu_cores=os.cpu_count() or 1, ram_total=ram_total,
            cuda_available=cuda_available, cuda_version=cuda_version, gpus=gpus,
            recommended_model=model, recommended_quantization=quant,
            can_run_local=can_run, reason=reason,
            git_info=git_info
        )
        return self.system_info
    
    def _detect_git_environment(self) -> GitInfo:
        """检测Git和Git LFS环境"""
        git_available = False
        git_version = None
        lfs_available = False
        lfs_version = None
        
        try:
            # 检测 git
            result = subprocess.run(
                ['git', '--version'],
                capture_output=True, text=True, timeout=5, **_SUBPROCESS_FLAGS
            )
            if result.returncode == 0:
                git_available = True
                # 解析版本号，例如 "git version 2.42.0.windows.1"
                version_text = result.stdout.strip()
                if 'version' in version_text:
                    git_version = version_text.split('version')[1].strip().split()[0]
                print(f"✅ Git: {git_version}")
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            print("⚠️  Git 未安装")
        except Exception as e:
            print(f"⚠️  Git 检测异常: {e}")
        
        if git_available:
            try:
                # 检测 git-lfs
                result = subprocess.run(
                    ['git', 'lfs', 'version'],
                    capture_output=True, text=True, timeout=5, **_SUBPROCESS_FLAGS
                )
                if result.returncode == 0:
                    lfs_available = True
                    # 解析版本号，例如 "git-lfs/3.4.0 (GitHub; windows amd64; go 1.21.1)"
                    version_text = result.stdout.strip()
                    if '/' in version_text:
                        lfs_version = version_text.split('/')[1].split()[0]
                    print(f"✅ Git LFS: {lfs_version}")
            except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
                print("⚠️  Git LFS 未安装")
            except Exception as e:
                print(f"⚠️  Git LFS 检测异常: {e}")
        
        return GitInfo(
            git_available=git_available,
            git_version=git_version,
            lfs_available=lfs_available,
            lfs_version=lfs_version
        )
        
    def _get_ram_total(self) -> int:
        """获取系统总内存(MB)"""
        if platform.system() == 'Windows':
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                class MEMSTAT(ctypes.Structure):
                    _fields_ = [('dwLength', ctypes.c_ulong), ('dwMemoryLoad', ctypes.c_ulong),
                               ('ullTotalPhys', ctypes.c_ulonglong), ('ullAvailPhys', ctypes.c_ulonglong),
                               ('ullTotalPageFile', ctypes.c_ulonglong), ('ullAvailPageFile', ctypes.c_ulonglong),
                               ('ullTotalVirtual', ctypes.c_ulonglong), ('ullAvailVirtual', ctypes.c_ulonglong),
                               ('ullAvailExtendedVirtual', ctypes.c_ulonglong)]
                stat = MEMSTAT()
                stat.dwLength = ctypes.sizeof(stat)
                kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
                return int(stat.ullTotalPhys / 1024 / 1024)
            except Exception:
                pass
        else:
            try:
                with open('/proc/meminfo') as f:
                    for line in f:
                        if 'MemTotal' in line:
                            return int(line.split()[1]) // 1024
            except Exception:
                pass
        return 8000
        
    def _detect_gpu_environment(self) -> Tuple[bool, Optional[str], List[GPUInfo]]:
        """统一检测GPU环境"""
        cuda_version = None
        gpus = []
        
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name,memory.total,memory.free,driver_version', 
                 '--format=csv,noheader,nounits'],
                capture_output=True, text=True, timeout=10, **_SUBPROCESS_FLAGS
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        parts = [p.strip() for p in line.split(',')]
                        if len(parts) >= 4:
                            try:
                                gpus.append(GPUInfo(
                                    name=parts[0], memory_total=int(float(parts[1])),
                                    memory_free=int(float(parts[2])), driver_version=parts[3]
                                ))
                            except (ValueError, IndexError):
                                pass
                
                result2 = subprocess.run(['nvidia-smi'], capture_output=True, text=True, 
                                        timeout=10, **_SUBPROCESS_FLAGS)
                if result2.returncode == 0:
                    for line in result2.stdout.split('\n'):
                        if 'CUDA Version' in line:
                            try:
                                cuda_version = line.split('CUDA Version:')[1].split()[0].strip()
                            except (IndexError, ValueError):
                                pass
                            break
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
            print(f"⚠️  nvidia-smi 检测失败: {e}")
            pass
        except Exception as e:
            print(f"⚠️  GPU 检测异常: {e}")
            pass
            
        if not gpus:
            try:
                import torch
                if torch.cuda.is_available():
                    cuda_version = cuda_version or torch.version.cuda
                    for i in range(torch.cuda.device_count()):
                        props = torch.cuda.get_device_properties(i)
                        gpus.append(GPUInfo(
                            name=props.name, 
                            memory_total=props.total_memory // (1024 * 1024),
                            compute_capability=f"{props.major}.{props.minor}"
                        ))
            except ImportError:
                print("⚠️  PyTorch 未安装，无法检测CUDA")
                pass
            except Exception as e:
                print(f"⚠️  PyTorch GPU 检测异常: {e}")
                pass
                
        return bool(gpus), cuda_version, gpus
        
    def _get_recommendation(self, cuda_available: bool, gpus: List[GPUInfo], 
                            ram_total: int) -> Tuple[str, str, bool, str]:
        """根据硬件推荐模型配置"""
        if not cuda_available or not gpus:
            return 'API_MODE', 'none', False, '未检测到NVIDIA GPU，建议使用API模式'
            
        max_vram = max(gpu.memory_total for gpu in gpus)
        
        if max_vram >= 16000:
            return 'AutoGLM-Phone-9B', 'fp16', True, f'{max_vram}MB显存，可运行FP16模型'
        elif max_vram >= 10000:
            return 'AutoGLM-Phone-9B', 'int8', True, f'{max_vram}MB显存，推荐INT8量化'
        elif max_vram >= 6000:
            return 'AutoGLM-Phone-9B-GGUF-Q4', 'q4_k_m', True, f'{max_vram}MB显存，推荐Q4量化'
        else:
            return 'API_MODE', 'none', False, f'显存不足({max_vram}MB)，建议使用API模式'
            
    def get_torch_install_command(self) -> str:
        """获取PyTorch安装命令"""
        if not self.system_info:
            self.detect()
        cuda_ver = self.system_info.cuda_version or ''
        
        if not self.system_info.cuda_available:
            return 'pip install torch torchvision torchaudio'
        if cuda_ver.startswith('12'):
            return 'pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121'
        elif cuda_ver.startswith('11'):
            return 'pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118'
        return 'pip install torch torchvision torchaudio'
            
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        if not self.system_info:
            self.detect()
        info = self.system_info
        return {
            'os': f"{info.os_name} {info.os_version}", 'python': info.python_version,
            'cpu_cores': info.cpu_cores, 'ram_gb': round(info.ram_total / 1024, 1),
            'cuda_available': info.cuda_available, 'cuda_version': info.cuda_version,
            'gpus': [{'name': g.name, 'vram_mb': g.memory_total} for g in info.gpus],
            'recommended': info.recommended_model, 'can_run_local': info.can_run_local,
            'reason': info.reason
        }
        
    def print_summary(self):
        """打印环境摘要"""
        if not self.system_info:
            self.detect()
        info = self.system_info
        
        print("\n" + "=" * 50)
        print("📊 系统环境检测")
        print("=" * 50)
        print(f"🖥️  系统: {info.os_name} | Python: {info.python_version}")
        print(f"💾 内存: {info.ram_total / 1024:.1f} GB | CPU: {info.cpu_cores}核")
        print(f"🎮 CUDA: {'✅ ' + (info.cuda_version or '可用') if info.cuda_available else '❌ 不可用'}")
        
        for gpu in info.gpus:
            print(f"🖼️  {gpu.name} ({gpu.memory_total / 1024:.1f}GB)")
            
        print(f"\n💡 推荐: {info.recommended_model} ({info.recommended_quantization})")
        print(f"   {'✅' if info.can_run_local else '❌'} {info.reason}")
        print("=" * 50 + "\n")


if __name__ == '__main__':
    detector = EnvironmentDetector()
    detector.detect()
    detector.print_summary()
