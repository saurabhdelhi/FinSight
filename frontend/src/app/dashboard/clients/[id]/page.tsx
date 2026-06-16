'use client';

import { useState, useEffect, use } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import api, { Client } from '@/lib/api';
import { ArrowLeft, Building, Activity, Database, FileText, CheckCircle2, XCircle, Trash2 } from 'lucide-react';
import { SyncTab } from './SyncTab';
import { AuditTab } from './AuditTab';
import { ScheduleIIITab } from './ScheduleIIITab';
import { ReportsTab } from './ReportsTab';
import { cn } from '@/lib/utils';

export default function ClientDashboard({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();
  const { id } = use(params);
  const [client, setClient] = useState<Client | null>(null);
  const [allClients, setAllClients] = useState<Client[]>([]);
  const [activeTab, setActiveTab] = useState('sync');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const loadClient = async () => {
    try {
      setLoading(true);
      const data = await api.getClient(id);
      setClient(data);
      
      const allRes = await api.getClients();
      setAllClients(allRes.clients);
    } catch (err: any) {
      setError(err.message || 'Failed to load client details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadClient();
  }, [id]);

  const confirmDelete = async () => {
    if (!client) return;
    setDeleteLoading(true);
    try {
      await api.deleteClient(client.id);
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Failed to delete client');
      setShowDeleteModal(false);
    } finally {
      setDeleteLoading(false);
    }
  };

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

  // Group and sort unique financial years for the dropdown
  const companyClients = allClients.filter(c => c.company_name === client.company_name);
  const uniqueYearClients: Client[] = [];
  const yearsSeen = new Set<string>();
  const sortedForDedup = [...companyClients].sort((a, b) => {
    const timeA = a.last_synced_at ? new Date(a.last_synced_at).getTime() : 0;
    const timeB = b.last_synced_at ? new Date(b.last_synced_at).getTime() : 0;
    if (timeB !== timeA) return timeB - timeA;
    return b.created_at.localeCompare(a.created_at);
  });
  sortedForDedup.forEach(c => {
    if (!yearsSeen.has(c.financial_year)) {
      yearsSeen.add(c.financial_year);
      uniqueYearClients.push(c);
    }
  });
  uniqueYearClients.sort((a, b) => b.financial_year.localeCompare(a.financial_year));

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
            {uniqueYearClients.length > 1 ? (
              <div className="flex items-center gap-1.5">
                <span>FY:</span>
                <select
                  value={client.id}
                  onChange={(e) => {
                    router.push(`/dashboard/clients/${e.target.value}`);
                  }}
                  className="bg-slate-900 border border-indigo-500/20 text-white rounded px-2 py-0.5 text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-indigo-500 cursor-pointer"
                >
                  {uniqueYearClients.map(c => (
                    <option key={c.id} value={c.id}>
                      {c.financial_year}
                    </option>
                  ))}
                </select>
              </div>
            ) : (
              <span>FY: {client.financial_year}</span>
            )}
            {client.gstin && <span>GST: {client.gstin}</span>}
            <span className="flex items-center gap-1">
              <span className={cn("w-2 h-2 rounded-full", client.last_synced_at ? "bg-green-500" : "bg-yellow-500")} />
              {client.last_synced_at ? 'Connected' : 'Not Synced'}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={() => setShowDeleteModal(true)} 
            className="btn-secondary text-red-400 hover:text-red-300 border-red-500/20 hover:border-red-500/40 hover:bg-red-500/10 flex items-center gap-2 font-medium"
          >
            <Trash2 className="w-4 h-4" />
            Delete Client
          </button>
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
        {activeTab === 'sync' && (
          <SyncTab 
            clientId={client.id} 
            lastSyncedAt={client.last_synced_at} 
            onSyncComplete={loadClient} 
          />
        )}
        {activeTab === 'audit' && <AuditTab clientId={client.id} />}
        {activeTab === 'schedule-iii' && <ScheduleIIITab clientId={client.id} />}
        {activeTab === 'reports' && <ReportsTab clientId={client.id} />}
      </div>

      {/* Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="glass-card max-w-md w-full p-6 border border-red-500/20 shadow-2xl">
            <h3 className="text-xl font-bold text-white mb-2 flex items-center gap-2">
              <Trash2 className="w-5 h-5 text-red-500" />
              Delete Client?
            </h3>
            <p className="text-gray-400 text-sm mb-6 leading-relaxed">
              Are you sure you want to delete <strong className="text-white">{client.company_name}</strong> for financial year <strong className="text-white">{client.financial_year}</strong>? 
              This will permanently delete all associated sync jobs, vouchers, ledger accounts, mappings, and generated reports. This action cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
              <button 
                onClick={() => setShowDeleteModal(false)} 
                className="btn-secondary"
                disabled={deleteLoading}
              >
                Cancel
              </button>
              <button 
                onClick={confirmDelete} 
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
                disabled={deleteLoading}
              >
                {deleteLoading ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
