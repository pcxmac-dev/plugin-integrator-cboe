"""Cboe (cboe.com) for Liminal: daily history of Cboe's indices (VIX from 1990), no key, a closed
archive; and VIX futures' daily history from 2004 (a feed of this plugin, `cboefutures`: one public
file a contract, the continuous chart VX1! built from them by the library's roll rules).

A Liminal plugin released on its own, registered under the entry point group `liminal.providers`:
one plugin, two feeds (PLUGINS: the indices' archive `cboe`, the futures `cboefutures`), each an
instance of a class of this module on the class contract (plugin API 2.0, liminal-libs 1.3.0:
liminal_libs.sources.plugin.FeedPlugin; what a feed declares its class attributes, what it does its
methods). The feeds share `CboeFeed`, a keyless public feed's plugin (liminal_libs.sources.archive:
PublicFeedPlugin). Its version is its distribution's (pyproject.toml); it relies on the contract and
nothing of the app outside it (docs/ARCHITECTURE.md in liminal-charts: "Providers are plugins").

Plugin API 2.2 (liminal-libs 1.49.0; the user, 2026-11-11: "each plugin should reflect the the API its attached to, and
present links that provide documentation"): each feed's `apis`, what it talks to (apis.py: Cboe's index history files
for `cboe`, the Cboe Futures Exchange's historical data for `cboefutures`, with Cboe's pages, every part of each and the
files it asks for among the rest), and `api_facts()`, what its client learned while it ran (facts.py), asking nothing.
"""
from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime, timedelta
from typing import Iterator

from liminal_libs.config import Tier
from liminal_libs.errors import NotEntitled, SourceError
from liminal_libs.freshness import Delay
from liminal_libs.futures import contract_month
from liminal_libs.models import Exchange, Instrument, country
from liminal_libs.sessions import MarketCalendar
from liminal_libs.sources.archive import ET, Archive, PublicFeedPlugin, bounds, ms
from liminal_libs.sources.http import PublicClient
from liminal_libs.sources.registry import public_client

from .apis import FUTURES_FILES, INDEX_FILES
from .facts import NOTES

BASE_URL = "https://cdn-api.cboe.com/api/global/us_indices/daily_prices"
# its plan and caps: a public file server with no published limits, one file an index
TIER = Tier("cboe-public", requests_per_minute=30, history_years=None, history_start=date(1990, 1, 1))
PER_RUN, PER_DAY = 50, 200
# VIX futures (the user, 2026-11-02: "lets include futures"): Cboe's daily files, one a contract, named by
# the contract's final settlement date (VX/VX_2026-11-18.csv: Trade Date, Futures, Open, High, Low, Close,
# Settle, Change, Total Volume, EFP, Open Interest; checked 2026-11-02). VX traded first on 2004-03-26.
FUTURES_URL = "https://cdn.cboe.com/data/us/futures/market_statistics/historical_data"
FUTURES_TIER = Tier("cboe-futures", requests_per_minute=30, history_years=None, history_start=date(2004, 3, 26))
FUTURES_PER_RUN, FUTURES_PER_DAY = 40, 200
PRODUCTS = {"VX": "Cboe Volatility Index (VIX) futures"}  # the products carried (Mini VIX, VXM, has files too: later)
CFE = Exchange("cboefutures", 1, "Cboe Futures Exchange", country("US"), mic="XCBF", acronym="CFE", type="exchange")
CALENDAR = MarketCalendar()  # Cboe's holidays are the NYSE's (Good Friday among them) for the settlement rule
_CONTRACT = re.compile(r"^([A-Z0-9]+?)([FGHJKMNQUVXZ])(\d{1,2})$")


def third_friday(year: int, month: int) -> date:
    first = date(year, month, 1)
    return first + timedelta(days=(4 - first.weekday()) % 7 + 14)


