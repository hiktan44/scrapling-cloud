from scrapling_cloud.analyzer import clean_api_key


def test_clean_api_key_ignores_placeholders() -> None:
    assert clean_api_key("") is None
    assert clean_api_key("<senin-z.ai-key>") is None
    assert clean_api_key("your-api-key") is None
    assert clean_api_key(" real-key ") == "real-key"
