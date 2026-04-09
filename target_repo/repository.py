"""
Repository: 将数据的保存与获取抽象化。
隐藏“数据保存在哪里”的具体细节。这样无论是更换为 SQLite、PostgreSQL 还是文件存储，都可以直接替换。

【步骤 5 学习的数据库设计要点】
- 规范化（Normalization）：将标签分离到独立表（多对多关系）。
- 索引（Index）：提高搜索速度的机制。
- JOIN（连接）：结合多个表的数据进行查询。

【步骤 6 学习的认证要点】
- users 表：保存用户信息和密码哈希。
- sessions 表：管理登录会话。
- user_id：记录备忘录的所有者，用于授权（访问控制）。
- 架构版本管理（Schema Versioning）：在不破坏现有数据的情况下修改表结构的方法。
"""

import sqlite3
from abc import ABC, abstractmethod # 抽象基类
from datetime import datetime

from entity import Memo, Tag, User

# --- 抽象存储库（接口） ---


class MemoRepository(ABC):
    """备忘录保存和获取的接口"""

    @abstractmethod
    def save(self, memo: Memo) -> Memo:
        """保存备忘录并返回带有ID的Memo"""
        # pass 是一个空操作占位符。
        # 由于这是一个在抽象基类（继承了 ABC 的类）里的方法，它只负责定义“契约（Contract）”，不负责实现逻辑。pass 告诉 Python：“这里什么都不用做，逻辑留给子类去写”。
        pass

    @abstractmethod
    def find_all(self, user_id: int | None = None) -> list[Memo]:
        """获取备忘录（指定user_id时只获取该用户的备忘录）"""
        pass

    @abstractmethod
    def find_by_id(self, memo_id: int) -> Memo | None:
        """通过ID获取备忘录。不存在则返回None"""
        pass

    @abstractmethod
    def find_by_tag(self, tag_name: str, user_id: int | None = None) -> list[Memo]:
        """通过标签名搜索备忘录（指定user_id时只搜索该用户的备忘录）"""
        pass

    @abstractmethod
    def update(self, memo: Memo) -> bool:
        """更新备忘录。成功返回True"""
        pass

    @abstractmethod
    def delete(self, memo_id: int) -> bool:
        """删除备忘录。成功返回True"""
        pass

    @abstractmethod
    def add_tag(self, memo_id: int, tag_id: int) -> bool:
        """为备忘录关联标签"""
        pass

    @abstractmethod
    def remove_tag(self, memo_id: int, tag_id: int) -> bool:
        """从备忘录移除标签"""
        pass


class TagRepository(ABC):
    """标签保存和获取的接口"""

    @abstractmethod
    def save(self, tag: Tag) -> Tag:
        """保存标签并返回带有ID的Tag"""
        pass

    @abstractmethod
    def find_by_name(self, name: str) -> Tag | None:
        """通过名称获取标签。不存在则返回None"""
        pass

    @abstractmethod
    def find_all(self) -> list[Tag]:
        """获取所有标签"""
        pass

    @abstractmethod
    def find_or_create(self, name: str) -> Tag:
        """通过名称查找标签，不存在则创建并返回"""
        pass


class UserRepository(ABC):
    """用户保存和获取的接口

    【教育要点: 为什么需要 find_by_username 和 find_by_id 两者？】
    - find_by_username: 用于登录时（用户输入的是用户名）
    - find_by_id: 用于从会话恢复用户时（数据库保存的是ID）
    """

    @abstractmethod
    def save(self, user: User) -> User:
        """保存用户并返回带有ID的User。
        用户名重复时抛出ValueError。
        """
        pass

    @abstractmethod
    def find_by_username(self, username: str) -> User | None:
        """通过用户名获取用户。不存在则返回None"""
        pass

    @abstractmethod
    def find_by_id(self, user_id: int) -> User | None:
        """通过ID获取用户。不存在则返回None"""
        pass


class SessionRepository(ABC):
    """会话（登录状态）管理的接口

    【教育要点: 什么是会话？】
    Web应用通常使用 Cookie + 服务器端会话存储（Redis等）来管理。
    CLI应用则：
    1. 登录成功 → 生成随机令牌
    2. 将令牌保存到本地文件（相当于浏览器的Cookie）
    3. 后续命令从文件读取令牌，通过数据库验证（相当于服务器端验证）
    """

    @abstractmethod
    def save(self, token: str, user_id: int, expires_at: datetime) -> None:
        """保存会话令牌"""
        pass

    @abstractmethod
    def find_by_token(self, token: str) -> tuple[int, datetime] | None:
        """从令牌返回 (user_id, expires_at)。不存在则返回None"""
        pass

    @abstractmethod
    def delete_by_token(self, token: str) -> bool:
        """通过令牌删除会话。成功返回True"""
        pass