def vx_expiration(month: date) -> date:
    """A VX contract's final settlement date (Cboe's rule): the Wednesday 30 days before the third
    Friday of the month after the contract month; when that Friday is a holiday, 30 days before the
    business day before it (March 2025: Good Friday was April 18, so Tuesday March 18)."""
    y, m = (month.year + 1, 1) if month.month == 12 else (month.year, month.month + 1)
    friday = third_friday(y, m)
    while not CALENDAR.is_trading_day(friday):
        friday -= timedelta(days=1)
    return friday - timedelta(days=30)


def contract_of(ticker: str) -> tuple[str, str] | None:
    """(product, contract) of an outright contract's ticker (VXX6, VXX26), or None."""
    m = _CONTRACT.match(ticker.upper())
    return (m.group(1), m.group(0)) if m else None


def read_contract(text: str) -> list[dict]:
    """A contract's daily file as day bars stamped at midnight US/Eastern of the trade date, its
    volume the day's total. A day the contract did not trade (a close of 0: the months before it
    is active, a thin far month) is its settlement price at all four, with no volume: the file's
    official daily record, kept so the contract counts as live; a day with neither is left out."""
    bars = []
    for row in csv.DictReader(io.StringIO(text)):
        row = {(k or "").strip("\ufeff \t"): (v or "").strip() for k, v in row.items() if isinstance(v, str)}
        try:
            d = date.fromisoformat(row["Trade Date"][:10])
            settle = float(row.get("Settle") or 0)
            o, h, l, c = (float(row.get(k) or 0) for k in ("Open", "High", "Low", "Close"))
            v = float(row.get("Total Volume") or 0)
        except (KeyError, ValueError):
            continue
        if c <= 0:
            if settle <= 0:
                continue
            o = h = l = c = settle
            v = 0.0
        elif o <= 0:
            o = c
        h, l = max(o, h, l, c), min(x for x in (o, h, l, c) if x > 0)
        bars.append({"t": ms(datetime(d.year, d.month, d.day, tzinfo=ET)), "o": o, "h": h, "l": l, "c": c, "v": v,
                     "vw": None, "n": None})
    return bars

CBOE_INDICES = {"VIX", "VIX9D", "VIX3M", "VIX6M", "VIX1Y", "VVIX", "SKEW", "VXN", "VXD", "RVX", "OVX", "GVZ",
                "VXEEM", "VXSLV", "VXAZN", "VXAPL", "VXGOG", "VXGS", "VXIBM", "BXM", "PUT"}


class CboeSource(Archive):
    """Cboe's daily history files: one request returns an index's whole history."""

    name = "cboe"
    assets = ("index",)

    def __init__(self, client: PublicClient):
        super().__init__(client)
        self._files: dict[str, list[dict]] = {}

    def resolutions(self, asset: str) -> tuple[str, ...]:
        return ("day",) if asset == "index" else ()

    def covers(self, ticker: str) -> bool:
        return ticker.upper().removeprefix("I:") in CBOE_INDICES

    def _history(self, code: str) -> list[dict]:
        """An index's whole daily history. Most files have DATE, OPEN, HIGH, LOW, CLOSE; some only
        a close (VVIX, SKEW: DATE and a column named after the index), whose bars are that close
        at all four prices. A file with rows of which none can be read is an error, never an empty
        history: the archive would be closed as complete without it."""
        if code not in self._files:
            text = self.client.text(f"/{code}_History.csv")
            bars, rows = [], 0
            for row in csv.DictReader(io.StringIO(text)):
                rows += 1
                row = {(k or "").strip("﻿ \t").upper(): v.strip() for k, v in row.items() if isinstance(v, str)}
                try:
                    d = datetime.strptime(row["DATE"], "%m/%d/%Y")
                    if all(row.get(k) for k in ("OPEN", "HIGH", "LOW")):
                        o, h, l, c = (float(row[k]) for k in ("OPEN", "HIGH", "LOW", "CLOSE"))
                    else:  # a close-only file (or a day it gives the close of only)
                        o = h = l = c = float(row.get("CLOSE") or row[code])
                except (KeyError, ValueError):
                    continue
                # day bars are stamped at midnight US/Eastern of the session date, like the other feeds'
                bars.append({"t": ms(datetime(d.year, d.month, d.day, tzinfo=ET)), "o": o, "h": h, "l": l, "c": c,
                             "v": None, "vw": None, "n": None})
            if not bars:  # answered (200), but nothing in it: not an outage, and not an empty history
                raise SourceError(200, f"Cboe {code}: no daily rows read from the history file ({rows} lines; "
                                       "format changed?); the archive stays open")
            self._files[code] = bars
        return self._files[code]

    def bar_pages(self, ticker, start, end, timespan, multiplier=1, descending=False, asset="index",
                  limit: int | None = None) -> Iterator[list[dict]]:
        if timespan != "day":
            raise NotEntitled(0, "Cboe publishes daily history only")
        code = ticker.upper().removeprefix("I:")
        if code not in CBOE_INDICES:
            raise NotEntitled(0, f"Cboe has no history file for {code}")
        a, b = bounds(start, end, ET)
        bars = [x for x in self._history(code) if a <= x["t"] < b]
        bars.sort(key=lambda x: -x["t"] if descending else x["t"])
        yield bars[:limit] if limit else bars

    def instrument(self, ticker: str, resolve_exchange: bool = True) -> Instrument:
        code = ticker.upper().removeprefix("I:")
        return Instrument(ticker=code, name=f"Cboe {code} index", details={"source": "Cboe daily history"})


