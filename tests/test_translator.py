"""T1.3: Unit tests for i18n/translator.py"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from i18n.translator import get_text
from i18n.en import STRINGS as EN
from i18n.zh import STRINGS as ZH


def test_i1_chinese_help_text():
    result = get_text("help_text", "zh")
    assert "CryptoEye Agent" in result

def test_i2_english_help_text():
    result = get_text("help_text", "en")
    assert "CryptoEye Agent" in result

def test_i3_dynamic_params():
    result = get_text("monitor_added", "zh", username="testuser")
    assert "@testuser" in result

def test_i3b_dynamic_params_english():
    result = get_text("monitor_added", "en", username="testuser")
    assert "@testuser" in result

def test_i4_fallback_to_english():
    result = get_text("help_text", "fr")
    assert "CryptoEye Agent" in result

def test_i5_nonexistent_key():
    result = get_text("this_key_does_not_exist", "zh")
    assert result == "this_key_does_not_exist"

def test_i6_all_keys_present_in_both_languages():
    """Verify en.py and zh.py have the exact same set of keys."""
    en_keys = set(EN.keys())
    zh_keys = set(ZH.keys())
    missing_in_zh = en_keys - zh_keys
    missing_in_en = zh_keys - en_keys
    assert not missing_in_zh, f"Keys in EN but missing in ZH: {missing_in_zh}"
    assert not missing_in_en, f"Keys in ZH but missing in EN: {missing_in_en}"

def test_i_help_text_contains_commands():
    """Help text should contain key command names."""
    for lang in ["en", "zh"]:
        result = get_text("help_text", lang)
        assert "/news" in result
        assert "/monitor" in result
        assert "/ask" in result
        assert "/tw_user" in result

def test_i_default_lang_is_zh():
    """Default language should be zh."""
    result = get_text("help_text")
    assert "CryptoEye Agent" in result
