import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  AlertTriangle,
  Check,
  ChevronDown,
  Database,
  FileJson,
  Filter,
  Lock,
  RefreshCcw,
  Upload,
  X
} from "lucide-react";
import "./styles.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "";
const TENANT = "acme-industrials";
const analystHeaders = { "X-Analyst-Email": "analyst@breatheesg.com" };

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...analystHeaders,
      ...(options.headers || {})
    }
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${response.status}`);
  }
  return response.json();
}

function fmtKg(value) {
  const n = Number(value || 0);
  if (n >= 1000) return `${(n / 1000).toFixed(2)} t`;
  return `${n.toFixed(1)} kg`;
}

function flagTone(flags) {
  if (!flags?.length) return "clean";
  if (flags.some((flag) => flag.severity === "error")) return "error";
  return "warning";
}

function App() {
  const [dashboard, setDashboard] = useState(null);
  const [records, setRecords] = useState([]);
  const [batches, setBatches] = useState([]);
  const [filters, setFilters] = useState({ status: "", source_type: "", scope: "", flagged: "" });
  const [selected, setSelected] = useState(null);
  const [sourceType, setSourceType] = useState("sap");
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");

  const query = useMemo(() => {
    const params = new URLSearchParams({ tenant: TENANT });
    Object.entries(filters).forEach(([key, value]) => value && params.set(key, value));
    return params.toString();
  }, [filters]);

  async function load() {
    const [dash, rows, batchRows] = await Promise.all([
      api(`/api/dashboard/?tenant=${TENANT}`),
      api(`/api/activity-records/?${query}`),
      api(`/api/batches/?tenant=${TENANT}`)
    ]);
    setDashboard(dash);
    setRecords(rows.results || rows);
    setBatches(batchRows.results || batchRows);
  }

  useEffect(() => {
    load().catch((error) => setNotice(error.message));
  }, [query]);

  async function seedDemo() {
    setBusy(true);
    try {
      await api("/api/ingestions/seed-demo/", { method: "POST", body: new FormData() });
      setNotice("Demo data reloaded");
      await load();
      setSelected(null);
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function uploadFile(event) {
    event.preventDefault();
    if (!file) return;
    const allowedExtensions = { sap: [".csv"], utility: [".csv"], travel: [".json"] };
    const lowerName = file.name.toLowerCase();
    const allowed = allowedExtensions[sourceType];
    if (!allowed.some((extension) => lowerName.endsWith(extension))) {
      setNotice(`${sourceType} upload expects ${allowed.join(" or ")} files. Screenshots/images are not supported.`);
      return;
    }
    const form = new FormData();
    form.append("tenant", TENANT);
    form.append("source_type", sourceType);
    form.append("file", file);
    setBusy(true);
    try {
      await api("/api/ingestions/upload/", { method: "POST", body: form });
      setNotice(`${file.name} ingested`);
      setFile(null);
      await load();
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function act(record, action) {
    setBusy(true);
    try {
      const updated = await api(`/api/activity-records/${record.id}/${action}/?tenant=${TENANT}`, { method: "POST", body: new FormData() });
      setRecords((items) => items.map((item) => (item.id === updated.id ? updated : item)));
      setSelected(updated);
      setNotice(action === "approve" ? "Record locked for audit" : "Record rejected");
      await load();
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <header className="topbar">
        <div>
          <p className="eyebrow">ACME INDUSTRIALS</p>
          <h1>ESG ingestion review</h1>
        </div>
        <button className="iconButton" onClick={seedDemo} disabled={busy} title="Reload sample data">
          <RefreshCcw size={18} />
          Seed demo
        </button>
      </header>

      {notice && (
        <div className="notice">
          <span>{notice}</span>
          <button onClick={() => setNotice("")} title="Dismiss">
            <X size={16} />
          </button>
        </div>
      )}

      <section className="metrics">
        <Metric label="Total emissions" value={fmtKg(dashboard?.total_kg_co2e)} />
        <Metric label="Rows received" value={dashboard?.rows || 0} />
        <Metric label="Flagged rows" value={dashboard?.flagged_rows || 0} />
        <Metric label="Approved" value={dashboard?.by_status?.approved || 0} />
      </section>

      <section className="workbench">
        <aside className="panel">
          <h2><Upload size={18} /> Ingestion</h2>
          <form onSubmit={uploadFile} className="uploadForm">
            <label>
              Source
              <select value={sourceType} onChange={(event) => setSourceType(event.target.value)}>
                <option value="sap">SAP fuel/procurement CSV</option>
                <option value="utility">Utility electricity CSV</option>
                <option value="travel">Travel JSON</option>
              </select>
            </label>
            <label>
              File
              <input type="file" onChange={(event) => setFile(event.target.files?.[0] || null)} />
            </label>
            <button className="primary" disabled={busy || !file}>
              <Upload size={16} />
              Upload
            </button>
          </form>

          <h2><Database size={18} /> Latest batches</h2>
          <div className="batchList">
            {batches.map((batch) => (
              <div className="batch" key={batch.id}>
                <div>
                  <strong>{batch.filename}</strong>
                  <span>{batch.connector.source_type} · {batch.row_count} rows</span>
                </div>
                <em>{batch.failed_count} failed</em>
              </div>
            ))}
          </div>
        </aside>

        <section className="records">
          <div className="filters">
            <Filter size={18} />
            <select value={filters.status} onChange={(event) => setFilters({ ...filters, status: event.target.value })}>
              <option value="">All statuses</option>
              <option value="needs_review">Needs review</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
            </select>
            <select value={filters.source_type} onChange={(event) => setFilters({ ...filters, source_type: event.target.value })}>
              <option value="">All sources</option>
              <option value="sap">SAP</option>
              <option value="utility">Utility</option>
              <option value="travel">Travel</option>
            </select>
            <select value={filters.scope} onChange={(event) => setFilters({ ...filters, scope: event.target.value })}>
              <option value="">All scopes</option>
              <option value="scope1">Scope 1</option>
              <option value="scope2">Scope 2</option>
              <option value="scope3">Scope 3</option>
            </select>
            <label className="check">
              <input
                type="checkbox"
                checked={filters.flagged === "1"}
                onChange={(event) => setFilters({ ...filters, flagged: event.target.checked ? "1" : "" })}
              />
              Flagged
            </label>
          </div>

          <div className="tableWrap">
            <table>
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Reference</th>
                  <th>Activity</th>
                  <th>Period</th>
                  <th>Quantity</th>
                  <th>Emissions</th>
                  <th>Quality</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {records.map((record) => (
                  <tr key={record.id} onClick={() => setSelected(record)} className={selected?.id === record.id ? "selected" : ""}>
                    <td><span className={`source ${record.source_type}`}>{record.source_type}</span></td>
                    <td>{record.source_reference}</td>
                    <td>{record.activity_type}<small>{record.category}</small></td>
                    <td>{record.activity_start}<small>{record.activity_end}</small></td>
                    <td>{Number(record.normalized_quantity).toLocaleString()}<small>{record.normalized_unit}</small></td>
                    <td>{fmtKg(record.kg_co2e)}</td>
                    <td><Quality flags={record.flags} score={record.data_quality_score} /></td>
                    <td><Status record={record} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <aside className="detail">
          {selected ? (
            <>
              <div className="detailHead">
                <div>
                  <p className="eyebrow">{selected.source_type} · {selected.scope}</p>
                  <h2>{selected.source_reference}</h2>
                </div>
                <ChevronDown size={18} />
              </div>
              <dl>
                <div><dt>Activity</dt><dd>{selected.activity_type}</dd></div>
                <div><dt>Facility</dt><dd>{selected.facility?.name || "Unmapped"}</dd></div>
                <div><dt>Factor</dt><dd>{selected.emission_factor?.key}</dd></div>
                <div><dt>CO2e</dt><dd>{fmtKg(selected.kg_co2e)}</dd></div>
              </dl>
              <div className={`flagBox ${flagTone(selected.flags)}`}>
                {selected.flags.length ? selected.flags.map((flag, index) => (
                  <p key={`${flag.code}-${index}`}>
                    <AlertTriangle size={15} />
                    <span>{flag.code}: {flag.message}</span>
                  </p>
                )) : <p><Check size={15} /> No flags</p>}
              </div>
              <div className="actions">
                <button className="primary" onClick={() => act(selected, "approve")} disabled={busy || selected.locked_for_audit}>
                  <Lock size={16} />
                  Approve
                </button>
                <button onClick={() => act(selected, "reject")} disabled={busy || selected.locked_for_audit}>
                  <X size={16} />
                  Reject
                </button>
              </div>
              <details open>
                <summary><FileJson size={16} /> Raw payload</summary>
                <pre>{JSON.stringify(selected.raw_record.payload, null, 2)}</pre>
              </details>
            </>
          ) : (
            <div className="emptyState">Select a row to inspect source data, flags, and audit status.</div>
          )}
        </aside>
      </section>
    </main>
  );
}

function Metric({ label, value }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Quality({ flags, score }) {
  return (
    <span className={`quality ${flagTone(flags)}`}>
      {flags?.length ? <AlertTriangle size={14} /> : <Check size={14} />}
      {score}
    </span>
  );
}

function Status({ record }) {
  return (
    <span className={`status ${record.status}`}>
      {record.locked_for_audit && <Lock size={13} />}
      {record.status.replace("_", " ")}
    </span>
  );
}

createRoot(document.getElementById("root")).render(<App />);
