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
  onViewSubscribers,
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
                  <th>actions</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((row) => (
                  <tr key={row.id || row.tag}>
                    {columns.map((column) => (
                      <td key={column}>{formatCell(row?.[column])}</td>
                    ))}
                    <td>
                      <div className="row-actions">
                        <button
                          type="button"
                          className="ghost"
                          onClick={() => onViewSubscribers(row)}
                        >
                          Subscribers
                        </button>
                      </div>
                    </td>
                  </tr>
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
