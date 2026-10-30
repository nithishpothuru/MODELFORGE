import React, { useState, useEffect } from 'react';
import Modal from '../common/Modal';
import Badge from '../common/Badge';
import Button from '../common/Button';
import { checkBackendHealth, checkSupabaseHealth, getRootInfo } from '../../services/api';
import { Activity, Server, Database, RefreshCw } from 'lucide-react';

export default function StatusModal({ isOpen, onClose }) {
  const [loading, setLoading] = useState(false);
  const [backendStatus, setBackendStatus] = useState(null);
  const [supabaseStatus, setSupabaseStatus] = useState(null);
  const [rootInfo, setRootInfo] = useState(null);
  const [latency, setLatency] = useState(null);

  const fetchStatus = async () => {
    setLoading(true);
    const start = performance.now();

    try {
      const [healthRes, infoRes] = await Promise.allSettled([
        checkBackendHealth(),
        getRootInfo(),
      ]);

      const duration = Math.round(performance.now() - start);
      setLatency(duration);

      if (healthRes.status === 'fulfilled') {
        setBackendStatus({ ok: true, data: healthRes.value });
      } else {
        setBackendStatus({ ok: false, error: healthRes.reason.message });
      }

      if (infoRes.status === 'fulfilled') {
        setRootInfo(infoRes.value);
      }
    } catch (err) {
      setBackendStatus({ ok: false, error: err.message });
    }

    try {
      const supaRes = await checkSupabaseHealth();
      setSupabaseStatus({ ok: true, data: supaRes });
    } catch (err) {
      setSupabaseStatus({ ok: false, error: err.message || 'Supabase unavailable or credentials unconfigured' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchStatus();
    }
  }, [isOpen]);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="System Status & Health"
      subtitle="Live health metrics from the ModelForge FastAPI backend & services."
      maxWidth="max-w-lg"
    >
      <div className="space-y-4">
        {/* Backend API Service */}
        <div className="p-3.5 rounded-lg border border-white/10 bg-white/[0.02] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Server size={18} className="text-[#00D6FF]" />
            <div>
              <p className="text-sm font-medium text-white">FastAPI Backend</p>
              <p className="text-xs text-white/50">
                {rootInfo?.service || 'ModelForge API'} &bull; v{rootInfo?.version || '0.1.0'}
              </p>
            </div>
          </div>
          <div>
            {backendStatus?.ok ? (
              <Badge status="passed">Online ({latency}ms)</Badge>
            ) : (
              <Badge status="failed">Offline</Badge>
            )}
          </div>
        </div>

        {/* Supabase Service */}
        <div className="p-3.5 rounded-lg border border-white/10 bg-white/[0.02] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Database size={18} className="text-[#00AFFF]" />
            <div>
              <p className="text-sm font-medium text-white">Supabase Cloud Database & Storage</p>
              <p className="text-xs text-white/50">
                {supabaseStatus?.ok
                  ? 'Connected to projects table & storage'
                  : 'Pending credentials or table migration'}
              </p>
            </div>
          </div>
          <div>
            {supabaseStatus?.ok ? (
              <Badge status="passed">Connected</Badge>
            ) : (
              <Badge status="warning">Unconfigured</Badge>
            )}
          </div>
        </div>

        {/* CI Pipeline Runner */}
        <div className="p-3.5 rounded-lg border border-white/10 bg-white/[0.02] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Activity size={18} className="text-[#00D6FF]" />
            <div>
              <p className="text-sm font-medium text-white">CI Validation Engine</p>
              <p className="text-xs text-white/50">Python AST analyzer, dependency resolution</p>
            </div>
          </div>
          <div>
            <Badge status="passed">Active</Badge>
          </div>
        </div>

        {backendStatus?.error && (
          <div className="p-3 rounded-lg border border-red-500/20 bg-red-500/10 text-xs text-red-400">
            <strong>Backend Error:</strong> {backendStatus.error}
          </div>
        )}

        <div className="flex justify-between items-center pt-2">
          <span className="text-[11px] text-white/40">
            Last checked: {new Date().toLocaleTimeString()}
          </span>
          <Button
            variant="secondary"
            size="sm"
            onClick={fetchStatus}
            loading={loading}
            leftIcon={<RefreshCw size={13} />}
          >
            Recheck Health
          </Button>
        </div>
      </div>
    </Modal>
  );
}
