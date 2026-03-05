"""T1.1: Unit tests for utils/validators.py"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.validators import validate_username, validate_coin_symbol, validate_signal


# === validate_username ===

def test_v1_valid_username():
    assert validate_username("elonmusk") == "elonmusk"

def test_v2_strip_at_prefix():
    assert validate_username("@elonmusk") == "elonmusk"

def test_v3_strip_whitespace():
    assert validate_username(" @test ") == "test"

def test_v4_too_long_username():
    assert validate_username("a" * 16) is None

def test_v5_illegal_characters():
    assert validate_username("user!name") is None

def test_v6_empty_string():
    assert validate_username("") is None

def test_v_underscore_allowed():
    assert validate_username("test_user") == "test_user"

def test_v_digits_allowed():
    assert validate_username("user123") == "user123"

def test_v_profile_url():
    assert validate_username("https://x.com/elonmusk") == "elonmusk"

def test_v_status_url():
    assert validate_username("https://twitter.com/elonmusk/status/123") == "elonmusk"


# === validate_coin_symbol ===

def test_v7_valid_coin():
    assert validate_coin_symbol("BTC") == "BTC"

def test_v8_lowercase_to_upper():
    assert validate_coin_symbol("eth") == "ETH"

def test_v9_invalid_coin():
    assert validate_coin_symbol("BTC!!") is None

def test_v_coin_with_digits():
    assert validate_coin_symbol("1inch") == "1INCH"

def test_v_coin_empty():
    assert validate_coin_symbol("") is None


# === validate_signal ===

def test_v10_signal_long():
    assert validate_signal("long") == "long"

def test_v11_signal_short_uppercase():
    assert validate_signal("SHORT") == "short"

def test_v12_signal_invalid():
    assert validate_signal("buy") is None

def test_v_signal_neutral():
    assert validate_signal("neutral") == "neutral"

def test_v_signal_with_spaces():
    assert validate_signal(" long ") == "long"
