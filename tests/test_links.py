from meeting_pipeline import config as config_mod
from meeting_pipeline import links
from meeting_pipeline.settings_server import render_settings_page


def _cfg():
    return config_mod.deep_merge(config_mod.DEFAULTS, {})


def test_donate_url_defaults_to_empty():
    assert links.donate_url() == ""


def test_donate_url_strips_whitespace(monkeypatch):
    monkeypatch.setattr(links, "DONATE_URL", "  https://example.com/buy/x  ")
    assert links.donate_url() == "https://example.com/buy/x"


def test_settings_page_hides_support_when_unset(monkeypatch):
    monkeypatch.setattr(links, "DONATE_URL", "")
    html = render_settings_page(_cfg())
    assert "Buy me a coffee" not in html


def test_settings_page_shows_support_when_set(monkeypatch):
    url = "https://marcriera.lemonsqueezy.com/buy/abc-123"
    monkeypatch.setattr(links, "DONATE_URL", url)
    html = render_settings_page(_cfg())
    assert "Buy me a coffee" in html
    assert url in html