class CboeFuturesSource(Archive):
    """VIX futures' daily history from Cboe's files: one file a contract (its whole life, read once a
    run), asked for by the contract's ticker (VXX6: the library's naming, contract_month) through
    its final settlement date (vx_expiration). Not an archive: the contracts trading on get their
    new days each run (the library rolls the continuous chart by volume)."""

    name = "cboefutures"
    assets = ("future",)
    archival = False

    def __init__(self, client: PublicClient):
        super().__init__(client)
        self._files: dict[tuple[str, date], list[dict]] = {}

    def resolutions(self, asset: str) -> tuple[str, ...]:
        return ("day",) if asset == "future" else ()

    def native_frames(self, asset: str) -> tuple:
        return ()

    def covers(self, ticker: str) -> bool:
        c = contract_of(ticker)
        return ticker.upper() in PRODUCTS or (c is not None and c[0] in PRODUCTS)

    def exchanges(self) -> list[Exchange]:
        return [CFE]

    def _file(self, product: str, expiration: date) -> list[dict]:
        """A contract's bars; a file that is not there (a month not listed yet, or never) is none."""
        key = (product, expiration)
        if key not in self._files:
            try:
                self._files[key] = read_contract(self.client.text(f"/{product}/{product}_{expiration.isoformat()}.csv"))
            except SourceError as e:
                if e.status != 404:
                    raise
                self._files[key] = []
        return self._files[key]

    def bar_pages(self, ticker, start, end, timespan, multiplier=1, descending=False, asset="future",
                  limit: int | None = None) -> Iterator[list[dict]]:
        if timespan != "day":
            raise NotEntitled(0, "Cboe publishes daily history only")
        c = contract_of(ticker)
        if c is None or c[0] not in PRODUCTS:
            raise NotEntitled(0, f"Cboe has no history file for {ticker}")
        product, contract = c
        around = end if isinstance(end, date) and not isinstance(end, datetime) else end.date()
        month = contract_month(contract, product, around)
        if month is None:
            raise NotEntitled(0, f"{ticker} is not a {product} contract")
        a, b = bounds(start, end, ET)
        bars = [x for x in self._file(product, vx_expiration(month)) if a <= x["t"] < b]
        bars.sort(key=lambda x: -x["t"] if descending else x["t"])
        yield bars[:limit] if limit else bars

    def futures_products(self, day=None) -> list[dict]:
        return [{"ticker": code, "name": name, "exchange": CFE.mic, "type": "volatility", "figi": None, "kind": "future"}
                for code, name in PRODUCTS.items()]

    def instrument(self, ticker: str, resolve_exchange: bool = True) -> Instrument:
        c = contract_of(ticker)
        product = c[0] if c else ticker.upper()
        return Instrument(ticker=ticker.upper(), name=PRODUCTS.get(product, f"Cboe {product} futures"), primary_exchange=CFE,
                          details={"source": "Cboe futures daily files"})


