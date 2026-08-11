"use client";

import { useState, useEffect } from "react";

interface Metrics {
  totalRequests: number;
  avgRelevance: number;
  faithfulnessRate: string;
  flaggedCount: number;
}

interface Trace {
  id: string;
  threadId: string;
  userQuery: string;
  llmResponse: string;
  hallucinationScore: number | null;
  relevanceScore: number | null;
  evalReasoning: string | null;
  totalTokens: number | null;
  guardrailFlagged: boolean | null;
  createdAt: string;
}

export default function ObservabilityDashboard() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [traces, setTraces] = useState<Trace[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch both endpoints concurrently
        const [metricsRes, tracesRes] = await Promise.all([
          fetch("http://localhost:8000/api/eval/metrics"),
          fetch("http://localhost:8000/api/eval/traces")
        ]);

        if (!metricsRes.ok || !tracesRes.ok) {
          throw new Error("Failed to fetch telemetry data. Is the backend running?");
        }

        setMetrics(await metricsRes.json());
        setTraces(await tracesRes.json());
        setError("");
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    
    // Auto-refresh the dashboard every 5 seconds
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-[#0b0f17] text-slate-200 p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Header Section */}
        <div className="flex justify-between items-end border-b border-slate-800 pb-4">
          <div>
            <h1 className="text-3xl font-bold text-white">LLM Observability</h1>
            <p className="text-slate-400 mt-1">Real-time pipeline evaluation & telemetry</p>
          </div>
          {loading && <span className="text-sm text-slate-500 animate-pulse">Syncing...</span>}
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/50 text-red-400 p-4 rounded-lg">
            {error}
          </div>
        )}

        {/* Top Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <MetricCard title="Total Queries" value={metrics?.totalRequests} />
          <MetricCard 
            title="Avg Relevance (1-5)" 
            value={metrics?.avgRelevance} 
            color={metrics?.avgRelevance && metrics.avgRelevance >= 4 ? "text-emerald-400" : "text-amber-400"}
          />
          <MetricCard 
            title="Faithfulness Rate" 
            value={metrics?.faithfulnessRate} 
            color="text-blue-400"
          />
          <MetricCard 
            title="Flagged Responses" 
            value={metrics?.flaggedCount} 
            color={metrics?.flaggedCount && metrics.flaggedCount > 0 ? "text-red-400" : "text-emerald-400"}
          />
        </div>

        {/* Traces Data Table */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
          <div className="px-6 py-4 border-b border-slate-800 bg-slate-800/30 flex justify-between items-center">
            <h2 className="text-lg font-semibold text-slate-200">Recent Traces</h2>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
                <thead className="bg-slate-900 text-slate-400 border-b border-slate-800">
                    <tr>
                    <th className="px-6 py-4 font-medium">Timestamp</th>
                    <th className="px-6 py-4 font-medium">Status</th>
                    <th className="px-6 py-4 font-medium">Safety</th>
                    <th className="px-6 py-4 font-medium">Query</th>
                    <th className="px-6 py-4 font-medium">Faithful</th>
                    <th className="px-6 py-4 font-medium">Relevance</th>
                    <th className="px-6 py-4 font-medium">Tokens</th>
                    <th className="px-6 py-4 font-medium">Judge Reasoning</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                    {traces.map((trace) => {
                    // Logic for the composite status
                    const isEvaluating = trace.hallucinationScore === null || trace.relevanceScore === null;
                    const isError = trace.hallucinationScore === 0;
                    const isPerfect = trace.hallucinationScore === 1 && trace?.relevanceScore >= 4;
                    const isWarning = trace.hallucinationScore === 1 && trace?.relevanceScore < 4;

                    return (
                        <tr key={trace.id} className="hover:bg-slate-800/40 transition-colors">
                        
                        {/* 1. Timestamp */}
                        <td className="px-6 py-4 whitespace-nowrap text-slate-500 align-top">
                            {new Date(trace.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                        </td>

                        {/* 2. OVERALL STATUS (The new column) */}
                        <td className="px-6 py-4 align-top">
                            {isEvaluating ? (
                            <span className="text-slate-500 text-xs animate-pulse">Evaluating...</span>
                            ) : isError ? (
                            <span className="px-2.5 py-1 rounded-md bg-red-500/10 text-red-400 border border-red-500/20 text-xs font-medium flex w-fit items-center gap-1.5">
                                <span className="w-1.5 h-1.5 rounded-full bg-red-500"></span> Error
                            </span>
                            ) : isPerfect ? (
                            <span className="px-2.5 py-1 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-medium flex w-fit items-center gap-1.5">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Perfect
                            </span>
                            ) : isWarning ? (
                            <span className="px-2.5 py-1 rounded-md bg-amber-500/10 text-amber-400 border border-amber-500/20 text-xs font-medium flex w-fit items-center gap-1.5">
                                <span className="w-1.5 h-1.5 rounded-full bg-amber-500"></span> Warning
                            </span>
                            ) : null}
                        </td>

                        <td className="px-6 py-4 align-top">
                            {trace.guardrailFlagged ? (
                                <span className="px-2.5 py-1 rounded-md bg-rose-500/10 text-rose-400 border border-rose-500/20 text-xs font-medium flex w-fit items-center gap-1.5">
                                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                </svg>
                                Violation
                                </span>
                            ) : (
                                <span className="px-2.5 py-1 rounded-md bg-slate-800 text-slate-400 border border-slate-700 text-xs font-medium flex w-fit items-center gap-1.5">
                                <svg className="w-3.5 h-3.5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                                </svg>
                                Safe
                                </span>
                            )}
                        </td>
                        
                        {/* 3. Query */}
                        <td className="px-6 py-4 min-w-[250px] max-w-sm whitespace-normal break-words text-slate-300 align-top">
                            {trace.userQuery}
                        </td>
                        
                        {/* 4. Faithful */}
                        <td className="px-6 py-4 align-top">
                            {trace.hallucinationScore === 1 ? (
                            <span className="px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-medium">Pass</span>
                            ) : trace.hallucinationScore === 0 ? (
                            <span className="px-3 py-1 rounded-full bg-red-500/10 text-red-400 border border-red-500/20 text-xs font-medium">Fail</span>
                            ) : (
                            <span className="text-slate-600">--</span>
                            )}
                        </td>
                        
                        {/* 5. Relevance */}
                        <td className="px-6 py-4 align-top">
                            {trace.relevanceScore !== null ? (
                            <span className={`font-medium ${trace.relevanceScore >= 4 ? 'text-emerald-400' : 'text-amber-400'}`}>
                                {trace.relevanceScore} / 5
                            </span>
                            ) : (
                            <span className="text-slate-600">--</span>
                            )}
                        </td>

                        {/* 6. Tokens */}
                        <td className="px-6 py-4 align-top text-slate-300">
                            {trace.totalTokens ? (
                            <span className="bg-slate-800 text-slate-300 px-2.5 py-1 rounded-md text-xs border border-slate-700">
                                {trace.totalTokens}
                            </span>
                            ) : (
                            <span className="text-slate-600">--</span>
                            )}
                        </td>
                        
                        {/* 7. Judge Reasoning */}
                        <td className="px-6 py-4 min-w-[300px] max-w-lg whitespace-normal break-words text-slate-400 align-top">
                            {trace.evalReasoning || "Waiting for judge..."}
                        </td>
                        
                        </tr>
                    );
                    })}
                </tbody>
               </table>
            
            {traces.length === 0 && !loading && (
              <div className="p-12 text-center text-slate-500">
                No traces recorded yet. Go to the chat and ask a question!
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}

// Sub-component for the top metrics
function MetricCard({ title, value, color = "text-white" }: { title: string; value: any; color?: string }) {
  return (
    <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl flex flex-col justify-center shadow-sm">
      <h3 className="text-slate-400 text-sm font-medium mb-2">{title}</h3>
      <p className={`text-4xl font-bold ${color}`}>{value ?? "--"}</p>
    </div>
  );
}