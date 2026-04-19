#!/usr/bin/env python3
"""
QQ邮箱授权码问题解决工具
使用CLI-Anything方法指导用户获取16位授权码并更新配置
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import click


def run_applescript(script: str) -> str:
    """运行AppleScript并返回结果"""
    try:
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            raise RuntimeError(f"AppleScript错误: {result.stderr}")
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        raise RuntimeError("AppleScript执行超时")


class QQMailAuthResolver:
    """QQ邮箱授权码问题解决器"""

    def __init__(self):
        self.project_dir = Path(__file__).parent
        self.env_file = self.project_dir / ".env"
        self.browser = "Safari"
        self.mail_url = "https://mail.qq.com"
        self.smtp_settings_url = (
            "https://mail.qq.com/cgi-bin/loginpage?t=account_security&sub=smtp_pop3"
        )

    def check_current_password(self) -> dict:
        """检查当前配置的密码"""
        current_password = None
        password_length = 0

        if self.env_file.exists():
            with open(self.env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("SMTP_PASSWORD="):
                        key, value = line.split("=", 1)
                        current_password = value.strip()
                        # 移除可能的引号
                        if current_password.startswith('"') and current_password.endswith('"'):
                            current_password = current_password[1:-1]
                        elif current_password.startswith("'") and current_password.endswith("'"):
                            current_password = current_password[1:-1]
                        password_length = len(current_password)
                        break

        return {
            "has_password": current_password is not None,
            "password": current_password,
            "length": password_length,
            "is_16_digit": password_length == 16
            and current_password
            and current_password.isalnum(),
            "is_8_digit": password_length == 8 and current_password and current_password.isalnum(),
            "is_qq_auth_code": password_length == 16
            and current_password
            and all(c.isalnum() or c in "_-" for c in current_password),
        }

    def open_qqmail_guided(self) -> str:
        """打开QQ邮箱并显示指导信息"""
        script = f"""
        tell application "{self.browser}"
            activate
            delay 1

            -- 创建新窗口
            make new document with properties {{URL:"{self.mail_url}"}}
            delay 3

            -- 显示指导信息
            display dialog "请按以下步骤操作：\\n\\n1. 登录您的QQ邮箱 (athenabot@qq.com)\\n2. 点击右上角设置图标 ⚙️\\n3. 选择'账户'选项卡\\n4. 找到'POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务'\\n5. 开启'POP3/SMTP服务'（如果未开启）\\n6. 点击'生成授权码'\\n7. 复制16位授权码\\n\\n完成后点击'确定'继续" with title "QQ邮箱授权码获取指南" buttons {{"确定", "取消"}} default button 1
        end tell
        """

        try:
            result = run_applescript(script)
            return "浏览器已打开，请按照指导获取授权码"
        except Exception as e:
            return f"打开浏览器失败: {e}"

    def open_smtp_settings_direct(self) -> str:
        """直接打开SMTP/POP3设置页面"""
        script = f"""
        tell application "{self.browser}"
            activate
            delay 1
            make new document with properties {{URL:"{self.smtp_settings_url}"}}
            delay 3
            return "已打开QQ邮箱SMTP/POP3设置页面"
        end tell
        """

        return run_applescript(script)

    def update_env_file(self, new_password: str) -> bool:
        """更新.env文件中的SMTP_PASSWORD"""
        if not self.env_file.exists():
            print(f"错误: 找不到.env文件: {self.env_file}")
            return False

        # 读取整个文件
        with open(self.env_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 查找并更新SMTP_PASSWORD行
        updated = False
        new_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("SMTP_PASSWORD="):
                # 保持原有格式（引号等）
                if '"' in line:
                    new_line = f'SMTP_PASSWORD="{new_password}"\n'
                elif "'" in line:
                    new_line = f"SMTP_PASSWORD='{new_password}'\n"
                else:
                    new_line = f"SMTP_PASSWORD={new_password}\n"
                new_lines.append(new_line)
                updated = True
            else:
                new_lines.append(line)

        # 如果没找到，添加到文件末尾
        if not updated:
            new_lines.append(f'\n# 更新于 {time.strftime("%Y-%m-%d %H:%M:%S")}\n')
            new_lines.append(f"SMTP_PASSWORD={new_password}\n")

        # 写入文件
        with open(self.env_file, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        return True

    def test_smtp_connection(self, password: str = None) -> dict:
        """测试SMTP连接"""
        import smtplib
        import ssl

        # 从.env文件读取其他配置
        smtp_server = "smtp.qq.com"
        smtp_port = 587
        username = "athenabot@qq.com"
        use_tls = True

        if not password:
            password_check = self.check_current_password()
            password = password_check["password"]

        if not password:
            return {"success": False, "error": "未提供密码"}

        result = {
            "server": smtp_server,
            "port": smtp_port,
            "username": username,
            "password_length": len(password) if password else 0,
            "success": False,
        }

        try:
            with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
                result["connection"] = "建立成功"
                server.ehlo()

                if use_tls:
                    server.starttls()
                    server.ehlo()
                    result["tls"] = "已启用"

                print(f"尝试登录，密码长度: {len(password)}")
                server.login(username, password)
                result["login"] = "成功"
                result["success"] = True

        except smtplib.SMTPAuthenticationError as e:
            result["error"] = f"认证失败: {e}"
            result["suggestion"] = "密码错误或不是16位授权码"
        except Exception as e:
            result["error"] = f"连接失败: {e}"

        return result

    def get_auth_code_via_dialog(self) -> str:
        """通过对话框获取用户输入的授权码"""
        script = """
        display dialog "请输入您获取的16位QQ邮箱授权码：" default answer "" with title "输入授权码" buttons {"确定", "取消"} default button 1
        """

        try:
            result = run_applescript(script)
            # 解析AppleScript返回结果
            if "button returned:确定" in result and "text returned:" in result:
                # 提取文本
                import re

                match = re.search(r"text returned:(.+)", result)
                if match:
                    auth_code = match.group(1).strip()
                    if len(auth_code) == 16 and auth_code.isalnum():
                        return auth_code
                    else:
                        raise ValueError(f"授权码长度不正确或包含非法字符: {len(auth_code)}位")
        except Exception as e:
            print(f"对话框输入失败: {e}")

        return None

    def create_step_by_step_guide(self) -> str:
        """创建分步指南"""
        guide = """# QQ邮箱16位授权码获取指南

