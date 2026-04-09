"""
UseCase 层测试。
用于验证业务逻辑是否运行正确。
Repository（仓库）使用了 Mock（伪实现） → 无需数据库即可进行测试！
"""

from datetime import datetime, timedelta

import pytest

from auth import hash_password
from entity import Memo, Tag, User
from repository import MemoRepository, SessionRepository, TagRepository, UserRepository
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


class FakeMemoRepository(MemoRepository):
    """用于测试的伪仓库。不使用真实数据库，而是在内存中的列表（list）上运行。"""

    def __init__(self):
        self.memos: list[Memo] = []  # 内存中的备忘录列表
        self.memo_tags: dict[int, list[int]] = {}  # 备忘录与标签的映射：memo_id -> [tag_id, ...]
        self.next_id = 1  # 模拟数据库的自增 ID

    def save(self, memo: Memo) -> Memo:
        """保存备忘录并分配 ID"""
        saved = Memo(
            id=self.next_id,
            content=memo.content,
            created_at=memo.created_at,
            updated_at=memo.updated_at,
            user_id=memo.user_id,
        )
        self.memos.append(saved)
        self.next_id += 1
        return saved

    def find_all(self, user_id: int | None = None) -> list[Memo]:
        """获取所有备忘录（若指定 user_id 则过滤）"""
        if user_id is not None:
            return [m for m in self.memos if m.user_id == user_id]
        return list(self.memos)

    def find_by_id(self, memo_id: int) -> Memo | None:
        """通过 ID 查找备忘录"""
        for memo in self.memos:
            if memo.id == memo_id:
                return memo
        return None

    def find_by_tag(self, tag_name: str, user_id: int | None = None) -> list[Memo]:
        """按标签查找（伪实现中默认返回空列表，可在具体测试中扩展）"""
        return []

    def update(self, memo: Memo) -> bool:
        """更新内存中的备忘录"""
        for i, m in enumerate(self.memos):
            if m.id == memo.id:
                self.memos[i] = memo
                return True
        return False

    def delete(self, memo_id: int) -> bool:
        """删除备忘录及其关联的标签记录"""
        for i, memo in enumerate(self.memos):
            if memo.id == memo_id:
                self.memos.pop(i)
                self.memo_tags.pop(memo_id, None)
                return True
        return False

    def add_tag(self, memo_id: int, tag_id: int) -> bool:
        """在内存中建立备忘录与标签的关联"""
        if memo_id not in self.memo_tags:
            self.memo_tags[memo_id] = []
        if tag_id in self.memo_tags[memo_id]:
            return False  # 已存在
        self.memo_tags[memo_id].append(tag_id)
        return True

    def remove_tag(self, memo_id: int, tag_id: int) -> bool:
        """解除备忘录与标签的关联"""
        if memo_id in self.memo_tags and tag_id in self.memo_tags[memo_id]:
            self.memo_tags[memo_id].remove(tag_id)
            return True
        return False


class FakeTagRepository(TagRepository):
    """用于测试的伪标签仓库"""

    def __init__(self):
        self.tags: list[Tag] = []
        self.next_id = 1

    def save(self, tag: Tag) -> Tag:
        saved = Tag(id=self.next_id, name=tag.name, created_at=tag.created_at)
        self.tags.append(saved)
        self.next_id += 1
        return saved

    def find_by_name(self, name: str) -> Tag | None:
        for tag in self.tags:
            if tag.name == name:
                return tag
        return None

    def find_all(self) -> list[Tag]:
        return list(self.tags)

    def find_or_create(self, name: str) -> Tag:
        """按名称查找标签，不存在则创建"""
        existing = self.find_by_name(name)
        if existing is not None:
            return existing
        return self.save(Tag.create(name))


class FakeUserRepository(UserRepository):
    """用于测试的伪用户仓库"""

    def __init__(self):
        self.users: list[User] = []
        self.next_id = 1

    def save(self, user: User) -> User:
        # 校验用户名是否重复
        if any(u.username == user.username for u in self.users):
            raise ValueError(f"用户名 '{user.username}' 已被占用")
        saved = User(
            id=self.next_id,
            username=user.username,
            password_hash=user.password_hash,
            created_at=user.created_at,
        )
        self.users.append(saved)
        self.next_id += 1
        return saved

    def find_by_username(self, username: str) -> User | None:
        for user in self.users:
            if user.username == username:
                return user
        return None

    def find_by_id(self, user_id: int) -> User | None:
        for user in self.users:
            if user.id == user_id:
                return user
        return None


