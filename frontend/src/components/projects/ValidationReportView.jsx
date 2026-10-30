import React from 'react';
import Badge from '../common/Badge';
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  FileCode,
  Package,
  Cpu,
  Clock,
  Terminal,
  ShieldCheck,
  AlertCircle,
} from 'lucide-react';

export default function ValidationReportView({ report }) {
  if (!report) return null;

  const isPassed = report.status === 'passed';
  const isWarning = report.status === 'warning';
  const isFailed = report.status === 'failed';

  const statusColor = isPassed
    ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10'
    : isWarning
    ? 'text-amber-400 border-amber-500/30 bg-amber-500/10'
    : 'text-red-400 border-red-500/30 bg-red-500/10';

  const durationStr = report.duration_seconds
    ? `${report.duration_seconds.toFixed(2)}s`
    : '0.0s';

  return (
    <div className="space-y-6">
      {/* Overview Banner */}
      <div className={`p-4 rounded-xl border flex items-start justify-between gap-4 ${statusColor}`}>
        <div className="flex items-start gap-3">
          {isPassed && <CheckCircle2 size={24} className="shrink-0 mt-0.5 text-emerald-400" />}
          {isWarning && <AlertTriangle size={24} className="shrink-0 mt-0.5 text-amber-400" />}
          {isFailed && <XCircle size={24} className="shrink-0 mt-0.5 text-red-400" />}
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-base capitalize text-white">
                CI Pipeline {report.status}
              </h3>
              <Badge status={report.status} size="xs" />
            </div>
            <p className="text-xs text-white/80 mt-1">
              {report.summary || 'Validation completed across structure, syntax, and dependency resolution.'}
            </p>
          </div>
        </div>

        <div className="text-right text-xs shrink-0 font-mono text-white/60">
          <div className="flex items-center justify-end gap-1">
            <Clock size={12} />
            <span>{durationStr}</span>
          </div>
        </div>
      </div>

      {/* Errors and Warnings List if any */}
      {report.errors && report.errors.length > 0 && (
        <div className="p-4 rounded-xl border border-red-500/30 bg-red-500/5 space-y-2">
          <h4 className="text-xs font-semibold text-red-400 uppercase tracking-wider flex items-center gap-1.5">
            <XCircle size={14} />
            <span>Critical Validation Errors ({report.errors.length})</span>
          </h4>
          <ul className="space-y-1 text-xs text-red-300">
            {report.errors.map((err, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-red-400 font-mono">•</span>
                <span>{err}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {report.warnings && report.warnings.length > 0 && (
        <div className="p-4 rounded-xl border border-amber-500/30 bg-amber-500/5 space-y-2">
          <h4 className="text-xs font-semibold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
            <AlertCircle size={14} />
            <span>Non-Fatal Warnings & Advice ({report.warnings.length})</span>
          </h4>
          <ul className="space-y-1 text-xs text-amber-300">
            {report.warnings.map((warn, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-amber-400 font-mono">•</span>
                <span>{warn}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Grid of Key Pipeline Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Python Runtime Stage */}
        <div className="p-4 rounded-xl border border-white/10 bg-white/[0.02]">
          <div className="flex items-center gap-2 text-white/50 text-xs font-medium uppercase tracking-wider mb-2">
            <Cpu size={14} className="text-[#00D6FF]" />
            <span>Python Runtime</span>
          </div>
          <p className="text-lg font-mono font-semibold text-white">
            Python {report.python_version?.version || '3.11'}
          </p>
          <p className="text-xs text-white/50 mt-1">
            Source: <span className="text-white/80 font-mono">{report.python_version?.source || 'auto-detected'}</span>
            {report.python_version?.is_inferred && ' (Inferred)'}
          </p>
        </div>

        {/* Entry Point Stage */}
        <div className="p-4 rounded-xl border border-white/10 bg-white/[0.02]">
          <div className="flex items-center gap-2 text-white/50 text-xs font-medium uppercase tracking-wider mb-2">
            <FileCode size={14} className="text-[#00D6FF]" />
            <span>Entry Point</span>
          </div>
          <p className="text-lg font-mono font-semibold text-white truncate" title={report.entry_point_validation?.detected_entry_point}>
            {report.entry_point_validation?.detected_entry_point || 'None detected'}
          </p>
          <p className="text-xs text-white/50 mt-1">
            Framework: <span className="text-[#00D6FF] capitalize">{report.entry_point_validation?.entry_point_type || 'Custom script'}</span>
          </p>
        </div>

        {/* Code Syntax Stage */}
        <div className="p-4 rounded-xl border border-white/10 bg-white/[0.02]">
          <div className="flex items-center gap-2 text-white/50 text-xs font-medium uppercase tracking-wider mb-2">
            <ShieldCheck size={14} className="text-[#00D6FF]" />
            <span>Syntax Integrity</span>
          </div>
          <p className="text-lg font-semibold text-white">
            {report.syntax_validation?.valid_files || 0} / {report.syntax_validation?.total_files || 0} Files Valid
          </p>
          <p className="text-xs text-white/50 mt-1">
            {report.syntax_validation?.syntax_errors?.length || 0} syntax errors
          </p>
        </div>
      </div>

      {/* Project Structure Breakdown */}
      {report.structure && (
        <div className="p-4 rounded-xl border border-white/10 bg-white/[0.02] space-y-3">
          <h4 className="text-xs font-semibold text-white/80 uppercase tracking-wider flex items-center gap-1.5">
            <FileCode size={14} className="text-[#00D6FF]" />
            <span>Project Structure & Frameworks</span>
          </h4>
          <div className="flex flex-wrap gap-2">
            {report.structure.detected_frameworks?.map((fw, i) => (
              <span key={i} className="px-2.5 py-1 rounded bg-[#00D6FF]/10 text-[#00D6FF] text-xs font-mono border border-[#00D6FF]/20">
                {fw}
              </span>
            ))}
            {report.structure.is_ml_project && (
              <span className="px-2.5 py-1 rounded bg-purple-500/10 text-purple-300 text-xs font-mono border border-purple-500/20">
                Machine Learning Pipeline
              </span>
            )}
            <span className="px-2.5 py-1 rounded bg-white/5 text-white/70 text-xs font-mono border border-white/10">
              {report.structure.total_python_files || 0} Python Source Files
            </span>
          </div>
        </div>
      )}

      {/* Resolved Dependencies Section */}
      <div className="p-4 rounded-xl border border-white/10 bg-white/[0.02] space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-semibold text-white/80 uppercase tracking-wider flex items-center gap-1.5">
            <Package size={14} className="text-[#00D6FF]" />
            <span>
              Resolved Dependencies ({report.dependency_resolution?.resolved_packages?.length || report.dependencies?.length || 0})
            </span>
          </h4>
          {report.dependency_resolution?.lock_file_generated && (
            <span className="text-[11px] font-mono text-[#00D6FF]">
              lockfile: requirements-resolved.txt generated
            </span>
          )}
        </div>

        {report.dependency_resolution?.resolved_packages && report.dependency_resolution.resolved_packages.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 max-h-60 overflow-y-auto pr-1">
            {report.dependency_resolution.resolved_packages.map((pkg, idx) => (
              <div
                key={idx}
                className="p-2 rounded bg-black/40 border border-white/5 flex items-center justify-between text-xs"
              >
                <span className="font-mono text-white/90 truncate">{pkg.name}</span>
                <span className="font-mono text-xs text-[#00D6FF] shrink-0 ml-2">
                  =={pkg.version}
                </span>
              </div>
            ))}
          </div>
        ) : report.dependencies && report.dependencies.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 max-h-60 overflow-y-auto pr-1">
            {report.dependencies.map((dep, idx) => (
              <div
                key={idx}
                className="p-2 rounded bg-black/40 border border-white/5 flex items-center justify-between text-xs"
              >
                <span className="font-mono text-white/90 truncate">{dep.name}</span>
                <span className="font-mono text-xs text-white/50 shrink-0 ml-2">
                  {dep.version_spec || 'latest'}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-white/40 italic">
            No external packages declared or required by AST analysis.
          </p>
        )}
      </div>

      {/* Diagnostic Output Snippet */}
      {report.dependency_validation?.output_snippet && (
        <div className="space-y-1.5">
          <div className="flex items-center gap-1.5 text-xs text-white/50 font-mono">
            <Terminal size={13} />
            <span>Environment Execution Log</span>
          </div>
          <pre className="p-3 bg-black/80 border border-white/10 rounded-lg text-[11px] font-mono text-white/80 overflow-x-auto whitespace-pre-wrap max-h-48">
            {report.dependency_validation.output_snippet}
          </pre>
        </div>
      )}
    </div>
  );
}

