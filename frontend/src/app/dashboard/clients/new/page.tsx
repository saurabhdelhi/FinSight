'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import api from '@/lib/api';
import { ArrowLeft, Server, Building } from 'lucide-react';

export default function NewClientPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const [form, setForm] = useState({
    company_name: '',
    tally_host: 'localhost',
    tally_port: 9000,
    financial_year: '2026-2027',
    company_number: '',
    gstin: '',
    pan: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      const client = await api.createClient(form);
      router.push(`/dashboard/clients/${client.id}`);
    } catch (err: any) {
      setError(err.message || 'Failed to create client');
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto animate-fade-in">
      <Link href="/dashboard" className="flex items-center gap-2 text-gray-400 hover:text-white mb-6 transition-colors">
        <ArrowLeft className="w-4 h-4" />
        Back to Clients
      </Link>

      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Add New Client</h1>
        <p className="text-gray-400">Configure Tally connection details and statutory information.</p>
      </div>

      {error && (
        <div className="p-4 mb-6 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="glass-card p-6 space-y-6">
          <div className="flex items-center gap-2 mb-4 text-indigo-400 border-b border-indigo-500/10 pb-2">
            <Building className="w-5 h-5" />
            <h2 className="text-lg font-semibold">Company Details</h2>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Company Name in Tally</label>
            <input
              type="text"
              className="input-field"
              placeholder="e.g. Acme Corp Pvt Ltd"
              value={form.company_name}
              onChange={(e) => setForm({ ...form, company_name: e.target.value })}
              required
            />
            <p className="text-xs text-gray-500 mt-1">Must match exactly with the company name open in Tally Prime.</p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Financial Year</label>
              <select 
                className="input-field"
                value={form.financial_year}
                onChange={(e) => setForm({ ...form, financial_year: e.target.value })}
              >
                <option value="2027-2028">2027-2028</option>
                <option value="2026-2027">2026-2027</option>
                <option value="2025-2026">2025-2026</option>
                <option value="2024-2025">2024-2025</option>
                <option value="2023-2024">2023-2024</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">CIN (Optional)</label>
              <input
                type="text"
                className="input-field"
                placeholder="L12345MH2000PLC123456"
                value={form.company_number}
                onChange={(e) => setForm({ ...form, company_number: e.target.value })}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">GSTIN (Optional)</label>
              <input
                type="text"
                className="input-field"
                placeholder="27ABCDE1234F1Z5"
                value={form.gstin}
                onChange={(e) => setForm({ ...form, gstin: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">PAN (Optional)</label>
              <input
                type="text"
                className="input-field"
                placeholder="ABCDE1234F"
                value={form.pan}
                onChange={(e) => setForm({ ...form, pan: e.target.value })}
              />
            </div>
          </div>
        </div>

        <div className="glass-card p-6 space-y-6">
          <div className="flex items-center gap-2 mb-4 text-indigo-400 border-b border-indigo-500/10 pb-2">
            <Server className="w-5 h-5" />
            <h2 className="text-lg font-semibold">Tally Connection Settings</h2>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Tally Server Host</label>
              <input
                type="text"
                className="input-field"
                value={form.tally_host}
                onChange={(e) => setForm({ ...form, tally_host: e.target.value })}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Port (XML API)</label>
              <input
                type="number"
                className="input-field"
                value={form.tally_port}
                onChange={(e) => setForm({ ...form, tally_port: parseInt(e.target.value) })}
                required
              />
            </div>
          </div>
          <div className="p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg text-sm text-blue-300">
            <strong>Note:</strong> Ensure Tally Prime is running on the host machine and the XML HTTP server is enabled (F12 Configure &gt; Advanced Configuration).
          </div>
        </div>

        <div className="flex justify-end gap-4 pt-4">
          <Link href="/dashboard" className="btn-secondary">
            Cancel
          </Link>
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Creating...' : 'Save Client'}
          </button>
        </div>
      </form>
    </div>
  );
}
