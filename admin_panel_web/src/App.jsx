import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  createEntity,
  deleteEntity,
  health,
  listEntities,
  listOrders,
  listSubscriberOrders,
  normalizeBaseUrl,
  updateEntity,
} from "./api.js";
import CopyMonitor from "./components/CopyMonitor.jsx";
import EntitySection from "./components/EntitySection.jsx";
import OrderMonitor from "./components/OrderMonitor.jsx";

const DEFAULT_BASE_URL = "http://localhost:8000";

const entityConfigs = [
  {
    key: "users",
    title: "Users",
    endpoint: "/users",
    columns: ["id", "first_name", "last_name", "username", "email", "phone", "is_active"],
    createFields: [
      { name: "first_name", label: "First name" },
      { name: "last_name", label: "Last name" },
      { name: "username", label: "Username" },
      { name: "email", label: "Email" },
      { name: "phone", label: "Phone" },
    ],
    updateFields: [
      { name: "id", label: "User ID", type: "number" },
      { name: "first_name", label: "First name" },
      { name: "last_name", label: "Last name" },
      { name: "username", label: "Username" },
      { name: "email", label: "Email" },
      { name: "phone", label: "Phone" },
      { name: "is_active", label: "Active", type: "boolean" },
    ],
  },
  {
    key: "strategies",
    title: "Strategies",
    endpoint: "/strategies",
    columns: ["id", "name", "description", "config", "user_id"],
    createFields: [
      { name: "name", label: "Name" },
      { name: "description", label: "Description", type: "textarea" },
      {
        name: "config",
        label: "Config (JSON string)",
        type: "json_string",
        placeholder: "{\"symbol\":\"NIFTY\"}",
      },
      { name: "user_id", label: "User ID", type: "number" },
    ],
    updateFields: [
      { name: "id", label: "Strategy ID", type: "number" },
      { name: "name", label: "Name" },
      { name: "description", label: "Description", type: "textarea" },
      {
        name: "config",
        label: "Config (JSON string)",
        type: "json_string",
        placeholder: "{\"symbol\":\"NIFTY\"}",
      },
      { name: "user_id", label: "User ID", type: "number" },
    ],
  },
  {
    key: "demat_apis",
    title: "Demat APIs",
    endpoint: "/demat-apis/",
    columns: ["id", "config", "user_id"],
    createFields: [
      {
        name: "config",
        label: "Config (JSON object)",
        type: "json_object",
        placeholder:
          "{\"api_provider\":\"upstox\",\"demat_provider\":\"upstox\",\"api_key\":\"\",\"api_secret\":\"\"}",
      },
      { name: "user_id", label: "User ID", type: "number" },
    ],
    updateFields: [
      { name: "id", label: "API ID", type: "number" },
      {
        name: "config",
        label: "Config (JSON object)",
        type: "json_object",
        placeholder:
          "{\"api_provider\":\"upstox\",\"demat_provider\":\"upstox\",\"api_key\":\"\",\"api_secret\":\"\"}",
      },
      { name: "user_id", label: "User ID", type: "number" },
    ],
  },
  {
    key: "strategy_subscriptions",
    title: "Strategy Subscriptions",
    endpoint: "/strategy-subscriptions",
    columns: ["id", "subscriber_id", "target_id", "multiplier"],
    createFields: [
      { name: "subscriber_id", label: "Subscriber ID", type: "number" },
      { name: "target_id", label: "Target ID", type: "number" },
      { name: "multiplier", label: "Multiplier", type: "number" },
    ],
    updateFields: [
      { name: "id", label: "Subscription ID", type: "number" },
      { name: "subscriber_id", label: "Subscriber ID", type: "number" },
      { name: "target_id", label: "Target ID", type: "number" },
      { name: "multiplier", label: "Multiplier", type: "number" },
    ],
  },
  {
    key: "demat_api_subscriptions",
    title: "Demat API Subscriptions",
    endpoint: "/demat-api-subscriptions",
    columns: ["id", "subscriber_id", "target_id", "multiplier", "is_active"],
    createFields: [
      { name: "subscriber_id", label: "Subscriber ID", type: "number" },
      { name: "target_id", label: "Target ID", type: "number" },
    ],
    updateFields: [
      { name: "id", label: "Subscription ID", type: "number" },
      { name: "subscriber_id", label: "Subscriber ID", type: "number" },
      { name: "target_id", label: "Target ID", type: "number" },
    ],
  },
];

