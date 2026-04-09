"""
Session: 管理CLI应用的认证状态。

【教育要点: 会话管理机制】
Web应用将令牌保存在Cookie中，每次请求时发送给服务器。
CLI应用无法使用Cookie，所以将令牌保存到文件中。

  Web应用           CLI应用
  ----------          ----------
  Cookie     ←→    ~/.memo_session（令牌文件）
  Redis/DB   ←→    SQLite sessions 表

登录流程:
1. 用户输入ID/密码
2. 服务器（UseCase）验证密码
3. 验证通过则生成随机令牌
4. 令牌同时保存到DB（sessions）和文件（~/.memo_session）
5. 下次执行命令时，从文件读取令牌并与DB进行比对

登出流程:
1. 从文件读取令牌
2. 从DB删除会话
3. 删除文件
"""

from pathlib import Path

# 会话文件保存位置（主目录下）
SESSION_FILE = Path.home() / ".memo_session"


def save_session(user_id: int, token: str) -> None:
    """将会话信息保存到文件"""
    SESSION_FILE.write_text(f"{user_id}:{token}", encoding="utf-8")


def load_session() -> tuple[int, str] | None:
    """从文件读取会话信息。未登录则返回None"""
    if not SESSION_FILE.exists():
        return None
    try:
        content = SESSION_FILE.read_text(encoding="utf-8").strip()
        user_id_str, token = content.split(":", 1)
        return (int(user_id_str), token)
    except (ValueError, FileNotFoundError):
        return None


def clear_session() -> None:
    """删除会话文件（登出）"""
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()
