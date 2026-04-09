import getpass
import sys
from datetime import datetime

import view
from repository import (
    SqliteMemoRepository,
    SqliteSessionRepository,
    SqliteTagRepository,
    SqliteUserRepository,
)
from session import clear_session, load_session, save_session
from usecase import (
    AddMemoUseCase,
    AddTagToMemoUseCase,
    DeleteMemoUseCase,
    EditMemoUseCase,
    ListMemosUseCase,
    ListTagsUseCase,
    LoginUserUseCase,
    LogoutUserUseCase,
    RegisterUserUseCase,
    RemoveTagFromMemoUseCase,
    SearchByTagUseCase,
)

# 初始化 Repository（仓库实例），并供所有 UseCase 共享
memo_repository = SqliteMemoRepository()
tag_repository = SqliteTagRepository(db_path=memo_repository.db_path)
user_repository = SqliteUserRepository(db_path=memo_repository.db_path)
session_repository = SqliteSessionRepository(db_path=memo_repository.db_path)


# --- 认证助手函数 ---


def get_current_user_id() -> int | None:
    """对比会话文件与数据库，返回当前登录的用户 ID。
    若未登录或会话过期，则返回 None。
    """
    session_info = load_session()
    if session_info is None:
        return None

    user_id, token = session_info

    # 在数据库端校验 Token
    result = session_repository.find_by_token(token)
    if result is None:
        clear_session()  # 同时清理本地文件
        return None

    _, expires_at = result
    if expires_at < datetime.now():
        # 会话已过期
        session_repository.delete_by_token(token)
        clear_session()
        return None

    return user_id


# --- 公开命令（无需认证） ---


def handle_register(args: list[str]) -> None:
    """register 命令：用户注册"""
    if len(args) < 1:
        view.show_error("请指定用户名: python app.py register 用户名")
        return
    username = args[0]
    password = getpass.getpass("密码: ")
    password_confirm = getpass.getpass("密码（确认）: ")
    if password != password_confirm:
        view.show_error("两次输入的密码不一致。")
        return
    usecase = RegisterUserUseCase(user_repository)
    try:
        user = usecase.execute(username, password)
        view.show_registered(user.username)
    except ValueError as e:
        view.show_error(str(e))


def handle_login(args: list[str]) -> None:
    """login 命令：登录"""
    if len(args) < 1:
        view.show_error("请指定用户名: python app.py login 用户名")
        return
    username = args[0]
    password = getpass.getpass("密码: ")
    usecase = LoginUserUseCase(user_repository, session_repository)
    try:
        user, token = usecase.execute(username, password)
        save_session(user.id, token)
        view.show_logged_in(user.username)
    except ValueError as e:
        view.show_error(str(e))


# --- 认证必须命令 ---


def handle_add(args: list[str], user_id: int) -> None:
    """add 命令处理：添加备忘录"""
    if len(args) < 1:
        view.show_error('请指定内容: python app.py add "备忘录内容"')
        return
    usecase = AddMemoUseCase(memo_repository)
    memo = usecase.execute(args[0], user_id=user_id)
    view.show_added(memo.content)


def handle_list(user_id: int) -> None:
    """list 命令处理：列出备忘录"""
    usecase = ListMemosUseCase(memo_repository)
    memos = usecase.execute(user_id=user_id)
    view.show_memos(memos)


def handle_edit(args: list[str], user_id: int) -> None:
    """edit 命令处理：编辑备忘录"""
    if len(args) < 2:
        view.show_error('请指定 ID 和内容: python app.py edit 1 "新内容"')
        return
    memo_id = int(args[0])
    new_content = args[1]
    usecase = EditMemoUseCase(memo_repository)
    memo = usecase.execute(memo_id, new_content, user_id=user_id)
    if memo is None:
        view.show_not_found(memo_id)
    else:
        view.show_edited(memo.id, memo.content)


def handle_delete(args: list[str], user_id: int) -> None:
    """delete 命令处理：删除备忘录"""
    if len(args) < 1:
        view.show_error("请指定 ID: python app.py delete 1")
        return
    memo_id = int(args[0])
    usecase = DeleteMemoUseCase(memo_repository)
    success = usecase.execute(memo_id, user_id=user_id)
    if success:
        view.show_deleted(memo_id)
    else:
        view.show_not_found(memo_id)


def handle_tag(args: list[str], user_id: int) -> None:
    """tag 命令处理：为备忘录添加标签"""
    if len(args) < 2:
        view.show_error('请指定 ID 和标签名: python app.py tag 1 "重要"')
        return
    memo_id = int(args[0])
    tag_name = args[1]
    usecase = AddTagToMemoUseCase(memo_repository, tag_repository)
    memo = usecase.execute(memo_id, tag_name, user_id=user_id)
    if memo is None:
        view.show_not_found(memo_id)
    else:
        view.show_tag_added(memo_id, tag_name)


def handle_untag(args: list[str], user_id: int) -> None:
    """untag 命令处理：从备忘录移除标签"""
    if len(args) < 2:
        view.show_error('请指定 ID 和标签名: python app.py untag 1 "重要"')
        return
    memo_id = int(args[0])
    tag_name = args[1]
    usecase = RemoveTagFromMemoUseCase(memo_repository, tag_repository)
    memo = usecase.execute(memo_id, tag_name, user_id=user_id)
    if memo is None:
        view.show_not_found(memo_id)
    else:
        view.show_tag_removed(memo_id, tag_name)


def handle_search(args: list[str], user_id: int) -> None:
    """search 命令处理：按标签搜索备忘录"""
    if len(args) < 1:
        view.show_error('请指定标签名: python app.py search "重要"')
        return
    tag_name = args[0]
    usecase = SearchByTagUseCase(memo_repository)
    memos = usecase.execute(tag_name, user_id=user_id)
    view.show_search_results(tag_name, memos)


def handle_tags(user_id: int) -> None:
    """tags 命令处理：列出所有标签"""
    usecase = ListTagsUseCase(tag_repository)
    tags = usecase.execute()
    view.show_tags(tags)


def handle_logout(args: list[str], user_id: int) -> None:
    """logout 命令：登出"""
    session_info = load_session()
    if session_info is not None:
        _, token = session_info
        LogoutUserUseCase(session_repository).execute(token)
    clear_session()
    view.show_logged_out()


def handle_whoami(args: list[str], user_id: int) -> None:
    """whoami 命令：显示当前登录的用户"""
    user = user_repository.find_by_id(user_id)
    if user is not None:
        view.show_current_user(user.username)


# --- 命令路由配置 ---


PUBLIC_COMMANDS = {
    "register": handle_register,
    "login": handle_login,
}

AUTH_COMMANDS = {
    "add": handle_add,
    "list": lambda args, uid: handle_list(uid),
    "edit": handle_edit,
    "delete": handle_delete,
    "tag": handle_tag,
    "untag": handle_untag,
    "search": handle_search,
    "tags": lambda args, uid: handle_tags(uid),
    "logout": handle_logout,
    "whoami": handle_whoami,
}


def main() -> None:
    """解析命令行参数并分发至相应的处理器"""
    if len(sys.argv) < 2:
        view.show_help()
        return

    command = sys.argv[1]
    args = sys.argv[2:]

    # 处理公开命令（无需认证）
    if command in PUBLIC_COMMANDS:
        PUBLIC_COMMANDS[command](args)
        return

    # 处理需要认证的命令
    if command in AUTH_COMMANDS:
        user_id = get_current_user_id()
        if user_id is None:
            view.show_login_required()
            return
        AUTH_COMMANDS[command](args, user_id)
        return

    view.show_unknown_command(command)