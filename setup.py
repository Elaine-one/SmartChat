"""
智能聊天助手一键安装脚本

此脚本用于安装项目所需的所有依赖和工具。
"""

import os
import sys
import subprocess
import platform

def run_command(command):
    """运行命令并打印输出"""
    print(f"执行: {command}")
    process = subprocess.Popen(
        command, 
        shell=True, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )
    
    for line in process.stdout:
        print(line.strip())
    
    process.wait()
    return process.returncode == 0

def install_requirements():
    """安装python依赖"""
    print("\n=== 安装Python依赖 ===")
    success = run_command(f"{sys.executable} -m pip install -r requirements.txt")
    if success:
        print("✓ 依赖安装成功")
    else:
        print("✗ 依赖安装失败")
    return success

def install_poppler_windows():
    """在Windows上安装Poppler"""
    if not platform.system() == "Windows":
        return True
    
    print("\n=== 安装Poppler工具 (用于PDF处理) ===")
    
    # 尝试从已存在的脚本安装
    setup_poppler_path = os.path.join("utils", "setup_poppler.py")
    if os.path.exists(setup_poppler_path):
        success = run_command(f"{sys.executable} {setup_poppler_path}")
        if success:
            print("✓ Poppler安装成功")
        else:
            print("✗ Poppler安装失败")
        return success
    else:
        print("未找到setup_poppler.py，跳过安装")
        return False

def create_dirs():
    """创建必要的目录"""
    print("\n=== 创建必要目录 ===")
    dirs = ["temp", "tools"]
    for d in dirs:
        if not os.path.exists(d):
            os.makedirs(d)
            print(f"创建目录: {d}")
        else:
            print(f"目录已存在: {d}")
    return True

def check_ollama():
    """检查Ollama是否安装和运行"""
    print("\n=== 检查Ollama ===")
    
    # 检查Ollama服务是否运行
    try:
        import requests
        response = requests.get("http://localhost:1314/api/tags")
        if response.status_code == 200:
            print("✓ Ollama服务正在运行")
            
            # 检查模型是否已安装
            models = response.json().get("models", [])
            model_names = [model.get("name", "") for model in models]
            
            required_models = ["qwen2.5:3b", "deepseek-r1:8b", "llama3.1:latest", "granite3.2-vision:latest"]
            missing_models = [model for model in required_models if not any(model in m for m in model_names)]
            
            if missing_models:
                print(f"⚠ 缺少以下模型: {', '.join(missing_models)}")
                print("请使用以下命令拉取模型:")
                for model in missing_models:
                    print(f"ollama pull {model}")
            else:
                print("✓ 所有必要的模型已安装")
            
            return True
        else:
            print("✗ Ollama服务未响应")
            return False
    except Exception as e:
        print(f"✗ Ollama检查失败: {str(e)}")
        print("请确保Ollama已安装并启动:")
        print("- Windows: https://ollama.com/download/windows")
        print("- Linux: curl -fsSL https://ollama.com/install.sh | sh")
        return False

def main():
    """主函数"""
    print("===============================")
    print("  智能聊天助手 - 一键安装脚本")
    print("===============================")
    
    success = True
    
    # 创建必要的目录
    if not create_dirs():
        success = False
    
    # 安装依赖
    if not install_requirements():
        success = False
    
    # 在Windows上安装Poppler
    if platform.system() == "Windows":
        if not install_poppler_windows():
            print("⚠ Poppler安装跳过或失败，可能会影响PDF处理功能")
    
    # 检查Ollama
    if not check_ollama():
        print("⚠ Ollama检查失败，请确保Ollama已安装并正确配置")
    
    # 安装结果
    if success:
        print("\n✓ 安装完成！")
        print("\n运行应用: streamlit run chatbot.py")
    else:
        print("\n⚠ 安装过程中遇到一些问题，请查看上面的错误消息。")
    
    return success

if __name__ == "__main__":
    main() 