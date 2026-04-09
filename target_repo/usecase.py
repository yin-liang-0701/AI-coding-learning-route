"""
UseCase: 业务逻辑。定义“作为一个备忘录应用能做什么”。
不了解数据库细节（交给 Repository 处理）。不了解 UI 细节。

【步骤 6 中新增的认证与授权要点】
- RegisterUserUseCase: 用户注册（校验 + 哈希化）
- LoginUserUseCase: 登录（密码验证 + 发放会话）
- LogoutUserUseCase: 登出（销毁会话）
- 在现有 UseCase 中增加 user_id：确保只能操作属于自己的备忘录（授权）
"""

import secrets
from datetime import datetime, timedelta

from auth import hash_password, verify_password
from entity import Memo, Tag, User
from repository import MemoRepository, SessionRepository, TagRepository, UserRepository


# === 认证用例 (Authentication UseCases) ===


class RegisterUserUseCase:
    """用户注册

    【教学要点：校验应该放在哪里？】
    输入数据的校验（Validation）应在 UseCase 层进行。
    - 实体层 (Entity)：纯粹的数据结构（不承担校验职责）。
    - 仓库层 (Repository)：仅负责数据持久化（不了解业务规则）。
    - 用例层 (UseCase)：检查业务规则的地方 ← 就在这里。
    """

    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def execute(self, username: str, password: str) -> User:
        if len(username) < 3:
            raise ValueError("用户名长度必须至少为 3 个字符")
        if len(password) < 8:
            raise ValueError("密码长度必须至少为 8 个字符")

        password_hashed = hash_password(password)
        user = User.create(username, password_hashed)
        return self.user_repo.save(user)


class LoginUserUseCase:
    """登录

    【教学要点：为什么要模糊错误信息？】
    如果显示“用户不存在”，会向攻击者泄露用户名是否已注册（即用户枚举攻击）。
    显示“用户名或密码错误”这种模糊的信息是安全方面的最佳实践。
    """

    def __init__(self, user_repo: UserRepository, session_repo: SessionRepository):
        self.user_repo = user_repo
        self.session_repo = session_repo

    def execute(self, username: str, password: str) -> tuple[User, str]:
        """登录成功返回 (User, token)。失败则抛出 ValueError"""
        user = self.user_repo.find_by_username(username)
        if user is None:
            raise ValueError("用户名或密码错误")

        if not verify_password(password, user.password_hash):
            raise ValueError("用户名或密码错误")

        # 生成会话 Token 并存入数据库
        token = secrets.token_hex(32)
        expires_at = datetime.now() + timedelta(days=7)
        self.session_repo.save(token, user.id, expires_at)

        return (user, token)


class LogoutUserUseCase:
    """登出（销毁会话）"""

    def __init__(self, session_repo: SessionRepository):
        self.session_repo = session_repo

    def execute(self, token: str) -> bool:
        return self.session_repo.delete_by_token(token)


# === 备忘录用例 (Memo UseCases，支持 user_id) ===


class AddMemoUseCase:
    """添加备忘录"""

    def __init__(self, repository: MemoRepository):
        self.repository = repository

    def execute(self, content: str, user_id: int | None = None) -> Memo:
        memo = Memo.create(content, user_id=user_id)
        return self.repository.save(memo)


class ListMemosUseCase:
    """列出备忘录列表"""

    def __init__(self, repository: MemoRepository):
        self.repository = repository

    def execute(self, user_id: int | None = None) -> list[Memo]:
        return self.repository.find_all(user_id=user_id)


class EditMemoUseCase:
    """编辑备忘录

    【教学要点：授权 (Authorization)】
    认证 (Authentication) = 确认你是谁（登录）。
    授权 (Authorization) = 确认你是否有权限（是否是备忘录的所有者？）。
    这两者是不同的概念。即使已登录，也无法编辑他人的备忘录。
    """

    def __init__(self, repository: MemoRepository):
        self.repository = repository

    def execute(self, memo_id: int, new_content: str, user_id: int | None = None) -> Memo | None:
        """编辑成功返回更新后的 Memo，未找到或无权限则返回 None"""
        memo = self.repository.find_by_id(memo_id)
        if memo is None:
            return None
        
        # 授权检查：如果不是自己的备忘录则禁止编辑
        if user_id is not None and memo.user_id != user_id:
            return None
            
        updated_memo = memo.update_content(new_content)
        self.repository.update(updated_memo)
        return updated_memo


class DeleteMemoUseCase:
    """删除备忘录"""

    def __init__(self, repository: MemoRepository):
        self.repository = repository

    def execute(self, memo_id: int, user_id: int | None = None) -> bool:
        """删除成功返回 True，未找到或无权限返回 False"""
        # 授权检查
        if user_id is not None:
            memo = self.repository.find_by_id(memo_id)
            if memo is None or memo.user_id != user_id:
                return False
        return self.repository.delete(memo_id)


class AddTagToMemoUseCase:
    """为备忘录添加标签"""

    def __init__(self, memo_repo: MemoRepository, tag_repo: TagRepository):
        self.memo_repo = memo_repo
        self.tag_repo = tag_repo

    def execute(self, memo_id: int, tag_name: str, user_id: int | None = None) -> Memo | None:
        """添加成功返回更新后的 Memo，备忘录未找到或无权限返回 None"""
        memo = self.memo_repo.find_by_id(memo_id)
        if memo is None:
            return None
        
        # 授权检查
        if user_id is not None and memo.user_id != user_id:
            return None
            
        tag = self.tag_repo.find_or_create(tag_name)
        self.memo_repo.add_tag(memo_id, tag.id)
        return self.memo_repo.find_by_id(memo_id)


class RemoveTagFromMemoUseCase:
    """从备忘录移除标签"""

    def __init__(self, memo_repo: MemoRepository, tag_repo: TagRepository):
        self.memo_repo = memo_repo
        self.tag_repo = tag_repo

    def execute(self, memo_id: int, tag_name: str, user_id: int | None = None) -> Memo | None:
        """移除成功返回更新后的 Memo，备忘录或标签未找到或无权限返回 None"""
        memo = self.memo_repo.find_by_id(memo_id)
        if memo is None:
            return None
        
        # 授权检查
        if user_id is not None and memo.user_id != user_id:
            return None
            
        tag = self.tag_repo.find_by_name(tag_name)
        if tag is None:
            return None
            
        self.memo_repo.remove_tag(memo_id, tag.id)
        return self.memo_repo.find_by_id(memo_id)


class SearchByTagUseCase:
    """按标签搜索备忘录"""

    def __init__(self, repository: MemoRepository):
        self.repository = repository

    def execute(self, tag_name: str, user_id: int | None = None) -> list[Memo]:
        return self.repository.find_by_tag(tag_name, user_id=user_id)


class ListTagsUseCase:
    """列出全系统标签（由于标签是全局共享的，因此不需要 user_id）"""

    def __init__(self, repository: TagRepository):
        self.repository = repository

    def execute(self) -> list[Tag]:
        return self.repository.find_all()