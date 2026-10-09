from bot.util import mask_secret


def test_mask_secret_keeps_only_first_eight_characters():
    masked = mask_secret("ghp_ABCDEFGH1234")
    assert masked == "ghp_ABCD****"
    assert masked.startswith("ghp_ABCD")
    assert "EFGH1234" not in masked


def test_mask_secret_empty():
    assert mask_secret("") == "****"
    assert mask_secret(None) == "****"
