'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import api, { Client } from '@/lib/api';
import { ArrowLeft, Building, Activity, Database, FileText, CheckCircle2, XCircle } from 'lucide-react';
import { SyncTab } from './SyncTab';
import { AuditTab } from './AuditTab';
import { ScheduleIIITab } from './ScheduleIIITab';
import { ReportsTab } from './ReportsTab';
import { cn } from '@/lib/utils';

export default function ClientDashboard({ params }: { params: { id: string } }) {
  const [client, setClient] = useState<Client | null>(null);
  const [activeTab, setActiveTab] = useState('sync');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadClient = async () => {
    try {
      const data = await api.getClient(params.id);
      setClient(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load client details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadClient();
  }, [params.id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !client) {
    return (
      <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400">
        {error || 'Client not found'}
      </div>
    );
  }

  const tabs = [
    { id: 'sync', label: 'Tally Sync', icon: Database },
    { id: 'audit', label: 'Audit Rules', icon: Activity },
    { id: 'schedule-iii', label: 'Schedule III', icon: Building },
    { id: 'reports', label: 'Reports', icon: FileText },
  ];

  return (
    <div className="animate-fade-in">
      <Link href="/dashboard" className="flex items-center gap-2 text-gray-400 hover:text-white mb-6 transition-colors">
        <ArrowLeft className="w-4 h-4" />
        Back to Clients
      </Link>

      {/* Header Card */}
      <div className="glass-card p-6 mb-8 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white mb-1">{client.company_name}</h1>
          <div className="flex items-center gap-4 text-sm text-gray-400">
            <span>FY: {client.financial_year}</span>
            {client.gstin && <span>GST: {client.gstin}</span>}
            <span className="flex items-center gap-1">
              <span className={cn("w-2 h-2 rounded-full", client.last_synced_at ? "bg-green-500" : "bg-yellow-500")} />
              {client.last_synced_at ? 'Connected' : 'Not Synced'}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Link href={`/dashboard/clients/${client.id}/settings`} className="btn-secondary">
            Settings
          </Link>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-indigo-500/10 mb-6">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'flex items-center gap-2 px-6 py-3 border-b-2 font-medium transition-colors',
                isActive 
                  ? 'border-indigo-500 text-indigo-400' 
                  : 'border-transparent text-gray-400 hover:text-gray-200 hover:border-gray-700'
              )}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      <div className="min-h-[500px]">
        {activeTab === 'sync' && <SyncTab clientId={client.id} lastSyncedAt={client.last_synced_at} />}
        {activeTab === 'audit' && <AuditTab clientId={client.id} />}
        {activeTab === 'schedule-iii' && <ScheduleIIITab clientId={client.id} />}
        {activeTab === 'reports' && <ReportsTab clientId={client.id} />}
      </div>
    </div>
  );
}
