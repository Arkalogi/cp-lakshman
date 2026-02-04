import React, { useEffect, useMemo, useState } from "react";
import { listMasterData, listSignalOrders, updateOrderStatus } from "../api.js";

const EMPTY_FORM = {
  strategy_id: "1",
  instrument_id: "",
  side: "buy",
  type: "enter_position",
  depends_on_signal_id: "",
  meta_data: "",
};

function formatCell(value) {
  if (value === null || value === undefined) {
    return "";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

export default function SignalsSection({ signals, baseUrl, onCreate, onRefresh, onError }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [instruments, setInstruments] = useState([]);
  const [instrumentQuery, setInstrumentQuery] = useState("");
  const [expandedSignalId, setExpandedSignalId] = useState(null);
  const [childOrdersBySignalId, setChildOrdersBySignalId] = useState({});
  const [loadingSignalId, setLoadingSignalId] = useState(null);
  const [statusForm, setStatusForm] = useState({
    order_id: "",
    status: "",
    filled_quantity: "",
    average_price: "",
    broker_order_id: "",
    error_code: "",
    error_message: "",
  });

  useEffect(() => {
    if (!baseUrl) {
      return;
    }
    let cancelled = false;
    listMasterData(baseUrl)
      .then((items) => {
        if (!cancelled) {
          setInstruments(items);
        }
      })
      .catch((error) => {
        if (!cancelled) {
          onError?.(error.message || "Failed to load master data.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [baseUrl, onError]);

  const filteredInstruments = useMemo(() => {
    const query = instrumentQuery.trim().toLowerCase();
    if (!query) {
      return instruments.slice(0, 100);
    }
    return instruments
      .filter((item) => {
        const idMatch = String(item.instrument_id || "").toLowerCase().includes(query);
        const symbolMatch = String(item.trading_symbol || "").toLowerCase().includes(query);
        const underlyingMatch = String(item.underlying || "").toLowerCase().includes(query);
        return idMatch || symbolMatch || underlyingMatch;
      })
      .slice(0, 200);
  }, [instrumentQuery, instruments]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    const payload = {
      strategy_id: Number(form.strategy_id),
      instrument_id: form.instrument_id,
      side: form.side,
    };
    if (form.type) {
      payload.type = form.type;
    }
    if (form.depends_on_signal_id) {
      payload.depends_on_signal_id = Number(form.depends_on_signal_id);
    }
    if (form.meta_data) {
      payload.meta_data = form.meta_data;
    }
    await onCreate(payload);
    setForm(EMPTY_FORM);
  };

  const handleToggleOrders = async (signal) => {
    if (!signal?.id) {
      onError?.("Signal ID is required.");
      return;
    }
    if (expandedSignalId === signal.id) {
      setExpandedSignalId(null);
      return;
    }
    setExpandedSignalId(signal.id);
    if (childOrdersBySignalId[signal.id]) {
      return;
    }
    setLoadingSignalId(signal.id);
    try {
      const list = await listSignalOrders(baseUrl, signal.id);
      setChildOrdersBySignalId((prev) => ({
        ...prev,
        [signal.id]: list,
      }));
    } catch (error) {
      onError?.(error.message || "Failed to load signal orders.");
    } finally {
      setLoadingSignalId(null);
    }
  };

  const handleUpdateStatus = async (event) => {
    event.preventDefault();
    const orderId = statusForm.order_id.trim();
    if (!orderId) {
      onError?.("Order ID is required.");
      return;
    }
    const payload = {};
    if (statusForm.status) payload.status = statusForm.status;
    if (statusForm.filled_quantity !== "") {
      payload.filled_quantity = Number(statusForm.filled_quantity);
    }
    if (statusForm.average_price !== "") {
      payload.average_price = Number(statusForm.average_price);
    }
    if (statusForm.broker_order_id) payload.broker_order_id = statusForm.broker_order_id;
    if (statusForm.error_code) payload.error_code = statusForm.error_code;
    if (statusForm.error_message) payload.error_message = statusForm.error_message;
    try {
      await updateOrderStatus(baseUrl, Number(orderId), payload);
      setStatusForm((prev) => ({ ...prev, status: "" }));
    } catch (error) {
      onError?.(error.message || "Failed to update order.");
    }
  };

  return (
    <section className="panel">
      <header className="panel-header">
        <div>
          <h2>Signals</h2>
          <p>Create entry/exit signals and review latest activity.</p>
        </div>
        <div className="panel-actions">
          <span className="pill">{signals?.length ?? 0} items</span>
          <button type="button" className="ghost" onClick={onRefresh}>
            Refresh
          </button>
        </div>
      </header>
      <div className="panel-content">
        <form className="form-grid" onSubmit={handleSubmit}>
          <div className="field">
            <label>Strategy ID</label>
            <input
              type="number"
              value={form.strategy_id}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, strategy_id: event.target.value }))
              }
              required
            />
          </div>
          <div className="field">
            <label>Instrument ID</label>
            <input
              value={form.instrument_id}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, instrument_id: event.target.value }))
              }
              required
              list="instrument-suggestions"
            />
          </div>
          <div className="field">
            <label>Find Instrument</label>
            <input
              value={instrumentQuery}
              onChange={(event) => setInstrumentQuery(event.target.value)}
              placeholder="Search by instrument_id / symbol / underlying"
            />
            <datalist id="instrument-suggestions">
              {filteredInstruments.map((item) => (
                <option key={item.instrument_id} value={item.instrument_id}>
                  {item.instrument_id} - {item.trading_symbol} ({item.underlying})
                </option>
              ))}
            </datalist>
          </div>
          <div className="field">
            <label>Side</label>
            <select
              value={form.side}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, side: event.target.value }))
              }
            >
              <option value="buy">buy</option>
              <option value="sell">sell</option>
            </select>
          </div>
          <div className="field">
            <label>Type</label>
            <select
              value={form.type}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, type: event.target.value }))
              }
            >
              <option value="enter_position">enter_position</option>
              <option value="exit_position">exit_position</option>
            </select>
          </div>
          <div className="field">
            <label>Depends On Signal ID</label>
            <input
              type="number"
              value={form.depends_on_signal_id}
              onChange={(event) =>
                setForm((prev) => ({
                  ...prev,
                  depends_on_signal_id: event.target.value,
                }))
              }
            />
          </div>
          <div className="field">
            <label>Meta Data</label>
            <textarea
              rows={3}
              value={form.meta_data}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, meta_data: event.target.value }))
              }
            />
          </div>
          <div className="row-actions">
            <button type="submit">Create Signal</button>
          </div>
        </form>

        {signals?.length ? (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  {Object.keys(signals[0] || {}).map((key) => (
                    <th key={key}>{key}</th>
                  ))}
                  <th>actions</th>
                </tr>
              </thead>
              <tbody>
                {signals.map((signal) => (
                  <React.Fragment key={signal.id || signal.strategy_id}>
                    <tr>
                      {Object.keys(signals[0] || {}).map((key) => (
                        <td key={key}>{formatCell(signal?.[key])}</td>
                      ))}
                      <td>
                        <button
                          type="button"
                          className="ghost"
                          onClick={() => handleToggleOrders(signal)}
                        >
                          {expandedSignalId === signal.id ? "Hide Orders" : "Show Orders"}
                        </button>
                      </td>
                    </tr>
                    {expandedSignalId === signal.id ? (
                      <tr className="subrow">
                        <td colSpan={(Object.keys(signals[0] || {}).length || 0) + 1}>
                          {loadingSignalId === signal.id ? (
                            <div className="empty-state">Loading signal orders...</div>
                          ) : childOrdersBySignalId[signal.id]?.length ? (
                            <div className="table-wrapper">
                              <table>
                                <thead>
                                  <tr>
                                    {Object.keys(
                                      childOrdersBySignalId[signal.id][0] || {}
                                    ).map((key) => (
                                      <th key={key}>{key}</th>
                                    ))}
                                  </tr>
                                </thead>
                                <tbody>
                                  {childOrdersBySignalId[signal.id].map(
                                    (order, index) => (
                                      <tr key={order.id || index}>
                                        {Object.keys(
                                          childOrdersBySignalId[signal.id][0] || {}
                                        ).map((key) => (
                                          <td key={key}>{formatCell(order?.[key])}</td>
                                        ))}
                                      </tr>
                                    )
                                  )}
                                </tbody>
                              </table>
                            </div>
                          ) : (
                            <div className="empty-state">No signal orders found.</div>
                          )}
                        </td>
                      </tr>
                    ) : null}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">No signals yet.</div>
        )}

        <form className="inline-form" onSubmit={handleUpdateStatus}>
          <div className="field">
            <label>Order ID</label>
            <input
              type="number"
              value={statusForm.order_id}
              onChange={(event) =>
                setStatusForm((prev) => ({ ...prev, order_id: event.target.value }))
              }
            />
          </div>
          <div className="field">
            <label>Status</label>
            <select
              value={statusForm.status}
              onChange={(event) =>
                setStatusForm((prev) => ({ ...prev, status: event.target.value }))
              }
            >
              <option value="">Select</option>
              <option value="pending">pending</option>
              <option value="completed">completed</option>
              <option value="failed">failed</option>
            </select>
          </div>
          <div className="field">
            <label>Filled Qty</label>
            <input
              type="number"
              value={statusForm.filled_quantity}
              onChange={(event) =>
                setStatusForm((prev) => ({
                  ...prev,
                  filled_quantity: event.target.value,
                }))
              }
            />
          </div>
          <div className="field">
            <label>Avg Price</label>
            <input
              type="number"
              value={statusForm.average_price}
              onChange={(event) =>
                setStatusForm((prev) => ({
                  ...prev,
                  average_price: event.target.value,
                }))
              }
            />
          </div>
          <div className="field">
            <label>Broker Order ID</label>
            <input
              value={statusForm.broker_order_id}
              onChange={(event) =>
                setStatusForm((prev) => ({
                  ...prev,
                  broker_order_id: event.target.value,
                }))
              }
            />
          </div>
          <div className="field">
            <label>Error Code</label>
            <input
              value={statusForm.error_code}
              onChange={(event) =>
                setStatusForm((prev) => ({
                  ...prev,
                  error_code: event.target.value,
                }))
              }
            />
          </div>
          <div className="field">
            <label>Error Message</label>
            <input
              value={statusForm.error_message}
              onChange={(event) =>
                setStatusForm((prev) => ({
                  ...prev,
                  error_message: event.target.value,
                }))
              }
            />
          </div>
          <button type="submit" className="ghost">
            Update Status
          </button>
        </form>
      </div>
    </section>
  );
}