class FakeSessionRepository(SessionRepository):
    """用于测试的伪会话仓库"""

    def __init__(self):
        # 使用字典存储：token -> (user_id, expires_at)
        self.sessions: dict[str, tuple[int, datetime]] = {}

    def save(self, token: str, user_id: int, expires_at: datetime) -> None:
        self.sessions[token] = (user_id, expires_at)

    def find_by_token(self, token: str) -> tuple[int, datetime] | None:
        return self.sessions.get(token)

    def delete_by_token(self, token: str) -> bool:
        if token in self.sessions:
            del self.sessions[token]
            return True
        return False


# === 备忘录现有测试 ===


def test_add_memo():
    """验证：可以成功添加备忘录"""
    repository = FakeMemoRepository()
    usecase = AddMemoUseCase(repository)

    memo = usecase.execute("新备忘录")

    assert memo.id == 1
    assert memo.content == "新备忘录"
    assert len(repository.find_all()) == 1


def test_list_memos():
    """验证：可以列出备忘录列表"""
    repository = FakeMemoRepository()

    # 预先添加备忘录
    add_usecase = AddMemoUseCase(repository)
    add_usecase.execute("备忘录 1")
    add_usecase.execute("备忘录 2")

    list_usecase = ListMemosUseCase(repository)
    memos = list_usecase.execute()

    assert len(memos) == 2
    assert memos[0].content == "备忘录 1"
    assert memos[1].content == "备忘录 2"


def test_edit_memo():
    """验证：可以编辑备忘录"""
    repository = FakeMemoRepository()
    add_usecase = AddMemoUseCase(repository)
    memo = add_usecase.execute("原始内容")

    edit_usecase = EditMemoUseCase(repository)
    updated = edit_usecase.execute(memo.id, "新内容")

    assert updated is not None
    assert updated.content == "新内容"


def test_edit_memo_not_found():
    """验证：编辑不存在的备忘录时应返回 None"""
    repository = FakeMemoRepository()
    edit_usecase = EditMemoUseCase(repository)

    result = edit_usecase.execute(9999, "内容")

    assert result is None


def test_delete_memo():
    """验证：可以成功删除备忘录"""
    repository = FakeMemoRepository()
    add_usecase = AddMemoUseCase(repository)
    memo = add_usecase.execute("待删除对象")

    delete_usecase = DeleteMemoUseCase(repository)
    result = delete_usecase.execute(memo.id)

    assert result is True
    assert len(repository.find_all()) == 0


def test_delete_memo_not_found():
    """验证：删除不存在的备忘录应返回 False"""
    repository = FakeMemoRepository()
    delete_usecase = DeleteMemoUseCase(repository)

    result = delete_usecase.execute(9999)

    assert result is False


# === 标签相关用例测试 (Tag UseCase Tests) ===


def test_add_tag_to_memo():
    """验证：可以给备忘录添加标签"""
    memo_repo = FakeMemoRepository()
    tag_repo = FakeTagRepository()

    # 准备数据：先在内存仓库保存一条备忘录
    memo = memo_repo.save(Memo.create("买东西"))
    usecase = AddTagToMemoUseCase(memo_repo, tag_repo)
    result = usecase.execute(memo.id, "重要")

    assert result is not None
    # 验证标签是否在标签库中被创建
    tag = tag_repo.find_by_name("重要")
    assert tag is not None
    # 验证备忘录与标签是否成功关联
    assert tag.id in memo_repo.memo_tags.get(memo.id, [])


def test_add_tag_to_nonexistent_memo():
    """验证：给不存在的备忘录添加标签应返回 None"""
    memo_repo = FakeMemoRepository()
    tag_repo = FakeTagRepository()

    usecase = AddTagToMemoUseCase(memo_repo, tag_repo)
    result = usecase.execute(9999, "重要")

    assert result is None


def test_remove_tag_from_memo():
    """验证：可以从备忘录移除标签"""
    memo_repo = FakeMemoRepository()
    tag_repo = FakeTagRepository()

    # 准备数据：创建备忘录和标签并建立关联
    memo = memo_repo.save(Memo.create("备忘录"))
    tag = tag_repo.save(Tag.create("重要"))
    memo_repo.add_tag(memo.id, tag.id)

    usecase = RemoveTagFromMemoUseCase(memo_repo, tag_repo)
    result = usecase.execute(memo.id, "重要")

    assert result is not None
    # 验证关联是否已解除
    assert tag.id not in memo_repo.memo_tags.get(memo.id, [])


