const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || "Request failed");
  if (payload.status && payload.status !== "success")
    throw new Error(payload.message || "Operation failed");
  return payload.data;
}

export const api = {
  // ── Watchlists ──────────────────────────────────────────────────────────────
  listWatchlists: () => request("/watchlists/"),
  createWatchlist: (body) =>
    request("/watchlists/", { method: "POST", body: JSON.stringify(body) }),
  addWatchlistItem: (watchlistId, instrumentId) =>
    request(`/watchlists/${watchlistId}/items`, {
      method: "POST",
      body: JSON.stringify({ instrument_id: instrumentId })
    }),
  // DELETE returns updated watchlist; instrument_id is the XTS string id
  removeWatchlistItem: (watchlistId, instrumentId) =>
    request(`/watchlists/${watchlistId}/items/${instrumentId}`, { method: "DELETE" }),

  // ── Strategies ──────────────────────────────────────────────────────────────
  listStrategies: () => request("/strategies/"),
  createStrategy: (body) =>
    request("/strategies/", { method: "POST", body: JSON.stringify(body) }),

  // ── Users  (backend only stores: first_name, last_name, username, email, phone)
  listUsers: () => request("/users/"),
  createUser: (body) =>
    request("/users/", { method: "POST", body: JSON.stringify(body) }),
  // Backend exposes PUT, not PATCH
  updateUser: (userId, body) =>
    request(`/users/${userId}`, { method: "PUT", body: JSON.stringify(body) }),
  deleteUser: (userId) =>
    request(`/users/${userId}`, { method: "DELETE" }),

  // ── Demat / Broker API credentials  (POST /demat-apis/)
  // config shape: { api_provider, demat_provider, api_key, api_secret,
  //                 mobile_number, totp_secret, pin, redirect_url }
  listDematApis: () => request("/demat-apis/"),
  createDematApi: (body) =>
    request("/demat-apis/", { method: "POST", body: JSON.stringify(body) }),
  updateDematApi: (apiId, body) =>
    request(`/demat-apis/${apiId}`, { method: "PUT", body: JSON.stringify(body) }),
  deleteDematApi: (apiId) =>
    request(`/demat-apis/${apiId}`, { method: "DELETE" }),

  // ── User IP Whitelist  (one record per user, stores static_ip + private_ip)
  // GET  /user-ips/user/{user_id}
  getUserIp: (userId) => request(`/user-ips/user/${userId}`),
  // POST /user-ips/  body: { user_id, static_ip, private_ip }
  createUserIp: (body) =>
    request("/user-ips/", { method: "POST", body: JSON.stringify(body) }),
  // PUT  /user-ips/{ip_id}  body: { static_ip?, private_ip? }
  updateUserIp: (ipId, body) =>
    request(`/user-ips/${ipId}`, { method: "PUT", body: JSON.stringify(body) }),
  // DELETE /user-ips/{ip_id}
  deleteUserIp: (ipId) =>
    request(`/user-ips/${ipId}`, { method: "DELETE" }),

  // ── Signals ─────────────────────────────────────────────────────────────────
  createSignal: (body) =>
    request("/signals/", { method: "POST", body: JSON.stringify(body) }),
  listSignals: () => request("/signals/"),

  // ── Instruments ─────────────────────────────────────────────────────────────
  searchInstruments: (query, limit = 25) =>
    request(`/master-data/search?trading_symbol=${encodeURIComponent(query)}&limit=${limit}&offset=0`)
};
