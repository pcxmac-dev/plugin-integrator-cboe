# plugin-integrator-cboe

Cboe for [Liminal](https://github.com/pcxmac-dev/liminal-charts): the daily history of Cboe's indices
(VIX from 1990, VIX9D, VIX3M, VVIX, SKEW and the other volatility indices), read from Cboe's public
history files. No key. It is a closed archive: once an index's history is in, it is not asked again.

And VIX futures (`VX1!`, `VX2!`: a second feed of the plugin, `cboefutures`): Cboe publishes a daily
file for each contract (VX traded from March 2004; CFE's page offers the contract files from 2013),
which the feed reads by the contract's final settlement date; the library rolls the continuous chart
from the contracts by volume. The feed is live: the contracts trading on get their new days each run.
Daily bars only.

A Liminal provider plugin released on its own. The app finds it through the entry point group
`liminal.providers` and lists it on the Plugins view and in `liminal-charts plugins`
as `package: plugin-integrator-cboe`, with this package's version.

## Its API

Each feed attaches to Cboe's public files (no key); its page in every app shows them (`apis`), with every part of each,
the files it asks for among the rest, and what its client learned (`api_facts()`):

- `cboe`: Cboe's index history files (`https://cdn-api.cboe.com/api/global/us_indices/daily_prices/{CODE}_History.csv`),
  linked from the [VIX historical data](https://www.cboe.com/tradable-products/vix/vix-historical-data) page; the
  indices described on [Cboe Global Indices](https://www.cboe.com/global-indices).
- `cboefutures`: the Cboe Futures Exchange's
  [historical data](https://www.cboe.com/markets/us/futures/market-statistics/historical-data/futures), a file a contract
  (`https://cdn.cboe.com/data/us/futures/market_statistics/historical_data/VX/VX_{YYYY-MM-DD}.csv`, from 2013; a contract
  without a file answers 403); the [VIX futures](https://www.cboe.com/tradable-products/vix/vix-futures) contract.
- Cboe's [terms](https://www.cboe.com/terms) and [use of content](https://www.cboe.com/use-of-content): the site's
  materials for personal, non-commercial use; anything else by Cboe's prior written consent.

## Install

Into the app's environment, from the app's folder:

```powershell
.venv\Scripts\python.exe -m pip install "plugin-integrator-cboe @ git+https://github.com/pcxmac-dev/plugin-integrator-cboe@v0.3.0"
```

or with the app's plugins (`pip install -e ".[plugins]"` in liminal-charts). The app loads it on its next
start.

## Compatibility

It is written for plugin API 2.2, the class contract (`PLUGINS`: each feed an instance of a `FeedPlugin`
subclass, `CboeIndices` and `CboeFutures` on the package's `CboeFeed`, a `PublicFeedPlugin`, each declaring what it
attaches to, `apis`; liminal-libs 1.49.0 or later). An app offering 2.2 or a later 2.x loads it; an app of another
major, or one older than 2.2, leaves it out and says why on the Plugins view.

## Develop

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install "liminal-libs @ git+https://github.com/pcxmac-dev/liminal-libs@main"
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m pytest -q
```

Tests never send requests (a fake session answers) and never read your keys.