def test_remove_tag_nonexistent_memo():
    """验证：从不存在的备忘录中移除标签应返回 None"""
    memo_repo = FakeMemoRepository()
    tag_repo = FakeTagRepository()

    usecase = RemoveTagFromMemoUseCase(memo_repo, tag_repo)
    result = usecase.execute(9999, "重要")

    assert result is None


def test_remove_nonexistent_tag():
    """验证：移除不存在的标签应返回 None"""
    memo_repo = FakeMemoRepository()
    tag_repo = FakeTagRepository()

    memo = memo_repo.save(Memo.create("备忘录"))
    usecase = RemoveTagFromMemoUseCase(memo_repo, tag_repo)
    result = usecase.execute(memo.id, "不存在的标签")

    assert result is None


def test_list_tags():
    """验证：可以获取全系统标签列表"""
    tag_repo = FakeTagRepository()
    tag_repo.save(Tag.create("重要"))
    tag_repo.save(Tag.create("日常"))

    usecase = ListTagsUseCase(tag_repo)
    tags = usecase.execute()

    assert len(tags) == 2
    names = [t.name for t in tags]
    assert "重要" in names
    assert "日常" in names


# === 认证用例测试 (Auth UseCase Tests) ===


def test_register_user():
    """验证：可以成功注册用户"""
    user_repo = FakeUserRepository()
    usecase = RegisterUserUseCase(user_repo)

    user = usecase.execute("testuser", "password123")

    assert user.id is not None
    assert user.username == "testuser"
    assert user.password_hash != "password123"  # 验证：存储的不是明文


def test_register_user_short_username():
    """验证：用户名过短时报错"""
    user_repo = FakeUserRepository()
    usecase = RegisterUserUseCase(user_repo)

    # 预期抛出 ValueError，提示信息包含 "3文字以上" (3个字符以上)
    with pytest.raises(ValueError, match="3文字以上"):
        usecase.execute("ab", "password123")


def test_register_user_short_password():
    """验证：密码过短时报错"""
    user_repo = FakeUserRepository()
    usecase = RegisterUserUseCase(user_repo)

    # 预期抛出 ValueError，提示信息包含 "8文字以上" (8个字符以上)
    with pytest.raises(ValueError, match="8文字以上"):
        usecase.execute("testuser", "short")


def test_register_user_duplicate():
    """验证：使用相同用户名重复注册时报错"""
    user_repo = FakeUserRepository()
    usecase = RegisterUserUseCase(user_repo)

    usecase.execute("testuser", "password123")
    with pytest.raises(ValueError, match="既に使われています"): # "已被占用"
        usecase.execute("testuser", "password456")


def test_login_success():
    """验证：使用正确的凭据可以成功登录"""
    user_repo = FakeUserRepository()
    session_repo = FakeSessionRepository()

    # 先注册用户
    register = RegisterUserUseCase(user_repo)
    register.execute("testuser", "password123")

    # 执行登录
    login = LoginUserUseCase(user_repo, session_repo)
    user, token = login.execute("testuser", "password123")

    assert user.username == "testuser"
    assert len(token) == 64  # hex(32字节) = 64个字符
    assert len(session_repo.sessions) == 1


def test_login_wrong_username():
    """验证：使用不存在的用户名登录时报错"""
    user_repo = FakeUserRepository()
    session_repo = FakeSessionRepository()

    login = LoginUserUseCase(user_repo, session_repo)
    with pytest.raises(ValueError, match="ユーザー名またはパスワードが間違っています"): # "用户名或密码错误"
        login.execute("nonexistent", "password123")


def test_login_wrong_password():
    """验证：使用错误的密码登录时报错"""
    user_repo = FakeUserRepository()
    session_repo = FakeSessionRepository()

    register = RegisterUserUseCase(user_repo)
    register.execute("testuser", "password123")

    login = LoginUserUseCase(user_repo, session_repo)
    with pytest.raises(ValueError, match="ユーザー名またはパスワードが間違っています"): # "用户名或密码错误"
        login.execute("testuser", "wrongpassword")


def test_login_error_message_is_ambiguous():
    """验证：登录错误信息具有模糊性（防御用户枚举攻击）

    确认“用户不存在”和“密码错误”返回的是完全相同的错误提示。
    """
    user_repo = FakeUserRepository()
    session_repo = FakeSessionRepository()

    register = RegisterUserUseCase(user_repo)
    register.execute("testuser", "password123")

    login = LoginUserUseCase(user_repo, session_repo)

    # 记录：用户名错误时的异常
    with pytest.raises(ValueError) as e1:
        login.execute("wronguser", "password123")

    # 记录：密码错误时的异常
    with pytest.raises(ValueError) as e2:
        login.execute("testuser", "wrongpassword")

    # 验证：两条错误信息必须完全一致
    assert str(e1.value) == str(e2.value)


