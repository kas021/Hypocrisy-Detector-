from backend.scraper.base import ScrapedItem
from backend.scraper.storage import RawItemStore


def test_scraper_storage_upsert(tmp_path):
    store_path = tmp_path / "raw.sqlite"
    item = ScrapedItem(
        id="item-1",
        url="https://example.com/news",
        title="Example",
        text="Example body",
        source_name="Example Source",
    )
    with RawItemStore(store_path) as store:
        inserted, updated = store.upsert_items([item])
        assert inserted == 1
        assert updated == 0
        inserted2, updated2 = store.upsert_items([item])
        assert inserted2 == 0
        assert updated2 == 1
        rows = list(store.conn.execute("SELECT COUNT(*) FROM raw_items"))
        assert rows[0][0] == 1
