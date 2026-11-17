import re
from app.security import hash_serial, new_serial

def test_serial_format_and_randomness():
    first = new_serial()
    second = new_serial()
    assert re.fullmatch(r"WRK-(?:[0-9A-F]{4}-){3}[0-9A-F]{4}", first)
    assert first != second

def test_serial_hash_is_case_and_space_insensitive():
    assert hash_serial(" wrk-abcd-1234-5678-9abc ") == hash_serial("WRK-ABCD-1234-5678-9ABC")

def test_serial_hash_is_not_plain_text():
    serial = new_serial()
    digest = hash_serial(serial)
    assert serial not in digest
    assert len(digest) == 64
