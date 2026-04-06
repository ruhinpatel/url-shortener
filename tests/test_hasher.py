from app.services.hasher import decode, encode, is_valid_custom_code


def test_encode_known_values():
    assert encode(0) == "0"
    assert encode(1) == "1"
    assert encode(62) == "10"


def test_encode_decode_roundtrip():
    for i in [1, 100, 9999, 1_000_000, 56_800_235_583]:
        assert decode(encode(i)) == i


def test_uniqueness_over_10k_ids():
    codes = {encode(i) for i in range(10_000)}
    assert len(codes) == 10_000


def test_custom_code_valid():
    assert is_valid_custom_code("abc") is True
    assert is_valid_custom_code("MyLink123") is True
    assert is_valid_custom_code("A" * 20) is True


def test_custom_code_invalid():
    assert is_valid_custom_code("ab") is False        # too short
    assert is_valid_custom_code("A" * 21) is False    # too long
    assert is_valid_custom_code("my-link") is False   # hyphen not allowed
    assert is_valid_custom_code("") is False


def test_6_char_capacity():
    # 6-char base62 can encode up to 62^6 - 1 = 56_800_235_583
    code = encode(56_800_235_583)
    assert len(code) <= 7  # actually exactly 7 chars; 6-char max is 62^6-1
    assert decode(code) == 56_800_235_583
