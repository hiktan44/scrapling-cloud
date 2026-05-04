from scrapling_cloud.learning import domain_from_url


def test_domain_from_url_normalizes_host() -> None:
    assert domain_from_url("https://Example.com/docs?q=1") == "example.com"
