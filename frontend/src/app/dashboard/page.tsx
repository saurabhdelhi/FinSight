'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import api, { Client } from '@/lib/api';
import { formatDate } from '@/lib/utils';
import { Building, Plus, MoreVertical, Database, Activity, Trash2 } from 'lucide-react';

export default function DashboardPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [selectedClientIds, setSelectedClientIds] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Dropdown & Deletion States
  const [activeDropdownId, setActiveDropdownId] = useState<string | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [clientToDelete, setClientToDelete] = useState<Client | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const loadClients = async () => {
    try {
      setLoading(true);
      const res = await api.getClients();
      setClients(res.clients);

      // Set initial selected client IDs for each unique company name to be the latest year
      const initialSelected: Record<string, string> = {};
      res.clients.forEach(client => {
        const name = client.company_name;
        if (!initialSelected[name]) {
          initialSelected[name] = client.id;
        } else {
          const currentSelected = res.clients.find(c => c.id === initialSelected[name]);
          if (currentSelected && client.financial_year > currentSelected.financial_year) {
            initialSelected[name] = client.id;
          }
        }
      });
      setSelectedClientIds(initialSelected);
    } catch (err: any) {
      setError(err.message || 'Failed to load clients');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadClients();
  }, []);

  // Close dropdown on click outside
  useEffect(() => {
    const handleOutsideClick = () => {
      setActiveDropdownId(null);
    };
    window.addEventListener('click', handleOutsideClick);
    return () => window.removeEventListener('click', handleOutsideClick);
  }, []);

  const handleDropdownToggle = (e: React.MouseEvent, clientId: string) => {
    e.preventDefault();
    e.stopPropagation();
    setActiveDropdownId(activeDropdownId === clientId ? null : clientId);
  };

  const triggerDeleteConfirm = (e: React.MouseEvent, client: Client) => {
    e.preventDefault();
    e.stopPropagation();
    setClientToDelete(client);
    setShowDeleteModal(true);
    setActiveDropdownId(null);
  };

  const confirmDelete = async () => {
    if (!clientToDelete) return;
    setDeleteLoading(true);
    try {
      await api.deleteClient(clientToDelete.id);
      setShowDeleteModal(false);
      setClientToDelete(null);
      await loadClients();
    } catch (err: any) {
      setError(err.message || 'Failed to delete client');
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

  return (
    <div className="animate-fade-in relative">
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
          {Array.from(new Set(clients.map(c => c.company_name))).sort().map((companyName) => {
            const companyClients = clients.filter(c => c.company_name === companyName);
            
            // Deduplicate clients by financial year prioritizing the best synced client row
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
            // Sort by year descending for display
            uniqueYearClients.sort((a, b) => b.financial_year.localeCompare(a.financial_year));
            
            const selectedId = selectedClientIds[companyName] || uniqueYearClients[0]?.id;
            const client = uniqueYearClients.find(c => c.id === selectedId) || uniqueYearClients[0];
            
            if (!client) return null;

            return (
              <Link href={`/dashboard/clients/${client.id}`} key={companyName} className="block group">
                <div className="glass-card p-6 h-full border border-indigo-500/10 hover:border-indigo-500/30 transition-all flex flex-col justify-between">
                  <div>
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-400">
                          <Building className="w-5 h-5" />
                        </div>
                        <div>
                          <h3 className="text-lg font-semibold text-white group-hover:text-indigo-400 transition-colors">
                            {client.company_name}
                          </h3>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="text-xs text-gray-500">FY:</span>
                            <select
                              value={client.id}
                              onChange={(e) => {
                                setSelectedClientIds(prev => ({
                                  ...prev,
                                  [companyName]: e.target.value
                                }));
                              }}
                              onClick={(e) => {
                                e.preventDefault();
                                e.stopPropagation();
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
                        </div>
                      </div>
                      
                      {/* Action Dropdown */}
                      <div className="relative">
                        <button 
                          onClick={(e) => handleDropdownToggle(e, client.id)} 
                          className="text-gray-500 hover:text-white p-1 rounded-md hover:bg-white/10 transition-colors"
                        >
                          <MoreVertical className="w-4 h-4" />
                        </button>
                        
                        {activeDropdownId === client.id && (
                          <div 
                            className="absolute right-0 mt-1 w-36 bg-slate-900 border border-indigo-500/20 rounded-md shadow-lg py-1 z-10"
                            onClick={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                            }}
                          >
                            <button
                              onClick={(e) => triggerDeleteConfirm(e, client)}
                              className="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-red-500/10 hover:text-red-300 transition-colors flex items-center gap-2"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                              Delete Client
                            </button>
                          </div>
                        )}
                      </div>
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
                  </div>

                  <div className="pt-4 border-t border-indigo-500/10 flex justify-between items-center text-sm">
                    <span className="text-indigo-400 font-medium">View Dashboard →</span>
                    {client.gstin && <span className="text-gray-500 text-xs">GST: {client.gstin.substring(0, 6)}...</span>}
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}

      {/* Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="glass-card max-w-md w-full p-6 border border-red-500/20 shadow-2xl">
            <h3 className="text-xl font-bold text-white mb-2 flex items-center gap-2">
              <Trash2 className="w-5 h-5 text-red-500" />
              Delete Client?
            </h3>
            <p className="text-gray-400 text-sm mb-6 leading-relaxed">
              Are you sure you want to delete <strong className="text-white">{clientToDelete?.company_name}</strong> for financial year <strong className="text-white">{clientToDelete?.financial_year}</strong>? 
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
