"""The Cboe plugin, run against the app installed beside it: its history files read, and the app
loading it from this package with its own version and the facts it had as a built-in."""
from __future__ import annotations

from datetime import date, datetime
from importlib.metadata import version

import pytest

from liminal_libs import composite, freshness
from liminal_libs.config import load_settings
from liminal_libs.errors import NotEntitled, SourceError
from liminal_libs.freshness import Delay
from liminal_libs.sources import is_archive, markets, provider, rate_window, registry, supports
from liminal_libs.sources.archive import ET, PublicFeedPlugin, ms
from liminal_libs.sources.http import PublicClient
from liminal_libs.sources.registry import FeedPlugin
from liminal_libs.symbols import resolve

import plugin_integrator_cboe
from plugin_integrator_cboe import (FUTURES_PER_DAY, FUTURES_PER_RUN, FUTURES_TIER, PER_DAY, PER_RUN, TIER, CboeFuturesSource,
                                 CboeSource, read_contract, vx_expiration)

from .conftest import FakeResponse, FakeSession


def _cboe(*texts: str):
    session = FakeSession([FakeResponse(200, t) for t in texts])
    return CboeSource(PublicClient("https://x.test/api", session=session, sleep=lambda s: None)), session


def test_cboe_reads_one_file_for_all_history():
    src, session = _cboe("DATE,OPEN,HIGH,LOW,CLOSE\n01/02/1990,17.24,17.24,17.24,17.24\n01/03/1990,18.19,18.5,18.0,18.19\n")
    bars = next(src.bar_pages("I:VIX", date(1990, 1, 1), date(1990, 1, 2), "day"))
    assert [b["c"] for b in bars] == [17.24] and bars[0]["t"] == ms(datetime(1990, 1, 2, tzinfo=ET))
    assert len(next(src.bar_pages("VIX", date(1990, 1, 1), date(1990, 1, 31), "day"))) == 2
    assert len(session.calls) == 1 and session.calls[0][0].endswith("/VIX_History.csv")  # cached
    with pytest.raises(NotEntitled):
        next(src.bar_pages("I:COMP", date(1990, 1, 1), date(1990, 1, 2), "day"))
    with pytest.raises(NotEntitled):
        next(src.bar_pages("I:VIX", date(1990, 1, 1), date(1990, 1, 2), "minute"))


def test_a_cboe_file_with_closes_only_is_read():
    src, _ = _cboe("﻿DATE,VVIX\n01/03/2007,87.63\n01/04/2007,88.19\n")
    bars = next(src.bar_pages("I:VVIX", date(2007, 1, 1), date(2007, 1, 31), "day"))
    assert [(b["o"], b["h"], b["l"], b["c"]) for b in bars] == [(87.63,) * 4, (88.19,) * 4]
    src, _ = _cboe("DATE,OPEN,HIGH,LOW,CLOSE\n01/02/1990,,,,17.24\n01/03/1990,18.19,18.5,18.0,18.19\n")
    bars = next(src.bar_pages("I:VIX", date(1990, 1, 1), date(1990, 1, 31), "day"))
    assert [b["h"] for b in bars] == [17.24, 18.5]  # a day with its close only, beside full days


def test_a_cboe_file_that_reads_as_nothing_is_an_error_not_an_empty_history():
    src, _ = _cboe("Date;Index;Value\n2007-01-03;VVIX;87.63\n")  # a format of its own
    with pytest.raises(SourceError, match="no daily rows"):
        next(src.bar_pages("I:VVIX", date(2007, 1, 1), date(2007, 1, 31), "day"))
    with pytest.raises(SourceError):
        next(_cboe("")[0].bar_pages("I:SKEW", date(2007, 1, 1), date(2007, 1, 31), "day"))


VX_FILE = ("Trade Date,Futures,Open,High,Low,Close,Settle,Change,Total Volume,EFP,Open Interest\n"
           "2026-02-23,X (Nov 2026),0.0000,21.0000,0.0000,0.0000,22.775,0,0,0,0\n"
           "2026-03-24,X (Nov 2026),0.0000,20.6000,24.2500,0.0000,23.8515,0.1765,0,0,0\n"
           "2026-10-30,X (Nov 2026),18.8000,21.9500,18.7500,20.1500,20.3603,2.2099,235927,1368,175455\n"
           "2026-11-02,X (Nov 2026),20.1500,20.5500,18.8500,20.3500,20.3752,0.0149,143670,0,173051\n")


def _futures(*responses):
    session = FakeSession(list(responses))
    return CboeFuturesSource(PublicClient("https://x.test/files", session=session, sleep=lambda s: None)), session


