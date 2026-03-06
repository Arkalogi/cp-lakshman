import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "./api";

const INDEX_KEYS = ["NSE_INDEX|Nifty 50", "NSE_INDEX|Nifty Bank"];

const defaultUser = {
  first_name: "Trade",
  last_name: "Operator",
  username: `operator_${Date.now()}`,
  email: `operator_${Date.now()}@copytrade.local`,
  phone: `${Math.floor(9000000000 + Math.random() * 999999999)}`
};

function apiToWsUrl(apiBaseUrl) {
  if (apiBaseUrl.startsWith("https://")) {
    return apiBaseUrl.replace("https://", "wss://");
  }
  return apiBaseUrl.replace("http://", "ws://");
}

export default function App() {
  const [watchlists, setWatchlists] = useState([]);
  const [strategies, setStrategies] = useState([]);
  const [signals, setSignals] = useState([]);
  const [selectedWatchlistId, setSelectedWatchlistId] = useState(null);
  const [selectedStrategyId, setSelectedStrategyId] = useState("");
  const [searchText, setSearchText] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [watchlistName, setWatchlistName] = useState("");
  const [watchlistDescription, setWatchlistDescription] = useState("");
  const [livePrices, setLivePrices] = useState({});
  const [indexPrices, setIndexPrices] = useState({});
  const [pricePulse, setPricePulse] = useState({});
  const [priceDirection, setPriceDirection] = useState({});
  const [toast, setToast] = useState("");
  const [busy, setBusy] = useState(false);

  const wsRef = useRef(null);
  const subscribedRef = useRef(new Set());
  const lastPriceRef = useRef({});
  const desiredInstrumentIdsRef = useRef([]);

  const selectedWatchlist = useMemo(
    () => watchlists.find((w) => w.id === selectedWatchlistId) || null,
    [watchlists, selectedWatchlistId]
  );

  const watchedInstrumentIds = useMemo(() => {
    const ids = new Set();
    for (const item of selectedWatchlist?.items || []) {
      if (item?.instrument_id !== undefined && item?.instrument_id !== null) {
        ids.add(String(item.instrument_id));
      }
      if (item?.upstox_instrument_key) {
        ids.add(String(item.upstox_instrument_key));
      }
    }
    return Array.from(ids);
  }, [selectedWatchlist]);

  const entrySignals = useMemo(
    () =>
      signals
        .filter((s) => s.type === "enter_position")
        .slice()
        .sort((a, b) => b.id - a.id),
    [signals]
  );

  const exitSignals = useMemo(
    () =>
      signals
        .filter((s) => s.type === "exit_position")
        .slice()
        .sort((a, b) => b.id - a.id),
    [signals]
  );

  const hasExitByEntryId = useMemo(() => {
    const index = new Set();
    for (const signal of exitSignals) {
      if (signal.depends_on_signal_id) {
        index.add(signal.depends_on_signal_id);
      }
    }
    return index;
  }, [exitSignals]);

  async function loadAll() {
    const [wl, st, sg] = await Promise.all([
      api.listWatchlists(),
      api.listStrategies(),
      api.listSignals()
    ]);
    setWatchlists(wl || []);
    setStrategies(st || []);
    setSignals(sg || []);
    if (!selectedWatchlistId && wl?.length) {
      setSelectedWatchlistId(wl[0].id);
    }
    if (!selectedStrategyId && st?.length) {
      setSelectedStrategyId(String(st[0].id));
    }
  }

  function syncWsSubscriptions(nextIds) {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    const current = subscribedRef.current;
    const target = new Set([...INDEX_KEYS, ...nextIds.map(String)]);
    const toSubscribe = [...target].filter((id) => !current.has(id));
    const toUnsubscribe = [...current].filter((id) => !target.has(id));

    if (toSubscribe.length) {
      ws.send(
        JSON.stringify({
          action: "subscribe",
          instrument_ids: toSubscribe
        })
      );
      toSubscribe.forEach((id) => current.add(id));
    }
    if (toUnsubscribe.length) {
      ws.send(
        JSON.stringify({
          action: "unsubscribe",
          instrument_ids: toUnsubscribe
        })
      );
      toUnsubscribe.forEach((id) => current.delete(id));
    }
  }

  useEffect(() => {
    loadAll().catch((e) => setToast(e.message));
  }, []);

  useEffect(() => {
    const apiBase = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
    const ws = new WebSocket(`${apiToWsUrl(apiBase)}/ws/prices`);
    wsRef.current = ws;

    ws.onopen = () => {
      syncWsSubscriptions(desiredInstrumentIdsRef.current);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "price" && data.instrument_id) {
          const instrumentId = String(data.instrument_id);
          const nextPrice = Number(data.price);
          const prevPrice = lastPriceRef.current[instrumentId];
          if (Number.isFinite(nextPrice) && Number.isFinite(prevPrice) && nextPrice !== prevPrice) {
            setPriceDirection((prev) => ({
              ...prev,
              [instrumentId]: nextPrice > prevPrice ? "up" : "down"
            }));
            setPricePulse((prev) => ({
              ...prev,
              [instrumentId]: (prev[instrumentId] || 0) + 1
            }));
          }
          lastPriceRef.current[instrumentId] = nextPrice;
          setLivePrices((prev) => ({
            ...prev,
            [instrumentId]: nextPrice
          }));
          if (INDEX_KEYS.includes(instrumentId)) {
            setIndexPrices((prev) => ({
              ...prev,
              [instrumentId]: nextPrice
            }));
          }
        }
      } catch (error) {
        setToast("Invalid websocket payload");
      }
    };

    ws.onerror = () => {
      setToast("Price websocket disconnected");
    };

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      wsRef.current = null;
      subscribedRef.current = new Set();
      lastPriceRef.current = {};
      desiredInstrumentIdsRef.current = [];
    };
  }, []);

  useEffect(() => {
    desiredInstrumentIdsRef.current = watchedInstrumentIds;
    syncWsSubscriptions(watchedInstrumentIds);
  }, [selectedWatchlistId, watchedInstrumentIds.join(",")]);

  async function createQuickStrategy() {
    setBusy(true);
    try {
      const user = await api.createUser(defaultUser);
      const strategy = await api.createStrategy({
        name: `Auto Strategy ${Date.now()}`,
        description: "Created from CopyTrade Desk",
        config: "{}",
        user_id: user.id
      });
      setStrategies((prev) => [strategy, ...prev]);
      setSelectedStrategyId(String(strategy.id));
      setToast("Strategy created and selected.");
    } catch (e) {
      setToast(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function createWatchlist() {
    if (!watchlistName.trim()) {
      setToast("Watchlist name is required.");
      return;
    }
    setBusy(true);
    try {
      const wl = await api.createWatchlist({
        name: watchlistName.trim(),
        description: watchlistDescription.trim() || null,
        instruments: []
      });
      setWatchlists((prev) => [wl, ...prev]);
      setSelectedWatchlistId(wl.id);
      setWatchlistName("");
      setWatchlistDescription("");
      setToast("Watchlist created.");
    } catch (e) {
      setToast(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function searchInstruments() {
    if (!searchText.trim()) {
      setSearchResults([]);
      return;
    }
    try {
      const result = await api.searchInstruments(searchText.trim(), 30);
      setSearchResults(result.items || []);
    } catch (e) {
      setToast(e.message);
    }
  }

  async function addToWatchlist(instrumentId) {
    if (!selectedWatchlistId) {
      setToast("Select a watchlist first.");
      return;
    }
    setBusy(true);
    try {
      const updated = await api.addWatchlistItem(selectedWatchlistId, instrumentId);
      setWatchlists((prev) =>
        prev.map((w) => (w.id === selectedWatchlistId ? updated : w))
      );
      setToast("Instrument added.");
    } catch (e) {
      setToast(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function removeFromWatchlist(instrumentId) {
    if (!selectedWatchlistId) return;
    setBusy(true);
    try {
      const updated = await api.removeWatchlistItem(selectedWatchlistId, instrumentId);
      setWatchlists((prev) =>
        prev.map((w) => (w.id === selectedWatchlistId ? updated : w))
      );
      setToast("Instrument removed.");
    } catch (e) {
      setToast(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function sendEntrySignal(instrumentId, side) {
    if (!selectedStrategyId) {
      setToast("Select a strategy first.");
      return;
    }
    setBusy(true);
    try {
      await api.createSignal({
        type: "enter_position",
        strategy_id: Number(selectedStrategyId),
        instrument_id: instrumentId,
        side
      });
      const sg = await api.listSignals();
      setSignals(sg || []);
      setToast(`${side.toUpperCase()} entry signal sent for ${instrumentId}.`);
    } catch (e) {
      setToast(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function sendExitSignal(entrySignal) {
    if (!entrySignal) return;
    if (hasExitByEntryId.has(entrySignal.id)) return;
    setBusy(true);
    try {
      const oppositeSide = entrySignal.side === "buy" ? "sell" : "buy";
      await api.createSignal({
        type: "exit_position",
        strategy_id: entrySignal.strategy_id,
        instrument_id: entrySignal.instrument_id,
        side: oppositeSide,
        depends_on_signal_id: entrySignal.id
      });
      const sg = await api.listSignals();
      setSignals(sg || []);
      setToast(`Exit signal created for entry #${entrySignal.id}.`);
    } catch (e) {
      setToast(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="shell">
      <header className="top">
        <div>
          <h1>CopyTrade Desk</h1>
          <p>Watchlists, discovery, live prices, and signal dispatch.</p>
        </div>
        <div className="signal-config">
          <select
            value={selectedStrategyId}
            onChange={(e) => setSelectedStrategyId(e.target.value)}
          >
            <option value="">Select Strategy</option>
            {strategies.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} (#{s.id})
              </option>
            ))}
          </select>
          <button onClick={createQuickStrategy} disabled={busy}>
            Quick Strategy
          </button>
        </div>
      </header>
      <section className="index-strip">
        {INDEX_KEYS.map((indexKey) => (
          <div key={indexKey} className="index-card">
            <span>{indexKey.replace("NSE_INDEX|", "")}</span>
            <b>{Number.isFinite(indexPrices[indexKey]) ? indexPrices[indexKey].toFixed(2) : "--"}</b>
          </div>
        ))}
      </section>

      <main className="grid">
        <section className="panel">
          <h2>Watchlists</h2>
          <div className="row">
            <input
              value={watchlistName}
              onChange={(e) => setWatchlistName(e.target.value)}
              placeholder="Watchlist name"
            />
            <button onClick={createWatchlist} disabled={busy}>
              Create
            </button>
          </div>
          <input
            value={watchlistDescription}
            onChange={(e) => setWatchlistDescription(e.target.value)}
            placeholder="Description (optional)"
          />
          <div className="list">
            {watchlists.map((w) => (
              <button
                key={w.id}
                className={w.id === selectedWatchlistId ? "pill active" : "pill"}
                onClick={() => setSelectedWatchlistId(w.id)}
              >
                {w.name}
              </button>
            ))}
          </div>
        </section>

        <section className="panel">
          <h2>Instrument Search</h2>
          <div className="row">
            <input
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              placeholder="Search by trading symbol..."
            />
            <button onClick={searchInstruments} disabled={busy}>
              Search
            </button>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Type</th>
                  <th>Exchange</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {searchResults.map((item) => (
                  <tr key={item.instrument_id}>
                    <td>{item.trading_symbol}</td>
                    <td>{item.instrument_type}</td>
                    <td>{item.exchange}</td>
                    <td>
                      <button
                        onClick={() => addToWatchlist(item.instrument_id)}
                        disabled={busy}
                      >
                        Add
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="panel wide">
          <h2>Selected Watchlist</h2>
          {!selectedWatchlist && <p>Select or create a watchlist.</p>}
          {selectedWatchlist && (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Instrument ID</th>
                    <th>Live Price</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {(selectedWatchlist.items || []).map((item) => {
                    const live = Number.isFinite(livePrices[String(item.instrument_id)])
                      ? livePrices[String(item.instrument_id)]
                      : livePrices[String(item.upstox_instrument_key || "")];
                    const pulse = pricePulse[String(item.instrument_id)] || 0;
                    const direction = priceDirection[String(item.instrument_id)];
                    const hasLive = Number.isFinite(live);
                    const badgeClass = [
                      "price-badge",
                      hasLive ? "live" : "",
                      direction ? `tick-${direction}` : ""
                    ]
                      .filter(Boolean)
                      .join(" ");
                    return (
                      <tr key={item.instrument_id}>
                        <td>{item.trading_symbol}</td>
                        <td>{item.instrument_id}</td>
                        <td>
                          <span key={`${item.instrument_id}-${pulse}`} className={badgeClass}>
                            {Number.isFinite(live) ? live.toFixed(2) : "--"}
                          </span>
                        </td>
                        <td className="actions">
                          <button
                            className="buy"
                            onClick={() => sendEntrySignal(item.instrument_id, "buy")}
                            disabled={busy}
                          >
                            BUY
                          </button>
                          <button
                            className="sell"
                            onClick={() => sendEntrySignal(item.instrument_id, "sell")}
                            disabled={busy}
                          >
                            SELL
                          </button>
                          <button
                            className="ghost"
                            onClick={() => removeFromWatchlist(item.instrument_id)}
                            disabled={busy}
                          >
                            Remove
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="panel wide">
          <h2>Signals</h2>
          <div className="signal-columns">
            <div className="signal-column entry-col">
              <h3>Entry Signals</h3>
              <div className="signal-list">
                {entrySignals.map((s) => {
                  const exited = hasExitByEntryId.has(s.id);
                  return (
                    <div key={s.id} className="signal-card entry">
                      <div>
                        <b>#{s.id}</b> {s.trading_symbol}
                      </div>
                      <div className="signal-meta">
                        <span className={s.side === "buy" ? "buy-text" : "sell-text"}>
                          {s.side}
                        </span>
                        <button
                          className="exit-btn"
                          disabled={busy || exited}
                          onClick={() => sendExitSignal(s)}
                        >
                          {exited ? "Exited" : "Exit"}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
            <div className="signal-column exit-col">
              <h3>Exit Signals</h3>
              <div className="signal-list">
                {exitSignals.map((s) => (
                  <div key={s.id} className="signal-card exit">
                    <div>
                      <b>#{s.id}</b> {s.trading_symbol}
                    </div>
                    <div className="signal-meta">
                      <span className={s.side === "buy" ? "buy-text" : "sell-text"}>
                        {s.side}
                      </span>
                      <span className="depends-on">
                        from #{s.depends_on_signal_id || "-"}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      </main>

      {toast && (
        <div className="toast" onAnimationEnd={() => setToast("")}>
          {toast}
        </div>
      )}
    </div>
  );
}
