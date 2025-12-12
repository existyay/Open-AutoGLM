# Phone Agent - AI 手机自动化助手

<div align="center">
<img src="resources/logo.svg" width="20%"/>
<h3>使用自然语言控制手机，AI自动完成各种任务</h3>

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20|%20macOS%20|%20Linux-lightgrey.svg)]()
</div>

<p align="center">
    👋 加入我们的 <a href="resources/WECHAT.md" target="_blank">微信</a> 社区
</p>

---

## ✨ 功能特点

- 🗣️ **自然语言控制** - 用自然语言描述任务，AI自动完成
- 📱 **多模态理解** - 视觉语言模型理解屏幕内容
- 🤖 **智能规划** - 自动规划操作流程，无需人工干预
- ☁️ **云端/本地双模式** - 支持API调用和本地模型部署
- 🎨 **现代化GUI** - 美观的图形界面，详细的执行日志
- 📦 **一键打包** - 支持打包为独立EXE，无需安装Python

## 🚀 快速开始

### 方式一：下载预编译版本（推荐）

1. 从 [Releases](https://github.com/zai-org/Open-AutoGLM/releases) 下载 `PhoneAgent.exe`
2. 双击运行
3. 连接手机，输入API Key，开始使用

### 方式二：源码运行

```bash
# 1. 克隆项目
git clone https://github.com/zai-org/Open-AutoGLM.git
cd Open-AutoGLM

# 2. 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# 3. 安装依赖
pip install -r requirements.txt
pip install -e .

# 4. 运行GUI
python run_agent_gui.py
```

## 📋 环境准备

### 1. ADB 工具

下载 [Android Platform Tools](https://developer.android.com/tools/releases/platform-tools) 并配置环境变量：

**Windows:**
- 解压到 `C:\platform-tools`
- 添加到系统PATH环境变量

**macOS/Linux:**
```bash
export PATH=$PATH:~/Downloads/platform-tools
```

### 2. Android 设备设置

1. **启用开发者模式**: 设置 → 关于手机 → 连续点击"版本号"7次
2. **启用USB调试**: 设置 → 开发者选项 → USB调试 ✓
3. **安装ADB Keyboard**: 下载 [ADBKeyboard.apk](https://github.com/senzhk/ADBKeyBoard/blob/master/ADBKeyboard.apk) 并在设置中启用

### 3. 连接测试

```bash
adb devices
# 应显示: List of devices attached
#         XXXXXX    device
```

## 🔑 API 配置

### 使用智谱AI API（推荐）

1. 访问 [智谱AI开放平台](https://open.bigmodel.cn/)
2. 注册并创建 API Key
3. 在程序中填入:
   - **Base URL**: `https://open.bigmodel.cn/api/paas/v4`
   - **模型**: `autoglm-phone`

## 💻 本地模型部署

如果你有 NVIDIA GPU（6GB+ 显存），可以部署本地模型：

### 系统要求

| 配置 | 最低要求 | 推荐配置 |
|------|---------|---------|
| GPU显存 | 6GB (INT4量化) | 16GB+ (FP16) |
| 系统内存 | 16GB | 32GB+ |
| CUDA | 11.8+ | 12.0+ |

### 部署步骤

1. 在GUI中选择"💻 本地模式"
2. 点击"🔍 检测环境"确认硬件配置
3. 选择模型源（国内推荐ModelScope）
4. 点击"⬇️ 下载模型"
5. 下载完成后点击"🚀 启动服务"

### 可用模型

| 模型 | 下载地址 |
|-----|---------|
| AutoGLM-Phone-9B | [HuggingFace](https://huggingface.co/zai-org/AutoGLM-Phone-9B) \| [ModelScope](https://modelscope.cn/models/ZhipuAI/AutoGLM-Phone-9B) |
| AutoGLM-Phone-9B-Multilingual | [HuggingFace](https://huggingface.co/zai-org/AutoGLM-Phone-9B-Multilingual) \| [ModelScope](https://modelscope.cn/models/ZhipuAI/AutoGLM-Phone-9B-Multilingual) |

## 📦 打包为EXE

```bash
python build_exe.py
# 选择 1. 完全独立版 - 单个EXE内置ADB
```

输出文件: `dist/PhoneAgent.exe`

## 📁 项目结构

```
Open-AutoGLM/
├── phone_agent/           # 核心代理模块
│   ├── agent.py          # 主Agent类
│   ├── model/            # 模型客户端
│   ├── adb/              # ADB控制模块
│   ├── actions/          # 动作处理器
│   ├── config/           # 配置和提示词
│   └── local_model/      # 本地模型管理
├── run_agent_gui.py      # GUI界面入口
├── run_agent.py          # 命令行入口
├── build_exe.py          # EXE打包脚本
└── requirements.txt      # 依赖列表
```

## 📖 使用示例

```python
from phone_agent import PhoneAgent
from phone_agent.model import ModelConfig
from phone_agent.agent import AgentConfig

# 配置模型
model_config = ModelConfig(
    api_key="your-api-key",
    base_url="https://open.bigmodel.cn/api/paas/v4",
    model_name="autoglm-phone"
)

# 配置Agent
agent_config = AgentConfig(lang="cn", max_steps=100)

# 创建并运行
agent = PhoneAgent(model_config=model_config, agent_config=agent_config)
result = agent.run("打开微信发消息给张三")
print(result)
```

## 🎯 任务示例

- 打开微信发送消息给张三
- 打开抖音刷5个视频
- 打开淘宝搜索手机壳
- 打开地图导航到最近的星巴克
- 打开设置查看电池状态

## ❓ 常见问题

### Q: 找不到设备？
A: 检查USB连接，确保开启USB调试，运行 `adb devices` 测试

### Q: 文字输入失败？
A: 确保已安装并启用 ADB Keyboard

### Q: API调用失败？
A: 检查API Key是否正确，网络是否正常

### Q: 本地模型显存不足？
A: 使用量化版本或降低 `--gpu-memory-utilization` 参数

## 📄 许可证

本项目采用 [Apache License 2.0](LICENSE) 许可证。

## ⚠️ 免责声明

本项目仅供研究和学习使用。严禁用于非法获取信息、干扰系统或任何违法活动。使用本软件即表示您同意 [使用条款](resources/privacy_policy.txt)。

---

<div align="center">
<b>Powered by AutoGLM & 智谱AI</b>
</div>
