import React, { useMemo } from "react";

function formatCell(value) {
  if (value === null || value === undefined) {
    return "";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

function OrderStatusForm({ onSubmit }) {
  const [form, setForm] = React.useState({
    order_id: "",
    status: "",
    filled_quantity: "",
    average_price: "",
    broker_order_id: "",
    error_code: "",
    error_message: "",
  });

  const handleChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    const orderId = form.order_id.trim();
    if (!orderId) {
      onSubmit(null, new Error("Order ID is required."));
      return;
    }
    const payload = {};
    if (form.status) payload.status = form.status;
    if (form.filled_quantity !== "") payload.filled_quantity = Number(form.filled_quantity);
    if (form.average_price !== "") payload.average_price = Number(form.average_price);
    if (form.broker_order_id) payload.broker_order_id = form.broker_order_id;
    if (form.error_code) payload.error_code = form.error_code;
    if (form.error_message) payload.error_message = form.error_message;
    onSubmit(Number(orderId), payload);
    setForm((prev) => ({ ...prev, status: "" }));
  };

  return (
    <form className="inline-form" onSubmit={handleSubmit}>
      <div className="field">
        <label>Order ID</label>
        <input
          type="number"
          value={form.order_id}
          onChange={(event) => handleChange("order_id", event.target.value)}
        />
      </div>
      <div className="field">
        <label>Status</label>
        <select
          value={form.status}
          onChange={(event) => handleChange("status", event.target.value)}
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
          value={form.filled_quantity}
          onChange={(event) => handleChange("filled_quantity", event.target.value)}
        />
      </div>
      <div className="field">
        <label>Avg Price</label>
        <input
          type="number"
          value={form.average_price}
          onChange={(event) => handleChange("average_price", event.target.value)}
        />
      </div>
      <div className="field">
        <label>Broker Order ID</label>
        <input
          value={form.broker_order_id}
          onChange={(event) => handleChange("broker_order_id", event.target.value)}
        />
      </div>
      <div className="field">
        <label>Error Code</label>
        <input
          value={form.error_code}
          onChange={(event) => handleChange("error_code", event.target.value)}
        />
      </div>
      <div className="field">
        <label>Error Message</label>
        <input
          value={form.error_message}
          onChange={(event) => handleChange("error_message", event.target.value)}
        />
      </div>
      <button type="submit" className="ghost">
        Update Status
      </button>
    </form>
  );
}

export default function OrderMonitor({
  orders,
  total,
  limit,
  offset,
  onRefresh,
  onToggleChildren,
  expandedOrderId,
  childOrdersBySignalId,
  loadingSignalId,
  onNext,
  onPrev,
  onUpdateStatus,
}) {
  const columns = useMemo(
    () => [
      "id",
      "tag",
      "trading_symbol",
      "side",
      "quantity",
      "price",
      "status",
      "created_at",
    ],
    []
  );

  return (
    <section className="panel">
      <header className="panel-header">
        <div>
          <h2>Orders</h2>
          <p>All orders and routed child orders grouped by signal.</p>
        </div>
        <div className="panel-actions">
          <span className="pill">
            {orders?.length ?? 0} / {total ?? 0}
          </span>
          <button type="button" className="ghost" onClick={onRefresh}>
            Refresh
          </button>
        </div>
      </header>
      <div className="panel-content">
        {orders?.length ? (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  {columns.map((column) => (
                    <th key={column}>{column}</th>
                  ))}
                  <th className="sticky-action">actions</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((row) => (
                  <React.Fragment key={row.id || row.tag}>
                    <tr>
                      {columns.map((column) => (
                        <td key={column}>{formatCell(row?.[column])}</td>
                      ))}
                      <td className="sticky-action">
                        <div className="row-actions">
                          <button
                            type="button"
                            className="icon-button"
                            onClick={() => onToggleChildren(row)}
                            aria-label={
                              expandedOrderId === row.signal_id
                                ? "Hide signal orders"
                                : "Show signal orders"
                            }
                          >
                            {expandedOrderId === row.signal_id ? (
                              <span className="icon-minus" aria-hidden="true"></span>
                            ) : (
                              <span className="icon-chevron" aria-hidden="true"></span>
                            )}
                          </button>
                        </div>
                      </td>
                    </tr>
                    {expandedOrderId === row.signal_id ? (
                      <tr className="subrow">
                        <td colSpan={columns.length + 1}>
                          {loadingSignalId === row.signal_id ? (
                            <div className="empty-state">
                              Loading signal orders...
                            </div>
                          ) : childOrdersBySignalId[row.signal_id]?.length ? (
                            <div className="table-wrapper">
                              <table>
                                <thead>
                                  <tr>
                                    {Object.keys(
                                      childOrdersBySignalId[row.signal_id][0] || {}
                                    ).map((key) => (
                                      <th key={key}>{key}</th>
                                    ))}
                                  </tr>
                                </thead>
                                <tbody>
                                  {childOrdersBySignalId[row.signal_id].map(
                                    (sub, index) => (
                                      <tr key={sub.id || index}>
                                        {Object.keys(
                                          childOrdersBySignalId[row.signal_id][0] || {}
                                        ).map((key) => (
                                          <td key={key}>{formatCell(sub?.[key])}</td>
                                        ))}
                                      </tr>
                                    )
                                  )}
                                </tbody>
                              </table>
                            </div>
                          ) : (
                            <div className="empty-state">
                              No signal orders found.
                            </div>
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
          <div className="empty-state">No orders yet.</div>
        )}
        <OrderStatusForm onSubmit={onUpdateStatus} />
        <div className="pagination">
          <button type="button" className="ghost" onClick={onPrev} disabled={offset <= 0}>
            Prev
          </button>
          <span className="page-label">
            {offset + 1}-{Math.min(offset + limit, total)} of {total}
          </span>
          <button
            type="button"
            className="ghost"
            onClick={onNext}
            disabled={offset + limit >= total}
          >
            Next
          </button>
        </div>
      </div>
    </section>
  );
}
