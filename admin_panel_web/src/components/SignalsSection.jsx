import React, { useState } from "react";

const EMPTY_FORM = {
  strategy_id: "",
  instrument_id: "",
  side: "buy",
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

export default function SignalsSection({ signals, onCreate, onRefresh }) {
  const [form, setForm] = useState(EMPTY_FORM);

  const handleSubmit = async (event) => {
    event.preventDefault();
    const payload = {
      strategy_id: Number(form.strategy_id),
      instrument_id: form.instrument_id,
      side: form.side,
    };
    if (form.meta_data) {
      payload.meta_data = form.meta_data;
    }
    await onCreate(payload);
    setForm(EMPTY_FORM);
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
            />
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
                </tr>
              </thead>
              <tbody>
                {signals.map((signal) => (
                  <tr key={signal.id || signal.strategy_id}>
                    {Object.keys(signals[0] || {}).map((key) => (
                      <td key={key}>{formatCell(signal?.[key])}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">No signals yet.</div>
        )}
      </div>
    </section>
  );
}