class CboeFeed(PublicFeedPlugin):
    """What the plugin's two feeds are alike (plugin API 2.2): a keyless public feed's plugin, its
    source (`source_class`) on the contract's public client at its `base_url`, its plan and caps its
    fixed `tier`, `per_run` and `per_day`; Cboe's own files (`kind` official), one file a symbol
    holding its whole history (`per_request`); its client noted under its API (`apis`, one each) for
    `api_facts`. Each feed declares the rest of its own."""

    api = "2.2"  # the contract it needs (the class contract; sources.http, sources.archive, part_of; 2.2: apis); its version: the distribution's
    kind = "official"
    per_request = {"day": None}  # one file per symbol (an index, a contract): its whole history

    def build(self, settings, request_budget):
        """The public feed's own build (PublicFeedPlugin.build), its client noted under the feed's API (held
        weakly: api_facts reads what it learned)."""
        source = super().build(settings, request_budget)
        NOTES.note(self.apis[0].name, source.client)
        return source

    def api_facts(self):
        """What its client learned of its Cboe files while it ran (the requests made, the last answer's clock, the
        last file's change), from what this process already holds: nothing is asked (facts.py)."""
        return NOTES.facts(a.name for a in self.apis)


class CboeIndices(CboeFeed):
    """The indices' archive: daily history of Cboe's indices, VIX from 1990 (no key)."""

    name = "cboe"
    title = "Cboe"
    base_url = BASE_URL
    source_class = CboeSource
    assets = frozenset({"index"})
    order = 50
    about = "daily history of Cboe's indices, VIX from 1990 (no key)"
    archival = True
    tier = TIER
    per_run, per_day = PER_RUN, PER_DAY
    limits = "none published (a public file server)"
    provides = {"index": ("day",)}
    apis = (INDEX_FILES,)  # what it attaches to (plugin API 2.2): Cboe's index history files (apis.py)

    def markets(self, settings):
        return {"index": "index"}

    def carries(self, spec):
        return spec.source_ticker.upper().removeprefix("I:") in CBOE_INDICES


class CboeFutures(CboeFeed):
    """VIX futures: a feed of this plugin on the same public file server (no key, no plan), live."""

    name = "cboefutures"
    title = "VIX futures"
    part_of = "cboe"
    account = "cboe"
    order = 51
    base_url = FUTURES_URL
    source_class = CboeFuturesSource
    assets = frozenset({"future"})
    about = "VIX futures' daily history from 2004: a public file a contract, the continuous chart VX1! from them (no key)"
    tier = FUTURES_TIER
    per_run, per_day = FUTURES_PER_RUN, FUTURES_PER_DAY
    limits = "shares Cboe's window: one public file server, no limits published"
    provides = {"future": ("day",)}
    bulk_resolution = "day"
    # when its data is published (the library's freshness.PLAN_DELAYS row for cboe-futures, declared here
    # too): a contract's day comes with its settlement after the session, so its day bars are expected
    # once the session is over, like a stock's on an end-of-day plan
    delays = {"cboe-futures": {"future": Delay("eod")}}
    apis = (FUTURES_FILES,)  # what it attaches to (plugin API 2.2): the Cboe Futures Exchange's historical data (apis.py)

    def build(self, settings, request_budget):
        """Its source on Cboe's public client: the window and the day cap are held under the account its
        requests count against (`account`, the indices' feed: one public file server, one window). Its
        client is noted under its API (held weakly: api_facts reads what it learned)."""
        source = self.source_class(public_client(self.account, self.base_url, settings, request_budget))
        NOTES.note(self.apis[0].name, source.client)
        return source

    def markets(self, settings):
        return {"future": "cfe"}

    def carries(self, spec):
        return spec.source_ticker.upper() in PRODUCTS


INDICES, FUTURES = CboeIndices(), CboeFutures()
PLUGINS = (INDICES, FUTURES)  # one plugin, two feeds: the indices' archive, and the VIX futures
