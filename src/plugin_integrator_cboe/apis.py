"""What the plugin's two feeds attach to (plugin API 2.2, liminal_libs.sources.apis): Cboe's daily index history files
(the indices' feed, `cboe`) and the Cboe Futures Exchange's historical data files (the VIX futures' feed, `cboefutures`).
Every address below was read on Cboe's own pages on 2026-11-11 (its VIX historical data page and the files it links;
CFE's historical data page, its product selector and its archives; the terms; each page's title checked), and every
index file the indices' feed carries was found on Cboe's CDN (a HEAD each, updated the evening before). Nothing is
asked to show it."""
from __future__ import annotations

from liminal_libs.sources.apis import Api, Area, Call, Link

VERIFIED = "2026-11-11"
INDICES_NAME = "Cboe index history files"
FUTURES_NAME = "Cboe Futures Exchange historical data"
CBOE = "https://www.cboe.com"
VIX_HISTORY = f"{CBOE}/tradable-products/vix/vix-historical-data"
CFE_HISTORY = f"{CBOE}/markets/us/futures/market-statistics/historical-data/futures"
CFE_FILES = "https://cdn.cboe.com/data/us/futures/market_statistics/historical_data"
TERMS = (Link("Terms and conditions", f"{CBOE}/terms", "terms"), Link("Use of Cboe content", f"{CBOE}/use-of-content", "terms"))
CBOE_TERMS = ("Cboe's terms: the site's materials for personal, non-commercial use (one copy); copying, distributing or "
              "building on them needs Cboe's prior written consent (a Request to Use Cboe Content)")

VIX_TERM = "VIX and its term structure"
VOL_OF_VOL = "Volatility of volatility and tail risk"
INDEX_VOL = "Index and ETF volatility"
STOCK_VOL = "Single-stock volatility"
BENCHMARKS = "Strategy benchmarks"
ARCHIVES = "Archives"
QUOTES = "Delayed quotes and charts"
FEED = "Cboe Global Indices Feed"
DATASHOP = "Cboe DataShop"

