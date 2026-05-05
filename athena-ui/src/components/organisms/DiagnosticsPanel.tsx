export function DiagnosticsPanel() {
  return (
    <aside className="fixed right-0 top-0 h-full flex flex-col p-6 overflow-y-auto w-72 border-l border-border-100 bg-surface-100/50 z-50">
      <div className="mb-8 flex flex-col gap-1">
        <h2 className="text-base font-semibold text-text-000 tracking-tight">System Diagnostics</h2>
        <p className="text-xs text-text-400 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
          Hardware Status: Nominal
        </p>
      </div>

      <div className="flex-1 flex flex-col gap-8">
        {/* Token Latency */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between text-brand-000 font-bold text-[11px] uppercase tracking-widest">
            <div className="flex items-center gap-2">
              <span>⚡</span>
              <span>Token Latency</span>
            </div>
            <span className="text-text-100 font-mono text-xs">24ms</span>
          </div>
          <div className="w-full h-1.5 bg-bg-200 rounded-full overflow-hidden">
            <div className="h-full bg-brand-000 rounded-full w-[15%] transition-all duration-1000" />
          </div>
        </div>

        {/* Context Window */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between text-text-400 font-bold text-[11px] uppercase tracking-widest hover:text-brand-000 transition-colors duration-200">
            <div className="flex items-center gap-2">
              <span>🗄️</span>
              <span>Context Window</span>
            </div>
            <span className="text-text-100 font-mono text-xs">82%</span>
          </div>
          <div className="w-full h-1.5 bg-bg-200 rounded-full overflow-hidden">
            <div className="h-full bg-accent-000 rounded-full w-[82%] transition-all duration-1000" />
          </div>
        </div>

        {/* GPU Clusters */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between text-text-400 font-bold text-[11px] uppercase tracking-widest hover:text-brand-000 transition-colors duration-200">
            <div className="flex items-center gap-2">
              <span>🖥️</span>
              <span>GPU Clusters</span>
            </div>
            <span className="text-text-100 font-mono text-xs">4/8 Active</span>
          </div>
          <div className="w-full h-1.5 bg-bg-200 rounded-full overflow-hidden flex gap-0.5">
            {Array.from({ length: 8 }, (_, i) => (
              <div
                key={i}
                className={`h-full rounded-full flex-1 ${i < 4 ? 'bg-brand-200' : 'bg-bg-300'}`}
              />
            ))}
          </div>
        </div>

        {/* Event Feed */}
        <div className="flex flex-col gap-2 flex-1 min-h-0">
          <div className="flex items-center justify-between text-text-400 font-bold text-[11px] uppercase tracking-widest hover:text-brand-000 transition-colors duration-200">
            <div className="flex items-center gap-2">
              <span>📡</span>
              <span>Event Feed</span>
            </div>
            <span className="w-2 h-2 rounded-full bg-warning-000" />
          </div>
          <div className="bg-surface-000 border border-border-100 rounded p-3 flex-1 min-h-[128px] overflow-y-auto text-[11px] font-mono text-text-400 flex flex-col gap-1.5">
            <div className="border-l-2 border-brand-000 pl-2 text-text-200">
              09:41:02 — MHA calc nominal
            </div>
            <div className="border-l-2 border-border-200 pl-2 opacity-60">
              09:40:15 — Cache hit rate: 94%
            </div>
            <div className="border-l-2 border-warning-000 pl-2 text-warning-000">
              09:39:50 — Minor gc pause detected
            </div>
            <div className="border-l-2 border-border-200 pl-2 opacity-60">
              09:38:11 — Thread 84.A started
            </div>
          </div>
        </div>
      </div>

      <div className="mt-auto pt-6 border-t border-border-100 flex flex-col gap-3">
        <button className="flex items-center gap-2 text-text-400 hover:text-brand-000 text-[11px] uppercase tracking-widest font-semibold transition-colors duration-200">
          <span>📥</span>
          <span>Export Logs</span>
        </button>
        <button className="flex items-center gap-2 text-text-400 hover:text-brand-000 text-[11px] uppercase tracking-widest font-semibold transition-colors duration-200">
          <span>🔗</span>
          <span>Documentation</span>
        </button>
      </div>
    </aside>
  )
}