# --- SQLite実装 ---


class SqliteMemoRepository(MemoRepository):
    """使用SQLite的备忘录存储库实现"""

    def __init__(self, db_path: str = "memo.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """通过模式版本管理的迁移

        【教育要点: 为什么需要版本管理？】
        CREATE TABLE IF NOT EXISTS 只能用于创建新表。
        不能用于添加列（ALTER TABLE）。
        生产环境中会使用Alembic或Prisma等迁移工具，
        但学习项目中使用这个手动版本管理来理解原理。
        """
        conn = sqlite3.connect(self.db_path)

        # 管理模式的版本表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY
            )
        """)

        current_version = conn.execute(
            "SELECT MAX(version) FROM schema_version"
        ).fetchone()[0] or 0

        # v0 → v1: 初始表（步骤5之前的结构）
        if current_version < 1:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memo_tags (
                    memo_id INTEGER NOT NULL REFERENCES memos(id) ON DELETE CASCADE,
                    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
                    PRIMARY KEY (memo_id, tag_id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memo_tags_tag_id
                ON memo_tags(tag_id)
            """)
            conn.execute("INSERT INTO schema_version VALUES (1)")

        # v1 → v2: 添加用户认证功能（步骤6）
        if current_version < 2:
            # 用户表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            # 会话表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
            """)
            # 为现有的memos表添加user_id列
            # ALTER TABLE 没有 IF NOT EXISTS，所以用 try-except 处理
            try:
                conn.execute(
                    "ALTER TABLE memos ADD COLUMN user_id INTEGER REFERENCES users(id)"
                )
            except sqlite3.OperationalError:
                pass  # 已添加
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memos_user_id ON memos(user_id)
            """)
            conn.execute("INSERT INTO schema_version VALUES (2)")

        conn.execute("PRAGMA foreign_keys = ON")
        conn.commit()
        conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        """获取连接（启用外键约束）"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _get_tags_for_memo(self, conn: sqlite3.Connection, memo_id: int) -> tuple[Tag, ...]:
        """获取备忘录关联的标签"""
        rows = conn.execute("""
            SELECT t.id, t.name, t.created_at
            FROM tags t
            JOIN memo_tags mt ON t.id = mt.tag_id
            WHERE mt.memo_id = ?
            ORDER BY t.name
        """, (memo_id,)).fetchall()
        return tuple(
            Tag(id=row[0], name=row[1], created_at=datetime.fromisoformat(row[2]))
            for row in rows
        )

    def _row_to_memo(self, row: tuple, tags: tuple[Tag, ...] = ()) -> Memo:
        """将数据库行转换为Memo实体"""
        memo_id, content, created_at, updated_at, user_id = row
        return Memo(
            id=memo_id,
            content=content,
            created_at=datetime.fromisoformat(created_at),
            updated_at=datetime.fromisoformat(updated_at),
            user_id=user_id,
            tags=tags,
        )

    def save(self, memo: Memo) -> Memo:
        conn = self._get_conn()
        cursor = conn.execute(
            "INSERT INTO memos (content, created_at, updated_at, user_id) VALUES (?, ?, ?, ?)",
            (memo.content, memo.created_at.isoformat(), memo.updated_at.isoformat(), memo.user_id),
        )
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return Memo( # 返回带有数据库分配ID的新Memo对象
            id=new_id,
            content=memo.content,
            created_at=memo.created_at,
            updated_at=memo.updated_at,
            user_id=memo.user_id,
        )

    def find_all(self, user_id: int | None = None) -> list[Memo]:
        """获取备忘录（包含标签信息）

        【避免N+1问题的设计】
        糟糕方法: 获取备忘录列表 → 为每个备忘录单独获取标签（N+1次查询）
        好方法: 获取备忘录列表 → 一次性获取所有标签关联 → 用Python组装

        【授权: 基于user_id的过滤】
        指定user_id时，只返回该用户的备忘录。
        其他用户的备忘录不可见 = 最小权限原则。
        """
        conn = self._get_conn()

        if user_id is not None:
            memo_rows = conn.execute(
                "SELECT id, content, created_at, updated_at, user_id FROM memos WHERE user_id = ? ORDER BY id",
                (user_id,),
            ).fetchall()
        else:
            memo_rows = conn.execute(
                "SELECT id, content, created_at, updated_at, user_id FROM memos ORDER BY id"
            ).fetchall()

        # 批量获取已获取备忘录ID列表对应的标签
        if memo_rows:
            memo_ids = [row[0] for row in memo_rows]
            placeholders = ",".join("?" * len(memo_ids))
            tag_rows = conn.execute(f"""
                SELECT mt.memo_id, t.id, t.name, t.created_at
                FROM memo_tags mt
                JOIN tags t ON mt.tag_id = t.id
                WHERE mt.memo_id IN ({placeholders})
                ORDER BY t.name
            """, memo_ids).fetchall()
        else:
            tag_rows = []
        conn.close()

        # 按备忘录ID对标签进行分组
        tags_by_memo: dict[int, list[Tag]] = {}
        for memo_id_val, tag_id, tag_name, tag_created in tag_rows:
            tag = Tag(id=tag_id, name=tag_name, created_at=datetime.fromisoformat(tag_created))
            tags_by_memo.setdefault(memo_id_val, []).append(tag)

        return [
            self._row_to_memo(row, tuple(tags_by_memo.get(row[0], [])))
            for row in memo_rows
        ]

    def find_by_id(self, memo_id: int) -> Memo | None:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT id, content, created_at, updated_at, user_id FROM memos WHERE id = ?",
            (memo_id,),
        ).fetchone()
        if row is None:
            conn.close()
            return None
        tags = self._get_tags_for_memo(conn, memo_id)
        conn.close()
        return self._row_to_memo(row, tags)

    def find_by_tag(self, tag_name: str, user_id: int | None = None) -> list[Memo]:
        """通过标签名搜索备忘录

        【JOIN查询实践】
        连接三个表来获取指定标签的备忘录。
        memo_tags的tag_id有索引所以速度很快。
        """
        conn = self._get_conn()

        if user_id is not None:
            memo_rows = conn.execute("""
                SELECT DISTINCT m.id, m.content, m.created_at, m.updated_at, m.user_id
                FROM memos m
                JOIN memo_tags mt ON m.id = mt.memo_id
                JOIN tags t ON mt.tag_id = t.id
                WHERE t.name = ? AND m.user_id = ?
                ORDER BY m.id
            """, (tag_name, user_id)).fetchall()
        else:
            memo_rows = conn.execute("""
                SELECT DISTINCT m.id, m.content, m.created_at, m.updated_at, m.user_id
                FROM memos m
                JOIN memo_tags mt ON m.id = mt.memo_id
                JOIN tags t ON mt.tag_id = t.id
                WHERE t.name = ?
                ORDER BY m.id
            """, (tag_name,)).fetchall()

        memos = []
        for row in memo_rows:
            tags = self._get_tags_for_memo(conn, row[0])
            memos.append(self._row_to_memo(row, tags))
        conn.close()
        return memos

    def update(self, memo: Memo) -> bool:
        if memo.id is None:
            return False
        conn = self._get_conn()
        cursor = conn.execute(
            "UPDATE memos SET content = ?, updated_at = ? WHERE id = ?",
            (memo.content, memo.updated_at.isoformat(), memo.id),
        )
        conn.commit()
        conn.close()
        return cursor.rowcount > 0

    def delete(self, memo_id: int) -> bool:
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM memos WHERE id = ?", (memo_id,))
        conn.commit()
        conn.close()
        return cursor.rowcount > 0

    def add_tag(self, memo_id: int, tag_id: int) -> bool:
        """为备忘录关联标签（向中间表INSERT）"""
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO memo_tags (memo_id, tag_id) VALUES (?, ?)",
                (memo_id, tag_id),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            # 已关联或ID不存在
            return False
        finally:
            conn.close()

    def remove_tag(self, memo_id: int, tag_id: int) -> bool:
        """从备忘录移除标签（从中间表DELETE）"""
        conn = self._get_conn()
        cursor = conn.execute(
            "DELETE FROM memo_tags WHERE memo_id = ? AND tag_id = ?",
            (memo_id, tag_id),
        )
        conn.commit()
        conn.close()
        return cursor.rowcount > 0