INDEX_FILES = Api(
    name=INDICES_NAME,
    maker="Cboe Global Markets",
    about=("The daily history Cboe publishes of its indices: one CSV file an index holding its whole life (VIX from "
           "1990; DATE, OPEN, HIGH, LOW, CLOSE, or a close alone for VVIX and SKEW), refreshed each evening on Cboe's "
           "CDN and linked from its VIX historical data page."),
    kind="feed",
    base="https://cdn-api.cboe.com/api/global/us_indices/daily_prices",
    version="the files {CODE}_History.csv as Cboe serves them in 2026",
    auth="none",
    limits=("none published (a public file server: one file an index, its whole history; asked at 30 a minute, 50 a "
            "run, 200 a day here). " + CBOE_TERMS),
    costs="",
    links=(
        Link("VIX historical data (the files)", VIX_HISTORY, "docs"),
        Link("Cboe Global Indices", f"{CBOE}/global-indices", "reference"),
        Link("VIX volatility products", f"{CBOE}/tradable-products/vix", "guide"),
        Link("Global Indices system status notices", f"{CBOE}/indices/notices/system", "status"),
        Link("Cboe DataShop (data for sale)", "https://datashop.cboe.com/", "pricing"),
        *TERMS,
    ),
    areas=(
        Area(VIX_TERM, "VIX (the S&P 500's 30-day implied volatility), VIX9D, VIX3M, VIX6M, VIX1Y", VIX_HISTORY,
             covered="each index's file: its whole daily history (VIX from 1990)"),
        Area(VOL_OF_VOL, "VVIX (the volatility of VIX) and SKEW (the S&P 500's tail risk): close-only files", VIX_HISTORY,
             covered="their files, the close at all four prices"),
        Area(INDEX_VOL, "VXN (Nasdaq-100), VXD (Dow), RVX (Russell 2000), OVX (crude oil), GVZ (gold), VXEEM (emerging "
                        "markets), VXSLV (silver)", VIX_HISTORY, covered="each index's file"),
        Area(STOCK_VOL, "VXAPL, VXAZN, VXGOG, VXGS, VXIBM: single stocks' implied volatility", VIX_HISTORY,
             covered="each index's file"),
        Area(BENCHMARKS, "BXM (the S&P 500 buy-write) and PUT (the put-write)", f"{CBOE}/global-indices",
             covered="each index's file"),
        Area(ARCHIVES, "VIX 1990-2003 as a spreadsheet, and VXO (the old S&P 100 volatility index: 1986-2003, 2004 to "
                       "January 2021)", VIX_HISTORY),
        Area(QUOTES, "the quotes dashboard's delayed index values and charts", f"{CBOE}/delayed_quotes/vix"),
        Area(FEED, "real-time index values for licensees", f"{CBOE}/data/global-indices-feed/"),
        Area(DATASHOP, "Cboe's historical index, options and futures data for sale", "https://datashop.cboe.com/"),
    ),
    calls=(
        Call("GET /{CODE}_History.csv", "an index's whole daily history (VIX_History.csv ...)", VIX_TERM,
             used="the history of each index it carries (VIX, VIX9D, VIX3M, VIX6M, VIX1Y, VVIX, SKEW, VXN, VXD, RVX, OVX, "
                  "GVZ, VXEEM, VXSLV, VXAZN, VXAPL, VXGOG, VXGS, VXIBM, BXM, PUT): one request an index",
             docs=VIX_HISTORY),
        Call("GET https://cdn.cboe.com/resources/us/indices/vixarchive.xls", "VIX 1990-2003 (a spreadsheet)", ARCHIVES,
             docs=VIX_HISTORY),
        Call("GET https://cdn.cboe.com/resources/us/indices/vxocurrent.csv", "VXO, 2004 to January 2021", ARCHIVES,
             docs=VIX_HISTORY),
        Call("GET https://cdn.cboe.com/resources/us/indices/vxoarchive.xls", "VXO, 1986-2003 (a spreadsheet)", ARCHIVES,
             docs=VIX_HISTORY),
    ),
    verified=VERIFIED,
)

DETAIL = "Price and volume detail: VIX futures (VX)"
MINI = "Mini VIX futures (VXM, VM)"
VOL_FUTURES = "Volatility index futures (VXN, RVX; GVZ, OVX, VXEEM, VXEWZ security futures)"
CREDIT = "Corporate bond index futures (IBHY, IBIG, iBoxx emerging markets)"
RATES = "Rate futures (7-day AMERIBOR)"
CRYPTO = "Crypto futures (bitcoin and ether: financially settled and continuous)"
OTHER = "Other index futures (S&P 500 variance, Magnificent 10, RPX composite)"
VOLUME_OI = "Daily volume and open interest by product"
WINDOW = "Settlement window executed volume"
ARCHIVE = "Historical data archive (2004 to 2013)"
MARGINS = "Margin archive"
IMBALANCE = "VIX imbalance reports"
SETTLEMENT = "VIX settlement series"
DAILY = "Daily market statistics"

