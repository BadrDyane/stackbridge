import { useEffect, useState } from "react";
import { getRuns } from "../api/runs";
import { getWorkflows } from "../api/workflows";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import LoadingSpinner from "../components/LoadingSpinner";

function aggregateByDate(runs) {
  const map = {};
  for (const run of runs) {
    const date = new Date(run.created_at).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    });
    map[date] = (map[date] || 0) + Number(run.total_cost_usd || 0);
  }
  return Object.entries(map)
    .map(([date, cost]) => ({ date, cost: parseFloat(cost.toFixed(6)) }))
    .slice(-14);
}

export default function CostDashboardPage() {
  const [runs, setRuns] = useState([]);
  const [workflows, setWorkflows] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getRuns(), getWorkflows()])
      .then(([r, wf]) => {
        setRuns(r);
        setWorkflows(wf);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading)
    return (
      <div className="page" style={{ textAlign: "center", paddingTop: 80 }}>
        <LoadingSpinner size={32} />
      </div>
    );

  const chartData = aggregateByDate(runs);
  const totalCost = runs.reduce((s, r) => s + Number(r.total_cost_usd || 0), 0);
  const totalTokens = runs.reduce((s, r) => s + (r.total_tokens || 0), 0);
  const avgCost = runs.length ? totalCost / runs.length : 0;

  // Cost per workflow
  const costByWorkflow = {};
  for (const run of runs) {
    const wf = workflows.find((w) => w.id === run.workflow_id);
    const name = wf?.name || run.workflow_id.slice(0, 8);
    costByWorkflow[name] = (costByWorkflow[name] || 0) + Number(run.total_cost_usd || 0);
  }

  return (
    <div className="page">
      <h1 className="page-title">Cost Dashboard</h1>

      <div
        className="grid-2"
        style={{ gridTemplateColumns: "1fr 1fr 1fr", marginBottom: 32 }}
      >
        <div className="card" style={{ textAlign: "center" }}>
          <div
            style={{
              fontSize: 28,
              fontWeight: 700,
              fontFamily: "var(--font-display)",
              color: "var(--color-warning)",
            }}
          >
            ${totalCost.toFixed(4)}
          </div>
          <div style={{ color: "var(--color-text-muted)", fontSize: 13, marginTop: 4 }}>
            Total Spend
          </div>
        </div>
        <div className="card" style={{ textAlign: "center" }}>
          <div
            style={{
              fontSize: 28,
              fontWeight: 700,
              fontFamily: "var(--font-display)",
              color: "var(--color-accent)",
            }}
          >
            {totalTokens.toLocaleString()}
          </div>
          <div style={{ color: "var(--color-text-muted)", fontSize: 13, marginTop: 4 }}>
            Total Tokens
          </div>
        </div>
        <div className="card" style={{ textAlign: "center" }}>
          <div
            style={{
              fontSize: 28,
              fontWeight: 700,
              fontFamily: "var(--font-display)",
              color: "var(--color-success)",
            }}
          >
            ${avgCost.toFixed(5)}
          </div>
          <div style={{ color: "var(--color-text-muted)", fontSize: 13, marginTop: 4 }}>
            Avg Cost / Run
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="card" style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 20 }}>
          Cost by Day
        </h2>
        {chartData.length === 0 ? (
          <div className="empty-state">
            <p>No data yet. Trigger some runs first.</p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={chartData} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2d3149" />
              <XAxis
                dataKey="date"
                tick={{ fill: "#94a3b8", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: "#94a3b8", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => `$${v.toFixed(4)}`}
              />
              <Tooltip
                contentStyle={{
                  background: "#1a1d27",
                  border: "1px solid #2d3149",
                  borderRadius: 6,
                  color: "#e2e8f0",
                  fontSize: 12,
                }}
                formatter={(v) => [`$${v.toFixed(6)}`, "Cost"]}
              />
              <Bar dataKey="cost" fill="#6366f1" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Cost by workflow */}
      <div className="card">
        <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16 }}>
          Cost by Workflow
        </h2>
        {Object.keys(costByWorkflow).length === 0 ? (
          <p style={{ color: "var(--color-text-muted)", fontSize: 13 }}>No data.</p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {Object.entries(costByWorkflow)
              .sort((a, b) => b[1] - a[1])
              .map(([name, cost]) => (
                <div
                  key={name}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "8px 12px",
                    background: "var(--color-surface-2)",
                    borderRadius: "var(--radius-sm)",
                  }}
                >
                  <span style={{ fontSize: 13, fontWeight: 500 }}>{name}</span>
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: 13,
                      color: "var(--color-warning)",
                    }}
                  >
                    ${cost.toFixed(6)}
                  </span>
                </div>
              ))}
          </div>
        )}
      </div>
    </div>
  );
}