def test_a_vx_contract_is_read_from_its_settlement_days_file():
    src, session = _futures(FakeResponse(200, VX_FILE), FakeResponse(404, "not found"))
    bars = next(src.bar_pages("VXX6", date(2026, 10, 1), date(2026, 11, 30), "day", asset="future"))
    assert session.calls[0][0].endswith("/VX/VX_2026-11-18.csv")  # November 2026: settled 30 days before December's third Friday
    assert [(b["c"], b["v"]) for b in bars] == [(20.15, 235927.0), (20.35, 143670.0)]
    assert bars[0]["t"] == ms(datetime(2026, 10, 30, tzinfo=ET)) and bars[0]["h"] == 21.95 and bars[0]["l"] == 18.75
    early = next(src.bar_pages("VXX26", date(2026, 2, 1), date(2026, 3, 31), "day", asset="future"))  # the same file, cached
    assert [(b["o"], b["h"], b["l"], b["c"], b["v"]) for b in early] == [(22.775,) * 4 + (0.0,), (23.8515,) * 4 + (0.0,)]
    assert len(session.calls) == 1
    assert next(src.bar_pages("VXZ6", date(2026, 10, 1), date(2026, 11, 30), "day", asset="future")) == []  # no file yet: 404
    assert session.calls[1][0].endswith("/VX/VX_2026-12-16.csv")
    newest = next(src.bar_pages("VXX6", date(2026, 1, 1), date(2026, 12, 31), "day", descending=True, asset="future", limit=1))
    assert [b["t"] for b in newest] == [ms(datetime(2026, 11, 2, tzinfo=ET))]
    with pytest.raises(NotEntitled):
        next(src.bar_pages("ESZ6", date(2026, 10, 1), date(2026, 11, 30), "day", asset="future"))
    with pytest.raises(NotEntitled):
        next(src.bar_pages("VXX6", date(2026, 10, 1), date(2026, 11, 30), "minute", asset="future"))
    assert src.covers("VX") and src.covers("VXX26") and not src.covers("ESZ6")
    assert src.futures_products() == [{"ticker": "VX", "name": "Cboe Volatility Index (VIX) futures", "exchange": "XCBF",
                                       "type": "volatility", "figi": None, "kind": "future"}]
    assert src.instrument("VXX6").primary_exchange.mic == "XCBF" and [e.acronym for e in src.exchanges()] == ["CFE"]
    assert read_contract("Trade Date,Futures,Open,High,Low,Close,Settle\nbad,,,,,,\n2026-01-02,X,0,0,0,0,0\n") == []


def test_vx_settlement_dates_follow_cboes_rule():
    assert vx_expiration(date(2026, 11, 1)) == date(2026, 11, 18)  # December 18 2026 is the third Friday: 30 days before
    assert vx_expiration(date(2026, 12, 1)) == date(2026, 12, 16)  # January 15 2027
    assert vx_expiration(date(2025, 3, 1)) == date(2025, 3, 18)  # Good Friday 2025 was April's third Friday: Thursday 17th, a Tuesday
    assert vx_expiration(date(2026, 1, 1)) == date(2026, 1, 21)  # February 20 2026


def test_the_app_loads_its_two_feeds_from_this_package_with_its_own_version():
    registry.reload()
    assert [p.name for p in plugin_integrator_cboe.PLUGINS] == ["cboe", "cboefutures"] and not hasattr(plugin_integrator_cboe, "PLUGIN")
    for name in ("cboe", "cboefutures"):
        p = provider(name)
        assert p is not None, dict(registry.errors())
        assert p.origin in {"package: plugin-integrator-cboe (plugin_integrator_cboe)", "plugins/plugin-integrator-cboe (plugin_integrator_cboe)"}  # its package, or its checkout in the workspace\'s plugin directory
        assert p.version == version("plugin-integrator-cboe") and p.api == "2.2"
        assert registry.api_refusal(p.api) is None
    assert plugin_integrator_cboe.INDICES.version == "" and plugin_integrator_cboe.FUTURES.version == ""
    assert not [why for where, why in registry.errors() if "cboe" in where or "cboe" in why]
    row = {r["name"]: r for r in registry.menu()}["cboe"]
    assert (row["version"], row["api"]) == (version("plugin-integrator-cboe"), "2.2")
    assert registry.plugin_feeds("cboe") == ["cboe", "cboefutures"] and registry.plugin_of("cboefutures") == "cboe"


