"""What the plugin's two feeds attach to (plugin API 2.2): Cboe's index history files and the Cboe Futures Exchange's
historical data as Cboe's pages describe them, the files each says it asks for being the ones its source really asks
for, what each one's client learned said without a request, and (LIMINAL_VENDOR_PAGES=1 only) every page they name
still answering. Nothing else is sent; no ledger or key is touched."""
from __future__ import annotations

import gc
import os
import re
from datetime import date

import pytest

from liminal_libs.config import load_settings
from liminal_libs.sources.apis import dead_links, problems, urls
from liminal_libs.sources.http import PublicClient

import plugin_integrator_cboe as cboe
from plugin_integrator_cboe import BASE_URL, FUTURES_URL, CboeFuturesSource, CboeSource
from plugin_integrator_cboe.apis import FUTURES_FILES, FUTURES_NAME, INDEX_FILES, INDICES_NAME
from plugin_integrator_cboe.facts import NOTES

from .conftest import FakeResponse, FakeSession

VIX_CSV = "DATE,OPEN,HIGH,LOW,CLOSE\n11/09/2026,17.10,18.20,16.90,17.55\n11/10/2026,17.50,17.90,16.80,16.95\n"
VX_CSV = ("Trade Date,Futures,Open,High,Low,Close,Settle,Change,Total Volume,EFP,Open Interest\n"
          "2026-11-09,X (Nov 2026),18.10,18.60,17.90,18.20,18.25,0.10,90000,0,250000\n"
          "2026-11-10,X (Nov 2026),18.20,18.40,17.60,17.70,17.75,-0.50,95000,0,240000\n")
TEMPLATES = ((re.compile(r"^/[A-Z0-9]+_History\.csv$"), "GET /{CODE}_History.csv"),
             (re.compile(r"^/([A-Z]+)/\1_\d{4}-\d{2}-\d{2}\.csv$"), "GET /{PRODUCT}/{PRODUCT}_{YYYY-MM-DD}.csv"))


@pytest.fixture(autouse=True)
def fresh_notes():
    NOTES.clear()
    yield
    NOTES.clear()


def _calls(session: FakeSession, base: str) -> set[str]:
    """The card's calls the files asked for are (their templates), or the paths themselves when none matches."""
    paths = [url.removeprefix(base) for url, _, _ in session.calls]
    return {next((call for pattern, call in TEMPLATES if pattern.match(p)), p) for p in paths}


def test_each_feed_declares_its_own_files_soundly_with_every_part_and_what_it_does_with_each():
    assert cboe.INDICES.apis == (INDEX_FILES,) and cboe.FUTURES.apis == (FUTURES_FILES,)
    for p in cboe.PLUGINS:
        assert problems(p.apis) == [] and all(u.startswith("https://") for u in urls(p.apis))
        for api in p.apis:
            assert {c.area for c in api.calls} <= {a.name for a in api.areas} and api.verified == "2026-11-11"
            assert not any(c.writes or c.costs for c in api.calls) and api.costs == "" and "personal" in api.limits
    assert (INDEX_FILES.name, FUTURES_FILES.name) == (INDICES_NAME, FUTURES_NAME)
    assert (INDEX_FILES.base, FUTURES_FILES.base) == (BASE_URL, FUTURES_URL)  # the cards' addresses are the clients'
    assert INDEX_FILES.docs.endswith("/vix-historical-data") and FUTURES_FILES.docs.endswith("/historical-data/futures")
    assert len(INDEX_FILES.areas) == 9 and len(INDEX_FILES.covered) == 5 and len(FUTURES_FILES.areas) == 14
    assert [a.name for a in FUTURES_FILES.covered] == ["Price and volume detail: VIX futures (VX)"]
    assert "403, not 404" in FUTURES_FILES.limits


def test_the_files_each_says_it_asks_for_are_the_ones_its_source_asks_for():
    session = FakeSession([FakeResponse(200, VIX_CSV)])
    indices = CboeSource(PublicClient(BASE_URL, session=session, sleep=lambda s: None))
    assert [b["c"] for b in next(indices.bar_pages("I:VIX", date(2026, 11, 9), date(2026, 11, 10), "day"))] == [17.55, 16.95]
    assert _calls(session, BASE_URL) == {c.name for c in INDEX_FILES.used} == {"GET /{CODE}_History.csv"}
    session = FakeSession([FakeResponse(200, VX_CSV)])
    futures = CboeFuturesSource(PublicClient(FUTURES_URL, session=session, sleep=lambda s: None))
    assert [b["c"] for b in next(futures.bar_pages("VXX6", date(2026, 11, 9), date(2026, 11, 10), "day"))] == [18.2, 17.7]
    assert session.calls[0][0] == f"{FUTURES_URL}/VX/VX_2026-11-18.csv"
    assert _calls(session, FUTURES_URL) == {c.name for c in FUTURES_FILES.used}


def test_api_facts_say_what_each_feeds_client_learned_and_ask_nothing():
    assert cboe.INDICES.api_facts() == {} and cboe.FUTURES.api_facts() == {}  # nothing built here yet
    s = load_settings(env={}, env_file=None)
    built = (cboe.INDICES.build(s, 7), cboe.FUTURES.build(s, 3))  # each build notes its client (no request)
    assert set(cboe.INDICES.api_facts()) == {INDICES_NAME} and set(cboe.FUTURES.api_facts()) == {FUTURES_NAME}
    assert cboe.FUTURES.api_facts()[FUTURES_NAME]["Requests"] == "0 so far (of 3 allowed)"
    del built
    gc.collect()
    assert cboe.INDICES.api_facts()[INDICES_NAME]["Run began"].endswith("(ended)")
    # a run's client as Cboe answers it (fakes, no ledger): the requests, the last file's change
    session = FakeSession([FakeResponse(200, VIX_CSV, {"Last-Modified": "Tue, 10 Nov 2026 22:30:48 GMT"})])
    src = CboeSource(PublicClient(BASE_URL, session=session, sleep=lambda s: None))
    NOTES.note(INDICES_NAME, src.client)
    next(src.bar_pages("I:VIX", date(2026, 11, 9), date(2026, 11, 10), "day"))
    said = cboe.INDICES.api_facts()[INDICES_NAME]
    assert said["Requests"] == "1 so far" and said["Last file changed"] == "Tue, 10 Nov 2026 22:30:48 GMT"
    assert FUTURES_NAME not in cboe.INDICES.api_facts()  # each feed says its own API's facts alone


@pytest.mark.skipif(os.environ.get("LIMINAL_VENDOR_PAGES") != "1", reason="asks Cboe's pages: set LIMINAL_VENDOR_PAGES=1")
def test_every_page_they_name_answers():
    assert dead_links(cboe.INDICES.apis + cboe.FUTURES.apis) == []