export default function App() {
  const [baseUrl, setBaseUrl] = useState(DEFAULT_BASE_URL);
  const [connected, setConnected] = useState(false);
  const [healthStatus, setHealthStatus] = useState("unknown");
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [orders, setOrders] = useState([]);
  const [ordersTotal, setOrdersTotal] = useState(0);
  const [ordersLimit, setOrdersLimit] = useState(20);
  const [ordersOffset, setOrdersOffset] = useState(0);
  const [subscriberOrders, setSubscriberOrders] = useState([]);
  const [subscriberModalOpen, setSubscriberModalOpen] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [data, setData] = useState(() =>
    entityConfigs.reduce((acc, entity) => {
      acc[entity.key] = [];
      return acc;
    }, {})
  );

  const normalizedBaseUrl = useMemo(() => normalizeBaseUrl(baseUrl), [baseUrl]);

  const refreshEntity = useCallback(
    async (entityKey, endpoint) => {
      const list = await listEntities(normalizedBaseUrl, endpoint);
      setData((prev) => ({ ...prev, [entityKey]: list }));
    },
    [normalizedBaseUrl]
  );

  const refreshAll = useCallback(async () => {
    if (!normalizedBaseUrl) {
      return;
    }
    setIsLoading(true);
    setError("");
    try {
      await Promise.all(
        entityConfigs.map((entity) => refreshEntity(entity.key, entity.endpoint))
      );
      const ordersPage = await listOrders(
        normalizedBaseUrl,
        ordersLimit,
        ordersOffset
      );
      setOrders(ordersPage.items);
      setOrdersTotal(ordersPage.total);
      const status = await health(normalizedBaseUrl);
      setHealthStatus(status);
      setNotice("Data refreshed.");
    } catch (err) {
      setError(err.message || "Failed to refresh.");
    } finally {
      setIsLoading(false);
    }
  }, [normalizedBaseUrl, refreshEntity]);

  useEffect(() => {
    if (!autoRefresh || !connected) {
      return undefined;
    }
    const interval = setInterval(() => {
      refreshAll();
    }, 5000);
    return () => clearInterval(interval);
  }, [autoRefresh, connected, refreshAll]);

  const connect = async () => {
    setConnected(true);
    await refreshAll();
  };

  const handleCreate = async (entity, payload, errorObj) => {
    if (errorObj) {
      setError(errorObj.message);
      return;
    }
    try {
      await createEntity(normalizedBaseUrl, entity.endpoint, payload);
      await refreshEntity(entity.key, entity.endpoint);
      setNotice(`${entity.title} created.`);
    } catch (err) {
      setError(err.message || "Create failed.");
    }
  };

  const handleUpdate = async (entity, id, payload, errorObj) => {
    if (errorObj) {
      setError(errorObj.message);
      return;
    }
    try {
      await updateEntity(normalizedBaseUrl, entity.endpoint, id, payload);
      await refreshEntity(entity.key, entity.endpoint);
      setNotice(`${entity.title} updated.`);
    } catch (err) {
      setError(err.message || "Update failed.");
    }
  };

  const handleDelete = async (entity, id, errorObj) => {
    if (errorObj) {
      setError(errorObj.message);
      return;
    }
    try {
      await deleteEntity(normalizedBaseUrl, entity.endpoint, id);
      await refreshEntity(entity.key, entity.endpoint);
      setNotice(`${entity.title} deleted.`);
    } catch (err) {
      setError(err.message || "Delete failed.");
    }
  };

  const handleOrderRefresh = async () => {
    try {
      const ordersPage = await listOrders(
        normalizedBaseUrl,
        ordersLimit,
        ordersOffset
      );
      setOrders(ordersPage.items);
      setOrdersTotal(ordersPage.total);
      setNotice("Orders refreshed.");
    } catch (err) {
      setError(err.message || "Failed to refresh orders.");
    }
  };

  const handleOrdersNext = async () => {
    const nextOffset = ordersOffset + ordersLimit;
    setOrdersOffset(nextOffset);
    try {
      const ordersPage = await listOrders(
        normalizedBaseUrl,
        ordersLimit,
        nextOffset
      );
      setOrders(ordersPage.items);
      setOrdersTotal(ordersPage.total);
    } catch (err) {
      setError(err.message || "Failed to load next orders page.");
    }
  };

  const handleOrdersPrev = async () => {
    const nextOffset = Math.max(0, ordersOffset - ordersLimit);
    setOrdersOffset(nextOffset);
    try {
      const ordersPage = await listOrders(
        normalizedBaseUrl,
        ordersLimit,
        nextOffset
      );
      setOrders(ordersPage.items);
      setOrdersTotal(ordersPage.total);
    } catch (err) {
      setError(err.message || "Failed to load previous orders page.");
    }
  };

  const handleViewSubscribers = async (order) => {
    if (!order?.id) {
      setError("Order ID is required to load subscriber orders.");
      return;
    }
    try {
      const list = await listSubscriberOrders(normalizedBaseUrl, order.id);
      setSubscriberOrders(list);
      setSelectedOrder(order);
      setSubscriberModalOpen(true);
    } catch (err) {
      setError(err.message || "Failed to load subscriber orders.");
    }
  };

  return (
    <div className="app">
      <header className="hero">
        <div>
          <span className="eyebrow">CopyTrade Admin</span>
          <h1>Live control surface for your copy engine.</h1>
          <p>
            Manage users, strategies, API subscriptions, and monitor copy traffic
            in one place.
          </p>
        </div>
        <div className="status-card">
          <div>
            <span className="label">API status</span>
            <strong>{healthStatus}</strong>
          </div>
          <div>
            <span className="label">Base URL</span>
            <strong>{normalizedBaseUrl || "-"}</strong>
          </div>
        </div>
      </header>

      <section className="panel control-panel">
        <div className="control-row">
          <div className="field">
            <label htmlFor="base-url">API Base URL</label>
            <input
              id="base-url"
              value={baseUrl}
              onChange={(event) => setBaseUrl(event.target.value)}
              placeholder="http://localhost:8000"
            />
          </div>
          <button onClick={connect} disabled={isLoading}>
            {connected ? "Reconnect" : "Connect"}
          </button>
          <button className="ghost" onClick={refreshAll} disabled={isLoading}>
            Refresh
          </button>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(event) => setAutoRefresh(event.target.checked)}
            />
            Auto refresh (5s)
          </label>
        </div>
        {notice ? <div className="notice">{notice}</div> : null}
        {error ? <div className="error">{error}</div> : null}
      </section>

      <CopyMonitor
        strategySubs={data.strategy_subscriptions}
        dematSubs={data.demat_api_subscriptions}
      />

      <OrderMonitor
        orders={orders}
        total={ordersTotal}
        limit={ordersLimit}
        offset={ordersOffset}
        onRefresh={handleOrderRefresh}
        onViewSubscribers={handleViewSubscribers}
        onNext={handleOrdersNext}
        onPrev={handleOrdersPrev}
      />

      {entityConfigs.map((entity) => (
        <EntitySection
          key={entity.key}
          title={entity.title}
          description={entity.description}
          data={data[entity.key]}
          columns={entity.columns}
          createFields={entity.createFields}
          updateFields={entity.updateFields}
          onCreate={(payload, errorObj) => handleCreate(entity, payload, errorObj)}
          onUpdate={(id, payload, errorObj) =>
            handleUpdate(entity, id, payload, errorObj)
          }
          onDelete={(id, errorObj) => handleDelete(entity, id, errorObj)}
        />
      ))}

      {subscriberModalOpen ? (
        <div
          className="modal-backdrop"
          onClick={() => setSubscriberModalOpen(false)}
        >
          <div className="modal-card" onClick={(event) => event.stopPropagation()}>
            <div className="form-card-header">
              <h3>
                Subscriber Orders for Order{" "}
                {selectedOrder?.id ? `#${selectedOrder.id}` : ""}
              </h3>
              <button
                type="button"
                className="ghost"
                onClick={() => setSubscriberModalOpen(false)}
              >
                Close
              </button>
            </div>
            {subscriberOrders.length ? (
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      {Object.keys(subscriberOrders[0] || {}).map((key) => (
                        <th key={key}>{key}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {subscriberOrders.map((row, index) => (
                      <tr key={row.id || index}>
                        {Object.keys(subscriberOrders[0] || {}).map((key) => (
                          <td key={key}>{String(row?.[key] ?? "")}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="empty-state">No subscriber orders found.</div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
