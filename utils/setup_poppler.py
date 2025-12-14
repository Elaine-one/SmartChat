"""
Poppler设置工具 - 用于Windows系统

此脚本自动下载和设置用于pdf2image的poppler工具。
"""

import os
import sys
import urllib.request
import zipfile
import shutil
import tempfile
import streamlit as st

def download_poppler_for_windows():
    """
    下载并安装poppler工具
    """
    if not sys.platform.startswith('win'):
        print("此脚本仅适用于Windows系统")
        return False
    
    # 创建./tools目录
    tools_dir = os.path.join(os.getcwd(), "tools")
    if not os.path.exists(tools_dir):
        os.makedirs(tools_dir)
    
    poppler_dir = os.path.join(tools_dir, "poppler")
    
    # 检查是否已安装
    if os.path.exists(os.path.join(poppler_dir, "bin", "pdftoppm.exe")):
        print("Poppler已安装")
        return True
    
    # 下载poppler
    poppler_url = "https://github.com/oschwartz10612/poppler-windows/releases/download/v23.11.0-0/Release-23.11.0-0.zip"
    print(f"正在下载Poppler (可能需要几分钟)...")
    
    try:
        # 创建临时文件
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        temp_file.close()
        
        # 下载文件
        urllib.request.urlretrieve(poppler_url, temp_file.name)
        
        # 解压文件
        print("正在解压Poppler...")
        with zipfile.ZipFile(temp_file.name, 'r') as zip_ref:
            zip_ref.extractall(tools_dir)
        
        # 将解压后的文件夹重命名为poppler
        extracted_dir = os.path.join(tools_dir, "Release-23.11.0-0")
        if os.path.exists(extracted_dir):
            # 如果poppler目录已存在，先删除
            if os.path.exists(poppler_dir):
                shutil.rmtree(poppler_dir)
            # 重命名目录
            os.rename(extracted_dir, poppler_dir)
        
        # 清理临时文件
        os.unlink(temp_file.name)
        
        print(f"Poppler安装成功: {poppler_dir}")
        return True
        
    except Exception as e:
        print(f"安装Poppler时出错: {str(e)}")
        return False

def setup_poppler_streamlit():
    """Streamlit UI版本的Poppler安装"""
    if not sys.platform.startswith('win'):
        st.error("此功能仅适用于Windows系统")
        return False
    
    with st.spinner("正在检查Poppler安装..."):
        # 创建./tools目录
        tools_dir = os.path.join(os.getcwd(), "tools")
        if not os.path.exists(tools_dir):
            os.makedirs(tools_dir)
        
        poppler_dir = os.path.join(tools_dir, "poppler")
        
        # 检查是否已安装
        if os.path.exists(os.path.join(poppler_dir, "bin", "pdftoppm.exe")):
            st.success("Poppler已安装")
            return True
    
    # 提示用户安装
    st.warning("处理PDF文件需要安装Poppler工具")
    
    if st.button("安装Poppler"):
        try:
            with st.spinner("正在下载Poppler (约20MB，可能需要几分钟)..."):
                # 下载poppler
                poppler_url = "https://github.com/oschwartz10612/poppler-windows/releases/download/v23.11.0-0/Release-23.11.0-0.zip"
                
                # 创建临时文件
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
                temp_file.close()
                
                # 下载文件
                urllib.request.urlretrieve(poppler_url, temp_file.name)
            
            with st.spinner("正在解压Poppler..."):
                # 解压文件
                with zipfile.ZipFile(temp_file.name, 'r') as zip_ref:
                    zip_ref.extractall(tools_dir)
                
                # 将解压后的文件夹重命名为poppler
                extracted_dir = os.path.join(tools_dir, "Release-23.11.0-0")
                if os.path.exists(extracted_dir):
                    # 如果poppler目录已存在，先删除
                    if os.path.exists(poppler_dir):
                        shutil.rmtree(poppler_dir)
                    # 重命名目录
                    os.rename(extracted_dir, poppler_dir)
                
                # 清理临时文件
                os.unlink(temp_file.name)
            
            st.success(f"Poppler安装成功！重启应用后即可使用PDF处理功能。")
            return True
            
        except Exception as e:
            st.error(f"安装Poppler时出错: {str(e)}")
            return False
    
    return False

if __name__ == "__main__":
    # 如果直接运行此脚本，则下载并安装poppler
    download_poppler_for_windows() 