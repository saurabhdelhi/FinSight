'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import api, { Client } from '@/lib/api';
import { formatDate } from '@/lib/utils';
import { Building, Plus, MoreVertical, Settings, Database, Activity } from 'lucide-react';

export default function DashboardPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadClients = async () => {
    try {
      setLoading(true);
      const res = await api.getClients();
      setClients(res.clients);
    } catch (err: any) {
      setError(err.message || 'Failed to load clients');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadClients();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-1">Your Clients</h1>
          <p className="text-gray-400">Manage Tally connections and audit runs</p>
        </div>
        <Link href="/dashboard/clients/new" className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" />
          Add Client
        </Link>
      </div>

      {error && (
        <div className="p-4 mb-6 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400">
          {error}
        </div>
      )}

      {clients.length === 0 && !error ? (
        <div className="glass-card p-12 text-center">
          <Building className="w-16 h-16 text-indigo-500/50 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-white mb-2">No clients added yet</h3>
          <p className="text-gray-400 mb-6 max-w-md mx-auto">
            Add your first client to start syncing Tally data, running audit rules, and generating Schedule III reports.
          </p>
          <Link href="/dashboard/clients/new" className="btn-primary">
            Add Your First Client
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {clients.map((client) => (
            <Link href={`/dashboard/clients/${client.id}`} key={client.id} className="block group">
              <div className="glass-card p-6 h-full border border-indigo-500/10 hover:border-indigo-500/30 transition-all">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-400">
                      <Building className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-white group-hover:text-indigo-400 transition-colors">
                        {client.company_name}
                      </h3>
                      <p className="text-xs text-gray-500">FY: {client.financial_year}</p>
                    </div>
                  </div>
                  <button className="text-gray-500 hover:text-white p-1">
                    <MoreVertical className="w-4 h-4" />
                  </button>
                </div>

                <div className="space-y-3 mb-6">
                  <div className="flex items-center gap-2 text-sm text-gray-400">
                    <Database className="w-4 h-4 text-gray-500" />
                    <span className="truncate">{client.tally_host}:{client.tally_port}</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-gray-400">
                    <Activity className="w-4 h-4 text-gray-500" />
                    <span>Last Sync: {client.last_synced_at ? formatDate(client.last_synced_at) : 'Never'}</span>
                  </div>
                </div>

                <div className="pt-4 border-t border-indigo-500/10 flex justify-between items-center text-sm">
                  <span className="text-indigo-400 font-medium">View Dashboard →</span>
                  {client.gstin && <span className="text-gray-500 text-xs">GST: {client.gstin.substring(0,6)}...</span>}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
