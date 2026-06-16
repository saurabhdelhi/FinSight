'use client';

import { useState, useEffect, useCallback } from 'react';
import api, { SyncJob } from '@/lib/api';
import { RefreshCw, CheckCircle2, XCircle, Clock, Database, Wifi, WifiOff } from 'lucide-react';
import { formatDateTime, timeAgo, cn } from '@/lib/utils';

export function SyncTab({ 
  clientId, 
  lastSyncedAt, 
  onSyncComplete 
}: { 
  clientId: string; 
  lastSyncedAt?: string; 
  onSyncComplete?: () => void; 
}) {
  const [syncHistory, setSyncHistory] = useState<SyncJob[]>([]);
  const [isSyncing, setIsSyncing] = useState(false);
  const [testStatus, setTestStatus] = useState<{success?: boolean, message?: string, testing: boolean}>({ testing: false });
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async (wasPreviouslySyncing?: boolean) => {
    try {
      const history = await api.getSyncHistory(clientId);
      setSyncHistory(history);
      const isCurrentlyRunning = history.length > 0 && history[0].status === 'running';
      setIsSyncing(isCurrentlyRunning);
      
      // If it was syncing in the background, and now it finished, notify parent
      if (wasPreviouslySyncing === true && !isCurrentlyRunning && onSyncComplete) {
        onSyncComplete();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [clientId, onSyncComplete]);

  useEffect(() => {
    loadData();
  }, [clientId]);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isSyncing) {
      interval = setInterval(() => loadData(true), 5000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [loadData, isSyncing]);

  const handleTestConnection = async () => {
    setTestStatus({ testing: true });
    try {
      const res = await api.testConnection(clientId);
      setTestStatus({ success: res.success, message: res.message, testing: false });
    } catch (err: any) {
      setTestStatus({ success: false, message: err.message, testing: false });
    }
  };

  const handleTriggerSync = async () => {
    setIsSyncing(true);
    try {
      await api.triggerSync(clientId);
      await loadData();
      if (onSyncComplete) {
        onSyncComplete();
      }
    } catch (err: any) {
      alert(err.message || 'Sync failed to start');
      setIsSyncing(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-center text-gray-500 animate-pulse">Loading sync status...</div>;
  }

  const latestSync = syncHistory[0];

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Sync Controls */}
        <div className="glass-card p-6">
          <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
            <Database className="w-5 h-5 text-indigo-400" />
            Tally Synchronization
          </h2>
          <p className="text-gray-400 text-sm mb-6">
            Extract ledgers, groups, and vouchers from Tally Prime via the XML HTTP interface.
          </p>

          <div className="flex gap-4 mb-6">
            <button 
              onClick={handleTriggerSync}
              disabled={isSyncing}
              className={cn("btn-primary flex-1 flex items-center justify-center gap-2", isSyncing && "opacity-50 cursor-not-allowed")}
            >
              <RefreshCw className={cn("w-5 h-5", isSyncing && "animate-spin")} />
              {isSyncing ? 'Syncing Now...' : 'Run Full Sync'}
            </button>
            <button 
              onClick={handleTestConnection}
              disabled={testStatus.testing}
              className="btn-secondary flex items-center gap-2"
            >
              {testStatus.testing ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Wifi className="w-4 h-4" />}
              Test Connection
            </button>
          </div>

          {testStatus.message && (
            <div className={cn("p-3 rounded-lg text-sm flex items-start gap-2 mb-4", 
              testStatus.success ? "bg-green-500/10 text-green-400 border border-green-500/20" : "bg-red-500/10 text-red-400 border border-red-500/20"
            )}>
              {testStatus.success ? <CheckCircle2 className="w-5 h-5 shrink-0" /> : <XCircle className="w-5 h-5 shrink-0" />}
              <span>{testStatus.message}</span>
            </div>
          )}

          {latestSync && latestSync.status === 'completed' && (
            <div className="mt-6 pt-6 border-t border-indigo-500/10">
              <h3 className="text-sm font-semibold text-gray-300 mb-3">Latest Sync Summary</h3>
              <div className="grid grid-cols-3 gap-4 text-center">
                <div className="bg-indigo-500/5 rounded-lg p-3 border border-indigo-500/10">
                  <div className="text-2xl font-bold text-indigo-400">{latestSync.groups_synced}</div>
                  <div className="text-xs text-gray-500">Groups</div>
                </div>
                <div className="bg-indigo-500/5 rounded-lg p-3 border border-indigo-500/10">
                  <div className="text-2xl font-bold text-indigo-400">{latestSync.ledgers_synced}</div>
                  <div className="text-xs text-gray-500">Ledgers</div>
                </div>
                <div className="bg-indigo-500/5 rounded-lg p-3 border border-indigo-500/10">
                  <div className="text-2xl font-bold text-indigo-400">{latestSync.vouchers_synced}</div>
                  <div className="text-xs text-gray-500">Vouchers</div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Sync History */}
        <div className="glass-card p-6 flex flex-col h-[400px]">
          <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
            <Clock className="w-5 h-5 text-indigo-400" />
            Sync History
          </h2>
          
          <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
            {syncHistory.length === 0 ? (
              <div className="text-center text-gray-500 py-10">No sync history available.</div>
            ) : (
              <div className="space-y-3">
                {syncHistory.map((job) => (
                  <div key={job.id} className="p-3 rounded-lg bg-indigo-500/5 border border-indigo-500/10">
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex items-center gap-2">
                        {job.status === 'completed' ? <CheckCircle2 className="w-4 h-4 text-green-500" /> :
                         job.status === 'failed' ? <XCircle className="w-4 h-4 text-red-500" /> :
                         <RefreshCw className="w-4 h-4 text-yellow-500 animate-spin" />}
                        <span className="font-medium text-sm text-gray-200 capitalize">{job.status}</span>
                      </div>
                      <span className="text-xs text-gray-500" title={formatDateTime(job.started_at)}>
                        {timeAgo(job.started_at)}
                      </span>
                    </div>
                    {job.error_message ? (
                      <p className="text-xs text-red-400 mt-1">{job.error_message}</p>
                    ) : (
                      <div className="text-xs text-gray-400 flex gap-3 mt-1">
                        <span>Ledgers: {job.ledgers_synced}</span>
                        <span>Vouchers: {job.vouchers_synced}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
