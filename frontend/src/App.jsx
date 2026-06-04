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

// ── Small reusable components ─────────────────────────────────────────────────

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

function Card({ title, action, children, noPad = false }) {
  return (
    <div className="bg-surface border border-border-color">
      <div className="px-4 py-3 border-b border-border-color flex justify-between items-center bg-surface-container-lowest">
        <h3 className="font-heading-section text-heading-section uppercase">{title}</h3>
        {action}
      </div>
      <div className={noPad ? "" : "p-4"}>{children}</div>
    </div>
  );
}

function StitchInput({ value, onChange, placeholder, type = "text", className = "", onKeyDown }) {
  return (
    <input
      type={type}
      value={value}
      onChange={onChange}
      onKeyDown={onKeyDown}
      placeholder={placeholder}
      className={`w-full bg-surface-container-low border border-outline-variant focus:border-primary focus:ring-0 font-data-mono text-data-mono px-2 py-1.5 text-[12px] outline-none ${className}`}
    />
  );
}

function StitchBtn({ onClick, disabled, children, variant = "primary", className = "", type = "button" }) {
  const base = "font-label-caps text-label-caps uppercase px-3 py-2 transition-colors active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap";
  const variants = {
    primary: "bg-primary text-white hover:bg-primary-container",
    success: "bg-success text-white hover:opacity-90",
    danger:  "bg-danger  text-white hover:opacity-90",
    ghost:   "bg-surface-container text-on-surface-variant hover:bg-surface-container-high border border-border-color",
  };
  return (
    <button type={type} onClick={onClick} disabled={disabled} className={`${base} ${variants[variant]} ${className}`}>
      {children}
    </button>
  );
}

