"""
本地模型管理模块
支持模型下载、环境检测和本地推理服务
"""

from phone_agent.local_model.environment import EnvironmentDetector, SystemInfo, GPUInfo
from phone_agent.local_model.downloader import ModelDownloader, DownloadProgress, VLLMServerManager, ModelInfo
from phone_agent.local_model.manager import LocalModelManager, LocalModelConfig, quick_setup

__all__ = [
    'LocalModelManager',
    'LocalModelConfig',
    'EnvironmentDetector',
    'SystemInfo',
    'GPUInfo',
    'ModelDownloader',
    'DownloadProgress',
    'VLLMServerManager',
    'ModelInfo',
    'quick_setup'
]