def test_it_keeps_the_facts_it_had_built_in():
    registry.reload()
    s = load_settings(env={}, env_file=None)
    view = s.for_source("cboe")
    assert (view.tier, view.max_requests_per_run, view.max_requests_per_day) == (TIER, PER_RUN, PER_DAY)
    assert rate_window("cboe", s)[0] == 30
    assert is_archive("cboe") and markets("cboe", s) == {"index": "index"}
    assert supports("cboe", resolve("I:VIX")) and not supports("cboe", resolve("IXIC"))
    assert composite.feed_kind("cboe", "index") == "official"
    # the VIX futures feed: the same public server, live (the front contracts trade on), its own market
    fut = s.for_source("cboefutures")
    assert (fut.tier, fut.max_requests_per_run, fut.max_requests_per_day) == (FUTURES_TIER, FUTURES_PER_RUN, FUTURES_PER_DAY)
    assert not is_archive("cboefutures") and markets("cboefutures", s) == {"future": "cfe"}
    assert supports("cboefutures", resolve("VX1!")) and supports("cboefutures", resolve("VX2!"))
    assert not supports("cboefutures", resolve("ES1!")) and not supports("cboefutures", resolve("I:VIX"))
    assert composite.feed_kind("cboefutures", "future") == "official"
    assert (provider("cboefutures").part_of, provider("cboefutures").account) == ("cboe", "cboe")


def test_each_feed_is_a_class_on_plugin_api_2_2():
    """The two feeds are instances of the module's classes (plugin API 2.2, liminal-libs 1.49.0): CboeFeed holds
    what both declare alike, each feed what is its own; the registry loads them as those classes."""
    assert isinstance(plugin_integrator_cboe.INDICES, plugin_integrator_cboe.CboeIndices)
    assert isinstance(plugin_integrator_cboe.FUTURES, plugin_integrator_cboe.CboeFutures)
    for p in plugin_integrator_cboe.PLUGINS:
        assert isinstance(p, plugin_integrator_cboe.CboeFeed) and isinstance(p, PublicFeedPlugin) and isinstance(p, FeedPlugin)
        assert p.api == "2.2" and not p.is_record and p.kind == "official" and p.request_bars("day") is None
    loaded = registry.reload()
    assert type(loaded["cboe"]) is plugin_integrator_cboe.CboeIndices and loaded["cboe"].api == "2.2"
    assert type(loaded["cboefutures"]) is plugin_integrator_cboe.CboeFutures and loaded["cboefutures"].api == "2.2"
    # the hooks each gives: its build (the indices' the public feed's own, the futures' on Cboe's account), its
    # markets and what it carries; the rest the contract's defaults (its fixed tier and caps, the plan's rate)
    for name in ("cboe", "cboefutures"):
        assert loaded[name].gives("build") and loaded[name].gives("markets") and loaded[name].gives("carries")
        assert not loaded[name].gives("view") and not loaded[name].gives("rate") and not loaded[name].gives("scan")
        assert not loaded[name].has_settings
    # the futures feed declares its publication delay itself, the library's row for it still in place
    assert plugin_integrator_cboe.FUTURES.delays == {"cboe-futures": {"future": Delay("eod")}}
    assert plugin_integrator_cboe.FUTURES.delays["cboe-futures"] == freshness.PLAN_DELAYS["cboe-futures"]
    assert not plugin_integrator_cboe.INDICES.delays and freshness.plan_delay(FUTURES_TIER, "future").kind == "eod"


def test_each_feed_builds_its_source_on_cboes_public_client(monkeypatch):
    held = []

    def fake_public_client(name, base_url, settings, budget):
        held.append((name, base_url, budget))
        return PublicClient(base_url, session=FakeSession([]), sleep=lambda s: None)
    monkeypatch.setattr(registry, "public_client", fake_public_client)  # the indices': the public feed's own build
    monkeypatch.setattr(plugin_integrator_cboe, "public_client", fake_public_client)  # the futures': on Cboe's account
    s = load_settings(env={}, env_file=None)
    indices, futures = plugin_integrator_cboe.INDICES.build(s, 7), plugin_integrator_cboe.FUTURES.build(s, 3)
    assert isinstance(indices, CboeSource) and isinstance(futures, CboeFuturesSource)
    assert held == [("cboe", plugin_integrator_cboe.BASE_URL, 7), ("cboe", plugin_integrator_cboe.FUTURES_URL, 3)]  # one window
    assert indices.client.base_url == plugin_integrator_cboe.BASE_URL and futures.client.base_url == plugin_integrator_cboe.FUTURES_URL
