#!/usr/bin/env python3
import os
import sys
import subprocess
import requests
import json

# ====== 配置区（请务必修改为你自己的信息）======
GITHUB_USERNAME = "ljqalex"
GITHUB_TOKEN = "123"  # ←←← 替换为你的有效 GitHub Token
# ===============================================

def run_cmd(cmd, cwd=None):
    result = subprocess.run(cmd, shell=True, cwd=cwd, 
                          capture_output=True, 
                          text=False)
    
    try:
        stdout = result.stdout.decode('utf-8', errors='replace') if result.stdout else ''
    except:
        stdout = str(result.stdout) # 极端情况转字符串
    
    try:
        stderr = result.stderr.decode('utf-8', errors='replace') if result.stderr else ''
    except:
        stderr = str(result.stderr)
        
    return result.returncode, stdout.strip() if stdout else '', stderr.strip() if stderr else ''

def is_git_repo(path):
    code, _, _ = run_cmd("git rev-parse --is-inside-work-tree", cwd=path)
    return code == 0

def create_github_repo(repo_name, private=True):
    """使用 GitHub API 创建私有仓库"""
    url = "https://api.github.com/user/repos"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "name": repo_name,
        "private": private,
        "auto_init": False,
        "description": f"Auto-created by script for {repo_name}"
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    
    if response.status_code == 201:
        print(f"[+] GitHub 私有仓库创建成功: https://github.com/{GITHUB_USERNAME}/{repo_name}")
        return True
    elif response.status_code == 422:
        print(f"[ℹ] GitHub 仓库已存在: {repo_name}")
        return True
    else:
        error_msg = response.json().get('message', 'Unknown error')
        print(f"[❌] 创建仓库失败 ({response.status_code}): {error_msg}")
        return False

def delete_github_repo(repo_name):
    """使用 GitHub API 删除指定仓库"""
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.delete(url, headers=headers)
    
    if response.status_code == 204:
        print(f"[🗑️] 仓库已成功删除: {GITHUB_USERNAME}/{repo_name}")
        return True
    elif response.status_code == 404:
        print(f"[⚠️] 仓库不存在或你没有权限访问: {GITHUB_USERNAME}/{repo_name}")
        return False
    else:
        error_msg = response.json().get('message', 'Unknown error')
        print(f"[❌] 删除失败 ({response.status_code}): {error_msg}")
        return False

def push_code(local_dir, repo_name):
    """推送整个目录内容到 GitHub（包括所有子目录和文件）"""
    remote_url_https = f"https://{GITHUB_USERNAME}:{GITHUB_TOKEN}@github.com/{GITHUB_USERNAME}/{repo_name}.git"
    remote_url_public = f"https://github.com/{GITHUB_USERNAME}/{repo_name}.git"

    print(f"📁 本地目录: {local_dir}")
    print(f"📦 目标仓库: {remote_url_public} (私有)")

    # 自动创建仓库（私有）
    if not create_github_repo(repo_name, private=True):
        print("无法创建或访问 GitHub 仓库，请检查 Token 和用户名。")
        sys.exit(1)

    # 初始化 Git（如果尚未初始化）
    if not is_git_repo(local_dir):
        print("[+] 初始化本地 Git 仓库...")
        run_cmd("git init", cwd=local_dir)

    # 设置远程仓库地址
    code, _, _ = run_cmd("git remote get-url origin", cwd=local_dir)
    if code != 0:
        run_cmd(f"git remote add origin {remote_url_https}", cwd=local_dir)
    else:
        run_cmd(f"git remote set-url origin {remote_url_https}", cwd=local_dir)

    # 添加所有文件（尊重 .gitignore）
    print("📤 正在添加所有文件和子目录（包括隐藏文件）...")
    code, out, err = run_cmd("git add .", cwd=local_dir)
    if code != 0:
        print(f"❌ git add 失败: {err}")
        sys.exit(1)

    # 检查是否有变更
    code, _, _ = run_cmd("git diff --cached --quiet", cwd=local_dir)
    if code == 0:
        print("ℹ️ 没有新变更，无需提交。")
        sys.exit(0)

    # 配置提交用户信息
    run_cmd('git config user.name "AutoPushBot"', cwd=local_dir)
    run_cmd('git config user.email "bot@example.com"', cwd=local_dir)

    # 提交
    print("📝 正在提交所有文件...")
    run_cmd('git commit -m "Auto push by script"', cwd=local_dir)

    # 推送
    print("[🚀] 正在推送到 GitHub...")
    run_cmd("git branch -M main", cwd=local_dir)
    code, out, err = run_cmd("git push -u origin main", cwd=local_dir)

    if code == 0:
        print("✅ 推送成功！")
        print(f"🌐 仓库地址: {remote_url_public}")
    else:
        print("❌ 推送失败:")
        print(err)
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        # 默认行为：推送当前目录到 ms
        local_dir = os.getcwd()
        repo_name = "ms"
        push_code(local_dir, repo_name)
        return

    # 删除模式
    if sys.argv[1] == "delete" and len(sys.argv) == 3:
        repo_name = sys.argv[2]
        print(f"[❓] 确认要删除 GitHub 仓库 '{GITHUB_USERNAME}/{repo_name}' 吗？此操作不可逆！")
        confirm = input("输入 'yes' 确认删除: ").strip().lower()
        if confirm == "yes":
            delete_github_repo(repo_name)
        else:
            print("取消删除。")
        return

    # 推送模式
    if len(sys.argv) == 2:
        local_dir = os.path.abspath(sys.argv[1])
        repo_name = "ms"
    elif len(sys.argv) == 3:
        local_dir = os.path.abspath(sys.argv[1])
        repo_name = sys.argv[2]
    else:
        print("用法:")
        print("  推送: python git.py [本地目录] [仓库名]")
        print("  删除: python git.py delete <仓库名>")
        sys.exit(1)

    if not os.path.exists(local_dir):
        print(f"错误: 目录不存在 -> {local_dir}")
        sys.exit(1)

    push_code(local_dir, repo_name)

if __name__ == "__main__":
    main()