## 问题诊断
当前配置的SMTP密码不是16位授权码，导致邮件发送失败。

## 解决方案
获取16位QQ邮箱授权码并更新配置。

## 分步操作指南

### 步骤1: 打开QQ邮箱
1. 打开Safari浏览器
2. 访问 https://mail.qq.com
3. 登录账号: athenabot@qq.com

### 步骤2: 进入账户设置
1. 登录后，点击右上角设置图标 ⚙️
2. 选择「账户」选项卡
3. 向下滚动到「POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务」部分

### 步骤3: 开启服务并生成授权码
1. 找到「POP3/SMTP服务」，点击「开启」
2. 根据提示完成安全验证（可能需要短信验证）
3. 开启后，点击「生成授权码」
4. 系统会生成一个16位的授权码（包含字母和数字）

### 步骤4: 复制授权码
1. 复制完整的16位授权码
2. 注意：授权码只显示一次，请立即复制保存

### 步骤5: 更新系统配置
1. 将授权码粘贴到配置工具中
2. 系统将自动更新.env文件
3. 测试SMTP连接确保配置正确

## 重要提示
- 授权码不是登录密码，是专门用于SMTP服务的
- 授权码为16位，包含字母和数字，不含特殊字符
- 每个授权码只能使用一次，生成新授权码后旧授权码失效
- 建议保存授权码到安全的地方

## 备用方案
如果无法通过网页生成授权码：
1. 使用QQ邮箱手机APP
2. 设置 → 账户 → POP3/IMAP/SMTP服务
3. 开启服务并获取授权码

