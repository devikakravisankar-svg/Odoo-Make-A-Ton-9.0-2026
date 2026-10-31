from app.utils.validators import validate_password_strength

def test_password_length_validation():
    # Exactly 8 characters (Must fail since requirement is MORE than 8 characters)
    is_valid, msg = validate_password_strength("Abc!1234")
    assert is_valid is False
    assert "more than 8" in msg

    # Less than 8 characters
    is_valid, msg = validate_password_strength("Abc!1")
    assert is_valid is False
    assert "more than 8" in msg

    # 9 characters with upper, lower, special
    is_valid, msg = validate_password_strength("Abc!12345")
    assert is_valid is True


def test_password_uppercase_validation():
    # Missing uppercase
    is_valid, msg = validate_password_strength("abcdef!123")
    assert is_valid is False
    assert "uppercase" in msg


def test_password_lowercase_validation():
    # Missing lowercase
    is_valid, msg = validate_password_strength("ABCDEF!123")
    assert is_valid is False
    assert "lowercase" in msg


def test_password_special_char_validation():
    # Missing special character
    is_valid, msg = validate_password_strength("Abcdef1234")
    assert is_valid is False
    assert "special character" in msg


def test_password_valid():
    is_valid, msg = validate_password_strength("StrongPass@2026")
    assert is_valid is True
    assert msg == ""
