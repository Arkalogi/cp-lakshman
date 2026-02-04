import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  createEntity,
  deleteEntity,
  health,
  listEntities,
  listOrders,
  listSignalOrders,
  normalizeBaseUrl,
  updateOrderStatus,
  updateEntity,
} from "./api.js";
import CopyMonitor from "./components/CopyMonitor.jsx";
import EntitySection from "./components/EntitySection.jsx";
import OrderMonitor from "./components/OrderMonitor.jsx";
import SignalsSection from "./components/SignalsSection.jsx";

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
  const [expandedSignalId, setExpandedSignalId] = useState(null);
  const [childOrdersBySignalId, setChildOrdersBySignalId] = useState({});
  const [loadingSignalId, setLoadingSignalId] = useState(null);
  const [data, setData] = useState(() =>
    entityConfigs.reduce((acc, entity) => {
      acc[entity.key] = [];
      return acc;
    }, { signals: [] })
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
      await refreshEntity("signals", "/signals");
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

  const handleToggleChildren = async (order) => {
    if (!order?.signal_id) {
      setError("Signal ID is required to load signal orders.");
      return;
    }
    if (expandedSignalId === order.signal_id) {
      setExpandedSignalId(null);
      return;
    }
    setExpandedSignalId(order.signal_id);
    if (childOrdersBySignalId[order.signal_id]) {
      return;
    }
    setLoadingSignalId(order.signal_id);
    try {
      const list = await listSignalOrders(normalizedBaseUrl, order.signal_id);
      setChildOrdersBySignalId((prev) => ({
        ...prev,
        [order.signal_id]: list,
      }));
    } catch (err) {
      setError(err.message || "Failed to load signal orders.");
    } finally {
      setLoadingSignalId(null);
    }
  };

  const handleUpdateOrderStatus = async (orderId, payload, errorObj) => {
    if (errorObj) {
      setError(errorObj.message);
      return;
    }
    try {
      await updateOrderStatus(normalizedBaseUrl, orderId, payload);
      await handleOrderRefresh();
      setNotice("Order status updated.");
    } catch (err) {
      setError(err.message || "Failed to update order.");
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

      <CopyMonitor strategySubs={data.strategy_subscriptions} />

      <SignalsSection
        signals={data.signals}
        onCreate={(payload, errorObj) => handleCreate({ key: "signals", endpoint: "/signals", title: "Signals" }, payload, errorObj)}
        onRefresh={() => refreshEntity("signals", "/signals")}
      />

      <OrderMonitor
        orders={orders}
        total={ordersTotal}
        limit={ordersLimit}
        offset={ordersOffset}
        onRefresh={handleOrderRefresh}
        onToggleChildren={handleToggleChildren}
        expandedOrderId={expandedSignalId}
        childOrdersBySignalId={childOrdersBySignalId}
        loadingSignalId={loadingSignalId}
        onNext={handleOrdersNext}
        onPrev={handleOrdersPrev}
        onUpdateStatus={handleUpdateOrderStatus}
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

    </div>
  );
}
