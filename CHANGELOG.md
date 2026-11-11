# Changelog

## 0.3.0 (2026-11-11)

Its APIs on its page (plugin API 2.2, liminal-libs 1.49.0; the user: "each plugin should reflect the the API its attached
to, and present links that provide documentation, the plugin interface should more or less contain what it already has,
BUT, it should also expose more of what the API is about"). Each feed declares what it talks to (`apis`), read from
Cboe's own pages on 2026-11-11 (`apis.py`):

- `cboe`: **Cboe's index history files** (cdn-api.cboe.com), with the VIX historical data page that links them, Cboe
  Global Indices, the VIX products, the indices' system status notices, DataShop and Cboe's terms; the indices in nine
  parts (VIX and its term structure, VVIX and SKEW, index and ETF volatility, single stocks, the strategy benchmarks,
  the archives, the delayed quotes, the Global Indices Feed, DataShop); the one call it makes (`{CODE}_History.csv`,
  each of its 21 indices found on Cboe's CDN) beside the archives' files;
- `cboefutures`: **the Cboe Futures Exchange's historical data** (cdn.cboe.com), with CFE's historical data page, the
  VIX futures page, the 2004-2013 archive, the daily statistics and the terms; the exchange's files in fourteen parts
  (VX's contract files, the other products its page lists, volume and open interest, the settlement window, the
  archives of settlement, margins and imbalances); the one call it makes (`{PRODUCT}/{PRODUCT}_{YYYY-MM-DD}.csv`) beside
  the others.

The cards say what Cboe's terms allow (the site's materials for personal, non-commercial use) and what the files' server
does: CFE's page offers contract files from 2013, and a contract without a file answers 403, not 404 (VX before 2013;
said on the card and in the README, the feed asks as before). `api_facts()` says, for each feed, what its client learned
while it ran, asking nothing: the requests made, the last answer's clock, the last file's change (`facts.py`: the client
held weakly, its last words kept when it goes). Tests: the contract at 2.2, the cards' calls the ones each source asks
for, the facts, and every page they name answering (only with `LIMINAL_VENDOR_PAGES=1`). On liminal-libs 1.49.0 or
later; every behaviour, limit and string as in 0.2.0.

## 0.2.0 (2026-11-03)

Renamed `plugin-integrator-cboe` (the package `plugin_integrator_cboe`; it was `liminal-plugin-cboe`) on 2026-11-03: the naming by system (plugins are `plugin-<app>-<name>`), on liminal-libs 1.4.0 (`liminal_libs`, the library renamed with it).

The plugin is a class on plugin API 2.0 (the class contract, liminal-libs 1.3.0; the user: "all the plugins under
liminal should basically follow inheritance/oop paradigm"): its two feeds are instances of `CboeIndices` and
`CboeFutures`, both on `CboeFeed`, a `PublicFeedPlugin` (the source class on the contract's public client at its
base URL; Cboe's files official, one file a symbol), what each declares its class attributes and what it does its
methods (`markets`, `carries`; the futures' `build` holds its client under Cboe's account, one public file server).
The futures feed declares its publication delay itself (`delays`: `cboe-futures`, end of day; the library's row
stays). `INDICES` and `FUTURES` stay the module's instances, `PLUGINS` the pair; every fact, limit and string is as
in 1.3.1. Its version is the release's, 0.2.0, as every Liminal plugin's on `release/0.2.0`; requires liminal-libs
1.3.0.

## 1.3.1 (2026-11-03)

The VIX futures feed's limits line says it shares Cboe's window (one public server), as the Plugins view lists each
feed's.

## 1.3.0 (2026-11-02)

VIX futures (the user: "lets include futures"): a second feed of the plugin, `cboefutures`, reads Cboe's daily
file of each VX contract (`VX/VX_<final settlement date>.csv`, from 2004-03-26: Trade Date, Open, High, Low, Close,
Settle, Total Volume), asked for by the library's contract names (VXX6) through Cboe's settlement rule (the
Wednesday 30 days before the next month's third Friday, holiday-shifted), so the continuous chart `VX1!` is
rolled by volume from them; a day without a trade is its settlement at all four prices with no volume. The
feed is live (its front contracts trade on), on the same public server, its market `cfe`, its exchange the
Cboe Futures Exchange (XCBF). The plugin's entry point is now the module (`PLUGINS`: `cboe`, `cboefutures`);
plugin API 1.12.

## 1.2.1 (2026-11-02)

The plugin imports the library as `liminal_libs` and depends on liminal-libs (the app, renamed liminal-charts, is no longer needed to run the tests; the user, 2026-11-02: "lets rename the app to liminal-charts").

## 1.2.0 (2026-10-31)

- Released as its own package, `plugin-integrator-cboe`, registered under the entry point group
  `liminal.providers`; its version is the distribution's.
- Its plan and request caps are in it (`TIER`, `PER_RUN`, `PER_DAY`), no longer in the app's
  `config.PUBLIC_FEEDS`.
- Plugin API 1.6.
- Renamed with the app before its first publication (massive -> liminal, 2026-11-01): the
  package was to be `massive-plugin-cboe`.

## 1.1.0 (2026-10-31)

- Built into the app (then massive-collate): its source class and client in its module (plugin API 1.6).

## 1.0.0 (2026-10-29)

- Built into the app (then massive-collate): the first versioned release (plugin API 1.0).
