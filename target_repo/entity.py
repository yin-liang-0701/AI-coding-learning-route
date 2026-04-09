"""
Entity: 定义备忘录（Memo）、标签（Tag）和用户（User）是什么。
不关心数据库，也不关心 UI。它们是纯粹的数据结构。
"""

from dataclasses import dataclass
from datetime import datetime


# “数据类”装饰器
# @dataclass: 自动为你生成 __init__()（构造函数）、__repr__()（打印格式）和 __eq__()（比较逻辑）。你不需要手动写 self.name = name 这种冗长的代码。
# frozen=True (不可变性):将类实例变为只读。一旦 Tag 对象被创建，你就不能修改它的属性
@dataclass(frozen=True) 
class Tag:
    """代表标签的数据结构"""
    id: int | None  # 新创建时为 None
    name: str
    created_at: datetime

    @staticmethod # 静态方法 ，不依赖于类的具体实例，也不依赖于类本身
    def create(name: str) -> "Tag":
        """创建一个新标签"""
        return Tag(id=None, name=name, created_at=datetime.now())


@dataclass(frozen=True)
class User:
    """代表用户的数据结构

    【教学要点：为什么持有 password_hash 而不是 password？】
    如果在实体中保存明文密码，存在不小心将其输出到日志或直接存入数据库的风险。
    在架构阶段就强制执行“不持有明文密码”的约束。
    哈希化处理应在实体之外（如 auth.py）完成。
    """
    id: int | None  # 新创建时为 None
    username: str
    password_hash: str
    created_at: datetime

    @staticmethod
    def create(username: str, password_hash: str) -> "User":
        """创建一个新用户"""
        return User(
            id=None,
            username=username,
            password_hash=password_hash,
            created_at=datetime.now(),
        )


@dataclass(frozen=True)
class Memo:
    """代表备忘录的数据结构"""
    id: int | None  # 新创建时为 None，持久化保存后分配 ID
    content: str
    created_at: datetime
    updated_at: datetime
    user_id: int | None = None  # 归属于哪个用户（用于认证功能）
    tags: tuple[Tag, ...] = ()  # 标签列表（因为是不可变的，所以使用 tuple）

    @staticmethod
    def create(content: str, user_id: int | None = None) -> "Memo":
        """创建一个新备忘录（此时尚未保存至数据库的状态）"""
        now = datetime.now()
        return Memo(id=None, content=content, created_at=now, updated_at=now, user_id=user_id)

    def update_content(self, new_content: str) -> "Memo":
        """返回一个更新了内容的新 Memo 对象（不修改原始对象）"""
        return Memo(
            id=self.id,
            content=new_content,
            created_at=self.created_at,
            updated_at=datetime.now(),
            user_id=self.user_id,
            tags=self.tags,
        )

    def add_tag(self, tag: Tag) -> "Memo":
        """返回一个添加了标签的新 Memo 对象（不修改原始对象）"""
        if any(t.name == tag.name for t in self.tags):
            return self  # 如果已存在同名标签，则直接返回原对象
        return Memo(
            id=self.id,
            content=self.content,
            created_at=self.created_at,
            updated_at=self.updated_at,
            user_id=self.user_id,
            tags=self.tags + (tag,),
        )

    def remove_tag(self, tag_name: str) -> "Memo":
        """返回一个移除了标签的新 Memo 对象（不修改原始对象）"""
        return Memo(
            id=self.id,
            content=self.content,
            created_at=self.created_at,
            updated_at=self.updated_at,
            user_id=self.user_id,
            tags=tuple(t for t in self.tags if t.name != tag_name),
        )