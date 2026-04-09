"""
Auth: 用于密码哈希化和校验的工具类。

【为什么要对密码进行哈希化？】
如果数据库（DB）以明文保存密码，一旦数据库泄露，所有用户的密码都会直接暴露。
通过哈希化处理，即使拿到数据也无法得知原始密码。

【为什么需要盐值（Salt）？】
如果不使用盐值，相同的密码（如 "password123"）始终会生成相同的哈希值。
攻击者可以预先制作常用密码的哈希对照表（彩虹表），从而实现通过哈希值反查原始密码。
加入盐值（随机字符串）混淆后，即使密码相同，每次生成的哈希值也会不同，从而保证安全。

【为什么生产环境下应该使用 bcrypt？】
SHA-256 是一种高速哈希函数。计算速度快意味着攻击者在进行暴力破解时，可以在短时间内尝试大量密码。
bcrypt 在设计上故意降低了运行速度，这使得暴力破解的成本剧增。
虽然在学习阶段使用 SHA-256 已经足够，但在实际的生产应用中，务必使用 bcrypt 或 Argon2。
"""

import hashlib
import secrets


def hash_password(password: str) -> str:
    """使用带盐值的 SHA-256 算法对密码进行哈希化。

    返回值格式: "盐值$哈希值"
    示例: "a1b2c3d4...$(SHA-256哈希值)"
    """
    salt = secrets.token_hex(16)  # 生成 32 位的随机盐值
    hash_value = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${hash_value}"


def verify_password(password: str, stored_hash: str) -> bool:
    """验证输入的密码是否与存储的哈希值一致。

    stored_hash 的格式应为 "盐值$哈希值"。
    使用相同的盐值对输入密码再次进行哈希，若结果一致则验证通过。
    """
    salt, hash_value = stored_hash.split("$", 1)
    return hashlib.sha256((salt + password).encode()).hexdigest() == hash_value