## 验证配置
更新后运行测试命令：
```bash
python3 test_notification_channels_final.py
```
检查邮件SMTP测试是否通过。
"""
        return guide


@click.group()
def cli():
    """QQ邮箱授权码问题解决工具"""
    pass


@cli.command()
def diagnose():
    """诊断当前密码配置"""
    resolver = QQMailAuthResolver()
    password_info = resolver.check_current_password()

    click.echo("=== QQ邮箱密码配置诊断 ===")
    click.echo(f"配置文件: {resolver.env_file}")
    click.echo(f"密码已配置: {password_info['has_password']}")

    if password_info["has_password"]:
        click.echo(f"密码长度: {password_info['length']} 位")
        click.echo(f"是否为16位: {password_info['is_16_digit']}")
        click.echo(f"是否为8位: {password_info['is_8_digit']}")
        click.echo(f"是否符合授权码格式: {password_info['is_qq_auth_code']}")

        if password_info["length"] == 8:
            click.echo("\n⚠️  问题: 密码为8位，QQ邮箱需要16位授权码")
            click.echo("   当前密码 'REDACTED_SMTP_PASSWORD' 是8位，可能是登录密码而非授权码")
        elif password_info["length"] != 16:
            click.echo(f"\n❌ 问题: 密码长度{password_info['length']}位，需要16位")
        else:
            click.echo("\n✅ 密码长度正确（16位）")

    # 测试SMTP连接
    click.echo("\n=== SMTP连接测试 ===")
    test_result = resolver.test_smtp_connection()

    if test_result.get("success"):
        click.echo("✅ SMTP连接测试通过")
    else:
        click.echo(f"❌ SMTP连接失败: {test_result.get('error', '未知错误')}")
        if test_result.get("suggestion"):
            click.echo(f"   建议: {test_result['suggestion']}")


@cli.command()
def guide():
    """显示分步获取授权码指南"""
    resolver = QQMailAuthResolver()
    guide_text = resolver.create_step_by_step_guide()
    click.echo(guide_text)


@cli.command()
def open_guide():
    """打开浏览器并显示操作指南"""
    resolver = QQMailAuthResolver()
    result = resolver.open_qqmail_guided()
    click.echo(result)


@cli.command()
def open_settings():
    """直接打开SMTP设置页面"""
    resolver = QQMailAuthResolver()
    result = resolver.open_smtp_settings_direct()
    click.echo(result)


@cli.command()
@click.option("--auth-code", prompt=True, hide_input=True, help="16位QQ邮箱授权码")
def update(auth_code):
    """更新.env文件中的授权码"""
    if len(auth_code) != 16:
        click.echo(f"❌ 错误: 授权码长度必须为16位，当前为{len(auth_code)}位")
        return

    if not auth_code.isalnum():
        click.echo("❌ 错误: 授权码只能包含字母和数字")
        return

    resolver = QQMailAuthResolver()

    # 备份原文件
    import shutil

    backup_file = resolver.env_file.with_suffix(".env.backup")
    shutil.copy2(resolver.env_file, backup_file)
    click.echo(f"✅ 已备份原文件到: {backup_file}")

    # 更新文件
    if resolver.update_env_file(auth_code):
        click.echo(f"✅ 已更新.env文件中的SMTP_PASSWORD")

        # 测试新配置
        click.echo("\n=== 测试新授权码 ===")
        test_result = resolver.test_smtp_connection(auth_code)

        if test_result.get("success"):
            click.echo("🎉 授权码更新成功！SMTP连接测试通过")
            click.echo(f"   服务器: {test_result['server']}:{test_result['port']}")
            click.echo(f"   用户名: {test_result['username']}")
        else:
            click.echo(f"⚠️  授权码已更新，但SMTP测试失败: {test_result.get('error')}")
            click.echo("   请检查授权码是否正确，或尝试其他端口/加密方式")
    else:
        click.echo("❌ 更新.env文件失败")


@cli.command()
def interactive():
    """交互式授权码获取和更新"""
    click.echo("=== QQ邮箱授权码交互式配置 ===")

    resolver = QQMailAuthResolver()

    # 1. 显示当前状态
    password_info = resolver.check_current_password()
    click.echo(f"\n1. 当前配置: {password_info['length']}位密码")

    # 2. 显示指南
    click.echo("\n2. 打开浏览器获取授权码...")
    resolver.open_qqmail_guided()

    # 3. 获取授权码
    click.echo("\n3. 请输入16位授权码")
    auth_code = resolver.get_auth_code_via_dialog()

    if not auth_code:
        click.echo("❌ 未获取到有效的授权码")
        return

    # 4. 更新配置
    click.echo(f"\n4. 更新配置...")
    if resolver.update_env_file(auth_code):
        click.echo("✅ 配置已更新")

        # 5. 测试
        click.echo("\n5. 测试SMTP连接...")
        test_result = resolver.test_smtp_connection(auth_code)

        if test_result.get("success"):
            click.echo("🎉 配置成功！邮件通知功能已恢复")
        else:
            click.echo(f"⚠️  配置已更新但测试失败: {test_result.get('error')}")
            click.echo("   请运行完整测试: python3 test_notification_channels_final.py")
    else:
        click.echo("❌ 更新配置失败")


@cli.command()
def test_smtp():
    """测试当前SMTP连接"""
    resolver = QQMailAuthResolver()
    test_result = resolver.test_smtp_connection()

    click.echo("=== SMTP连接测试 ===")
    click.echo(f"服务器: {test_result.get('server')}:{test_result.get('port')}")
    click.echo(f"用户名: {test_result.get('username')}")
    click.echo(f"密码长度: {test_result.get('password_length')}位")

    if test_result.get("success"):
        click.echo("✅ SMTP连接测试通过")
        click.echo(f"连接: {test_result.get('connection', 'N/A')}")
        click.echo(f"TLS: {test_result.get('tls', 'N/A')}")
        click.echo(f"登录: {test_result.get('login', 'N/A')}")
    else:
        click.echo(f"❌ SMTP连接测试失败")
        click.echo(f"错误: {test_result.get('error', '未知错误')}")
        if test_result.get("suggestion"):
            click.echo(f"建议: {test_result.get('suggestion')}")


if __name__ == "__main__":
    cli()
