const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    ...options
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || "Request failed");
  }
  if (payload.status && payload.status !== "success") {
    throw new Error(payload.message || "Operation failed");
  }
  return payload.data;
}

export const api = {
  listWatchlists: () => request("/watchlists/"),
  createWatchlist: (body) =>
    request("/watchlists/", { method: "POST", body: JSON.stringify(body) }),
  addWatchlistItem: (watchlistId, instrumentId) =>
    request(`/watchlists/${watchlistId}/items`, {
      method: "POST",
      body: JSON.stringify({ instrument_id: instrumentId })
    }),
  removeWatchlistItem: (watchlistId, instrumentId) =>
    request(`/watchlists/${watchlistId}/items/${instrumentId}`, {
      method: "DELETE"
    }),
  listStrategies: () => request("/strategies/"),
  createUser: (body) =>
    request("/users/", { method: "POST", body: JSON.stringify(body) }),
  createStrategy: (body) =>
    request("/strategies/", { method: "POST", body: JSON.stringify(body) }),
  createSignal: (body) =>
    request("/signals/", { method: "POST", body: JSON.stringify(body) }),
  listSignals: () => request("/signals/"),
  searchInstruments: (query, limit = 25) =>
    request(
      `/master-data/search?trading_symbol=${encodeURIComponent(
        query
      )}&limit=${limit}&offset=0`
    )
};
