from app.news.collector import is_recent, parse_feed
from app.news.sources import Source
from app.news.tags import get_tags

RSS = b"""<?xml version="1.0"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
<channel><title>Test</title>
<item>
  <title>Bitcoin ETF inflows hit record as SEC approves options</title>
  <link>https://example.com/btc-etf</link>
  <pubDate>Mon, 13 Oct 2026 09:00:00 GMT</pubDate>
  <description><![CDATA[<p>Spot <b>Bitcoin</b> ETFs saw $1B inflows.</p>
  The post Bitcoin ETF appeared first on Test.]]></description>
  <media:thumbnail url="https://example.com/img.jpg"/>
</item>
<item>
  <title>Protocol drained in $40M exploit</title>
  <link>https://example.com/hack</link>
  <description>A DeFi lending protocol was hacked.</description>
</item>
<item>
  <title>No link item</title>
  <link>javascript:alert(1)</link>
</item>
</channel></rss>"""


def test_parse_feed_cleans_and_tags():
    items = parse_feed(RSS, Source("Test", "https://example.com/rss", "https://example.com"))
    assert len(items) == 2  # the javascript: link is dropped

    etf = items[0]
    assert etf.date == "2026-10-13"
    assert etf.image == "https://example.com/img.jpg"
    assert etf.summary == "Spot Bitcoin ETFs saw $1B inflows."
    assert "Bitcoin" in etf.tags and "Regulation" in etf.tags

    hack = items[1]
    assert "Security" in hack.tags and "DeFi" in hack.tags


def test_is_recent_window():
    assert is_recent("2026-10-01", "2026-10-14")
    assert not is_recent("2026-06-01", "2026-10-14")
    assert is_recent("2026-12-01", "2026-10-14")  # future-dated feeds pass through
    assert is_recent("garbage", "2026-10-14")


def test_tags_fall_back_to_crypto():
    assert get_tags("Nothing to see here") == ["Crypto"]


def test_tags_respect_word_boundaries():
    assert "Regulation" not in get_tags("The second half of the year")
    assert "Ethereum" not in get_tags("Ethics in finance")