def test_logout():
    """验证：登出操作会销毁会话（Session）"""
    user_repo = FakeUserRepository()
    session_repo = FakeSessionRepository()

    register = RegisterUserUseCase(user_repo)
    register.execute("testuser", "password123")

    login = LoginUserUseCase(user_repo, session_repo)
    _, token = login.execute("testuser", "password123")

    logout = LogoutUserUseCase(session_repo)
    result = logout.execute(token)

    assert result is True
    assert len(session_repo.sessions) == 0


# === 授权测试（备忘录所有权校验） ===


def test_list_memos_only_shows_own():
    """验证：仅在列表中显示属于自己的备忘录"""
    repository = FakeMemoRepository()
    add_usecase = AddMemoUseCase(repository)

    # 准备数据：Alice 有 2 条，Bob 有 1 条
    add_usecase.execute("Alice 的备忘录", user_id=1)
    add_usecase.execute("Bob 的备忘录", user_id=2)
    add_usecase.execute("Alice 的第 2 条", user_id=1)

    list_usecase = ListMemosUseCase(repository)

    # 验证 Alice 只能看到自己的 2 条
    alice_memos = list_usecase.execute(user_id=1)
    assert len(alice_memos) == 2

    # 验证 Bob 只能看到自己的 1 条
    bob_memos = list_usecase.execute(user_id=2)
    assert len(bob_memos) == 1


def test_edit_memo_by_other_user():
    """验证：无法编辑其他用户的备忘录"""
    repository = FakeMemoRepository()
    add_usecase = AddMemoUseCase(repository)
    memo = add_usecase.execute("Alice 的备忘录", user_id=1)

    edit_usecase = EditMemoUseCase(repository)
    # Bob 尝试编辑 Alice 的备忘录
    result = edit_usecase.execute(memo.id, "尝试改写", user_id=2)

    assert result is None  # 验证：无法编辑（返回 None）
    # 验证：数据库中的原始内容未被改变
    assert repository.find_by_id(memo.id).content == "Alice 的备忘录"


def test_edit_memo_by_owner():
    """验证：所有者可以编辑自己的备忘录"""
    repository = FakeMemoRepository()
    add_usecase = AddMemoUseCase(repository)
    memo = add_usecase.execute("Alice 的备忘录", user_id=1)

    edit_usecase = EditMemoUseCase(repository)
    result = edit_usecase.execute(memo.id, "更新后的内容", user_id=1)

    assert result is not None
    assert result.content == "更新后的内容"


def test_delete_memo_by_other_user():
    """验证：无法删除其他用户的备忘录"""
    repository = FakeMemoRepository()
    add_usecase = AddMemoUseCase(repository)
    memo = add_usecase.execute("Alice 的备忘录", user_id=1)

    delete_usecase = DeleteMemoUseCase(repository)
    # Bob 尝试删除 Alice 的备忘录
    result = delete_usecase.execute(memo.id, user_id=2)

    assert result is False # 验证：删除失败
    assert repository.find_by_id(memo.id) is not None  # 验证：数据依然存在


def test_add_tag_by_other_user():
    """验证：无法为其他用户的备忘录添加标签"""
    memo_repo = FakeMemoRepository()
    tag_repo = FakeTagRepository()
    add_usecase = AddMemoUseCase(memo_repo)
    memo = add_usecase.execute("Alice 的备忘录", user_id=1)

    tag_usecase = AddTagToMemoUseCase(memo_repo, tag_repo)
    # Bob 尝试给 Alice 的备忘录打标签
    result = tag_usecase.execute(memo.id, "重要", user_id=2)

    assert result is None


def test_remove_tag_by_other_user():
    """验证：无法从其他用户的备忘录中移除标签"""
    memo_repo = FakeMemoRepository()
    tag_repo = FakeTagRepository()
    # 准备数据：Alice 有一条带标签的备忘录
    memo = memo_repo.save(Memo.create("Alice 的备忘录", user_id=1))
    tag = tag_repo.save(Tag.create("重要"))
    memo_repo.add_tag(memo.id, tag.id)

    remove_usecase = RemoveTagFromMemoUseCase(memo_repo, tag_repo)
    # Bob 尝试移除该标签
    result = remove_usecase.execute(memo.id, "重要", user_id=2)

    assert result is None
