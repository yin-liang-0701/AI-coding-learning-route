"""
View: 仅负责界面展示。不涉及 SQL 或 数据库。
仅接收 Memo/Tag 实体并将其 print（打印）出来。
"""

from entity import Memo, Tag


def show_added(content: str) -> None:
    """显示添加成功"""
    print(f"已添加: {content}")


def _format_tags(tags: tuple[Tag, ...]) -> str:
    """格式化标签列表"""
    if len(tags) == 0:
        return ""
    tag_names = ", ".join(f"#{t.name}" for t in tags)
    return f" [{tag_names}]"


def show_memos(memos: list[Memo]) -> None:
    """显示备忘录列表（带标签）"""
    if len(memos) == 0:
        print("暂无备忘录。")
        return

    for memo in memos:
        date = memo.created_at.strftime("%Y-%m-%d")
        tags = _format_tags(memo.tags)
        print(f"  [{memo.id}] {memo.content}{tags}  ({date})")


def show_edited(memo_id: int, new_content: str) -> None:
    """显示编辑成功"""
    print(f"已更新: [{memo_id}] {new_content}")


def show_deleted(memo_id: int) -> None:
    """显示删除成功"""
    print(f"已删除: ID {memo_id}")


def show_not_found(memo_id: int) -> None:
    """显示未找到备忘录"""
    print(f"未找到 ID 为 {memo_id} 的备忘录。")


def show_tag_added(memo_id: int, tag_name: str) -> None:
    """显示标签添加成功"""
    print(f"已添加标签: 为 ID {memo_id} 添加了 #{tag_name}")


def show_tag_removed(memo_id: int, tag_name: str) -> None:
    """显示标签移除成功"""
    print(f"已移除标签: 从 ID {memo_id} 中移除了 #{tag_name}")


def show_tag_not_found(tag_name: str) -> None:
    """显示标签未找到"""
    print(f"未找到标签「{tag_name}」。")


def show_tags(tags: list[Tag]) -> None:
    """显示所有标签列表"""
    if len(tags) == 0:
        print("暂无标签。")
        return

    print("标签列表:")
    for tag in tags:
        print(f"  #{tag.name}")


def show_search_results(tag_name: str, memos: list[Memo]) -> None:
    """显示标签搜索结果"""
    if len(memos) == 0:
        print(f"未找到带有 #{tag_name} 标签的备忘录。")
        return

    print(f"带有 #{tag_name} 标签的备忘录 (共 {len(memos)} 件):")
    for memo in memos:
        date = memo.created_at.strftime("%Y-%m-%d")
        tags = _format_tags(memo.tags)
        print(f"  [{memo.id}] {memo.content}{tags}  ({date})")


def show_help() -> None:
    """显示使用帮助"""
    print("""
用法:
  --- 认证 ---
  python app.py register 用户名    - 用户注册
  python app.py login 用户名       - 登录
  python app.py logout             - 登出
  python app.py whoami             - 显示当前登录用户

  --- 备忘录操作（需登录） ---
  python app.py add "内容"         - 添加备忘录
  python app.py list               - 显示所有备忘录
  python app.py edit ID "新内容"   - 编辑备忘录
  python app.py delete ID          - 删除备忘录
  python app.py tag ID "标签名"    - 为备忘录添加标签
  python app.py untag ID "标签名"  - 从备忘录移除标签
  python app.py search "标签名"    - 按标签搜索
  python app.py tags               - 列出所有标签
""")


def show_unknown_command(command: str) -> None:
    """显示未知命令"""
    print(f"未知命令: {command}")
    show_help()


def show_error(message: str) -> None:
    """显示错误信息"""
    print(message)


# === 认证相关展示 ===


def show_registered(username: str) -> None:
    """显示注册成功"""
    print(f"用户注册成功: {username}")


def show_logged_in(username: str) -> None:
    """显示登录成功"""
    print(f"已登录: {username}")


def show_logged_out() -> None:
    """显示登出成功"""
    print("已成功退出登录。")


def show_current_user(username: str) -> None:
    """显示当前登录用户"""
    print(f"当前登录中: {username}")


def show_login_required() -> None:
    """显示需要登录"""
    print("请先登录: python app.py login 用户名")