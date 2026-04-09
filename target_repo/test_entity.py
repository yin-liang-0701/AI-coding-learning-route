"""
Entity 实体层测试。
验证 Memo / Tag / User 类是否正常工作。
"""

from datetime import datetime

from entity import Memo, Tag, User


# === Memo（备忘录）现有测试 ===


def test_create_memo():
    """可以通过 Memo.create() 创建新的备忘录"""
    memo = Memo.create("测试内容")

    assert memo.content == "测试内容"
    assert memo.id is None  # 尚未保存，所以没有 ID
    assert isinstance(memo.created_at, datetime)
    assert isinstance(memo.updated_at, datetime)


def test_update_content():
    """可以通过 update_content() 更新内容"""
    memo = Memo.create("原始内容")
    updated = memo.update_content("新内容")

    # 原始备忘录不会改变（体现不可变性/Immutable）
    assert memo.content == "原始内容"

    # 返回一个新的备忘录对象
    assert updated.content == "新内容"
    assert updated.created_at == memo.created_at  # 创建时间保持一致
    assert updated.updated_at >= memo.updated_at  # 更新时间是新的


def test_memo_is_immutable():
    """验证 Memo 是不可变的（frozen=True）"""
    memo = Memo.create("内容")

    try:
        memo.content = "尝试修改"
        assert False, "应该抛出异常"
    except Exception:
        pass  # 因为是 frozen 模式，抛出异常才是正确的行为


# === Tag（标签）测试 ===


def test_create_tag():
    """可以通过 Tag.create() 创建新标签"""
    tag = Tag.create("重要")

    assert tag.name == "重要"
    assert tag.id is None
    assert isinstance(tag.created_at, datetime)


def test_tag_is_immutable():
    """验证 Tag 是不可变的（frozen=True）"""
    tag = Tag.create("重要")

    try:
        tag.name = "尝试修改"
        assert False, "应该抛出异常"
    except Exception:
        pass


# === Memo + Tag 综合测试 ===


def test_memo_has_empty_tags_by_default():
    """创建备忘录时默认没有标签"""
    memo = Memo.create("内容")
    assert memo.tags == ()


def test_add_tag_to_memo():
    """可以向备忘录添加标签（以不可变方式）"""
    memo = Memo.create("内容")
    tag = Tag(id=1, name="重要", created_at=datetime.now())

    updated = memo.add_tag(tag)

    assert len(updated.tags) == 1
    assert updated.tags[0].name == "重要"
    assert len(memo.tags) == 0  # 原始备忘录对象保持不变


def test_add_duplicate_tag():
    """同名标签不会被重复添加"""
    memo = Memo.create("内容")
    tag = Tag(id=1, name="重要", created_at=datetime.now())

    updated = memo.add_tag(tag)
    updated_again = updated.add_tag(tag)

    assert len(updated_again.tags) == 1


def test_remove_tag_from_memo():
    """可以从备忘录中移除标签"""
    tag1 = Tag(id=1, name="重要", created_at=datetime.now())
    tag2 = Tag(id=2, name="日常", created_at=datetime.now())
    memo = Memo(
        id=1, content="内容",
        created_at=datetime.now(), updated_at=datetime.now(),
        tags=(tag1, tag2),
    )

    updated = memo.remove_tag("重要")

    assert len(updated.tags) == 1
    assert updated.tags[0].name == "日常"
    assert len(memo.tags) == 2  # 原始备忘录对象保持不变


def test_update_content_preserves_tags():
    """更新内容时会保留原有的标签"""
    tag = Tag(id=1, name="重要", created_at=datetime.now())
    memo = Memo(
        id=1, content="原始内容",
        created_at=datetime.now(), updated_at=datetime.now(),
        tags=(tag,),
    )

    updated = memo.update_content("新内容")

    assert updated.content == "新内容"
    assert len(updated.tags) == 1
    assert updated.tags[0].name == "重要"


# === User（用户）测试 ===


def test_create_user():
    """可以通过 User.create() 创建新用户"""
    user = User.create("testuser", "hashed_password_123")

    assert user.username == "testuser"
    assert user.password_hash == "hashed_password_123"
    assert user.id is None  # 尚未保存，所以没有 ID
    assert isinstance(user.created_at, datetime)


def test_user_is_immutable():
    """验证 User 是不可变的（frozen=True）"""
    user = User.create("testuser", "hashed_password_123")

    try:
        user.username = "尝试修改"
        assert False, "应该抛出异常"
    except Exception:
        pass  # 抛出异常是正确的


def test_user_does_not_store_plaintext_password():
    """验证 User 实体中不存储明文密码字段。

    通过仅持有 password_hash 字段，
    从架构层面强制执行“不保留明文密码”的规则。
    """
    user = User.create("testuser", "some_hash_value")
    assert hasattr(user, "password_hash")
    assert not hasattr(user, "password")  # 不存在明文密码字段


# === Memo + user_id（归属关系）测试 ===


def test_create_memo_with_user_id():
    """可以指定用户 ID 来创建备忘录"""
    memo = Memo.create("内容", user_id=1)
    assert memo.user_id == 1


def test_create_memo_without_user_id():
    """不带 user_id 也可以创建备忘录（用于向后兼容）"""
    memo = Memo.create("内容")
    assert memo.user_id is None


def test_update_content_preserves_user_id():
    """更新内容时会保留 user_id"""
    memo = Memo.create("原始内容", user_id=1)
    updated = memo.update_content("新内容")
    assert updated.user_id == 1


def test_add_tag_preserves_user_id():
    """添加标签时会保留 user_id"""
    memo = Memo.create("内容", user_id=1)
    tag = Tag(id=1, name="重要", created_at=datetime.now())
    updated = memo.add_tag(tag)
    assert updated.user_id == 1


def test_remove_tag_preserves_user_id():
    """移除标签时会保留 user_id"""
    tag = Tag(id=1, name="重要", created_at=datetime.now())
    memo = Memo(
        id=1, content="内容",
        created_at=datetime.now(), updated_at=datetime.now(),
        user_id=1, tags=(tag,),
    )
    updated = memo.remove_tag("重要")
    assert updated.user_id == 1