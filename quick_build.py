#!/usr/bin/env python3
"""
Jenkins快速构建触发工具
支持命令行参数快速触发构建
增强版：详细日志输出 + 构建监控 + 通知

【教学】模块职责：
- 触发 Jenkins 构建
- 调用监控模块等待构建完成
- 发送通知

用法: python quick_build.py <job_name> <branch> [--no-wait]
"""

import sys
import requests
from requests.auth import HTTPBasicAuth
import configparser
import os
import json
from datetime import datetime

# 【教学】导入我们自己的监控模块
from jenkins_monitor import JenkinsBuildMonitor


class JenkinsQuickBuild:
    """Jenkins快速构建器（带监控和通知功能）"""

    def __init__(self, config_file='jenkins_config.ini'):
        self.config = configparser.ConfigParser()
        self.config_file = config_file

        # 读取配置文件
        if os.path.exists(config_file):
            self.config.read(config_file)
        else:
            print(f"❌ 配置文件 {config_file} 不存在")
            print("请先运行 trigger_jenkins_build.py 进行配置")
            sys.exit(1)

        # 初始化会话
        self.base_url = self.config.get('jenkins', 'url')
        self.username = self.config.get('jenkins', 'user')
        self.api_token = self.config.get('jenkins', 'token')

        # 【教学】读取邮件配置（可选）
        self.email_config = None
        if self.config.has_section('email'):
            self.email_config = {
                'smtp_server': self.config.get('email', 'smtp_server'),
                'smtp_port': self.config.getint('email', 'smtp_port'),
                'sender': self.config.get('email', 'sender'),
                'password': self.config.get('email', 'password'),
                'receiver': self.config.get('email', 'receiver')
            }

        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(self.username, self.api_token)
        self.session.headers.update({'Content-Type': 'application/json'})
    
    def _print_separator(self, char="-", length=70):
        print(char * length)
    
    def trigger_build(self, job_name, branch="main", wait_for_completion=True):
        """
        【教学】快速触发构建

        参数：
            job_name: 任务名称
            branch: 分支名称
            wait_for_completion: 是否等待构建完成（默认 True）

        返回：
            bool: 构建是否成功
        """
        # 打印详细日志
        print("\n" + "=" * 70)
        print("🚀 Jenkins 快速构建日志")
        print("=" * 70)
        print(f"⏰ 触发时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        print(f"\n📝 构建信息:")
        self._print_separator()
        print(f"   🌐 Jenkins服务器: {self.base_url}")
        print(f"   👤 用户: {self.username}")
        print(f"   🔑 API Token: {'*' * len(self.api_token)}")
        print(f"   📋 任务名称: {job_name}")
        print(f"   🌿 分支: {branch}")

        # 构建URL和参数
        url = f"{self.base_url}/job/{job_name}/buildWithParameters"
        params = {'tag': branch, 'branch':branch}

        self._print_separator()
        print(f"\n📡 请求详情:")
        print(f"   方法: POST")
        print(f"   URL: {url}")
        print(f"   参数: {json.dumps(params, ensure_ascii=False)}")

        self._print_separator()
        print("\n🔄 正在发送构建请求...\n")

        try:
            response = self.session.post(url, params=params, timeout=60)

            self._print_separator()
            print(f"\n📥 响应详情:")
            print(f"   状态码: {response.status_code}")
            print(f"   状态文本: {response.reason}")

            self._print_separator()

            if response.status_code in [200, 201]:
                print("\n✅ 构建任务已成功触发!")

                # 获取队列信息
                queue_location = response.headers.get('Location', '')
                if queue_location:
                    print(f"\n📍 队列位置: {queue_location}")

                print(f"\n💡 访问地址:")
                print(f"   {self.base_url}/job/{job_name}")

                # 【教学】如果需要等待构建完成，调用监控模块
                if wait_for_completion and queue_location:
                    print("\n" + "=" * 70)
                    print("🔍 开始监控构建...")
                    print("=" * 70)

                    # 创建监控器
                    monitor = JenkinsBuildMonitor(
                        self.base_url,
                        self.username,
                        self.api_token,
                        self.email_config
                    )

                    # 监控构建
                    success = monitor.monitor_build(job_name, queue_location)
                    return success
                else:
                    print("\n" + "=" * 70)
                    return True

            else:
                print(f"\n❌ 构建触发失败! HTTP {response.status_code}")
                print(f"\n📄 响应内容: {response.text[:500]}")
                print(f"\n🔍 建议:")
                print(f"   1. 检查任务名称 '{job_name}' 是否正确")
                print(f"   2. 检查分支 '{branch}' 是否存在")
                print(f"   3. 确认API Token是否有效")
                print("\n" + "=" * 70)
                return False

        except requests.exceptions.Timeout:
            print(f"\n❌ 请求超时 (60秒)")
            print(f"   检查 {self.base_url} 是否可访问")
            print("\n" + "=" * 70)
            return False
        except requests.exceptions.ConnectionError as e:
            print(f"\n❌ 连接失败: {e}")
            print(f"   检查Jenkins URL: {self.base_url}")
            print("\n" + "=" * 70)
            return False
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            print("\n" + "=" * 70)
            return False


def create_config_template():
    """
    【教学】创建配置文件模板

    配置文件说明：
    1. [jenkins] 部分：Jenkins 服务器配置（必需）
    2. [email] 部分：邮件通知配置（可选）

    邮件配置说明：
    - smtp_server: SMTP 服务器地址
    - smtp_port: SMTP 端口（通常 465 或 587）
    - sender: 发件人邮箱
    - password: 邮箱授权码（不是登录密码！）
    - receiver: 收件人邮箱

    常见邮箱 SMTP 配置：
    - QQ邮箱: smtp.qq.com:465
    - 163邮箱: smtp.163.com:465
    - Gmail: smtp.gmail.com:587
    """
    config_content = """[jenkins]
# Jenkins 服务器配置
url = http://your-jenkins-server:port
user = your-username
token = your-api-token

[email]
# 邮件通知配置（可选，如不需要可删除此部分）
# 注意：password 是邮箱授权码，不是登录密码！
# QQ邮箱授权码获取：邮箱设置 -> 账户 -> POP3/IMAP/SMTP -> 生成授权码
smtp_server = smtp.qq.com
smtp_port = 465
sender = your-email@qq.com
password = your-email-auth-code
receiver = receiver@example.com
"""

    with open('jenkins_config.ini', 'w') as f:
        f.write(config_content)

    print("✅ 配置文件模板已创建: jenkins_config.ini")
    print("\n📝 配置步骤:")
    print("=" * 60)
    print("1. 编辑 jenkins_config.ini，填入你的 Jenkins 信息")
    print("2. （可选）配置邮件通知：")
    print("   - QQ邮箱：设置 -> 账户 -> 生成授权码")
    print("   - 163邮箱：设置 -> POP3/SMTP -> 开启并获取授权码")
    print("3. 如不需要邮件通知，删除 [email] 部分即可")
    print("=" * 60)


def main():
    """
    【教学】主函数

    命令行参数：
    - python quick_build.py <任务名> [分支名] [--no-wait]
    - --no-wait: 不等待构建完成，触发后立即返回
    """
    if len(sys.argv) < 2:
        print("Jenkins快速构建触发工具 (增强版 - 带监控)")
        print("=" * 60)
        print("用法:")
        print("  创建配置: python quick_build.py --config")
        print("  快速构建: python quick_build.py <任务名> [分支名] [--no-wait]")
        print("=" * 60)

        if os.path.exists('jenkins_config.ini'):
            print("\n💡 使用示例:")
            print("  python quick_build.py chatgpt-api-service")
            print("  python quick_build.py chatgpt-api-service dev")
            print("  python quick_build.py chatgpt-api-service main --no-wait")
        else:
            print("\n💡 请先运行: python quick_build.py --config")

        sys.exit(0)

    # 创建配置文件
    if sys.argv[1] == '--config':
        create_config_template()
        sys.exit(0)

    # 解析参数
    job_name = sys.argv[1]
    branch = "main"
    wait_for_completion = True

    # 检查可选参数
    for arg in sys.argv[2:]:
        if arg == '--no-wait':
            wait_for_completion = False
        else:
            branch = arg

    # 快速触发构建
    builder = JenkinsQuickBuild()
    success = builder.trigger_build(job_name, branch, wait_for_completion)

    # 【教学】根据构建结果设置退出码
    # 0: 成功，1: 失败
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
