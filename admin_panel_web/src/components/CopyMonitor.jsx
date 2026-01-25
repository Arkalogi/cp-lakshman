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

export default function CopyMonitor({ strategySubs, dematSubs }) {
  const rows = useMemo(() => {
    const strategyRows = (strategySubs || []).map((row) => ({
      type: "strategy",
      ...row,
    }));
    const dematRows = (dematSubs || []).map((row) => ({
      type: "demat_api",
      ...row,
    }));
    return [...strategyRows, ...dematRows];
  }, [strategySubs, dematSubs]);

  const columns = useMemo(() => {
    const keys = new Set(["type"]);
    rows.forEach((row) => Object.keys(row || {}).forEach((key) => keys.add(key)));
    return Array.from(keys);
  }, [rows]);

  return (
    <section className="panel">
      <header className="panel-header">
        <div>
          <h2>Copy Monitor</h2>
          <p>Unified view of active copy relationships and subscriptions.</p>
        </div>
        <span className="pill">{rows.length} rows</span>
      </header>
      <div className="panel-content">
        {rows.length ? (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  {columns.map((column) => (
                    <th key={column}>{column}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row, rowIndex) => (
                  <tr key={`${rowIndex}-${row?.id ?? "row"}`}>
                    {columns.map((column) => (
                      <td key={column}>{formatCell(row?.[column])}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">No copy subscriptions yet.</div>
        )}
      </div>
    </section>
  );
}
