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

export default function OrderMonitor({
  orders,
  total,
  limit,
  offset,
  onRefresh,
  onToggleSubscribers,
  expandedOrderId,
  subscriberOrdersByOrderId,
  loadingOrderId,
  onNext,
  onPrev,
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
          <p>Parent orders generated from Upstox fills.</p>
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
                          onClick={() => onToggleSubscribers(row)}
                          aria-label={
                            expandedOrderId === row.id
                              ? "Hide subscriber orders"
                              : "Show subscriber orders"
                          }
                        >
                          {expandedOrderId === row.id ? (
                            <span className="icon-minus" aria-hidden="true"></span>
                          ) : (
                            <span className="icon-chevron" aria-hidden="true"></span>
                          )}
                        </button>
                      </div>
                    </td>
                  </tr>
                    {expandedOrderId === row.id ? (
                      <tr className="subrow">
                        <td colSpan={columns.length + 1}>
                          {loadingOrderId === row.id ? (
                            <div className="empty-state">
                              Loading subscriber orders...
                            </div>
                          ) : subscriberOrdersByOrderId[row.id]?.length ? (
                            <div className="table-wrapper">
                              <table>
                                <thead>
                                  <tr>
                                    {Object.keys(
                                      subscriberOrdersByOrderId[row.id][0] || {}
                                    ).map((key) => (
                                      <th key={key}>{key}</th>
                                    ))}
                                  </tr>
                                </thead>
                                <tbody>
                                  {subscriberOrdersByOrderId[row.id].map(
                                    (sub, index) => (
                                      <tr key={sub.id || index}>
                                        {Object.keys(
                                          subscriberOrdersByOrderId[row.id][0] || {}
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
                              No subscriber orders found.
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
