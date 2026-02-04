export function normalizeBaseUrl(baseUrl) {
  if (!baseUrl) {
    return "";
  }
  return baseUrl.endsWith("/") ? baseUrl.slice(0, -1) : baseUrl;
}

async function parseJsonResponse(response) {
  const text = await response.text();
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text);
  } catch (error) {
    throw new Error("Invalid JSON response from API.");
  }
}

export async function request(baseUrl, path, options = {}) {
  const url = `${normalizeBaseUrl(baseUrl)}${path}`;
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });
  const data = await parseJsonResponse(response);
  if (!response.ok) {
    const message = data?.detail || data?.message || response.statusText;
    throw new Error(message || "Request failed.");
  }
  if (data?.status && data.status !== "success") {
    throw new Error(data.message || "API returned an error.");
  }
  return data;
}

export async function health(baseUrl) {
  const url = `${normalizeBaseUrl(baseUrl)}/health`;
  const response = await fetch(url);
  const data = await parseJsonResponse(response);
  return data?.status || "unknown";
}

export async function listEntities(baseUrl, endpoint) {
  const collectionPath = endpoint.endsWith("/") ? endpoint : `${endpoint}/`;
  const data = await request(baseUrl, collectionPath);
  if (!data) {
    return [];
  }
  const payload = data.data ?? [];
  return Array.isArray(payload) ? payload : [payload];
}

export async function listOrders(baseUrl, limit = 20, offset = 0) {
  const query = `?limit=${limit}&offset=${offset}`;
  const data = await request(baseUrl, `/orders/${query}`);
  const payload = data?.data || {};
  return {
    items: Array.isArray(payload.items) ? payload.items : [],
    total: Number(payload.total || 0),
    limit: Number(payload.limit || limit),
    offset: Number(payload.offset || offset),
  };
}

export async function listSignalOrders(baseUrl, signalId, status) {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  const data = await request(baseUrl, `/signals/${signalId}/orders${query}`);
  const payload = data?.data ?? [];
  return Array.isArray(payload) ? payload : [payload];
}

export async function listChildOrders(baseUrl, params = {}) {
  const query = new URLSearchParams(params).toString();
  const suffix = query ? `?${query}` : "";
  const data = await request(baseUrl, `/orders/children${suffix}`);
  const payload = data?.data ?? [];
  return Array.isArray(payload) ? payload : [payload];
}

export async function updateOrderStatus(baseUrl, orderId, payload) {
  return request(baseUrl, `/orders/${orderId}/status`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function createEntity(baseUrl, endpoint, payload) {
  const collectionPath = endpoint.endsWith("/") ? endpoint : `${endpoint}/`;
  return request(baseUrl, collectionPath, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateEntity(baseUrl, endpoint, id, payload) {
  return request(baseUrl, `${endpoint}/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function deleteEntity(baseUrl, endpoint, id) {
  return request(baseUrl, `${endpoint}/${id}`, {
    method: "DELETE",
  });
}
