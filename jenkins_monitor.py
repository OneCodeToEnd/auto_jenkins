#!/usr/bin/env python3
"""
Jenkins 构建监控和通知模块

【教学】模块职责：
1. 监控构建状态（轮询 Jenkins API）
2. 发送通知（桌面通知、邮件通知）

【教学】为什么要独立模块？
- 单一职责：只负责监控和通知
- 可复用：其他脚本也可以导入使用
- 易测试：可以单独测试监控逻辑
"""

import time
import subprocess
import platform
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from requests.auth import HTTPBasicAuth


class JenkinsBuildMonitor:
    """
    【教学】Jenkins 构建监控器

    核心功能：
    1. 从队列获取构建编号
    2. 监控构建进度
    3. 发送通知
    """

    def __init__(self, base_url, username, api_token, email_config=None):
        """
        初始化监控器

        参数：
            base_url: Jenkins 服务器地址
            username: 用户名
            api_token: API Token
            email_config: 邮件配置（可选）
        """
        self.base_url = base_url
        self.username = username
        self.api_token = api_token
        self.email_config = email_config

        # 创建 HTTP 会话
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(username, api_token)

    def get_build_number_from_queue(self, queue_url, timeout=60):
        """
        【教学】从队列获取构建编号

        Jenkins 构建流程：
        1. 触发构建 → 进入队列（返回队列 URL）
        2. 等待资源 → 队列中等待
        3. 开始执行 → 分配构建编号

        我们需要轮询队列 API，直到获取构建编号

        参数：
            queue_url: 队列 URL，如 http://jenkins/queue/item/123/
            timeout: 超时时间（秒）

        返回：
            build_number: 构建编号，失败返回 None
        """
        print(f"\n⏳ 等待构建从队列中启动...")
        print(f"   队列 URL: {queue_url}")

        start_time = time.time()
        dots = 0

        while time.time() - start_time < timeout:
            try:
                # Jenkins API: 添加 /api/json 获取 JSON 数据
                api_url = f"{queue_url}api/json"
                response = self.session.get(api_url, timeout=10)

                if response.status_code == 200:
                    data = response.json()

                    # 【关键】executable 字段包含构建信息
                    if 'executable' in data and data['executable']:
                        build_number = data['executable']['number']
                        print(f"\n✅ 构建已启动，编号: #{build_number}")
                        return build_number

                # 显示等待进度
                dots += 1
                if dots % 5 == 0:
                    elapsed = time.time() - start_time
                    print(f"\n   已等待 {elapsed:.0f} 秒...", end="", flush=True)
                else:
                    print(".", end="", flush=True)

                # 每 2 秒查询一次
                time.sleep(2)

            except Exception as e:
                print(f"\n⚠️  查询队列失败: {e}")
                time.sleep(2)

        print(f"\n⚠️  超时 {timeout} 秒，构建可能仍在队列中")
        return None

    def get_build_status(self, job_name, build_number):
        """
        【教学】获取构建状态

        Jenkins Build API:
        - URL: /job/{job_name}/{build_number}/api/json
        - 关键字段：
          * building: true/false（是否正在构建）
          * result: SUCCESS/FAILURE/ABORTED/UNSTABLE（构建结果）
          * duration: 构建耗时（毫秒）
          * timestamp: 开始时间戳

        返回：
            dict: 构建状态信息，失败返回 None
        """
        try:
            url = f"{self.base_url}/job/{job_name}/{build_number}/api/json"
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return {
                    'building': data.get('building', False),
                    'result': data.get('result'),
                    'duration': data.get('duration', 0),
                    'url': data.get('url', ''),
                    'timestamp': data.get('timestamp', 0)
                }
            return None

        except Exception as e:
            print(f"⚠️  查询构建状态失败: {e}")
            return None

    def wait_for_build_complete(self, job_name, build_number, check_interval=5):
        """
        【教学】等待构建完成

        轮询策略：
        1. 定期查询构建状态（默认 5 秒一次）
        2. 检查 building 字段：
           - true: 继续等待
           - false: 构建完成
        3. 显示进度信息

        参数：
            job_name: 任务名称
            build_number: 构建编号
            check_interval: 检查间隔（秒）

        返回：
            dict: 构建结果信息
        """
        print(f"\n🔄 监控构建进度...")
        print(f"   任务: {job_name}")
        print(f"   编号: #{build_number}")
        print(f"   URL: {self.base_url}/job/{job_name}/{build_number}")
        print(f"\n   等待中", end="", flush=True)

        start_time = time.time()
        dots = 0

        while True:
            status = self.get_build_status(job_name, build_number)

            if not status:
                # 查询失败，继续等待
                time.sleep(check_interval)
                continue

            # 【关键】检查是否完成
            if not status['building']:
                elapsed = time.time() - start_time
                print(f"\n\n✅ 构建完成！总耗时: {elapsed:.1f} 秒")
                return status

            # 显示进度（每次打印一个点）
            dots += 1
            if dots % 10 == 0:
                elapsed = time.time() - start_time
                print(f"\n   已等待 {elapsed:.0f} 秒...", end="", flush=True)
            else:
                print(".", end="", flush=True)

            time.sleep(check_interval)

    def send_desktop_notification(self, title, message):
        """
        【教学】发送桌面通知

        不同操作系统的实现：
        - macOS: osascript（AppleScript）
        - Linux: notify-send
        - Windows: 可以用 PowerShell 或 win10toast 库

        参数：
            title: 通知标题
            message: 通知内容
        """
        try:
            system = platform.system()

            if system == "Darwin":  # macOS
                # 使用 AppleScript 显示通知
                script = f'display notification "{message}" with title "{title}"'
                subprocess.run(['osascript', '-e', script], check=True)
                print("📱 桌面通知已发送（macOS）")

            elif system == "Linux":
                # 使用 notify-send 命令
                subprocess.run(['notify-send', title, message], check=True)
                print("📱 桌面通知已发送（Linux）")

            elif system == "Windows":
                # Windows 可以用 PowerShell
                print("⚠️  Windows 桌面通知需要额外配置")

            else:
                print(f"⚠️  当前系统 {system} 暂不支持桌面通知")

        except FileNotFoundError:
            print("⚠️  桌面通知工具未安装")
            if system == "Linux":
                print("   提示：运行 sudo apt-get install libnotify-bin")

        except Exception as e:
            print(f"⚠️  发送桌面通知失败: {e}")

    def send_email_notification(self, subject, body):
        """
        【教学】发送邮件通知

        SMTP 邮件发送流程：
        1. 连接 SMTP 服务器（如 smtp.qq.com）
        2. 登录（使用邮箱和授权码）
        3. 构造邮件（MIME 格式）
        4. 发送邮件

        常见 SMTP 服务器：
        - QQ邮箱: smtp.qq.com:465
        - 163邮箱: smtp.163.com:465
        - Gmail: smtp.gmail.com:587

        参数：
            subject: 邮件主题
            body: 邮件正文（支持 HTML）
        """
        if not self.email_config:
            print("⚠️  未配置邮件通知，跳过")
            return

        try:
            # 读取邮件配置
            smtp_server = self.email_config.get('smtp_server')
            smtp_port = self.email_config.get('smtp_port', 465)
            sender = self.email_config.get('sender')
            password = self.email_config.get('password')
            receiver = self.email_config.get('receiver')

            # 检查必要参数
            if not all([smtp_server, sender, password, receiver]):
                print("⚠️  邮件配置不完整，跳过")
                return

            # 构造邮件
            msg = MIMEMultipart()
            msg['From'] = sender
            msg['To'] = receiver
            msg['Subject'] = subject

            # 添加正文（HTML 格式）
            msg.attach(MIMEText(body, 'html', 'utf-8'))

            # 发送邮件（使用 SSL）
            with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                server.login(sender, password)
                server.send_message(msg)

            print(f"📧 邮件通知已发送到: {receiver}")

        except Exception as e:
            print(f"⚠️  发送邮件失败: {e}")
            print(f"配置: {self.email_config}")
            print(f"   提示：检查 SMTP 配置和授权码")

    def notify_build_result(self, job_name, build_number, status):
        """
        【教学】发送构建结果通知

        整合所有通知方式：
        1. 终端输出（始终显示）
        2. 桌面通知（如果支持）
        3. 邮件通知（如果配置）

        参数：
            job_name: 任务名称
            build_number: 构建编号
            status: 构建状态信息
        """
        result = status.get('result', 'UNKNOWN')
        duration = status.get('duration', 0) / 1000  # 毫秒转秒
        url = status.get('url', '')

        # 1. 终端输出
        print("\n" + "=" * 70)
        print(f"📊 构建结果报告")
        print("=" * 70)
        print(f"   任务名称: {job_name}")
        print(f"   构建编号: #{build_number}")
        print(f"   构建结果: {result}")
        print(f"   构建耗时: {duration:.1f} 秒")
        print(f"   构建地址: {url}")

        if result == "SUCCESS":
            print(f"\n✅ 构建成功！")
        else:
            print(f"\n❌ 构建失败！")

        print("=" * 70)

        # 2. 桌面通知
        title = f"Jenkins 构建{'成功' if result == 'SUCCESS' else '失败'}"
        message = f"{job_name} #{build_number}\\n耗时: {duration:.1f}秒"
        self.send_desktop_notification(title, message)

        # 3. 邮件通知
        email_subject = f"[Jenkins] {job_name} #{build_number} - {result}"
        email_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                table {{ border-collapse: collapse; width: 100%; }}
                td, th {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                .success {{ color: green; font-weight: bold; }}
                .failure {{ color: red; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h2>Jenkins 构建报告</h2>
            <table>
                <tr><td><b>任务名称</b></td><td>{job_name}</td></tr>
                <tr><td><b>构建编号</b></td><td>#{build_number}</td></tr>
                <tr><td><b>构建结果</b></td><td class="{'success' if result == 'SUCCESS' else 'failure'}">{result}</td></tr>
                <tr><td><b>构建耗时</b></td><td>{duration:.1f} 秒</td></tr>
                <tr><td><b>构建地址</b></td><td><a href="{url}">{url}</a></td></tr>
            </table>
        </body>
        </html>
        """
        self.send_email_notification(email_subject, email_body)

    def monitor_build(self, job_name, queue_url, queue_timeout=60, check_interval=5):
        """
        【教学】完整的构建监控流程

        流程：
        1. 从队列获取构建编号
        2. 等待构建完成
        3. 发送通知

        参数：
            job_name: 任务名称
            queue_url: 队列 URL
            queue_timeout: 队列超时时间
            check_interval: 状态检查间隔

        返回：
            bool: 构建是否成功
        """
        # 步骤1：获取构建编号
        build_number = self.get_build_number_from_queue(queue_url, queue_timeout)
        if not build_number:
            print("❌ 无法获取构建编号")
            return False

        # 步骤2：等待构建完成
        status = self.wait_for_build_complete(job_name, build_number, check_interval)
        if not status:
            print("❌ 无法获取构建状态")
            return False

        # 步骤3：发送通知
        self.notify_build_result(job_name, build_number, status)

        # 返回构建是否成功
        return status.get('result') == 'SUCCESS'


# 【教学】如果直接运行此文件，显示使用说明
if __name__ == "__main__":
    print("=" * 70)
    print("Jenkins 构建监控模块")
    print("=" * 70)
    print("\n这是一个库模块，不能直接运行。")
    print("\n使用方法：")
    print("  from jenkins_monitor import JenkinsBuildMonitor")
    print("\n  monitor = JenkinsBuildMonitor(base_url, username, api_token)")
    print("  monitor.monitor_build(job_name, queue_url)")
    print("\n详细用法请参考 quick_build.py")
    print("=" * 70)

