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
