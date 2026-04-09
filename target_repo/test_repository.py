"""
Repository 层的测试。
验证 SQLiteMemoRepository / SqliteTagRepository / SqliteUserRepository /
SqliteSessionRepository 是否正确工作。
测试使用临时数据库。
"""

import os
import tempfile
from datetime import datetime, timedelta

import pytest

from auth import hash_password
from entity import Memo, Tag, User
from repository import (
    SqliteMemoRepository,
    SqliteSessionRepository,
    SqliteTagRepository,
    SqliteUserRepository,
)


@pytest.fixture
def db_path():
    """创建测试用的临时数据库路径，测试完成后删除"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def repository(db_path):
    """备忘录存储库"""
    return SqliteMemoRepository(db_path=db_path)


@pytest.fixture
def tag_repository(db_path):
    """标签存储库（共享同一个数据库）"""
    # 因为MemoRepository需要先创建表，所以先初始化
    SqliteMemoRepository(db_path=db_path)
    return SqliteTagRepository(db_path=db_path)


# === 备忘录基础测试 ===


def test_save_and_find_all(repository):
    """保存的备忘录可以通过列表获取"""
    memo = Memo.create("测试备忘录")
    saved = repository.save(memo)

    assert saved.id is not None  # 已分配ID
    assert saved.content == "测试备忘录"

    all_memos = repository.find_all()
    assert len(all_memos) == 1
    assert all_memos[0].content == "测试备忘录"


def test_find_by_id(repository):
    """可以通过ID获取特定备忘录"""
    memo = Memo.create("搜索目标")
    saved = repository.save(memo)

    found = repository.find_by_id(saved.id)
    assert found is not None
    assert found.content == "搜索目标"


def test_find_by_id_not_found(repository):
    """不存在的ID返回None"""
    found = repository.find_by_id(9999)
    assert found is None


def test_update(repository):
    """可以更新备忘录"""
    memo = Memo.create("原始内容")
    saved = repository.save(memo)

    updated_memo = saved.update_content("新内容")
    result = repository.update(updated_memo)
    assert result is True

    found = repository.find_by_id(saved.id)
    assert found.content == "新内容"


def test_delete(repository):
    """可以删除备忘录"""
    memo = Memo.create("删除目标")
    saved = repository.save(memo)

    result = repository.delete(saved.id)
    assert result is True

    found = repository.find_by_id(saved.id)
    assert found is None


def test_delete_not_found(repository):
    """删除不存在的ID返回False"""
    result = repository.delete(9999)
    assert result is False


# === 标签存储库测试 ===


def test_tag_save_and_find(db_path):
    """可以保存标签并通过名称搜索"""
    memo_repo = SqliteMemoRepository(db_path=db_path)
    tag_repo = SqliteTagRepository(db_path=db_path)

    tag = Tag.create("重要")
    saved = tag_repo.save(tag)

    assert saved.id is not None
    assert saved.name == "重要"

    found = tag_repo.find_by_name("重要")
    assert found is not None
    assert found.name == "重要"


def test_tag_find_by_name_not_found(db_path):
    """不存在的标签返回None"""
    SqliteMemoRepository(db_path=db_path)
    tag_repo = SqliteTagRepository(db_path=db_path)

    found = tag_repo.find_by_name("不存在")
    assert found is None


def test_tag_find_or_create(db_path):
    """find_or_create 返回现有标签或创建新标签"""
    SqliteMemoRepository(db_path=db_path)
    tag_repo = SqliteTagRepository(db_path=db_path)

    # 1回目: 新規作成
    tag1 = tag_repo.find_or_create("重要")
    assert tag1.id is not None

    # 第二次：返回已存在的
    tag2 = tag_repo.find_or_create("重要")
    assert tag2.id == tag1.id


def test_tag_find_all(db_path):
    """可以获取所有标签列表"""
    SqliteMemoRepository(db_path=db_path)
    tag_repo = SqliteTagRepository(db_path=db_path)

    tag_repo.save(Tag.create("重要"))
    tag_repo.save(Tag.create("日常"))

    tags = tag_repo.find_all()
    assert len(tags) == 2
    names = [t.name for t in tags]
    assert "重要" in names
    assert "日常" in names


# === 备忘录+标签关联测试 ===


def test_add_tag_to_memo(db_path):
    """可以给备忘录关联标签"""
    memo_repo = SqliteMemoRepository(db_path=db_path)
    tag_repo = SqliteTagRepository(db_path=db_path)

    memo = memo_repo.save(Memo.create("购物清单"))
    tag = tag_repo.save(Tag.create("日常"))

    result = memo_repo.add_tag(memo.id, tag.id)
    assert result is True

    # 可以获取带标签的
    found = memo_repo.find_by_id(memo.id)
    assert len(found.tags) == 1
    assert found.tags[0].name == "日常"


def test_add_duplicate_tag_to_memo(db_path):
    """重复关联同一标签不会报错"""
    memo_repo = SqliteMemoRepository(db_path=db_path)
    tag_repo = SqliteTagRepository(db_path=db_path)

    memo = memo_repo.save(Memo.create("备忘录"))
    tag = tag_repo.save(Tag.create("重要"))

    memo_repo.add_tag(memo.id, tag.id)
    result = memo_repo.add_tag(memo.id, tag.id)  # 2回目
    assert result is False  # 已关联


def test_remove_tag_from_memo(db_path):
    """可以从备忘录移除标签"""
    memo_repo = SqliteMemoRepository(db_path=db_path)
    tag_repo = SqliteTagRepository(db_path=db_path)

    memo = memo_repo.save(Memo.create("备忘录"))
    tag = tag_repo.save(Tag.create("重要"))

    memo_repo.add_tag(memo.id, tag.id)
    result = memo_repo.remove_tag(memo.id, tag.id)
    assert result is True

    found = memo_repo.find_by_id(memo.id)
    assert len(found.tags) == 0


def test_find_by_tag(db_path):
    """可以通过标签名搜索备忘录（JOIN查询）"""
    memo_repo = SqliteMemoRepository(db_path=db_path)
    tag_repo = SqliteTagRepository(db_path=db_path)

    memo1 = memo_repo.save(Memo.create("购物清单"))
    memo2 = memo_repo.save(Memo.create("工作备忘录"))
    memo3 = memo_repo.save(Memo.create("日记"))

    tag_important = tag_repo.save(Tag.create("重要"))
    tag_daily = tag_repo.save(Tag.create("日常"))

    memo_repo.add_tag(memo1.id, tag_daily.id)
    memo_repo.add_tag(memo1.id, tag_important.id)
    memo_repo.add_tag(memo2.id, tag_important.id)
    # memo3没有标签

    # 搜索"重要"标签 → memo1, memo2匹配
    results = memo_repo.find_by_tag("重要")
    assert len(results) == 2
    ids = [m.id for m in results]
    assert memo1.id in ids
    assert memo2.id in ids

    # 搜索"日常"标签 → 只有memo1
    results = memo_repo.find_by_tag("日常")
    assert len(results) == 1
    assert results[0].id == memo1.id

    # 不存在的标签→空结果
    results = memo_repo.find_by_tag("不存在")
    assert len(results) == 0


def test_find_all_with_tags(db_path):
    """find_all可以同时获取标签信息"""
    memo_repo = SqliteMemoRepository(db_path=db_path)
    tag_repo = SqliteTagRepository(db_path=db_path)

    memo = memo_repo.save(Memo.create("测试"))
    tag1 = tag_repo.save(Tag.create("重要"))
    tag2 = tag_repo.save(Tag.create("日常"))

    memo_repo.add_tag(memo.id, tag1.id)
    memo_repo.add_tag(memo.id, tag2.id)

    all_memos = memo_repo.find_all()
    assert len(all_memos) == 1
    assert len(all_memos[0].tags) == 2
    tag_names = [t.name for t in all_memos[0].tags]
    assert "重要" in tag_names
    assert "日常" in tag_names


def test_delete_memo_cascades_tags(db_path):
    """删除备忘录时标签关联也会被删除（级联删除）"""
    memo_repo = SqliteMemoRepository(db_path=db_path)
    tag_repo = SqliteTagRepository(db_path=db_path)

    memo = memo_repo.save(Memo.create("待删除备忘录"))
    tag = tag_repo.save(Tag.create("重要"))
    memo_repo.add_tag(memo.id, tag.id)

    memo_repo.delete(memo.id)

    # 标签本身保留（其他备忘录可能还要使用）
    found_tag = tag_repo.find_by_name("重要")
    assert found_tag is not None


# === 用户存储库测试 ===


def test_user_save_and_find(db_path):
    """可以保存用户并通过用户名搜索"""
    SqliteMemoRepository(db_path=db_path)  # 表初始化
    user_repo = SqliteUserRepository(db_path=db_path)

    user = User.create("测试用户", hash_password("password123"))
    saved = user_repo.save(user)

    assert saved.id is not None
    assert saved.username == "测试用户"

    found = user_repo.find_by_username("测试用户")
    assert found is not None
    assert found.username == "测试用户"
    assert found.id == saved.id


def test_user_find_by_id(db_path):
    """可以通过ID获取用户"""
    SqliteMemoRepository(db_path=db_path)
    user_repo = SqliteUserRepository(db_path=db_path)

    user = User.create("测试用户", hash_password("password123"))
    saved = user_repo.save(user)

    found = user_repo.find_by_id(saved.id)
    assert found is not None
    assert found.username == "测试用户"


def test_user_find_by_username_not_found(db_path):
    """不存在的用户名返回None"""
    SqliteMemoRepository(db_path=db_path)
    user_repo = SqliteUserRepository(db_path=db_path)

    found = user_repo.find_by_username("不存在")
    assert found is None


def test_user_duplicate_username(db_path):
    """尝试注册相同用户名会抛出ValueError"""
    SqliteMemoRepository(db_path=db_path)
    user_repo = SqliteUserRepository(db_path=db_path)

    user1 = User.create("测试用户", hash_password("pass1"))
    user_repo.save(user1)

    user2 = User.create("测试用户", hash_password("pass2"))
    with pytest.raises(ValueError, match="已被使用"):
        user_repo.save(user2)


def test_user_password_not_stored_as_plaintext(db_path):
    """确认密码没有以明文形式保存"""
    SqliteMemoRepository(db_path=db_path)
    user_repo = SqliteUserRepository(db_path=db_path)

    user = User.create("测试用户", hash_password("mypassword"))
    saved = user_repo.save(user)

    found = user_repo.find_by_username("测试用户")
    assert found.password_hash != "mypassword"  # 不是明文
    assert "$" in found.password_hash  # 盐值$哈希格式


# === 会话存储库测试 ===


def test_session_save_and_find(db_path):
    """可以保存会话并通过令牌搜索"""
    SqliteMemoRepository(db_path=db_path)
    user_repo = SqliteUserRepository(db_path=db_path)
    session_repo = SqliteSessionRepository(db_path=db_path)

    # 先创建用户
    user = user_repo.save(User.create("测试用户", hash_password("pass")))

    expires = datetime.now() + timedelta(days=7)
    session_repo.save("test_token_123", user.id, expires)

    result = session_repo.find_by_token("test_token_123")
    assert result is not None
    user_id, expires_at = result
    assert user_id == user.id


def test_session_find_not_found(db_path):
    """不存在的令牌返回None"""
    SqliteMemoRepository(db_path=db_path)
    session_repo = SqliteSessionRepository(db_path=db_path)

    result = session_repo.find_by_token("nonexistent_token")
    assert result is None


def test_session_delete(db_path):
    """可以删除会话（登出）"""
    SqliteMemoRepository(db_path=db_path)
    user_repo = SqliteUserRepository(db_path=db_path)
    session_repo = SqliteSessionRepository(db_path=db_path)

    user = user_repo.save(User.create("测试用户", hash_password("pass")))
    expires = datetime.now() + timedelta(days=7)
    session_repo.save("token_to_delete", user.id, expires)

    result = session_repo.delete_by_token("token_to_delete")
    assert result is True

    # 删除后无法找到
    assert session_repo.find_by_token("token_to_delete") is None


def test_session_delete_not_found(db_path):
    """删除不存在的令牌返回False"""
    SqliteMemoRepository(db_path=db_path)
    session_repo = SqliteSessionRepository(db_path=db_path)

    result = session_repo.delete_by_token("nonexistent")
    assert result is False


# === 备忘录 + 用户ID的测试 ===


def test_save_memo_with_user_id(db_path):
    """可以使用用户ID保存和获取备忘录"""
    memo_repo = SqliteMemoRepository(db_path=db_path)
    user_repo = SqliteUserRepository(db_path=db_path)

    user = user_repo.save(User.create("测试用户", hash_password("pass")))
    memo = memo_repo.save(Memo.create("用户的备忘录", user_id=user.id))

    found = memo_repo.find_by_id(memo.id)
    assert found is not None
    assert found.user_id == user.id


def test_find_all_filters_by_user_id(db_path):
    """find_all(user_id)只获取自己的备忘录"""
    memo_repo = SqliteMemoRepository(db_path=db_path)
    user_repo = SqliteUserRepository(db_path=db_path)

    user1 = user_repo.save(User.create("alice", hash_password("pass1")))
    user2 = user_repo.save(User.create("bob", hash_password("pass2")))

    memo_repo.save(Memo.create("Alice的备忘录1", user_id=user1.id))
    memo_repo.save(Memo.create("Alice的备忘录2", user_id=user1.id))
    memo_repo.save(Memo.create("Bob的备忘录", user_id=user2.id))

    # 只获取Alice的备忘录
    alice_memos = memo_repo.find_all(user_id=user1.id)
    assert len(alice_memos) == 2
    assert all(m.user_id == user1.id for m in alice_memos)

    # 只获取Bob的备忘录
    bob_memos = memo_repo.find_all(user_id=user2.id)
    assert len(bob_memos) == 1
    assert bob_memos[0].content == "Bob的备忘录"

    # 不指定user_id → 获取所有备忘录
    all_memos = memo_repo.find_all()
    assert len(all_memos) == 3


def test_find_by_tag_filters_by_user_id(db_path):
    """find_by_tag(tag, user_id)只搜索自己的备忘录"""
    memo_repo = SqliteMemoRepository(db_path=db_path)
    tag_repo = SqliteTagRepository(db_path=db_path)
    user_repo = SqliteUserRepository(db_path=db_path)

    user1 = user_repo.save(User.create("alice", hash_password("pass1")))
    user2 = user_repo.save(User.create("bob", hash_password("pass2")))

    memo1 = memo_repo.save(Memo.create("Alice的重要备忘录", user_id=user1.id))
    memo2 = memo_repo.save(Memo.create("Bob的重要备忘录", user_id=user2.id))

    tag = tag_repo.save(Tag.create("重要"))
    memo_repo.add_tag(memo1.id, tag.id)
    memo_repo.add_tag(memo2.id, tag.id)

    # 只搜索Alice的"重要"标签备忘录
    results = memo_repo.find_by_tag("重要", user_id=user1.id)
    assert len(results) == 1
    assert results[0].content == "Alice的重要备忘录"

    # 不指定user_id → 搜索所有用户的"重要"备忘录
    results = memo_repo.find_by_tag("重要")
    assert len(results) == 2
