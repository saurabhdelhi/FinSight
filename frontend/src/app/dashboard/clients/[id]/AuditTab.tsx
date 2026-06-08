'use client';

import { useState, useEffect } from 'react';
import api, { AuditRun, AuditFinding } from '@/lib/api';
import { Activity, Play, AlertTriangle, ShieldCheck, Filter, ArrowRight } from 'lucide-react';
import { cn, formatINR, severityColor, riskScoreColor, formatDateTime } from '@/lib/utils';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip } from 'recharts';

export function AuditTab({ clientId }: { clientId: string }) {
  const [auditRun, setAuditRun] = useState<AuditRun | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [loading, setLoading] = useState(true);
  const [filterSeverity, setFilterSeverity] = useState<string>('all');

  const loadAudit = async () => {
    try {
      const res = await api.getLatestAudit(clientId);
      setAuditRun(res);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAudit();
  }, [clientId]);

  const handleRunAudit = async () => {
    setIsRunning(true);
    try {
      const res = await api.runAudit(clientId);
      setAuditRun(res);
    } catch (err: any) {
      alert(err.message || 'Audit execution failed');
    } finally {
      setIsRunning(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-center text-gray-500 animate-pulse">Loading audit data...</div>;
  }

  if (!auditRun) {
    return (
      <div className="glass-card p-12 text-center animate-fade-in">
        <ShieldCheck className="w-16 h-16 text-indigo-500/50 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-white mb-2">Run Initial Audit</h2>
        <p className="text-gray-400 mb-6 max-w-lg mx-auto">
          Execute 200+ intelligent audit rules against the synced Tally data to identify anomalies, non-compliance, and errors.
        </p>
        <button onClick={handleRunAudit} disabled={isRunning} className="btn-primary text-lg px-8 flex items-center gap-2 mx-auto">
          {isRunning ? <Activity className="w-5 h-5 animate-spin" /> : <Play className="w-5 h-5" />}
          {isRunning ? 'Analyzing data...' : 'Run Audit Engine'}
        </button>
      </div>
    );
  }

  // Prepare chart data
  const chartData = [
    { name: 'Critical', value: auditRun.critical_count, color: '#ef4444' },
    { name: 'High', value: auditRun.high_count, color: '#f97316' },
    { name: 'Medium', value: auditRun.medium_count, color: '#eab308' },
    { name: 'Low', value: auditRun.low_count, color: '#10b981' },
  ].filter(d => d.value > 0);

  // Filter findings
  const filteredFindings = auditRun.findings.filter(
    f => filterSeverity === 'all' || f.severity === filterSeverity
  );

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="glass-card p-6 md:col-span-2">
          <div className="flex justify-between items-start mb-6">
            <div>
              <h2 className="text-xl font-bold text-white mb-1">Audit Summary</h2>
              <p className="text-xs text-gray-500">Last run: {formatDateTime(auditRun.run_at)}</p>
            </div>
            <button onClick={handleRunAudit} disabled={isRunning} className="btn-secondary text-sm flex items-center gap-2">
              <RefreshIcon isRunning={isRunning} />
              Re-run Audit
            </button>
          </div>

          <div className="flex items-center gap-8">
            {/* Risk Gauge */}
            <div className="flex-shrink-0">
              <div 
                className="risk-gauge shadow-lg shadow-indigo-500/10" 
                style={{ 
                  '--gauge-pct': `${auditRun.risk_score}%`, 
                  '--gauge-color': auditRun.risk_score > 70 ? '#ef4444' : auditRun.risk_score > 40 ? '#f97316' : '#10b981' 
                } as any}
              >
                <div className="risk-gauge-inner">
                  <span className={cn("text-3xl font-bold", riskScoreColor(auditRun.risk_score))}>
                    {auditRun.risk_score.toFixed(0)}
                  </span>
                  <span className="text-[10px] text-gray-400 uppercase tracking-wider">Risk Score</span>
                </div>
              </div>
            </div>

            <div className="flex-1 grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatBox label="Rules Run" value={auditRun.rules_executed} />
              <StatBox label="Total Findings" value={auditRun.total_findings} />
              <StatBox label="Critical" value={auditRun.critical_count} color="text-red-400" />
              <StatBox label="High" value={auditRun.high_count} color="text-orange-400" />
            </div>
          </div>
        </div>

        {/* Chart */}
        <div className="glass-card p-6 flex flex-col items-center justify-center">
          <h3 className="text-sm font-semibold text-gray-300 w-full mb-2">Severity Breakdown</h3>
          <div className="w-full h-[140px]">
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={chartData} innerRadius={40} outerRadius={60} paddingAngle={2} dataKey="value">
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <RechartsTooltip 
                    contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.9)', borderColor: 'rgba(99, 102, 241, 0.2)', borderRadius: '8px' }}
                    itemStyle={{ color: '#fff' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-green-500/50">
                <ShieldCheck className="w-12 h-12" />
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Findings List */}
      <div className="glass-card overflow-hidden">
        <div className="p-4 border-b border-indigo-500/10 flex justify-between items-center bg-indigo-500/5">
          <h3 className="font-bold text-white flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-indigo-400" />
            Detailed Findings ({filteredFindings.length})
          </h3>
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-500" />
            <select 
              className="bg-gray-900 border border-gray-700 text-sm rounded-lg px-2 py-1 text-gray-300 focus:outline-none focus:border-indigo-500"
              value={filterSeverity}
              onChange={e => setFilterSeverity(e.target.value)}
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>
        </div>

        {filteredFindings.length === 0 ? (
          <div className="p-8 text-center text-gray-500">No findings match the selected filter.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Rule ID</th>
                  <th>Severity</th>
                  <th>Title / Category</th>
                  <th>Ledger / Party</th>
                  <th className="text-right">Amount (₹)</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {filteredFindings.map((f, i) => {
                  const colors = severityColor(f.severity);
                  return (
                    <tr key={i} className="group">
                      <td className="text-gray-400 font-mono text-xs">{f.rule_id}</td>
                      <td>
                        <span className={cn("badge", colors.bg, colors.text, "border", colors.border)}>
                          <span className={cn("w-1.5 h-1.5 rounded-full mr-1", colors.dot)} />
                          {f.severity}
                        </span>
                      </td>
                      <td>
                        <div className="font-medium text-gray-200">{f.title}</div>
                        <div className="text-xs text-gray-500">{f.category}</div>
                      </td>
                      <td className="text-gray-300">{f.ledger_name || '-'}</td>
                      <td className="text-right font-mono text-gray-300">
                        {f.amount ? formatINR(f.amount) : '-'}
                      </td>
                      <td className="text-center">
                        <button className="p-1 rounded bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 opacity-0 group-hover:opacity-100 transition-opacity">
                          <ArrowRight className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function StatBox({ label, value, color = "text-white" }: { label: string, value: number, color?: string }) {
  return (
    <div className="bg-indigo-500/5 rounded-xl p-4 border border-indigo-500/10 text-center">
      <div className={cn("text-2xl font-bold mb-1", color)}>{value}</div>
      <div className="text-xs text-gray-500 font-medium uppercase tracking-wider">{label}</div>
    </div>
  );
}

function RefreshIcon({ isRunning }: { isRunning: boolean }) {
  if (isRunning) return <Activity className="w-4 h-4 animate-spin" />;
  return <Play className="w-4 h-4" />;
}
