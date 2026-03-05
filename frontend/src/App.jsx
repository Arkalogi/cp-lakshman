import { useEffect, useMemo, useState } from "react";
import { api } from "./api";

const defaultUser = {
  first_name: "Trade",
  last_name: "Operator",
  username: `operator_${Date.now()}`,
  email: `operator_${Date.now()}@copytrade.local`,
  phone: `${Math.floor(9000000000 + Math.random() * 999999999)}`
};

export default function App() {
  const [watchlists, setWatchlists] = useState([]);
  const [strategies, setStrategies] = useState([]);
  const [signals, setSignals] = useState([]);
  const [selectedWatchlistId, setSelectedWatchlistId] = useState(null);
  const [selectedStrategyId, setSelectedStrategyId] = useState("");
  const [signalType, setSignalType] = useState("enter_position");
  const [searchText, setSearchText] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [watchlistName, setWatchlistName] = useState("");
  const [watchlistDescription, setWatchlistDescription] = useState("");
  const [toast, setToast] = useState("");
  const [busy, setBusy] = useState(false);

  const selectedWatchlist = useMemo(
    () => watchlists.find((w) => w.id === selectedWatchlistId) || null,
    [watchlists, selectedWatchlistId]
  );

  async function loadAll() {
    const [wl, st, sg] = await Promise.all([
      api.listWatchlists(),
      api.listStrategies(),
      api.listSignals()
    ]);
    setWatchlists(wl || []);
    setStrategies(st || []);
    setSignals((sg || []).slice().reverse().slice(0, 12));
    if (!selectedWatchlistId && wl?.length) {
      setSelectedWatchlistId(wl[0].id);
    }
    if (!selectedStrategyId && st?.length) {
      setSelectedStrategyId(String(st[0].id));
    }
  }

  useEffect(() => {
    loadAll().catch((e) => setToast(e.message));
  }, []);

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

  async function sendSignal(instrumentId, side) {
    if (!selectedStrategyId) {
      setToast("Select a strategy first.");
      return;
    }
    setBusy(true);
    try {
      await api.createSignal({
        type: signalType,
        strategy_id: Number(selectedStrategyId),
        instrument_id: instrumentId,
        side
      });
      const sg = await api.listSignals();
      setSignals((sg || []).slice().reverse().slice(0, 12));
      setToast(`${side.toUpperCase()} signal sent for ${instrumentId}.`);
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
          <p>Watchlists, discovery, and one-click signal dispatch.</p>
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
          <select value={signalType} onChange={(e) => setSignalType(e.target.value)}>
            <option value="enter_position">enter_position</option>
            <option value="exit_position">exit_position</option>
          </select>
          <button onClick={createQuickStrategy} disabled={busy}>
            Quick Strategy
          </button>
        </div>
      </header>

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
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {(selectedWatchlist.items || []).map((item) => (
                    <tr key={item.instrument_id}>
                      <td>{item.trading_symbol}</td>
                      <td>{item.instrument_id}</td>
                      <td className="actions">
                        <button
                          className="buy"
                          onClick={() => sendSignal(item.instrument_id, "buy")}
                          disabled={busy}
                        >
                          BUY
                        </button>
                        <button
                          className="sell"
                          onClick={() => sendSignal(item.instrument_id, "sell")}
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
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="panel">
          <h2>Recent Signals</h2>
          <div className="list scroll">
            {signals.map((s) => (
              <div key={s.id} className="signal-row">
                <span>{s.trading_symbol}</span>
                <b className={s.side === "buy" ? "buy-text" : "sell-text"}>
                  {s.side}
                </b>
              </div>
            ))}
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
