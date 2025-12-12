#!/usr/bin/env python3
"""
Phone Agent 终端交互式启动脚本
简单输入自然语言任务即可运行
"""

import os
import sys

# 设置编码
os.environ['PYTHONIOENCODING'] = 'utf-8'

from phone_agent import PhoneAgent
from phone_agent.model import ModelConfig
from phone_agent.agent import AgentConfig


def print_banner():
    """打印启动横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║           🤖 Phone Agent - AI手机自动化助手 🤖                ║
║                                                              ║
║  使用自然语言控制你的手机，自动完成各种任务                  ║
║  输入 'quit' 或 'exit' 退出程序                              ║
║  输入 'help' 查看帮助                                        ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)


def print_help():
    """打印帮助信息"""
    help_text = """
📖 使用帮助:
─────────────────────────────────────────────────────────────
  • 直接输入任务描述即可执行，例如:
    > 打开微信发消息给文件传输助手
    > 打开bilibili搜索有趣的视频
    > 打开淘宝搜索无线耳机
    
  • 特殊命令:
    quit/exit  - 退出程序
    help       - 显示帮助
    config     - 显示当前配置
    apps       - 列出支持的应用
─────────────────────────────────────────────────────────────
"""
    print(help_text)


def list_apps():
    """列出支持的应用"""
    from phone_agent.config.apps import APP_PACKAGES
    print("\n📱 支持的应用列表:")
    print("─" * 50)
    for i, app in enumerate(sorted(APP_PACKAGES.keys()), 1):
        print(f"  {i:2d}. {app}")
    print("─" * 50)
    print()


def main():
    print_banner()
    
    # 配置API
    default_base_url = "https://open.bigmodel.cn/api/paas/v4"
    default_model = "autoglm-phone"
    
    # 从环境变量或用户输入获取API Key
    api_key = os.environ.get("PHONE_AGENT_API_KEY", "")
    
    if not api_key:
        print("🔑 请输入智谱 API Key (或按回车使用默认配置):")
        api_key = input("   API Key: ").strip()
        
    if not api_key:
        # 使用默认的API Key（如果有的话）
        api_key = "235b78f683fc4870b0983c8f17df5962.IpKHxmTIiIrqhk0k"
        print(f"   使用默认 API Key")
    
    # 创建模型配置
    model_config = ModelConfig(
        base_url=default_base_url,
        model_name=default_model,
        api_key=api_key,
    )
    
    # 创建Agent配置
    agent_config = AgentConfig(
        max_steps=100,
        lang="cn",
        verbose=True,
    )
    
    print(f"\n✅ 配置完成!")
    print(f"   模型: {default_model}")
    print(f"   API: {default_base_url}")
    print()
    
    # 创建Agent
    try:
        agent = PhoneAgent(model_config=model_config, agent_config=agent_config)
        print("✅ Agent 初始化成功!\n")
    except Exception as e:
        print(f"❌ Agent 初始化失败: {e}")
        return
    
    print_help()
    
    # 主循环
    while True:
        try:
            print("─" * 60)
            task = input("🎯 请输入任务 > ").strip()
            
            if not task:
                continue
                
            if task.lower() in ['quit', 'exit', 'q']:
                print("\n👋 再见!")
                break
                
            if task.lower() == 'help':
                print_help()
                continue
                
            if task.lower() == 'config':
                print(f"\n📋 当前配置:")
                print(f"   Base URL: {default_base_url}")
                print(f"   Model: {default_model}")
                print(f"   API Key: {api_key[:10]}...{api_key[-4:]}")
                print()
                continue
                
            if task.lower() == 'apps':
                list_apps()
                continue
            
            # 执行任务
            print(f"\n🚀 开始执行任务: {task}\n")
            try:
                result = agent.run(task)
                print(f"\n✅ 任务完成!")
                print(f"   结果: {result}")
            except Exception as e:
                print(f"\n❌ 任务执行失败: {e}")
            print()
            
        except KeyboardInterrupt:
            print("\n\n⚠️ 任务已中断")
            continue
        except EOFError:
            print("\n👋 再见!")
            break


if __name__ == "__main__":
    main()
