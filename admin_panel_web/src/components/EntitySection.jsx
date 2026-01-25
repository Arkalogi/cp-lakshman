import React, { useMemo, useState } from "react";

const EMPTY = "";

function buildInitialForm(fields) {
  return fields.reduce((acc, field) => {
    acc[field.name] = field.type === "boolean" ? EMPTY : "";
    return acc;
  }, {});
}

function toPayload(fields, form) {
  const payload = {};
  for (const field of fields) {
    const raw = form[field.name];
    if (raw === "" || raw === EMPTY || raw === undefined || raw === null) {
      continue;
    }
    if (field.type === "number") {
      payload[field.name] = Number(raw);
    } else if (field.type === "boolean") {
      payload[field.name] = raw === "true";
    } else if (field.type === "json_object") {
      payload[field.name] = JSON.parse(raw);
    } else if (field.type === "json_string") {
      payload[field.name] = raw;
    } else {
      payload[field.name] = raw;
    }
  }
  return payload;
}

function InputField({ field, value, onChange }) {
  const id = `field-${field.name}`;
  if (field.type === "textarea" || field.type === "json_object" || field.type === "json_string") {
    return (
      <div className="field">
        <label htmlFor={id}>{field.label}</label>
        <textarea
          id={id}
          value={value}
          placeholder={field.placeholder || ""}
          rows={field.rows || 4}
          onChange={(event) => onChange(field.name, event.target.value)}
        />
      </div>
    );
  }
  if (field.type === "boolean") {
    return (
      <div className="field">
        <label htmlFor={id}>{field.label}</label>
        <select
          id={id}
          value={value}
          onChange={(event) => onChange(field.name, event.target.value)}
        >
          <option value="">Select</option>
          <option value="true">true</option>
          <option value="false">false</option>
        </select>
      </div>
    );
  }
  return (
    <div className="field">
      <label htmlFor={id}>{field.label}</label>
      <input
        id={id}
        type={field.type === "number" ? "number" : "text"}
        value={value}
        placeholder={field.placeholder || ""}
        onChange={(event) => onChange(field.name, event.target.value)}
      />
    </div>
  );
}

function DataTable({ columns, rows }) {
  const visibleColumns = useMemo(() => {
    if (columns?.length) {
      return columns;
    }
    const keys = new Set();
    rows.forEach((row) => Object.keys(row || {}).forEach((key) => keys.add(key)));
    return Array.from(keys);
  }, [columns, rows]);

  if (!rows?.length) {
    return <div className="empty-state">No data yet.</div>;
  }

  return (
    <div className="table-wrapper">
      <table>
        <thead>
          <tr>
            {visibleColumns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={`${rowIndex}-${row?.id ?? "row"}`}>
              {visibleColumns.map((column) => (
                <td key={column}>{formatCell(row?.[column])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatCell(value) {
  if (value === null || value === undefined) {
    return "";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

export default function EntitySection({
  title,
  description,
  data,
  columns,
  createFields,
  updateFields,
  onCreate,
  onUpdate,
  onDelete,
}) {
  const [createForm, setCreateForm] = useState(buildInitialForm(createFields));
  const [updateForm, setUpdateForm] = useState(buildInitialForm(updateFields));
  const [deleteId, setDeleteId] = useState("");

  const handleCreate = async (event) => {
    event.preventDefault();
    try {
      const payload = toPayload(createFields, createForm);
      await onCreate(payload);
      setCreateForm(buildInitialForm(createFields));
    } catch (error) {
      onCreate(null, error);
    }
  };

  const handleUpdate = async (event) => {
    event.preventDefault();
    try {
      const payload = toPayload(updateFields, updateForm);
      if (!payload.id) {
        throw new Error("ID is required for updates.");
      }
      const { id, ...rest } = payload;
      await onUpdate(id, rest);
      setUpdateForm(buildInitialForm(updateFields));
    } catch (error) {
      onUpdate(null, null, error);
    }
  };

  const handleDelete = async (event) => {
    event.preventDefault();
    if (!deleteId) {
      onDelete(null, new Error("ID is required for delete."));
      return;
    }
    await onDelete(deleteId);
    setDeleteId("");
  };

  return (
    <section className="panel">
      <header className="panel-header">
        <div>
          <h2>{title}</h2>
          {description ? <p>{description}</p> : null}
        </div>
        <span className="pill">{data?.length ?? 0} items</span>
      </header>

      <div className="panel-content">
        <div className="panel-forms">
          <form onSubmit={handleCreate} className="form-card">
            <h3>Create</h3>
            <div className="form-grid">
              {createFields.map((field) => (
                <InputField
                  key={`create-${field.name}`}
                  field={field}
                  value={createForm[field.name]}
                  onChange={(name, value) =>
                    setCreateForm((prev) => ({ ...prev, [name]: value }))
                  }
                />
              ))}
            </div>
            <button type="submit">Create</button>
          </form>

          <form onSubmit={handleUpdate} className="form-card">
            <h3>Modify</h3>
            <div className="form-grid">
              {updateFields.map((field) => (
                <InputField
                  key={`update-${field.name}`}
                  field={field}
                  value={updateForm[field.name]}
                  onChange={(name, value) =>
                    setUpdateForm((prev) => ({ ...prev, [name]: value }))
                  }
                />
              ))}
            </div>
            <button type="submit">Update</button>
          </form>

          <form onSubmit={handleDelete} className="form-card">
            <h3>Cancel / Delete</h3>
            <div className="form-grid">
              <div className="field">
                <label htmlFor={`${title}-delete-id`}>ID</label>
                <input
                  id={`${title}-delete-id`}
                  type="number"
                  value={deleteId}
                  onChange={(event) => setDeleteId(event.target.value)}
                />
              </div>
            </div>
            <button type="submit" className="ghost">
              Delete
            </button>
          </form>
        </div>

        <div className="panel-table">
          <DataTable columns={columns} rows={data} />
        </div>
      </div>
    </section>
  );
}