class SqliteTagRepository(TagRepository):
    """使用SQLite的标签存储库实现"""

    def __init__(self, db_path: str = "memo.db"):
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _row_to_tag(self, row: tuple) -> Tag:
        tag_id, name, created_at = row
        return Tag(id=tag_id, name=name, created_at=datetime.fromisoformat(created_at))

    def save(self, tag: Tag) -> Tag:
        conn = self._get_conn()
        cursor = conn.execute(
            "INSERT INTO tags (name, created_at) VALUES (?, ?)",
            (tag.name, tag.created_at.isoformat()),
        )
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return Tag(id=new_id, name=tag.name, created_at=tag.created_at)

    def find_by_name(self, name: str) -> Tag | None:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT id, name, created_at FROM tags WHERE name = ?",
            (name,),
        ).fetchone()
        conn.close()
        if row is None:
            return None
        return self._row_to_tag(row)

    def find_all(self) -> list[Tag]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, name, created_at FROM tags ORDER BY name"
        ).fetchall()
        conn.close()
        return [self._row_to_tag(row) for row in rows]

    def find_or_create(self, name: str) -> Tag:
        """查找标签，不存在则创建"""
        existing = self.find_by_name(name)
        if existing is not None:
            return existing
        return self.save(Tag.create(name))


class SqliteUserRepository(UserRepository):
    """使用 SQLite 实现的用户仓库"""

    def __init__(self, db_path: str = "memo.db"):
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接（开启外键约束）"""
        conn = sqlite3.connect(self.db_path)
        # 显式开启外键限制，确保数据引用一致性
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _row_to_user(self, row: tuple) -> User:
        """将数据库查询到的行（tuple）映射为 User 实体对象"""
        user_id, username, password_hash, created_at = row
        return User(
            id=user_id,
            username=username,
            password_hash=password_hash,
            # 将存储的字符串格式时间转换回 datetime 对象
            created_at=datetime.fromisoformat(created_at),
        )

    def save(self, user: User) -> User:
        """保存用户数据"""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                (user.username, user.password_hash, user.created_at.isoformat()),
            )
            conn.commit()
            # 返回带有数据库自增 ID 的新 User 对象
            return User(
                id=cursor.lastrowid,
                username=user.username,
                password_hash=user.password_hash,
                created_at=user.created_at,
            )
        except sqlite3.IntegrityError:
            # 当用户名违反 UNIQUE 约束时触发
            raise ValueError(f"用户名 '{user.username}' 已被占用")
        finally:
            conn.close()

    def find_by_username(self, username: str) -> User | None:
        """通过用户名查找用户"""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT id, username, password_hash, created_at FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        conn.close()
        if row is None:
            return None
        return self._row_to_user(row)

    def find_by_id(self, user_id: int) -> User | None:
        """通过 ID 查找用户"""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT id, username, password_hash, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        conn.close()
        if row is None:
            return None
        return self._row_to_user(row)


class SqliteSessionRepository(SessionRepository):
    """
    基于 SQLite 的会话仓库（Session Repository）实现。

    【教学要点：为什么要在数据库中也进行会话管理？】
    如果仅仅是将 Token（令牌）保存在本地文件中，一旦 Token 被伪造，系统将无法察觉。
    通过在数据库（DB）侧同步持有 Token 并进行比对，可以实现：
    - 登出时：在服务器端（数据库）同步注销会话，使其失效。
    - 有效期校验：可以检查会话是否已过期。
    - 安全管理：管理员可以主动删除可疑的会话记录。

    这与 Web 应用中“Cookie + 服务端会话（Server-side Session）”的原理完全一致。
    """

    def __init__(self, db_path: str = "memo.db"):
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def save(self, token: str, user_id: int, expires_at: datetime) -> None:
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token, user_id, datetime.now().isoformat(), expires_at.isoformat()),
        )
        conn.commit()
        conn.close()

    def find_by_token(self, token: str) -> tuple[int, datetime] | None:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT user_id, expires_at FROM sessions WHERE token = ?",
            (token,),
        ).fetchone()
        conn.close()
        if row is None:
            return None
        return (row[0], datetime.fromisoformat(row[1]))

    def delete_by_token(self, token: str) -> bool:
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        conn.close()
        return cursor.rowcount > 0