FUTURES_FILES = Api(
    name=FUTURES_NAME,
    maker="Cboe Futures Exchange (Cboe Global Markets)",
    about=("CFE's market statistics as files: a CSV a futures contract with its daily trading (Trade Date, Futures, "
           "Open, High, Low, Close, Settle, Change, Total Volume, EFP, Open Interest), named by its final settlement "
           "date, for each product its page lists (the price and volume detail, 2013 to now); every product's daily "
           "volume and open interest from 2004; settlement, margin and imbalance archives."),
    kind="feed",
    base=CFE_FILES,
    version="the files {PRODUCT}/{PRODUCT}_{YYYY-MM-DD}.csv as CFE serves them in 2026",
    auth="none",
    limits=("none published (a public file server, kept in one window with the indices' here: 30 a minute, 40 a run, "
            "200 a day). A contract without a file answers 403, not 404 (VX before 2013). " + CBOE_TERMS),
    costs="",
    links=(
        Link("Futures historical data (CFE)", CFE_HISTORY, "docs"),
        Link("VIX futures (the contract)", f"{CBOE}/tradable-products/vix/vix-futures", "reference"),
        Link("Historical data archive (2004 to 2013)",
             f"{CBOE}/markets/us/futures/market-statistics/historical-data/settlement-archive", "docs"),
        Link("CFE daily market statistics", f"{CBOE}/markets/us/futures/market-statistics/daily/futures", "docs"),
        Link("Cboe DataShop (data for sale)", "https://datashop.cboe.com/", "pricing"),
        *TERMS,
    ),
    areas=(
        Area(DETAIL, "a file a VX contract (with its trade-at-settlement, VXT), 2013 to now: its whole life by day",
             CFE_HISTORY,
             covered="a contract's file through its final settlement date (once a run): VX's daily bars, the "
                     "continuous chart VX1! built from them by the library's roll rules"),
        Area(MINI, "the Mini VIX futures' files (VXM with TAS, and the older VM)", CFE_HISTORY),
        Area(VOL_FUTURES, "futures on Cboe's other volatility indices: Nasdaq-100, Russell 2000, gold, crude oil, "
                          "emerging markets and Brazil ETFs", CFE_HISTORY),
        Area(CREDIT, "futures on Cboe's high yield and investment grade corporate bond indices and iBoxx emerging "
                     "market bonds", CFE_HISTORY),
        Area(RATES, "futures on the 7-day AMERIBOR rate", CFE_HISTORY),
        Area(CRYPTO, "bitcoin and ether futures, financially settled and continuous", CFE_HISTORY),
        Area(OTHER, "S&P 500 variance futures, the Magnificent 10 index and the Radar Logic RPX composite", CFE_HISTORY),
        Area(VOLUME_OI, "cfevoloi.csv: every product's daily volume and open interest, 2004 to now", CFE_HISTORY),
        Area(WINDOW, "the volume executed in each day's settlement window", CFE_HISTORY),
        Area(ARCHIVE, "volume and open interest by product for select products, 2004 to 2013, and VX's 2013 contracts",
             f"{CBOE}/markets/us/futures/market-statistics/historical-data/settlement-archive"),
        Area(MARGINS, "CFE's margin requirements as they were",
             f"{CBOE}/us/futures/market_statistics/historical_data/margin_archive/"),
        Area(IMBALANCE, "the VIX settlement's imbalance reports, 2008 to 2018",
             f"{CBOE}/us/futures/market_statistics/historical_data/historical-imbalance-reports/"),
        Area(SETTLEMENT, "the series of values VIX derivatives settle on",
             f"{CBOE}/markets/us/futures/market-statistics/vix-settlement-series"),
        Area(DAILY, "the day's volume and open interest by contract", f"{CBOE}/markets/us/futures/market-statistics/daily/futures"),
    ),
    calls=(
        Call("GET /{PRODUCT}/{PRODUCT}_{YYYY-MM-DD}.csv", "a contract's daily history, named by its final settlement "
             "date (VX/VX_2026-11-18.csv)", DETAIL, used="a VX contract's daily bars, one request a contract",
             docs=CFE_HISTORY),
        Call("GET /cfevoloi.csv", "every product's daily volume and open interest, 2004 to now", VOLUME_OI, docs=CFE_HISTORY),
        Call("GET /cfe_daily_settlement_window_executed_volume.csv", "each day's settlement-window volume", WINDOW,
             docs=CFE_HISTORY),
        Call("GET https://cdn.cboe.com/resources/futures/archive/volume-and-price/CFE_{M}{YY}_VX.csv", "a 2013 VX "
             "contract's archived file (CFE_F13_VX.csv to CFE_Z13_VX.csv)", ARCHIVE,
             docs=f"{CBOE}/markets/us/futures/market-statistics/historical-data/settlement-archive"),
    ),
    verified=VERIFIED,
)
