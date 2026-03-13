import pytest
import pytest_check as check
from src.crawler import LinkScout

@pytest.mark.asyncio
async def test_crawler(targets):
    scout = LinkScout()
    result = await scout.run(targets)
    assert_valid_results(result)

def test_mock_validation(mock_results):
    assert_valid_results(mock_results)

def assert_valid_results(result):
    assert result and isinstance(result, list), "Crawler returned an empty or invalid result set."
    for item in result:
        check.is_true(item.url.startswith("https"), f"Insecure URL: {item.url} as {item.text} from {item.parent}")
        check.is_true(bool(item.text and str(item.text).strip()), f"Empty text: {item.url}")
        check.is_not_none(item.parent, f"Parent missing: {item.url}")