"""
auth 模块测试。
用于验证密码哈希的生成与校验功能是否正常运行。
"""

from auth import hash_password, verify_password


def test_hash_password_contains_salt_and_hash():
    """验证哈希结果是否包含“盐值$哈希值”的格式"""
    result = hash_password("password123")
    assert "$" in result
    salt, hash_value = result.split("$")
    assert len(salt) == 32   # 16 字节 = 32 位十六进制字符串
    assert len(hash_value) == 64  # SHA-256 = 64 位十六进制字符串


def test_verify_password_correct():
    """验证：输入正确的密码应通过校验"""
    hashed = hash_password("password123")
    assert verify_password("password123", hashed) is True


def test_verify_password_wrong():
    """验证：输入错误的密码不应通过校验"""
    hashed = hash_password("password123")
    assert verify_password("wrongpassword", hashed) is False


def test_same_password_different_hashes():
    """验证：即使密码相同，每次生成的哈希值也不同（盐值的效果）

    【教育要点：什么是盐值（Salt）？】
    如果没有盐值，相同的密码始终会生成相同的哈希值。
    攻击者可以预先制作“常用密码列表 → 哈希值列表”的对应表（彩虹表），
    从而实现从哈希值反查原始密码。

    通过在密码中混入盐值（随机字符串）后再进行哈希，
    即使密码相同，每次生成的哈希值也会完全不同，从而有效防御彩虹表攻击。
    """
    hash1 = hash_password("password123")
    hash2 = hash_password("password123")
    assert hash1 != hash2  # 因为盐值不同，所以结果也不同

    # 但两个不同的哈希值都应该能通过正确密码的验证
    assert verify_password("password123", hash1) is True
    assert verify_password("password123", hash2) is True


def test_empty_password():
    """验证：即使是空字符串密码，哈希和校验功能也能正常工作
    （注意：格式校验是 UseCase 层的职责，auth 层不负责拦截空密码）
    """
    hashed = hash_password("")
    assert verify_password("", hashed) is True
    assert verify_password("something", hashed) is False