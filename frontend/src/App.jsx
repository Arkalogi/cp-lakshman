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
  if (apiBaseUrl.startsWith("https://")) return apiBaseUrl.replace("https://", "wss://");
  return apiBaseUrl.replace("http://", "ws://");
}

// ── Nav Item ──────────────────────────────────────────────────────────────────
function NavItem({ icon, label, active, onClick }) {
  return (
    <div
      onClick={onClick}
      className={`flex items-center px-6 py-3 cursor-pointer transition-colors duration-100 ${
        active
          ? "bg-surface-container text-primary border-l-2 border-primary font-bold"
          : "text-on-surface-variant hover:bg-surface-container-low border-l-2 border-transparent"
      }`}
    >
      <span className="material-symbols-outlined mr-3 text-[18px]">{icon}</span>
      <span className="font-label-caps text-label-caps uppercase">{label}</span>
    </div>
  );
}

// ── Section Card ──────────────────────────────────────────────────────────────
function Card({ title, action, children }) {
  return (
    <div className="bg-surface border border-border-color">
      <div className="px-4 py-3 border-b border-border-color flex justify-between items-center bg-surface-container-lowest">
        <h3 className="font-heading-section text-heading-section uppercase">{title}</h3>
        {action}
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

// ── Stitch Input ──────────────────────────────────────────────────────────────
function StitchInput({ value, onChange, placeholder, type = "text", className = "" }) {
  return (
    <input
      type={type}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      className={`w-full bg-surface-container-low border border-outline-variant focus:border-primary focus:ring-0 font-data-mono text-data-mono px-2 py-1.5 text-[12px] outline-none ${className}`}
    />
  );
}

// ── Stitch Button ─────────────────────────────────────────────────────────────
function StitchBtn({ onClick, disabled, children, variant = "primary", className = "" }) {
  const base = "font-label-caps text-label-caps uppercase px-3 py-2 transition-colors active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed";
  const variants = {
    primary: "bg-primary text-white hover:bg-primary-container",
    success: "bg-success text-white hover:opacity-90",
    danger:  "bg-danger text-white hover:opacity-90",
    ghost:   "bg-surface-container text-on-surface-variant hover:bg-surface-container-high border border-border-color",
  };
  return (
    <button onClick={onClick} disabled={disabled} className={`${base} ${variants[variant]} ${className}`}>
      {children}
    </button>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [activeNav, setActiveNav] = useState("dashboard");
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
  const [previousClose, setPreviousClose] = useState({});
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
      if (item?.instrument_id !== undefined && item?.instrument_id !== null)
        ids.add(String(item.instrument_id));
      if (item?.upstox_instrument_key)
        ids.add(String(item.upstox_instrument_key));
    }
    return Array.from(ids);
  }, [selectedWatchlist]);

  const entrySignals = useMemo(
    () => signals.filter((s) => s.type === "enter_position").slice().sort((a, b) => b.id - a.id),
    [signals]
  );
  const exitSignals = useMemo(
    () => signals.filter((s) => s.type === "exit_position").slice().sort((a, b) => b.id - a.id),
    [signals]
  );
  const hasExitByEntryId = useMemo(() => {
    const index = new Set();
    for (const signal of exitSignals) {
      if (signal.depends_on_signal_id) index.add(signal.depends_on_signal_id);
    }
    return index;
  }, [exitSignals]);

  async function loadAll() {
    const [wl, st, sg] = await Promise.all([
      api.listWatchlists(), api.listStrategies(), api.listSignals()
    ]);
    setWatchlists(wl || []);
    setStrategies(st || []);
    setSignals(sg || []);
    if (!selectedWatchlistId && wl?.length) setSelectedWatchlistId(wl[0].id);
    if (!selectedStrategyId && st?.length) setSelectedStrategyId(String(st[0].id));
  }

  function syncWsSubscriptions(nextIds) {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    const current = subscribedRef.current;
    const target = new Set([...INDEX_KEYS, ...nextIds.map(String)]);
    const toSubscribe = [...target].filter((id) => !current.has(id));
    const toUnsubscribe = [...current].filter((id) => !target.has(id));
    if (toSubscribe.length) {
      ws.send(JSON.stringify({ action: "subscribe", instrument_ids: toSubscribe }));
      toSubscribe.forEach((id) => current.add(id));
    }
    if (toUnsubscribe.length) {
      ws.send(JSON.stringify({ action: "unsubscribe", instrument_ids: toUnsubscribe }));
      toUnsubscribe.forEach((id) => current.delete(id));
    }
  }

  useEffect(() => { loadAll().catch((e) => setToast(e.message)); }, []);

  useEffect(() => {
    const apiBase = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
    const ws = new WebSocket(`${apiToWsUrl(apiBase)}/ws/prices`);
    wsRef.current = ws;
    ws.onopen = () => syncWsSubscriptions(desiredInstrumentIdsRef.current);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "price" && data.instrument_id) {
          const instrumentId = String(data.instrument_id);
          const nextPrice = Number(data.price);
          const prevPrice = lastPriceRef.current[instrumentId];
          if (Number.isFinite(nextPrice) && Number.isFinite(prevPrice) && nextPrice !== prevPrice) {
            setPriceDirection((prev) => ({ ...prev, [instrumentId]: nextPrice > prevPrice ? "up" : "down" }));
            setPricePulse((prev) => ({ ...prev, [instrumentId]: (prev[instrumentId] || 0) + 1 }));
          }
          lastPriceRef.current[instrumentId] = nextPrice;
          setLivePrices((prev) => ({ ...prev, [instrumentId]: nextPrice }));
          const nextPreviousClose = Number(data.previous_close);
          if (Number.isFinite(nextPreviousClose) && nextPreviousClose > 0) {
            setPreviousClose((prev) => ({ ...prev, [instrumentId]: nextPreviousClose }));
          }
          if (INDEX_KEYS.includes(instrumentId)) {
            setIndexPrices((prev) => ({ ...prev, [instrumentId]: nextPrice }));
          }
        }
      } catch { setToast("Invalid websocket payload"); }
    };
    ws.onerror = () => setToast("Price websocket disconnected");
    return () => {
      wsRef.current?.close();
      wsRef.current = null;
      subscribedRef.current = new Set();
      lastPriceRef.current = {};
      desiredInstrumentIdsRef.current = [];
      setPreviousClose({});
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
    } catch (e) { setToast(e.message); }
    finally { setBusy(false); }
  }

  async function createWatchlist() {
    if (!watchlistName.trim()) { setToast("Watchlist name is required."); return; }
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
    } catch (e) { setToast(e.message); }
    finally { setBusy(false); }
  }

  async function searchInstruments() {
    if (!searchText.trim()) { setSearchResults([]); return; }
    try {
      const result = await api.searchInstruments(searchText.trim(), 30);
      setSearchResults(result.items || []);
    } catch (e) { setToast(e.message); }
  }

  async function addToWatchlist(instrumentId) {
    if (!selectedWatchlistId) { setToast("Select a watchlist first."); return; }
    setBusy(true);
    try {
      const updated = await api.addWatchlistItem(selectedWatchlistId, instrumentId);
      setWatchlists((prev) => prev.map((w) => (w.id === selectedWatchlistId ? updated : w)));
      setToast("Instrument added.");
    } catch (e) { setToast(e.message); }
    finally { setBusy(false); }
  }

  async function removeFromWatchlist(instrumentId) {
    if (!selectedWatchlistId) return;
    setBusy(true);
    try {
      const updated = await api.removeWatchlistItem(selectedWatchlistId, instrumentId);
      setWatchlists((prev) => prev.map((w) => (w.id === selectedWatchlistId ? updated : w)));
      setToast("Instrument removed.");
    } catch (e) { setToast(e.message); }
    finally { setBusy(false); }
  }

  async function sendEntrySignal(instrumentId, side) {
    if (!selectedStrategyId) { setToast("Select a strategy first."); return; }
    setBusy(true);
    try {
      await api.createSignal({ type: "enter_position", strategy_id: Number(selectedStrategyId), instrument_id: instrumentId, side });
      const sg = await api.listSignals();
      setSignals(sg || []);
      setToast(`${side.toUpperCase()} entry signal sent.`);
    } catch (e) { setToast(e.message); }
    finally { setBusy(false); }
  }

  async function sendExitSignal(entrySignal) {
    if (!entrySignal || hasExitByEntryId.has(entrySignal.id)) return;
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
    } catch (e) { setToast(e.message); }
    finally { setBusy(false); }
  }

  // ── Index strip helper ──────────────────────────────────────────────────────
  function IndexCard({ indexKey }) {
    const live = indexPrices[indexKey];
    const prev = previousClose[indexKey];
    const diff = Number.isFinite(live) && Number.isFinite(prev) ? live - prev : null;
    const pct = Number.isFinite(diff) && Number.isFinite(prev) && prev !== 0 ? (diff / prev) * 100 : null;
    const isUp = Number.isFinite(diff) && diff > 0;
    const isDown = Number.isFinite(diff) && diff < 0;
    return (
      <div className="bg-surface border border-border-color p-4 flex justify-between items-center">
        <div>
          <p className="font-label-caps text-label-caps text-outline uppercase">{indexKey.replace("NSE_INDEX|", "")}</p>
          <p className={`font-data-mono text-[18px] font-bold mt-1 ${isUp ? "text-success" : isDown ? "text-danger" : "text-on-surface"}`}>
            {Number.isFinite(live) ? live.toFixed(2) : "--"}
          </p>
        </div>
        <div className="text-right">
          <p className={`font-data-mono text-[11px] font-bold ${isUp ? "text-success" : isDown ? "text-danger" : "text-outline"}`}>
            {Number.isFinite(diff) && Number.isFinite(pct)
              ? `${diff >= 0 ? "+" : ""}${diff.toFixed(2)} (${pct >= 0 ? "+" : ""}${pct.toFixed(2)}%)`
              : "--"}
          </p>
          <p className="font-data-micro text-data-micro text-outline mt-1 uppercase">Today</p>
        </div>
      </div>
    );
  }

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div className="bg-background text-on-surface font-body-standard selection:bg-primary-container selection:text-on-primary-container">

      {/* ── Sidebar ── */}
      <aside className="fixed left-0 top-0 h-full w-[240px] z-50 bg-surface border-r border-border-color flex flex-col py-4">
        <div className="px-6 mb-8">
          <h1 className="font-heading-display text-heading-display font-bold text-primary uppercase tracking-tighter">CopyTrade</h1>
          <p className="font-body-compact text-body-compact text-outline">Admin Console</p>
        </div>
        <nav className="flex-grow">
          <NavItem icon="dashboard"    label="Dashboard"    active={activeNav === "dashboard"}   onClick={() => setActiveNav("dashboard")} />
          <NavItem icon="query_stats"  label="Watchlists"   active={activeNav === "watchlists"}  onClick={() => setActiveNav("watchlists")} />
          <NavItem icon="search"       label="Instruments"  active={activeNav === "instruments"} onClick={() => setActiveNav("instruments")} />
          <NavItem icon="bolt"         label="Signals"      active={activeNav === "signals"}     onClick={() => setActiveNav("signals")} />
          <NavItem icon="settings"     label="Settings"     active={activeNav === "settings"}    onClick={() => setActiveNav("settings")} />
        </nav>
        <div className="px-6 mt-auto space-y-2 border-t border-border-color pt-4">
          <div className="flex items-center py-2 text-on-surface-variant hover:text-primary cursor-pointer transition-all">
            <span className="material-symbols-outlined mr-3 text-[18px]">help</span>
            <span className="font-body-compact text-body-compact">Help Center</span>
          </div>
          <div className="flex items-center py-2 text-on-surface-variant hover:text-danger cursor-pointer transition-all">
            <span className="material-symbols-outlined mr-3 text-[18px]">logout</span>
            <span className="font-body-compact text-body-compact">Sign Out</span>
          </div>
        </div>
      </aside>

      {/* ── Top Header ── */}
      <header className="fixed top-0 right-0 left-[240px] z-40 h-14 bg-surface border-b border-border-color flex items-center justify-between px-4">
        <div className="flex items-center gap-4">
          <h2 className="font-heading-section text-heading-section uppercase text-on-surface">Admin Console</h2>
          <div className="relative">
            <span className="absolute inset-y-0 left-3 flex items-center text-outline">
              <span className="material-symbols-outlined text-[16px]">search</span>
            </span>
            <input
              className="pl-9 pr-4 py-1.5 bg-surface-container-low border border-outline-variant focus:border-primary focus:ring-0 font-data-mono text-[12px] w-56 outline-none"
              placeholder="Search instruments..."
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && searchInstruments()}
            />
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-3 py-1 bg-success/10 border border-success/20">
            <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse"></span>
            <span className="font-data-mono text-data-mono text-success">SYSTEM ONLINE</span>
          </div>
          {/* Strategy selector */}
          <div className="flex items-center gap-2">
            <select
              value={selectedStrategyId}
              onChange={(e) => setSelectedStrategyId(e.target.value)}
              className="bg-surface-container-low border border-outline-variant font-data-mono text-[11px] px-2 py-1.5 text-on-surface outline-none focus:border-primary"
            >
              <option value="">Select Strategy</option>
              {strategies.map((s) => (
                <option key={s.id} value={s.id}>{s.name} (#{s.id})</option>
              ))}
            </select>
            <StitchBtn onClick={createQuickStrategy} disabled={busy} variant="ghost">
              + Quick
            </StitchBtn>
          </div>
          <span className="material-symbols-outlined p-2 text-on-surface-variant hover:text-primary cursor-pointer text-[20px]">notifications</span>
        </div>
      </header>

      {/* ── Main Content ── */}
      <main className="ml-[240px] pt-14 min-h-screen data-grid-bg">
        <div className="p-6 space-y-6">

          {/* Index Strip */}
          <div className="grid grid-cols-2 gap-4">
            {INDEX_KEYS.map((k) => <IndexCard key={k} indexKey={k} />)}
          </div>

          {/* 3-col grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">

            {/* ── Col 1: Watchlists ── */}
            <div className="space-y-6">
              <Card title="Watchlists">
                <div className="space-y-3">
                  <StitchInput
                    value={watchlistName}
                    onChange={(e) => setWatchlistName(e.target.value)}
                    placeholder="Watchlist name"
                  />
                  <StitchInput
                    value={watchlistDescription}
                    onChange={(e) => setWatchlistDescription(e.target.value)}
                    placeholder="Description (optional)"
                  />
                  <StitchBtn onClick={createWatchlist} disabled={busy} className="w-full">
                    Create Watchlist
                  </StitchBtn>
                  <div className="pt-2 flex flex-wrap gap-2">
                    {watchlists.map((w) => (
                      <button
                        key={w.id}
                        onClick={() => setSelectedWatchlistId(w.id)}
                        className={`font-label-caps text-label-caps uppercase px-3 py-1.5 transition-colors ${
                          w.id === selectedWatchlistId
                            ? "bg-primary text-white"
                            : "bg-surface-container text-on-surface-variant hover:bg-surface-container-high border border-border-color"
                        }`}
                      >
                        {w.name}
                      </button>
                    ))}
                  </div>
                </div>
              </Card>

              {/* Instrument Search */}
              <Card title="Instrument Search">
                <div className="space-y-3">
                  <div className="flex gap-2">
                    <StitchInput
                      value={searchText}
                      onChange={(e) => setSearchText(e.target.value)}
                      placeholder="Trading symbol..."
                    />
                    <StitchBtn onClick={searchInstruments} disabled={busy}>
                      Go
                    </StitchBtn>
                  </div>
                  <div className="max-h-[280px] overflow-y-auto divide-y divide-border-color">
                    {searchResults.length === 0 && (
                      <p className="font-body-compact text-body-compact text-outline py-4 text-center">
                        No results. Enter a symbol above.
                      </p>
                    )}
                    {searchResults.map((item) => (
                      <div key={item.instrument_id} className="flex items-center justify-between py-2 hover:bg-surface-container-low transition-colors px-1">
                        <div>
                          <p className="font-data-mono text-data-mono font-bold">{item.trading_symbol}</p>
                          <p className="font-label-caps text-[9px] text-outline uppercase">{item.instrument_type} · {item.exchange}</p>
                        </div>
                        <StitchBtn onClick={() => addToWatchlist(item.instrument_id)} disabled={busy} variant="ghost">
                          + Add
                        </StitchBtn>
                      </div>
                    ))}
                  </div>
                </div>
              </Card>
            </div>

            {/* ── Col 2: Selected Watchlist (live prices) ── */}
            <div className="lg:col-span-1">
              <Card
                title={selectedWatchlist ? selectedWatchlist.name : "Watchlist"}
                action={<span className="font-data-micro text-data-micro text-outline uppercase">Live Prices</span>}
              >
                {!selectedWatchlist ? (
                  <p className="font-body-compact text-body-compact text-outline text-center py-6">
                    Select or create a watchlist.
                  </p>
                ) : (
                  <div className="max-h-[480px] overflow-y-auto divide-y divide-border-color">
                    {(selectedWatchlist.items || []).map((item) => {
                      const instrumentId = String(item.instrument_id);
                      const upstoxKey = String(item.upstox_instrument_key || "");
                      const live = Number.isFinite(livePrices[instrumentId]) ? livePrices[instrumentId] : livePrices[upstoxKey];
                      const prevClose = Number.isFinite(previousClose[instrumentId]) ? previousClose[instrumentId] : previousClose[upstoxKey];
                      const dayDiff = Number.isFinite(live) && Number.isFinite(prevClose) ? live - prevClose : null;
                      const dayPct = Number.isFinite(dayDiff) && Number.isFinite(prevClose) && prevClose !== 0 ? (dayDiff / prevClose) * 100 : null;
                      const pulse = pricePulse[instrumentId] || pricePulse[upstoxKey] || 0;
                      const direction = priceDirection[instrumentId] || priceDirection[upstoxKey];
                      const hasLive = Number.isFinite(live);
                      const isUp = hasLive && direction === "up";
                      const isDown = hasLive && direction === "down";
                      return (
                        <div key={item.instrument_id} className="py-3 px-1 hover:bg-surface-container-low transition-colors">
                          <div className="flex items-center justify-between mb-2">
                            <div>
                              <p className="font-data-mono text-data-mono font-bold">{item.trading_symbol}</p>
                              <p className="font-label-caps text-[9px] text-outline">#{item.instrument_id}</p>
                            </div>
                            <div className="text-right">
                              <span
                                key={`${item.instrument_id}-${pulse}`}
                                className={`font-data-mono text-[13px] font-bold price-pop-anim ${
                                  isUp ? "text-success" : isDown ? "text-danger" : "text-on-surface"
                                } ${hasLive ? "" : "text-outline"}`}
                              >
                                {hasLive ? live.toFixed(2) : "--"}
                              </span>
                              {Number.isFinite(dayDiff) && Number.isFinite(dayPct) && (
                                <p className={`font-data-micro text-[9px] mt-0.5 ${dayDiff >= 0 ? "text-success" : "text-danger"}`}>
                                  {dayDiff >= 0 ? "+" : ""}{dayDiff.toFixed(2)} ({dayPct >= 0 ? "+" : ""}{dayPct.toFixed(2)}%)
                                </p>
                              )}
                            </div>
                          </div>
                          <div className="flex gap-2">
                            <StitchBtn onClick={() => sendEntrySignal(item.instrument_id, "buy")} disabled={busy} variant="success" className="flex-1 text-[9px] py-1">
                              BUY
                            </StitchBtn>
                            <StitchBtn onClick={() => sendEntrySignal(item.instrument_id, "sell")} disabled={busy} variant="danger" className="flex-1 text-[9px] py-1">
                              SELL
                            </StitchBtn>
                            <StitchBtn onClick={() => removeFromWatchlist(item.instrument_id)} disabled={busy} variant="ghost" className="text-[9px] py-1 px-2">
                              ✕
                            </StitchBtn>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </Card>
            </div>

            {/* ── Col 3: Signals ── */}
            <div className="space-y-6">
              {/* Entry Signals */}
              <Card
                title="Entry Signals"
                action={
                  <span className="px-1.5 py-0.5 bg-success/10 border border-success/20 font-data-micro text-[8px] text-success uppercase">
                    {entrySignals.length} Active
                  </span>
                }
              >
                <div className="max-h-[240px] overflow-y-auto space-y-2">
                  {entrySignals.length === 0 && (
                    <p className="font-body-compact text-body-compact text-outline text-center py-4">No entry signals yet.</p>
                  )}
                  {entrySignals.map((s) => {
                    const exited = hasExitByEntryId.has(s.id);
                    return (
                      <div key={s.id} className="bg-surface-container-low border border-border-color p-3 flex items-center justify-between gap-2">
                        <div>
                          <p className="font-data-mono text-data-mono font-bold">#{s.id} {s.trading_symbol}</p>
                          <span className={`font-label-caps text-[9px] uppercase font-bold ${s.side === "buy" ? "text-success" : "text-danger"}`}>
                            {s.side}
                          </span>
                        </div>
                        <StitchBtn
                          onClick={() => sendExitSignal(s)}
                          disabled={busy || exited}
                          variant={exited ? "ghost" : "danger"}
                          className="text-[9px] py-1 px-2"
                        >
                          {exited ? "Exited" : "Exit"}
                        </StitchBtn>
                      </div>
                    );
                  })}
                </div>
              </Card>

              {/* Exit Signals */}
              <Card
                title="Exit Signals"
                action={
                  <span className="px-1.5 py-0.5 bg-danger/10 border border-danger/20 font-data-micro text-[8px] text-danger uppercase">
                    {exitSignals.length} Closed
                  </span>
                }
              >
                <div className="max-h-[240px] overflow-y-auto space-y-2">
                  {exitSignals.length === 0 && (
                    <p className="font-body-compact text-body-compact text-outline text-center py-4">No exit signals yet.</p>
                  )}
                  {exitSignals.map((s) => (
                    <div key={s.id} className="bg-surface-container-low border border-border-color p-3 flex items-center justify-between gap-2">
                      <div>
                        <p className="font-data-mono text-data-mono font-bold">#{s.id} {s.trading_symbol}</p>
                        <span className={`font-label-caps text-[9px] uppercase font-bold ${s.side === "buy" ? "text-success" : "text-danger"}`}>
                          {s.side}
                        </span>
                      </div>
                      <span className="font-data-micro text-[9px] text-outline">from #{s.depends_on_signal_id || "-"}</span>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          </div>

          {/* Footer status bar */}
          <div className="border-t border-border-color pt-4 flex justify-between items-center text-outline font-data-micro">
            <div className="flex gap-6">
              <span className="flex items-center gap-1">
                <span className="material-symbols-outlined text-[12px]">lock</span> ENCRYPTED AES-256
              </span>
              <span className="flex items-center gap-1">
                <span className="material-symbols-outlined text-[12px]">dns</span> WEBSOCKET LIVE
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-success animate-pulse"></span>
              <span>PRIMARY GATEWAY ACTIVE</span>
            </div>
          </div>
        </div>
      </main>

      {/* ── Toast ── */}
      {toast && (
        <div
          className="fixed right-4 bottom-4 z-50 bg-inverse-surface text-inverse-on-surface px-4 py-3 font-body-compact text-body-compact shadow-lg toast-anim"
          onAnimationEnd={() => setToast("")}
        >
          {toast}
        </div>
      )}
    </div>
  );
}
