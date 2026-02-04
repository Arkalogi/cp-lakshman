import React, { createContext, useContext, useMemo, useState } from "react";

const NotificationContext = createContext(null);

let nextId = 1;

export function NotificationProvider({ children }) {
  const [items, setItems] = useState([]);

  const push = (type, message, options = {}) => {
    const id = nextId++;
    const ttl = Number(options.ttl ?? 4000);
    setItems((prev) => [...prev, { id, type, message }]);
    if (ttl > 0) {
      window.setTimeout(() => {
        setItems((prev) => prev.filter((item) => item.id !== id));
      }, ttl);
    }
    return id;
  };

  const remove = (id) => {
    setItems((prev) => prev.filter((item) => item.id !== id));
  };

  const api = useMemo(
    () => ({
      success: (message, options) => push("success", message, options),
      error: (message, options) => push("error", message, options),
      info: (message, options) => push("info", message, options),
      remove,
    }),
    []
  );

  return (
    <NotificationContext.Provider value={api}>
      {children}
      <NotificationStack items={items} onDismiss={remove} />
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error("useNotifications must be used within NotificationProvider");
  }
  return context;
}

function NotificationStack({ items, onDismiss }) {
  return (
    <div className="toast-stack" aria-live="polite">
      {items.map((item) => (
        <div key={item.id} className={`toast toast-${item.type}`}>
          <span>{item.message}</span>
          <button
            type="button"
            className="toast-dismiss"
            onClick={() => onDismiss(item.id)}
            aria-label="Dismiss notification"
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
}