// Compact index ticker shown at top of every view
function IndexStrip({ indexPrices, previousClose, serverDayChange }) {
  return (
    <div className="grid grid-cols-2 gap-4 mb-2">
      {INDEX_KEYS.map((k) => {
        const live = indexPrices[k];
        const prev = previousClose[k];
        // Prefer server-computed day change; fall back to frontend arithmetic
        const sdc  = serverDayChange?.[k];
        const diff = sdc ? sdc.change : (Number.isFinite(live) && Number.isFinite(prev) ? live - prev : null);
        const pct  = sdc ? sdc.pct   : (Number.isFinite(diff) && prev !== 0 ? (diff / prev) * 100 : null);
        const isUp   = Number.isFinite(diff) && diff > 0;
        const isDown = Number.isFinite(diff) && diff < 0;
        return (
          <div key={k} className="bg-surface border border-border-color px-4 py-3 flex justify-between items-center">
            <div>
              <p className="font-label-caps text-label-caps text-outline uppercase">{k.replace("NSE_INDEX|", "")}</p>
              <p className={`font-data-mono text-[20px] font-bold mt-0.5 ${isUp ? "text-success" : isDown ? "text-danger" : "text-on-surface"}`}>
                {Number.isFinite(live) ? live.toFixed(2) : <span className="text-outline">--</span>}
              </p>
            </div>
            <div className="text-right">
              <p className={`font-data-mono text-[12px] font-bold ${isUp ? "text-success" : isDown ? "text-danger" : "text-outline"}`}>
                {Number.isFinite(diff) && Number.isFinite(pct)
                  ? `${diff >= 0 ? "+" : ""}${diff.toFixed(2)} (${pct >= 0 ? "+" : ""}${pct.toFixed(2)}%)`
                  : "--"}
              </p>
              <p className="font-data-micro text-data-micro text-outline mt-1 uppercase">Today</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [activeNav, setActiveNav] = useState("dashboard");

  // ── Core data ──
  const [watchlists,        setWatchlists]        = useState([]);
  const [strategies,        setStrategies]        = useState([]);
  const [signals,           setSignals]           = useState([]);
  const [users,             setUsers]             = useState([]);
  const [subscriptions,     setSubscriptions]     = useState([]);

  // ── Watchlist UI ──
  const [selectedWatchlistId,   setSelectedWatchlistId]   = useState(null);
  const [watchlistName,         setWatchlistName]         = useState("");
  const [watchlistDescription,  setWatchlistDescription]  = useState("");
  const [searchText,            setSearchText]            = useState("");
  const [searchResults,         setSearchResults]         = useState([]);

  // ── Strategy ──
  const [selectedStrategyId, setSelectedStrategyId] = useState("");

  // ── User form (only fields the backend User model accepts) ──
  const [newUser, setNewUser] = useState({ first_name: "", last_name: "", email: "", phone: "" });

  // ── User management UI ──
  const [userSearch,     setUserSearch]     = useState("");
  const [expandedUserId, setExpandedUserId] = useState(null);
  const [profileForm,    setProfileForm]    = useState(null);
  const [subscriptionForm, setSubscriptionForm] = useState(null);

  // IP Whitelist — one record per user: { id, static_ip, private_ip } or null
  const [userIpData,  setUserIpData]  = useState({}); // { [userId]: record | null | "loading" }
  const [ipForm,      setIpForm]      = useState({ static_ip: "", private_ip: "" });
  const [editingIpId, setEditingIpId] = useState(null); // ip record id being edited

  // DematApi (broker credentials) — list per user
  const [dematApis,    setDematApis]    = useState([]); // all demat apis, filtered by user in render
  const [dematForm,    setDematForm]    = useState(null); // null | { userId, apiId|null, api_provider, demat_provider, api_key, api_secret, mobile_number, totp_secret, pin, redirect_url }

  const API_PROVIDERS    = ["upstox","kite","shoonya","angelone","paper","grow"];
  const DEMAT_PROVIDERS  = ["upstox","zerodha","finvasia","angelone","arkalogi","grow","demo"];
  const PROVIDER_PAIRS   = { upstox:"upstox", zerodha:"kite", finvasia:"shoonya", angelone:"angelone", arkalogi:"paper", grow:"grow", demo:"paper" };

  // ── Live prices ──
  const [livePrices,    setLivePrices]    = useState({});
  const [indexPrices,   setIndexPrices]   = useState({});
  const [previousClose, setPreviousClose] = useState({});
  const [pricePulse,    setPricePulse]    = useState({});
  const [priceDirection,setPriceDirection]= useState({});
  // Server-computed day change (authoritative when available)
  const [serverDayChange, setServerDayChange] = useState({}); // { [id]: { change, pct } }

  const [toast,    setToast]    = useState("");
  const [busy,     setBusy]     = useState(false);
  const [wsStatus, setWsStatus] = useState("connecting"); // "connecting"|"connected"|"disconnected"
  const [priceCount, setPriceCount] = useState(0); // total messages received (debug)

  const wsRef               = useRef(null);
  const subscribedRef       = useRef(new Set());
  const lastPriceRef        = useRef({});
  const desiredIdsRef       = useRef([]);
  const reconnectTimerRef   = useRef(null);
  const mountedRef          = useRef(true);
  // Store syncWsSubs in a ref so onopen always calls the latest version (no stale-closure risk)
  const syncWsSubsRef       = useRef(null);

  // ── Derived ──────────────────────────────────────────────────────────────────
  const selectedWatchlist = useMemo(
    () => watchlists.find((w) => w.id === selectedWatchlistId) || null,
    [watchlists, selectedWatchlistId]
  );

  const watchedInstrumentIds = useMemo(() => {
    const ids = new Set();
    for (const item of selectedWatchlist?.items || []) {
      if (item?.instrument_id != null)        ids.add(String(item.instrument_id));
      if (item?.upstox_instrument_key)        ids.add(String(item.upstox_instrument_key));
    }
    return Array.from(ids);
  }, [selectedWatchlist]);

  const entrySignals = useMemo(
    () => signals.filter(s => s.type === "enter_position").slice().sort((a,b) => b.id - a.id),
    [signals]
  );
  const exitSignals = useMemo(
    () => signals.filter(s => s.type === "exit_position").slice().sort((a,b) => b.id - a.id),
    [signals]
  );
  const hasExitByEntryId = useMemo(() => {
    const s = new Set();
    for (const sig of exitSignals) if (sig.depends_on_signal_id) s.add(sig.depends_on_signal_id);
    return s;
  }, [exitSignals]);

  // ── Data loading ──────────────────────────────────────────────────────────────
  async function loadAll() {
    const [wl, st, sg, us, da, ss] = await Promise.all([
      api.listWatchlists(), api.listStrategies(), api.listSignals(), api.listUsers(), api.listDematApis(),
      api.listStrategySubscriptions()
    ]);
    setWatchlists(wl || []);
    setStrategies(st || []);
    setSignals(sg || []);
    setUsers(us || []);
    setDematApis(Array.isArray(da) ? da : []);
    setSubscriptions(Array.isArray(ss) ? ss : []);
    if (!selectedWatchlistId && wl?.length)   setSelectedWatchlistId(wl[0].id);
    if (!selectedStrategyId  && st?.length)   setSelectedStrategyId(String(st[0].id));
  }

  // ── WebSocket subscription sync ───────────────────────────────────────────────
  // Defined as a regular function AND stored in a ref so ws.onopen always calls
  // the latest version without any stale-closure risk.
  function syncWsSubs(nextIds) {
    const ws      = wsRef.current;
    const readyState = ws ? ws.readyState : -1;
    const desired = [INDEX_KEYS[0], INDEX_KEYS[1], ...nextIds.map(String)];

    console.log(
      `[WS] syncWsSubs — readyState:${readyState} desired:${desired.length} subscribed:${subscribedRef.current.size}`,
      desired
    );

    if (!ws || readyState !== WebSocket.OPEN) {
      console.warn("[WS] Not open yet — will retry when onopen fires. desiredIdsRef updated.");
      desiredIdsRef.current = nextIds;   // ensure onopen picks up latest
      return;
    }

    const cur    = subscribedRef.current;
    const target = new Set(desired);
    const toSub  = [...target].filter(id => !cur.has(id));
    const toUnsub= [...cur].filter(id => !target.has(id));

    try {
      if (toSub.length) {
        ws.send(JSON.stringify({ action: "subscribe", instrument_ids: toSub }));
        toSub.forEach(id => cur.add(id));
        console.log("[WS] ✅ Subscribed:", toSub);
      } else {
        console.log("[WS] ℹ️ Nothing new to subscribe (already have all desired IDs)");
      }
      if (toUnsub.length) {
        ws.send(JSON.stringify({ action: "unsubscribe", instrument_ids: toUnsub }));
        toUnsub.forEach(id => cur.delete(id));
        console.log("[WS] ❌ Unsubscribed:", toUnsub);
      }
    } catch (e) {
      console.warn("[WS] Send failed:", e);
    }
  }
  // Keep the ref current on every render so ws.onopen always has the latest version
  syncWsSubsRef.current = syncWsSubs;

  useEffect(() => { loadAll().catch(e => setToast(e.message)); }, []);

  // ── WebSocket with auto-reconnect ────────────────────────────────────────────
  useEffect(() => {
    mountedRef.current = true;

    function connect() {
      if (!mountedRef.current) return;
      const apiBase = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
      setWsStatus("connecting");

      let ws;
      try {
        ws = new WebSocket(`${apiToWsUrl(apiBase)}/ws/prices`);
      } catch (e) {
        scheduleReconnect();
        return;
      }
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) { ws.close(); return; }
        // Clear tracked subscriptions — the new WS connection has no subscriptions yet
        subscribedRef.current = new Set();
        setWsStatus("connected");
        console.log("[WS] Connection open. Re-subscribing desired IDs:", desiredIdsRef.current);
        // Use the ref so we always call the LATEST syncWsSubs, not the stale closure
        syncWsSubsRef.current(desiredIdsRef.current);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "price" && data.instrument_id) {
            const id   = String(data.instrument_id);
            const next = Number(data.price);
            if (!Number.isFinite(next)) return;

            // Tick direction (for animation)
            const prev = lastPriceRef.current[id];
            if (Number.isFinite(prev) && next !== prev) {
              setPriceDirection(p => ({ ...p, [id]: next > prev ? "up" : "down" }));
              setPricePulse(p => ({ ...p, [id]: (p[id] || 0) + 1 }));
            }
            lastPriceRef.current[id] = next;
            setLivePrices(p => ({ ...p, [id]: next }));
            setPriceCount(c => c + 1);

            // Previous close
            const pc = Number(data.previous_close);
            if (Number.isFinite(pc) && pc > 0) {
              setPreviousClose(p => ({ ...p, [id]: pc }));
            }

            // Server-computed day change (authoritative — calculated in the hub)
            const dc    = data.day_change    != null ? Number(data.day_change)    : null;
            const dcPct = data.day_change_pct != null ? Number(data.day_change_pct) : null;
            if (Number.isFinite(dc) && Number.isFinite(dcPct)) {
              setServerDayChange(p => ({ ...p, [id]: { change: dc, pct: dcPct } }));
            }

            if (INDEX_KEYS.includes(id)) {
              setIndexPrices(p => ({ ...p, [id]: next }));
            }
          }
        } catch { /* ignore malformed frames */ }
      };

      ws.onclose = () => {
        if (wsRef.current === ws) wsRef.current = null;
        if (mountedRef.current) {
          setWsStatus("disconnected");
          scheduleReconnect();
        }
      };

      ws.onerror = () => {
        // onclose fires right after onerror, so just log here
        console.warn("[WS] Price feed error");
      };
    }

    function scheduleReconnect() {
      if (!mountedRef.current) return;
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = setTimeout(() => {
        if (mountedRef.current) connect();
      }, 3000);
    }

    connect();

    return () => {
      mountedRef.current = false;
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      wsRef.current?.close();
      wsRef.current      = null;
      subscribedRef.current = new Set();
      lastPriceRef.current  = {};
      desiredIdsRef.current = [];
      setPreviousClose({});
    };
  }, []);

  // Runs when: watchlist changes, instrument list changes, OR active tab changes.
  // activeNav dependency ensures switching to Watchlists/Signals always syncs and logs.
  useEffect(() => {
    desiredIdsRef.current = watchedInstrumentIds;
    console.log(
      `[WS] Subscription sync — tab:"${activeNav}" watchlist:${selectedWatchlistId} instruments:${watchedInstrumentIds.length}`,
      watchedInstrumentIds
    );
    syncWsSubs(watchedInstrumentIds);
  }, [selectedWatchlistId, watchedInstrumentIds.join(","), activeNav]);

  // ── Helpers: live price for an instrument ────────────────────────────────────
  function getLiveData(item) {
    const id  = String(item.instrument_id ?? "");
    const key = String(item.upstox_instrument_key ?? "");

    const live      = Number.isFinite(livePrices[id])    ? livePrices[id]    : livePrices[key];
    const prevClose = Number.isFinite(previousClose[id]) ? previousClose[id] : previousClose[key];
    const pulse     = pricePulse[id]     || pricePulse[key]     || 0;
    const direction = priceDirection[id] || priceDirection[key];

    // Prefer server-computed day change (hub calculates it from authoritative cp).
    // Fall back to frontend arithmetic if the server hasn't sent it yet.
    const serverDC = serverDayChange[id] || serverDayChange[key];
    const dayDiff  = serverDC
      ? serverDC.change
      : (Number.isFinite(live) && Number.isFinite(prevClose) ? live - prevClose : null);
    const dayPct   = serverDC
      ? serverDC.pct
      : (Number.isFinite(dayDiff) && prevClose !== 0 ? (dayDiff / prevClose) * 100 : null);

    return { live, prevClose, dayDiff, dayPct, pulse, direction };
  }

  // ── Actions: Strategy ────────────────────────────────────────────────────────
  async function createQuickStrategy() {
    setBusy(true);
    try {
      const user     = await api.createUser(defaultUser);
      const strategy = await api.createStrategy({ name: `Auto Strategy ${Date.now()}`, description: "Created from CopyTrade Desk", config: "{}", user_id: user.id });
      setStrategies(prev => [strategy, ...prev]);
      setSelectedStrategyId(String(strategy.id));
      setToast("Strategy created.");
    } catch (e) { setToast(e.message); }
    finally { setBusy(false); }
  }

  // ── Actions: Watchlist ───────────────────────────────────────────────────────
  async function createWatchlist() {
    if (!watchlistName.trim()) { setToast("Watchlist name is required."); return; }
    setBusy(true);
    try {
      const wl = await api.createWatchlist({ name: watchlistName.trim(), description: watchlistDescription.trim() || null, instruments: [] });
      setWatchlists(prev => [wl, ...prev]);
      setSelectedWatchlistId(wl.id);
      setWatchlistName(""); setWatchlistDescription("");
      setToast("Watchlist created.");
    } catch (e) { setToast(e.message); }
    finally { setBusy(false); }
  }

  async function deleteSelectedWatchlist() {
    if (!selectedWatchlistId) return;
    if (!window.confirm(`Delete watchlist "${selectedWatchlist?.name || selectedWatchlistId}"?`)) return;
    setBusy(true);
    try {
      await api.deleteWatchlist(selectedWatchlistId);
      const remaining = watchlists.filter(w => w.id !== selectedWatchlistId);
      setWatchlists(remaining);
      setSelectedWatchlistId(remaining[0]?.id || null);
      setToast("Watchlist deleted.");
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
      setWatchlists(prev => prev.map(w => w.id === selectedWatchlistId ? updated : w));
      setToast("Instrument added.");
    } catch (e) { setToast(e.message); }
    finally { setBusy(false); }
  }

  // FIX #1 — robust remove: optimistic local update + API call
  async function removeFromWatchlist(instrumentId) {
    if (!selectedWatchlistId) return;
    // Optimistic: remove locally immediately so UI feels instant
    setWatchlists(prev => prev.map(w => {
      if (w.id !== selectedWatchlistId) return w;
      return { ...w, items: (w.items || []).filter(it => String(it.instrument_id) !== String(instrumentId)) };
    }));
    try {
      await api.removeWatchlistItem(selectedWatchlistId, instrumentId);
      setToast("Instrument removed.");
    } catch (e) {
      // Rollback: reload watchlists from server
      const fresh = await api.listWatchlists().catch(() => null);
      if (fresh) setWatchlists(fresh);
      setToast(e.message);
    }
  }

  // ── Actions: Signals ─────────────────────────────────────────────────────────
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
      await api.createSignal({ type: "exit_position", strategy_id: entrySignal.strategy_id, instrument_id: entrySignal.instrument_id, side: entrySignal.side === "buy" ? "sell" : "buy", depends_on_signal_id: entrySignal.id });
      const sg = await api.listSignals();
      setSignals(sg || []);
      setToast(`Exit signal created for entry #${entrySignal.id}.`);
    } catch (e) { setToast(e.message); }
    finally { setBusy(false); }
  }

  // ── Actions: Users ───────────────────────────────────────────────────────────
  async function createNewUser() {
    if (!newUser.first_name.trim() || !newUser.email.trim()) {
      setToast("First name and email are required."); return;
    }
    setBusy(true);
    try {
      const created = await api.createUser({
        first_name: newUser.first_name.trim(),
        last_name:  newUser.last_name.trim(),
        username:   newUser.email.trim().split("@")[0] + "_" + Date.now(),
        email:      newUser.email.trim(),
        phone:      newUser.phone.trim() || "0000000000",
      });
      setUsers(prev => [created, ...prev]);
      setNewUser({ first_name: "", last_name: "", email: "", phone: "" });
      setToast("User created.");
    } catch (e) { setToast(e.message); }
    finally { setBusy(false); }
  }

  async function removeUser(userId) {
    setBusy(true);
    try {
      await api.deleteUser(userId);
      setUsers(prev => prev.filter(u => u.id !== userId));
      const removedApiIds = new Set(dematApis.filter(d => d.user_id === userId).map(d => d.id));
      setDematApis(prev => prev.filter(d => d.user_id !== userId));
      setSubscriptions(prev => prev.filter(s => !removedApiIds.has(s.subscriber_id)));
      if (expandedUserId === userId) setExpandedUserId(null);
      setToast("User removed.");
    } catch (e) { setToast(e.message); }
    finally { setBusy(false); }
  }

  async function saveUserProfile() {
    if (!profileForm) return;
    setBusy(true);
    try {
      const updated = await api.updateUser(profileForm.id, {
        first_name: profileForm.first_name.trim(),
        last_name: profileForm.last_name.trim(),
        username: profileForm.username.trim(),
        email: profileForm.email.trim(),
        phone: profileForm.phone.trim(),
        is_active: profileForm.is_active,
      });
      setUsers(prev => prev.map(u => u.id === updated.id ? updated : u));
      setProfileForm(updated);
      setToast("User profile updated.");
    } catch (e) { setToast(e.message); }
    finally { setBusy(false); }
  }

  async function saveStrategySubscription() {
    if (!subscriptionForm) return;
    if (!subscriptionForm.subscriber_id || !subscriptionForm.target_id) {
      setToast("Select a broker API and strategy."); return;
    }
    setBusy(true);
    try {
      const body = {
        subscriber_id: Number(subscriptionForm.subscriber_id),
        target_id: Number(subscriptionForm.target_id),
        total_fund: Number(subscriptionForm.total_fund || 0),
        fund_allocation_precentage: Number(subscriptionForm.allocation_percent || 0) / 100,
        fund_deployed: Number(subscriptionForm.fund_deployed || 0),
      };
      let result;
      if (subscriptionForm.id) {
        result = await api.updateStrategySubscription(subscriptionForm.id, body);
        setSubscriptions(prev => prev.map(s => s.id === result.id ? result : s));
      } else {
        result = await api.createStrategySubscription(body);
        setSubscriptions(prev => [result, ...prev]);
      }
      setSubscriptionForm(null);
      setToast("Strategy subscription saved.");
    } catch (e) { setToast(e.message); }
    finally { setBusy(false); }
  }

  async function removeStrategySubscription(subscriptionId) {
    setBusy(true);
    try {
      await api.deleteStrategySubscription(subscriptionId);
      setSubscriptions(prev => prev.filter(s => s.id !== subscriptionId));
      setToast("Strategy subscription removed.");
    } catch (e) { setToast(e.message); }
    finally { setBusy(false); }
  }

  // ── DematApi (broker credentials) via /demat-apis/ ──────────────────────────
  async function saveDematApi() {
    if (!dematForm) return;
    setBusy(true);
    try {
      const body = {
        user_id: dematForm.userId,
        config: {
          api_provider:   dematForm.api_provider   || "paper",
          demat_provider: dematForm.demat_provider || "arkalogi",
          api_key:        dematForm.api_key        || null,
          api_secret:     dematForm.api_secret     || null,
          mobile_number:  dematForm.mobile_number  || null,
          totp_secret:    dematForm.totp_secret    || null,
          pin:            dematForm.pin            || null,
          redirect_url:   dematForm.redirect_url   || null,
        }
      };
      let result;
      if (dematForm.apiId) {
        result = await api.updateDematApi(dematForm.apiId, body);
        setDematApis(prev => prev.map(d => d.id === dematForm.apiId ? result : d));
      } else {
        result = await api.createDematApi(body);
        setDematApis(prev => [result, ...prev]);
      }
      setDematForm(null);
      setToast("Broker API saved.");
    } catch (e) { setToast(e.message); }
    finally { setBusy(false); }
  }

  async function removeDematApi(apiId) {
    setBusy(true);
    try {
      await api.deleteDematApi(apiId);
      setDematApis(prev => prev.filter(d => d.id !== apiId));
      setToast("Broker API removed.");
    } catch (e) { setToast(e.message); }
    finally { setBusy(false); }
  }

  // ── IP whitelist via /user-ips/  (one record per user: static_ip + private_ip)
  async function loadUserIp(userId) {
    setUserIpData(prev => ({ ...prev, [userId]: "loading" }));
    try {
      const record = await api.getUserIp(userId);
      setUserIpData(prev => ({ ...prev, [userId]: record || null }));
    } catch {
      setUserIpData(prev => ({ ...prev, [userId]: null }));
    }
  }

  async function saveUserIp(userId) {
    if (!ipForm.static_ip.trim() || !ipForm.private_ip.trim()) {
      setToast("Both Static IP and Private IP are required."); return;
    }
    setBusy(true);
    try {
      const existing = userIpData[userId];
      let result;
      if (existing && existing !== "loading" && existing.id) {
        result = await api.updateUserIp(existing.id, {
          static_ip:  ipForm.static_ip.trim(),
          private_ip: ipForm.private_ip.trim(),
        });
      } else {
        result = await api.createUserIp({
          user_id:    userId,
          static_ip:  ipForm.static_ip.trim(),
          private_ip: ipForm.private_ip.trim(),
        });
      }
      setUserIpData(prev => ({ ...prev, [userId]: result }));
      setEditingIpId(null);
      setIpForm({ static_ip: "", private_ip: "" });
      setToast("IP whitelist saved.");
    } catch (e) { setToast(e.message); }
    finally { setBusy(false); }
  }

  async function deleteUserIp(ipId, userId) {
    setBusy(true);
    try {
      await api.deleteUserIp(ipId);
      setUserIpData(prev => ({ ...prev, [userId]: null }));
      setToast("IP record deleted.");
    } catch (e) { setToast(e.message); }
    finally { setBusy(false); }
  }

  function toggleExpandUser(userId) {
    if (expandedUserId === userId) { setExpandedUserId(null); return; }
    setExpandedUserId(userId);
    const user = users.find(u => u.id === userId);
    if (user) setProfileForm({ ...user });
    setSubscriptionForm(null);
    if (userIpData[userId] === undefined) loadUserIp(userId);
  }

  function startEditIp(userId) {
    const existing = userIpData[userId];
    setEditingIpId(userId);
    setIpForm({
      static_ip:  existing && existing !== "loading" ? existing.static_ip  || "" : "",
      private_ip: existing && existing !== "loading" ? existing.private_ip || "" : "",
    });
  }

  // ── Live price cell ───────────────────────────────────────────────────────────
  function PriceCell({ item }) {
    const { live, dayDiff, dayPct, pulse, direction } = getLiveData(item);
    const hasLive = Number.isFinite(live);
    const isUp    = hasLive && direction === "up";
    const isDown  = hasLive && direction === "down";
    return (
      <div>
        <span
          key={`${item.instrument_id}-${pulse}`}
          className={`font-data-mono text-[13px] font-bold price-pop-anim ${isUp ? "text-success" : isDown ? "text-danger" : hasLive ? "text-on-surface" : "text-outline"}`}
        >
          {hasLive ? live.toFixed(2) : "--"}
        </span>
        {Number.isFinite(dayDiff) && Number.isFinite(dayPct) && (
          <p className={`font-data-micro text-[9px] mt-0.5 ${dayDiff >= 0 ? "text-success" : "text-danger"}`}>
            {dayDiff >= 0 ? "+" : ""}{dayDiff.toFixed(2)} ({dayPct >= 0 ? "+" : ""}{dayPct.toFixed(2)}%)
          </p>
        )}
      </div>
    );
  }

  // ── Render ────────────────────────────────────────────────────────────────────
  const pageTitles = { dashboard: "Dashboard", watchlists: "Watchlists", users: "User Management", signals: "Signals", settings: "Settings" };

  return (
    <div className="bg-background text-on-surface font-body-standard">

      {/* ── Sidebar ── */}
      <aside className="fixed left-0 top-0 h-full w-[240px] z-50 bg-surface border-r border-border-color flex flex-col py-4">
        <div className="px-6 mb-8">
          <h1 className="font-heading-display text-heading-display font-bold text-primary uppercase tracking-tighter">CopyTrade</h1>
          <p className="font-body-compact text-body-compact text-outline">Admin Console</p>
        </div>
        <nav className="flex-grow">
          <NavItem icon="dashboard"   label="Dashboard"  active={activeNav === "dashboard"}  onClick={() => setActiveNav("dashboard")} />
          <NavItem icon="query_stats" label="Watchlists" active={activeNav === "watchlists"} onClick={() => setActiveNav("watchlists")} />
          <NavItem icon="group"       label="Users"      active={activeNav === "users"}      onClick={() => setActiveNav("users")} />
          <NavItem icon="bolt"        label="Signals"    active={activeNav === "signals"}    onClick={() => setActiveNav("signals")} />
          <NavItem icon="settings"    label="Settings"   active={activeNav === "settings"}   onClick={() => setActiveNav("settings")} />
        </nav>
        <div className="px-6 mt-auto space-y-1 border-t border-border-color pt-4">
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
        <h2 className="font-heading-section text-heading-section uppercase">{pageTitles[activeNav]}</h2>
        <div className="flex items-center gap-3">
          {/* WS live status */}
          {wsStatus === "connected" && (
            <div className="flex items-center gap-2 px-3 py-1 bg-success/10 border border-success/20">
              <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse"></span>
              <span className="font-data-mono text-data-mono text-success">LIVE · {priceCount} ticks</span>
            </div>
          )}
          {wsStatus === "connecting" && (
            <div className="flex items-center gap-2 px-3 py-1 bg-warning/10 border border-warning/20">
              <span className="w-1.5 h-1.5 rounded-full bg-warning animate-pulse"></span>
              <span className="font-data-mono text-data-mono text-warning">CONNECTING…</span>
            </div>
          )}
          {wsStatus === "disconnected" && (
            <div className="flex items-center gap-2 px-3 py-1 bg-danger/10 border border-danger/20">
              <span className="w-1.5 h-1.5 rounded-full bg-danger"></span>
              <span className="font-data-mono text-data-mono text-danger">RECONNECTING…</span>
            </div>
          )}
          <select
            value={selectedStrategyId}
            onChange={(e) => setSelectedStrategyId(e.target.value)}
            className="bg-surface-container-low border border-outline-variant font-data-mono text-[11px] px-2 py-1.5 text-on-surface outline-none focus:border-primary"
          >
            <option value="">Select Strategy</option>
            {strategies.map(s => <option key={s.id} value={s.id}>{s.name} (#{s.id})</option>)}
          </select>
          <StitchBtn onClick={createQuickStrategy} disabled={busy} variant="ghost">+ Strategy</StitchBtn>
          <span className="material-symbols-outlined p-2 text-on-surface-variant hover:text-primary cursor-pointer text-[20px]">notifications</span>
        </div>
      </header>

      {/* ── Main ── */}
      <main className="ml-[240px] pt-14 min-h-screen data-grid-bg">
        <div className="p-6 space-y-4">

          {/* ══════════ DASHBOARD ══════════ */}
          {activeNav === "dashboard" && (
            <>
              <IndexStrip indexPrices={indexPrices} previousClose={previousClose} serverDayChange={serverDayChange} />
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {[
                  { label: "Watchlists",     value: watchlists.length, icon: "query_stats",  color: "text-primary" },
                  { label: "Users",          value: users.length,      icon: "group",         color: "text-primary" },
                  { label: "Open Positions", value: entrySignals.filter(s => !hasExitByEntryId.has(s.id)).length, icon: "trending_up", color: "text-success" },
                  { label: "Closed Trades",  value: exitSignals.length, icon: "check_circle",  color: "text-outline" },
                ].map(stat => (
                  <div key={stat.label} className="bg-surface border border-border-color p-4 relative overflow-hidden group">
                    <span className={`material-symbols-outlined absolute top-3 right-3 text-4xl opacity-10 group-hover:opacity-20 transition-opacity ${stat.color}`}>{stat.icon}</span>
                    <p className="font-label-caps text-label-caps text-outline uppercase">{stat.label}</p>
                    <p className={`font-data-mono text-[28px] font-bold mt-1 ${stat.color}`}>{stat.value}</p>
                  </div>
                ))}
              </div>
              <Card title="Recent Signals" action={<span className="font-data-micro text-data-micro text-outline">Latest 10</span>}>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead><tr className="border-b border-border-color">
                      {["#", "Symbol", "Type", "Side", "Strategy", "Status"].map(h => (
                        <th key={h} className="text-left py-2 px-3 font-label-caps text-[9px] text-outline uppercase">{h}</th>
                      ))}
                    </tr></thead>
                    <tbody className="divide-y divide-border-color">
                      {signals.length === 0 && <tr><td colSpan={6} className="text-center py-8 font-body-compact text-body-compact text-outline">No signals yet.</td></tr>}
                      {[...signals].sort((a,b) => b.id - a.id).slice(0,10).map(s => (
                        <tr key={s.id} className="hover:bg-surface-container-low transition-colors">
                          <td className="py-2 px-3 font-data-mono text-data-mono text-outline">#{s.id}</td>
                          <td className="py-2 px-3 font-data-mono text-data-mono font-bold">{s.trading_symbol || "--"}</td>
                          <td className="py-2 px-3 font-label-caps text-[9px] uppercase text-on-surface-variant">{s.type === "enter_position" ? "Entry" : "Exit"}</td>
                          <td className="py-2 px-3"><span className={`font-label-caps text-[9px] font-bold uppercase ${s.side === "buy" ? "text-success" : "text-danger"}`}>{s.side}</span></td>
                          <td className="py-2 px-3 font-data-mono text-data-mono text-outline">#{s.strategy_id}</td>
                          <td className="py-2 px-3">
                            <span className={`font-label-caps text-[9px] uppercase px-2 py-0.5 ${s.type === "enter_position" && !hasExitByEntryId.has(s.id) ? "bg-success/10 text-success" : "bg-surface-container text-outline"}`}>
                              {s.type === "enter_position" ? (hasExitByEntryId.has(s.id) ? "Closed" : "Open") : "Exit"}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            </>
          )}

          {/* ══════════ WATCHLISTS ══════════ */}
          {activeNav === "watchlists" && (
            <>
              {/* FIX #4 — index strip on watchlist page */}
              <IndexStrip indexPrices={indexPrices} previousClose={previousClose} serverDayChange={serverDayChange} />

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
                {/* Left column */}
                <div className="space-y-4">
                  <Card title="Create Watchlist">
                    <div className="space-y-2">
                      <div>
                        <label className="font-label-caps text-[9px] text-outline uppercase block mb-1">Name *</label>
                        <StitchInput value={watchlistName} onChange={e => setWatchlistName(e.target.value)} placeholder="e.g. Nifty50 Core"
                          onKeyDown={e => e.key === "Enter" && createWatchlist()} />
                      </div>
                      <div>
                        <label className="font-label-caps text-[9px] text-outline uppercase block mb-1">Description</label>
                        <StitchInput value={watchlistDescription} onChange={e => setWatchlistDescription(e.target.value)} placeholder="Optional" />
                      </div>
                      <StitchBtn onClick={createWatchlist} disabled={busy} className="w-full">Create</StitchBtn>
                    </div>
                    {watchlists.length > 0 && (
                      <div className="mt-4 pt-4 border-t border-border-color">
                        <p className="font-label-caps text-[9px] text-outline uppercase mb-2">Your Watchlists</p>
                        <div className="flex flex-wrap gap-2">
                          {watchlists.map(w => (
                            <button key={w.id} onClick={() => setSelectedWatchlistId(w.id)}
                              className={`font-label-caps text-label-caps uppercase px-3 py-1.5 transition-colors ${w.id === selectedWatchlistId ? "bg-primary text-white" : "bg-surface-container text-on-surface-variant hover:bg-surface-container-high border border-border-color"}`}>
                              {w.name}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </Card>

                  <Card title="Add Instruments">
                    <div className="space-y-2">
                      <div className="flex gap-2">
                        <StitchInput value={searchText} onChange={e => setSearchText(e.target.value)} placeholder="Search symbol..."
                          onKeyDown={e => e.key === "Enter" && searchInstruments()} />
                        <StitchBtn onClick={searchInstruments} disabled={busy}>Go</StitchBtn>
                      </div>
                      <div className="max-h-[340px] overflow-y-auto divide-y divide-border-color">
                        {searchResults.length === 0
                          ? <p className="font-body-compact text-body-compact text-outline text-center py-6">Enter a symbol and press Go or Enter.</p>
                          : searchResults.map(item => (
                            <div key={item.instrument_id} className="flex items-center justify-between py-2.5 hover:bg-surface-container-low transition-colors px-1">
                              <div>
                                <p className="font-data-mono text-data-mono font-bold">{item.trading_symbol}</p>
                                <p className="font-label-caps text-[9px] text-outline uppercase">{item.instrument_type} · {item.exchange}</p>
                              </div>
                              <StitchBtn onClick={() => addToWatchlist(item.instrument_id)} disabled={busy} variant="ghost">+ Add</StitchBtn>
                            </div>
                          ))
                        }
                      </div>
                    </div>
                  </Card>
                </div>

                {/* Right: live price table — FIX #4 */}
                <div className="lg:col-span-2">
                  <Card
                    title={selectedWatchlist ? `${selectedWatchlist.name} — Live Prices` : "Select a Watchlist"}
                    action={
                      <div className="flex items-center gap-3">
                        <span className="font-data-micro text-data-micro text-outline uppercase">{selectedWatchlist?.items?.length || 0} instruments</span>
                        {selectedWatchlist && (
                          <button
                            onClick={deleteSelectedWatchlist}
                            disabled={busy}
                            title="Delete watchlist"
                            className="material-symbols-outlined text-[16px] text-outline hover:text-danger transition-colors disabled:opacity-40"
                          >
                            delete
                          </button>
                        )}
                      </div>
                    }
                    noPad
                  >
                    {!selectedWatchlist
                      ? <p className="font-body-compact text-body-compact text-outline text-center py-10 px-4">Select a watchlist.</p>
                      : (selectedWatchlist.items || []).length === 0
                      ? <p className="font-body-compact text-body-compact text-outline text-center py-10 px-4">Watchlist empty — add instruments from the search panel.</p>
                      : (
                        <div className="overflow-x-auto">
                          <table className="w-full">
                            <thead>
                              <tr className="border-b border-border-color bg-surface-container-lowest">
                                {["Symbol", "Instr. ID", "Live Price", "Change", "Action"].map(h => (
                                  <th key={h} className="text-left py-2 px-4 font-label-caps text-[9px] text-outline uppercase">{h}</th>
                                ))}
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-border-color">
                              {(selectedWatchlist.items || []).map(item => {
                                const { live, dayDiff, dayPct, pulse, direction } = getLiveData(item);
                                const hasLive = Number.isFinite(live);
                                const isUp    = hasLive && direction === "up";
                                const isDown  = hasLive && direction === "down";
                                return (
                                  <tr key={item.instrument_id} className="hover:bg-surface-container-low transition-colors">
                                    <td className="py-3 px-4 font-data-mono text-data-mono font-bold">{item.trading_symbol}</td>
                                    <td className="py-3 px-4 font-data-mono text-data-mono text-outline">#{item.instrument_id}</td>
                                    <td className="py-3 px-4">
                                      <span key={`${item.instrument_id}-${pulse}`}
                                        className={`font-data-mono text-[14px] font-bold price-pop-anim ${isUp ? "text-success" : isDown ? "text-danger" : hasLive ? "text-on-surface" : "text-outline"}`}>
                                        {hasLive ? live.toFixed(2) : "--"}
                                      </span>
                                    </td>
                                    <td className="py-3 px-4">
                                      {Number.isFinite(dayDiff) && Number.isFinite(dayPct)
                                        ? <span className={`font-data-mono text-[11px] font-bold ${dayDiff >= 0 ? "text-success" : "text-danger"}`}>
                                            {dayDiff >= 0 ? "+" : ""}{dayDiff.toFixed(2)} ({dayPct >= 0 ? "+" : ""}{dayPct.toFixed(2)}%)
                                          </span>
                                        : <span className="text-outline font-data-mono text-data-mono">--</span>
                                      }
                                    </td>
                                    <td className="py-3 px-4">
                                      {/* FIX #1 — delete watchlist item button */}
                                      <button
                                        onClick={() => removeFromWatchlist(item.instrument_id)}
                                        disabled={busy}
                                        className="flex items-center gap-1 font-label-caps text-[9px] uppercase text-outline hover:text-danger transition-colors disabled:opacity-40"
                                      >
                                        <span className="material-symbols-outlined text-[14px]">delete</span> Remove
                                      </button>
                                    </td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      )
                    }
                  </Card>
                </div>
              </div>
            </>
          )}

          {/* ══════════ USERS ══════════ */}
          {activeNav === "users" && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">

              {/* Left: Add user */}
              <div>
                <Card title="Add New User" action={<span className="px-1.5 py-0.5 bg-primary/10 border border-primary/20 font-data-micro text-[8px] text-primary uppercase">{users.length} Total</span>}>
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="font-label-caps text-[9px] text-outline uppercase block mb-1">First Name *</label>
                        <StitchInput value={newUser.first_name} onChange={e => setNewUser(u => ({ ...u, first_name: e.target.value }))} placeholder="John" />
                      </div>
                      <div>
                        <label className="font-label-caps text-[9px] text-outline uppercase block mb-1">Last Name</label>
                        <StitchInput value={newUser.last_name} onChange={e => setNewUser(u => ({ ...u, last_name: e.target.value }))} placeholder="Doe" />
                      </div>
                    </div>
                    <div>
                      <label className="font-label-caps text-[9px] text-outline uppercase block mb-1">Email *</label>
                      <StitchInput value={newUser.email} onChange={e => setNewUser(u => ({ ...u, email: e.target.value }))} placeholder="john@example.com" type="email" />
                    </div>
                    <div>
                      <label className="font-label-caps text-[9px] text-outline uppercase block mb-1">Phone</label>
                      <StitchInput value={newUser.phone} onChange={e => setNewUser(u => ({ ...u, phone: e.target.value }))} placeholder="9XXXXXXXXX" />
                    </div>
                    <StitchBtn onClick={createNewUser} disabled={busy} className="w-full">Create User</StitchBtn>
                  </div>
                </Card>
              </div>

              {/* Right: User table with expandable rows */}
              <div className="lg:col-span-2 space-y-3">
                <StitchInput value={userSearch} onChange={e => setUserSearch(e.target.value)} placeholder="Filter by name, email or username..." />
                <Card title="All Users" noPad>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-border-color bg-surface-container-lowest">
                          {["", "#", "Name", "Email", "Phone", "Active", ""].map((h, i) => (
                            <th key={i} className="text-left py-2 px-3 font-label-caps text-[9px] text-outline uppercase">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {users.length === 0 && (
                          <tr><td colSpan={7} className="text-center py-8 font-body-compact text-body-compact text-outline">No users yet.</td></tr>
                        )}
                        {users
                          .filter(u => {
                            const q = userSearch.toLowerCase();
                            return !q || `${u.first_name} ${u.last_name}`.toLowerCase().includes(q) || u.email?.toLowerCase().includes(q) || u.username?.toLowerCase().includes(q);
                          })
                          .map(u => {
                            const userDematApis = dematApis.filter(d => d.user_id === u.id);
                            const userApiIds = new Set(userDematApis.map(d => d.id));
                            const userSubscriptions = subscriptions.filter(s => userApiIds.has(s.subscriber_id));
                            const ipRecord = userIpData[u.id];
                            return (
                              <>
                                {/* Main user row */}
                                <tr key={u.id} onClick={() => toggleExpandUser(u.id)} className="border-b border-border-color hover:bg-surface-container-low transition-colors cursor-pointer">
                                  <td className="py-2.5 px-3 w-8">
                                    <button onClick={(e) => { e.stopPropagation(); toggleExpandUser(u.id); }}
                                      className="material-symbols-outlined text-[16px] text-outline hover:text-primary transition-colors">
                                      {expandedUserId === u.id ? "expand_less" : "expand_more"}
                                    </button>
                                  </td>
                                  <td className="py-2.5 px-3 font-data-mono text-data-mono text-outline">#{u.id}</td>
                                  <td className="py-2.5 px-3 font-data-mono text-data-mono font-bold">{u.first_name} {u.last_name}</td>
                                  <td className="py-2.5 px-3 font-body-compact text-body-compact">{u.email}</td>
                                  <td className="py-2.5 px-3 font-data-mono text-data-mono text-outline">{u.phone || "--"}</td>
                                  <td className="py-2.5 px-3">
                                    <span className={`font-label-caps text-[9px] uppercase px-1.5 py-0.5 ${u.is_active !== false ? "bg-success/10 text-success" : "bg-outline/10 text-outline"}`}>
                                      {u.is_active !== false ? "Active" : "Inactive"}
                                    </span>
                                  </td>
                                  <td className="py-2.5 px-3">
                                    <button onClick={(e) => { e.stopPropagation(); removeUser(u.id); }} disabled={busy}
                                      className="material-symbols-outlined text-[16px] text-outline hover:text-danger transition-colors">
                                      delete
                                    </button>
                                  </td>
                                </tr>

                                {/* Expanded: Broker APIs + IP Whitelist */}
                                {expandedUserId === u.id && (
                                  <tr key={`${u.id}-exp`} className="bg-surface-container-lowest border-b border-border-color">
                                    <td colSpan={7} className="px-4 py-5">
                                      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">

                                        {/* User profile */}
                                        <div>
                                          <div className="flex items-center justify-between mb-3">
                                            <p className="font-label-caps text-[9px] text-primary uppercase flex items-center gap-1">
                                              <span className="material-symbols-outlined text-[12px]">person</span> Profile
                                            </p>
                                          </div>
                                          {profileForm?.id === u.id && (
                                            <div className="space-y-2">
                                              {[
                                                { label: "First Name", field: "first_name", type: "text" },
                                                { label: "Last Name", field: "last_name", type: "text" },
                                                { label: "Username", field: "username", type: "text" },
                                                { label: "Email", field: "email", type: "email" },
                                                { label: "Phone", field: "phone", type: "text" },
                                              ].map(({ label, field, type }) => (
                                                <div key={field}>
                                                  <label className="font-label-caps text-[9px] text-outline uppercase block mb-1">{label}</label>
                                                  <StitchInput type={type} value={profileForm[field] || ""} onChange={e => setProfileForm(f => ({ ...f, [field]: e.target.value }))} />
                                                </div>
                                              ))}
                                              <label className="flex items-center gap-2 font-label-caps text-[9px] text-outline uppercase cursor-pointer">
                                                <input type="checkbox" checked={profileForm.is_active !== false} onChange={e => setProfileForm(f => ({ ...f, is_active: e.target.checked }))} />
                                                Active user
                                              </label>
                                              <StitchBtn onClick={saveUserProfile} disabled={busy} className="w-full">Save Profile</StitchBtn>
                                            </div>
                                          )}
                                        </div>

                                        {/* ── Broker API credentials (DematApi) ── */}
                                        <div>
                                          <div className="flex items-center justify-between mb-3">
                                            <p className="font-label-caps text-[9px] text-primary uppercase flex items-center gap-1">
                                              <span className="material-symbols-outlined text-[12px]">vpn_key</span> Broker APIs
                                            </p>
                                            <StitchBtn variant="ghost" className="text-[9px] py-1 px-2"
                                              onClick={() => setDematForm({ userId: u.id, apiId: null, api_provider: "paper", demat_provider: "arkalogi", api_key: "", api_secret: "", mobile_number: "", totp_secret: "", pin: "", redirect_url: "" })}>
                                              + Add
                                            </StitchBtn>
                                          </div>

                                          {/* Add/Edit form */}
                                          {dematForm?.userId === u.id && (
                                            <div className="bg-surface border border-border-color p-3 mb-3 space-y-2">
                                              <div className="grid grid-cols-2 gap-2">
                                                <div>
                                                  <label className="font-label-caps text-[9px] text-outline uppercase block mb-1">Demat Provider</label>
                                                  <select value={dematForm.demat_provider}
                                                    onChange={e => setDematForm(f => ({ ...f, demat_provider: e.target.value, api_provider: PROVIDER_PAIRS[e.target.value] || "paper" }))}
                                                    className="w-full bg-surface-container-low border border-outline-variant font-data-mono text-[11px] px-2 py-1.5 outline-none focus:border-primary capitalize">
                                                    {DEMAT_PROVIDERS.map(p => <option key={p} value={p}>{p}</option>)}
                                                  </select>
                                                </div>
                                                <div>
                                                  <label className="font-label-caps text-[9px] text-outline uppercase block mb-1">API Provider</label>
                                                  <div className="bg-surface-container border border-outline-variant px-2 py-1.5 font-data-mono text-[11px] text-outline capitalize">{dematForm.api_provider}</div>
                                                </div>
                                              </div>
                                              {[
                                                { label: "API Key",      field: "api_key",       type: "text" },
                                                { label: "API Secret",   field: "api_secret",    type: "password" },
                                                { label: "Mobile",       field: "mobile_number", type: "text" },
                                                { label: "TOTP Secret",  field: "totp_secret",   type: "text" },
                                                { label: "PIN",          field: "pin",           type: "password" },
                                                { label: "Redirect URL", field: "redirect_url",  type: "text" },
                                              ].map(({ label, field, type }) => (
                                                <div key={field}>
                                                  <label className="font-label-caps text-[9px] text-outline uppercase block mb-1">{label}</label>
                                                  <StitchInput type={type} value={dematForm[field] || ""} onChange={e => setDematForm(f => ({ ...f, [field]: e.target.value }))} placeholder={label} />
                                                </div>
                                              ))}
                                              <div className="flex gap-2 pt-1">
                                                <StitchBtn onClick={saveDematApi} disabled={busy} className="flex-1">Save</StitchBtn>
                                                <StitchBtn onClick={() => setDematForm(null)} variant="ghost" className="flex-1">Cancel</StitchBtn>
                                              </div>
                                            </div>
                                          )}

                                          {/* Existing DematApis */}
                                          {userDematApis.length === 0 && !dematForm
                                            ? <p className="font-data-mono text-data-mono text-outline">No broker APIs configured.</p>
                                            : userDematApis.map(d => (
                                              <div key={d.id} className="border border-border-color p-3 mb-2 group">
                                                <div className="flex justify-between items-start">
                                                  <div>
                                                    <p className="font-data-mono text-data-mono font-bold capitalize">{d.config?.demat_provider || "—"}</p>
                                                    <p className="font-label-caps text-[9px] text-outline capitalize">{d.config?.api_provider || "—"}</p>
                                                    {d.config?.api_key && (
                                                      <p className="font-data-mono text-[10px] text-outline mt-1">{d.config.api_key.slice(0,10)}••••</p>
                                                    )}
                                                  </div>
                                                  <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                    <button onClick={() => setDematForm({ userId: u.id, apiId: d.id, api_provider: d.config?.api_provider || "paper", demat_provider: d.config?.demat_provider || "arkalogi", api_key: d.config?.api_key || "", api_secret: d.config?.api_secret || "", mobile_number: d.config?.mobile_number || "", totp_secret: d.config?.totp_secret || "", pin: d.config?.pin || "", redirect_url: d.config?.redirect_url || "" })}
                                                      className="material-symbols-outlined text-[14px] text-outline hover:text-primary transition-colors">edit</button>
                                                    <button onClick={() => removeDematApi(d.id)} disabled={busy}
                                                      className="material-symbols-outlined text-[14px] text-outline hover:text-danger transition-colors">delete</button>
                                                  </div>
                                                </div>
                                              </div>
                                            ))
                                          }
                                        </div>

                                        {/* ── IP Whitelist (one record: static_ip + private_ip) ── */}
                                        <div>
                                          <div className="flex items-center justify-between mb-3">
                                            <p className="font-label-caps text-[9px] text-primary uppercase flex items-center gap-1">
                                              <span className="material-symbols-outlined text-[12px]">router</span> IP Whitelist
                                            </p>
                                          </div>

                                          {ipRecord === "loading" && (
                                            <p className="font-data-mono text-data-mono text-outline">Loading…</p>
                                          )}

                                          {/* Show/Edit form */}
                                          {editingIpId === u.id ? (
                                            <div className="space-y-2">
                                              <div>
                                                <label className="font-label-caps text-[9px] text-outline uppercase block mb-1">Static IP *</label>
                                                <StitchInput value={ipForm.static_ip} onChange={e => setIpForm(f => ({ ...f, static_ip: e.target.value }))} placeholder="203.0.113.10" />
                                              </div>
                                              <div>
                                                <label className="font-label-caps text-[9px] text-outline uppercase block mb-1">Private IP *</label>
                                                <StitchInput value={ipForm.private_ip} onChange={e => setIpForm(f => ({ ...f, private_ip: e.target.value }))} placeholder="10.0.0.5" />
                                              </div>
                                              <div className="flex gap-2">
                                                <StitchBtn onClick={() => saveUserIp(u.id)} disabled={busy} className="flex-1">Save</StitchBtn>
                                                <StitchBtn onClick={() => setEditingIpId(null)} variant="ghost" className="flex-1">Cancel</StitchBtn>
                                              </div>
                                            </div>
                                          ) : ipRecord && ipRecord !== "loading" ? (
                                            <div className="border border-border-color p-3 group">
                                              <div className="flex justify-between items-start">
                                                <div className="space-y-1.5">
                                                  {[
                                                    { label: "Static IP",  val: ipRecord.static_ip },
                                                    { label: "Private IP", val: ipRecord.private_ip },
                                                  ].map(({ label, val }) => (
                                                    <div key={label} className="flex gap-4 justify-between">
                                                      <span className="font-label-caps text-[9px] text-outline uppercase">{label}</span>
                                                      <span className="font-data-mono text-data-mono">{val || "—"}</span>
                                                    </div>
                                                  ))}
                                                </div>
                                                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                  <button onClick={() => startEditIp(u.id)}
                                                    className="material-symbols-outlined text-[14px] text-outline hover:text-primary transition-colors">edit</button>
                                                  <button onClick={() => deleteUserIp(ipRecord.id, u.id)} disabled={busy}
                                                    className="material-symbols-outlined text-[14px] text-outline hover:text-danger transition-colors">delete</button>
                                                </div>
                                              </div>
                                            </div>
                                          ) : ipRecord !== "loading" && (
                                            <div>
                                              <p className="font-data-mono text-data-mono text-outline mb-2">No IP whitelist set.</p>
                                              <StitchBtn onClick={() => startEditIp(u.id)} variant="ghost" className="w-full">+ Set IP Whitelist</StitchBtn>
                                            </div>
                                          )}
                                        </div>

                                        {/* Strategy subscriptions and fund allocation */}
                                        <div>
                                          <div className="flex items-center justify-between mb-3">
                                            <p className="font-label-caps text-[9px] text-primary uppercase flex items-center gap-1">
                                              <span className="material-symbols-outlined text-[12px]">account_tree</span> Strategy Subscriptions
                                            </p>
                                            <StitchBtn
                                              variant="ghost"
                                              className="text-[9px] py-1 px-2"
                                              disabled={userDematApis.length === 0}
                                              onClick={() => setSubscriptionForm({
                                                userId: u.id,
                                                id: null,
                                                subscriber_id: userDematApis[0]?.id || "",
                                                target_id: strategies[0]?.id || "",
                                                total_fund: "",
                                                allocation_percent: "100",
                                                fund_deployed: "",
                                              })}
                                            >
                                              + Add
                                            </StitchBtn>
                                          </div>

                                          {userDematApis.length === 0 && (
                                            <p className="font-data-mono text-data-mono text-outline mb-2">Add a broker API before subscribing.</p>
                                          )}

                                          {subscriptionForm?.userId === u.id && (
                                            <div className="bg-surface border border-border-color p-3 mb-3 space-y-2">
                                              <div>
                                                <label className="font-label-caps text-[9px] text-outline uppercase block mb-1">Broker API *</label>
                                                <select value={subscriptionForm.subscriber_id} onChange={e => setSubscriptionForm(f => ({ ...f, subscriber_id: e.target.value }))}
                                                  className="w-full bg-surface-container-low border border-outline-variant font-data-mono text-[11px] px-2 py-1.5 outline-none focus:border-primary">
                                                  {userDematApis.map(d => <option key={d.id} value={d.id}>{d.config?.demat_provider || "Broker"} #{d.id}</option>)}
                                                </select>
                                              </div>
                                              <div>
                                                <label className="font-label-caps text-[9px] text-outline uppercase block mb-1">Strategy *</label>
                                                <select value={subscriptionForm.target_id} onChange={e => setSubscriptionForm(f => ({ ...f, target_id: e.target.value }))}
                                                  className="w-full bg-surface-container-low border border-outline-variant font-data-mono text-[11px] px-2 py-1.5 outline-none focus:border-primary">
                                                  {strategies.map(s => <option key={s.id} value={s.id}>{s.name} (#{s.id})</option>)}
                                                </select>
                                              </div>
                                              {[
                                                { label: "Total Fund", field: "total_fund" },
                                                { label: "Allocation %", field: "allocation_percent" },
                                                { label: "Fund Deployed", field: "fund_deployed" },
                                              ].map(({ label, field }) => (
                                                <div key={field}>
                                                  <label className="font-label-caps text-[9px] text-outline uppercase block mb-1">{label}</label>
                                                  <StitchInput type="number" value={subscriptionForm[field]} onChange={e => setSubscriptionForm(f => ({ ...f, [field]: e.target.value }))} placeholder="0" />
                                                </div>
                                              ))}
                                              <div className="flex gap-2">
                                                <StitchBtn onClick={saveStrategySubscription} disabled={busy} className="flex-1">Save</StitchBtn>
                                                <StitchBtn onClick={() => setSubscriptionForm(null)} variant="ghost" className="flex-1">Cancel</StitchBtn>
                                              </div>
                                            </div>
                                          )}

                                          {userSubscriptions.length === 0 && !subscriptionForm
                                            ? <p className="font-data-mono text-data-mono text-outline">No strategy subscriptions.</p>
                                            : userSubscriptions.map(s => {
                                              const strategy = strategies.find(st => st.id === s.target_id);
                                              const broker = userDematApis.find(d => d.id === s.subscriber_id);
                                              const allocation = Number(s.fund_allocation_precentage || 0);
                                              const allocationPercent = allocation <= 1 ? allocation * 100 : allocation;
                                              return (
                                                <div key={s.id} className="border border-border-color p-3 mb-2 group">
                                                  <div className="flex justify-between gap-2">
                                                    <div>
                                                      <p className="font-data-mono text-data-mono font-bold">{strategy?.name || `Strategy #${s.target_id}`}</p>
                                                      <p className="font-label-caps text-[9px] text-outline capitalize">{broker?.config?.demat_provider || "Broker"} #{s.subscriber_id}</p>
                                                      <p className="font-data-mono text-[10px] text-outline mt-1">Fund {Number(s.total_fund || 0).toFixed(2)} · Allocation {allocationPercent.toFixed(0)}%</p>
                                                    </div>
                                                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                      <button onClick={() => setSubscriptionForm({
                                                        userId: u.id,
                                                        id: s.id,
                                                        subscriber_id: s.subscriber_id,
                                                        target_id: s.target_id,
                                                        total_fund: s.total_fund,
                                                        allocation_percent: allocationPercent,
                                                        fund_deployed: s.fund_deployed,
                                                      })} className="material-symbols-outlined text-[14px] text-outline hover:text-primary transition-colors">edit</button>
                                                      <button onClick={() => removeStrategySubscription(s.id)} disabled={busy}
                                                        className="material-symbols-outlined text-[14px] text-outline hover:text-danger transition-colors">delete</button>
                                                    </div>
                                                  </div>
                                                </div>
                                              );
                                            })
                                          }
                                        </div>
                                      </div>
                                    </td>
                                  </tr>
                                )}
                              </>
                            );
                          })
                        }
                      </tbody>
                    </table>
                  </div>
                </Card>
              </div>
            </div>
          )}

          {/* ══════════ SIGNALS ══════════ */}
          {activeNav === "signals" && (
            <>
              {/* FIX #4 — index strip on signals page */}
              <IndexStrip indexPrices={indexPrices} previousClose={previousClose} serverDayChange={serverDayChange} />

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">

                {/* Left: fire signals via watchlist — FIX #4 live prices */}
                <Card
                  title="Fire Signals"
                  action={<span className="px-1.5 py-0.5 bg-danger/10 border border-danger/20 font-data-micro text-[8px] text-danger uppercase animate-pulse">LIVE</span>}
                  noPad
                >
                  <div className="p-4 space-y-3 border-b border-border-color">
                    <div>
                      <label className="font-label-caps text-[9px] text-outline uppercase block mb-1">Strategy *</label>
                      <div className="flex gap-2">
                        <select value={selectedStrategyId} onChange={e => setSelectedStrategyId(e.target.value)}
                          className="flex-1 bg-surface-container-low border border-outline-variant font-data-mono text-[12px] px-2 py-1.5 outline-none focus:border-primary">
                          <option value="">— select —</option>
                          {strategies.map(s => <option key={s.id} value={s.id}>{s.name} (#{s.id})</option>)}
                        </select>
                        <StitchBtn onClick={createQuickStrategy} disabled={busy} variant="ghost">+ New</StitchBtn>
                      </div>
                    </div>
                    <div>
                      <label className="font-label-caps text-[9px] text-outline uppercase block mb-1">Watchlist</label>
                      <div className="flex flex-wrap gap-2">
                        {watchlists.length === 0
                          ? <p className="font-body-compact text-body-compact text-outline">No watchlists — create one in the Watchlists tab.</p>
                          : watchlists.map(w => (
                            <button key={w.id} onClick={() => setSelectedWatchlistId(w.id)}
                              className={`font-label-caps text-label-caps uppercase px-3 py-1.5 transition-colors ${w.id === selectedWatchlistId ? "bg-primary text-white" : "bg-surface-container text-on-surface-variant hover:bg-surface-container-high border border-border-color"}`}>
                              {w.name}
                            </button>
                          ))
                        }
                      </div>
                    </div>
                  </div>

                  {/* Instrument rows with live prices + BUY/SELL */}
                  {!selectedWatchlist
                    ? <p className="font-body-compact text-body-compact text-outline text-center py-8 px-4">Select a watchlist above.</p>
                    : (selectedWatchlist.items || []).length === 0
                    ? <p className="font-body-compact text-body-compact text-outline text-center py-8 px-4">Watchlist is empty.</p>
                    : (
                      <div className="divide-y divide-border-color max-h-[520px] overflow-y-auto">
                        {(selectedWatchlist.items || []).map(item => {
                          const { live, dayDiff, dayPct, pulse, direction } = getLiveData(item);
                          const hasLive = Number.isFinite(live);
                          const isUp    = hasLive && direction === "up";
                          const isDown  = hasLive && direction === "down";
                          return (
                            <div key={item.instrument_id} className="px-4 py-3 hover:bg-surface-container-low transition-colors">
                              <div className="flex items-center justify-between mb-2">
                                <div>
                                  <p className="font-data-mono text-data-mono font-bold">{item.trading_symbol}</p>
                                  <p className="font-label-caps text-[9px] text-outline">#{item.instrument_id}</p>
                                </div>
                                <div className="text-right">
                                  <span key={`${item.instrument_id}-${pulse}`}
                                    className={`font-data-mono text-[16px] font-bold price-pop-anim ${isUp ? "text-success" : isDown ? "text-danger" : hasLive ? "text-on-surface" : "text-outline"}`}>
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
                                <StitchBtn onClick={() => sendEntrySignal(item.instrument_id, "buy")} disabled={busy} variant="success" className="flex-1 py-1 text-[10px]">▲ BUY</StitchBtn>
                                <StitchBtn onClick={() => sendEntrySignal(item.instrument_id, "sell")} disabled={busy} variant="danger" className="flex-1 py-1 text-[10px]">▼ SELL</StitchBtn>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )
                  }
                </Card>

                {/* Right: open & closed signals */}
                <div className="space-y-4">
                <Card
                  title="Open Positions"
                  action={<span className="px-1.5 py-0.5 bg-success/10 border border-success/20 font-data-micro text-[8px] text-success uppercase">{entrySignals.filter(s => !hasExitByEntryId.has(s.id)).length} Open</span>}
                  noPad
                >
                  <div className="divide-y divide-border-color max-h-[280px] overflow-y-auto">
                    {entrySignals.length === 0 && <p className="font-body-compact text-body-compact text-outline text-center py-6 px-4">No open positions.</p>}
                    {entrySignals.map(s => {
                      const exited = hasExitByEntryId.has(s.id);
                      return (
                        <div key={s.id} className={`flex items-center justify-between px-4 py-3 gap-3 ${exited ? "opacity-50" : ""}`}>
                          <div>
                            <div className="flex items-center gap-2">
                              <span className={`font-label-caps text-[9px] font-bold uppercase px-1.5 py-0.5 ${s.side === "buy" ? "bg-success/10 text-success" : "bg-danger/10 text-danger"}`}>{s.side}</span>
                              <p className="font-data-mono text-data-mono font-bold">{s.trading_symbol || "--"}</p>
                            </div>
                            <p className="font-label-caps text-[9px] text-outline mt-0.5">#{s.id} · Strategy #{s.strategy_id}</p>
                          </div>
                          <StitchBtn onClick={() => sendExitSignal(s)} disabled={busy || exited} variant={exited ? "ghost" : "danger"} className="text-[9px] py-1 px-3 shrink-0">
                            {exited ? "Closed" : "Close →"}
                          </StitchBtn>
                        </div>
                      );
                    })}
                  </div>
                </Card>

                <Card
                  title="Closed Trades"
                  action={<span className="font-data-micro text-data-micro text-outline uppercase">{exitSignals.length} Total</span>}
                  noPad
                >
                  <div className="divide-y divide-border-color max-h-[280px] overflow-y-auto">
                    {exitSignals.length === 0 && <p className="font-body-compact text-body-compact text-outline text-center py-6 px-4">No closed trades.</p>}
                    {exitSignals.map(s => (
                      <div key={s.id} className="flex items-center justify-between px-4 py-3 gap-3">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className={`font-label-caps text-[9px] font-bold uppercase px-1.5 py-0.5 ${s.side === "buy" ? "bg-success/10 text-success" : "bg-danger/10 text-danger"}`}>{s.side}</span>
                            <p className="font-data-mono text-data-mono font-bold">{s.trading_symbol || "--"}</p>
                          </div>
                          <p className="font-label-caps text-[9px] text-outline mt-0.5">Exit #{s.id} · from Entry #{s.depends_on_signal_id || "?"}</p>
                        </div>
                        <span className="font-label-caps text-[9px] uppercase text-outline bg-surface-container px-2 py-1 border border-border-color">Closed</span>
                      </div>
                    ))}
                  </div>
                </Card>
              </div>
            </div>
          </>
          )}

          {/* ══════════ SETTINGS ══════════ */}
          {activeNav === "settings" && (
            <div className="bg-surface border border-border-color p-12 text-center">
              <span className="material-symbols-outlined text-5xl text-outline block mb-3">settings</span>
              <p className="font-heading-section text-heading-section uppercase text-outline">Settings coming soon</p>
            </div>
          )}

          {/* Footer */}
          <div className="border-t border-border-color pt-4 flex justify-between items-center text-outline font-data-micro">
            <div className="flex gap-6">
              <span className="flex items-center gap-1"><span className="material-symbols-outlined text-[12px]">lock</span> AES-256</span>
              <span className="flex items-center gap-1"><span className="material-symbols-outlined text-[12px]">dns</span> WS LIVE</span>
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
        <div className="fixed right-4 bottom-4 z-50 bg-inverse-surface text-inverse-on-surface px-4 py-3 font-body-compact text-body-compact shadow-lg toast-anim" onAnimationEnd={() => setToast("")}>
          {toast}
        </div>
      )}
    </div>
  );
}
