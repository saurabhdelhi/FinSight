'use client';

import { useState, useEffect } from 'react';
import api, { BalanceSheet, ProfitAndLoss } from '@/lib/api';
import { Building, TrendingUp, CheckCircle2, XCircle } from 'lucide-react';
import { cn, formatINRCompact, formatINR } from '@/lib/utils';

export function ScheduleIIITab({ clientId }: { clientId: string }) {
  const [bs, setBs] = useState<BalanceSheet | null>(null);
  const [pl, setPl] = useState<ProfitAndLoss | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadData = async () => {
      try {
        const [bsData, plData] = await Promise.all([
          api.getBalanceSheet(clientId),
          api.getProfitAndLoss(clientId)
        ]);
        setBs(bsData);
        setPl(plData);
      } catch (err: any) {
        setError(err.message || 'Failed to load Schedule III data');
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [clientId]);

  if (loading) {
    return <div className="p-8 text-center text-gray-500 animate-pulse">Mapping trial balance to Schedule III...</div>;
  }

  if (error || !bs || !pl) {
    return (
      <div className="p-8 text-center">
        <p className="text-red-400 mb-4">{error || 'No data available'}</p>
        <p className="text-gray-500 text-sm">Please ensure Tally sync is completed.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-4 mb-4">
        <div className="glass-card flex-1 p-4 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <Building className="w-5 h-5 text-indigo-400" />
            <span className="font-semibold text-white">Balance Sheet Tally Status:</span>
          </div>
          {bs.is_balanced ? (
            <span className="flex items-center gap-1 text-green-400 font-medium">
              <CheckCircle2 className="w-5 h-5" /> Balanced
            </span>
          ) : (
            <span className="flex items-center gap-1 text-red-400 font-medium">
              <XCircle className="w-5 h-5" /> Mismatch
            </span>
          )}
        </div>
        
        <div className="glass-card flex-1 p-4 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-green-400" />
            <span className="font-semibold text-white">Net Profit:</span>
          </div>
          <span className={cn("font-mono font-bold text-lg", pl.net_profit >= 0 ? "text-green-400" : "text-red-400")}>
            {formatINRCompact(pl.net_profit)}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Balance Sheet */}
        <div className="glass-card p-0 overflow-hidden flex flex-col">
          <div className="bg-indigo-500/10 p-4 border-b border-indigo-500/20">
            <h2 className="text-lg font-bold text-white">Balance Sheet</h2>
            <p className="text-xs text-gray-400">As per MCA Schedule III (Division I)</p>
          </div>
          
          <div className="p-4 flex-1 overflow-y-auto custom-scrollbar" style={{ maxHeight: '600px' }}>
            <Section title="I. EQUITY AND LIABILITIES" />
            
            {Object.entries(bs.equity_and_liabilities).map(([category, items]) => (
              <Category key={category} title={category} items={items} />
            ))}
            
            <div className="flex justify-between items-center py-3 mt-4 border-t-2 border-indigo-500/30 bg-indigo-500/5 px-2 rounded">
              <span className="font-bold text-indigo-100">TOTAL EQUITY AND LIABILITIES</span>
              <span className="font-mono font-bold text-indigo-300">{formatINR(bs.total_equity_liabilities)}</span>
            </div>

            <div className="mt-8">
              <Section title="II. ASSETS" />
              {Object.entries(bs.assets).map(([category, items]) => (
                <Category key={category} title={category} items={items} />
              ))}
              
              <div className="flex justify-between items-center py-3 mt-4 border-t-2 border-indigo-500/30 bg-indigo-500/5 px-2 rounded">
                <span className="font-bold text-indigo-100">TOTAL ASSETS</span>
                <span className="font-mono font-bold text-indigo-300">{formatINR(bs.total_assets)}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Profit & Loss */}
        <div className="glass-card p-0 overflow-hidden flex flex-col">
          <div className="bg-purple-500/10 p-4 border-b border-purple-500/20">
            <h2 className="text-lg font-bold text-white">Statement of Profit & Loss</h2>
            <p className="text-xs text-gray-400">As per MCA Schedule III (Division I)</p>
          </div>
          
          <div className="p-4 flex-1 overflow-y-auto custom-scrollbar" style={{ maxHeight: '600px' }}>
            
            <Section title="INCOME" />
            <Category title="" items={pl.revenue} hideTitle />
            <div className="flex justify-between items-center py-2 border-t border-gray-700 mt-2 px-2">
              <span className="font-semibold text-gray-300">Total Income</span>
              <span className="font-mono font-semibold text-gray-300">{formatINR(pl.total_revenue)}</span>
            </div>

            <div className="mt-6">
              <Section title="EXPENSES" />
              <Category title="" items={pl.expenses} hideTitle />
              <div className="flex justify-between items-center py-2 border-t border-gray-700 mt-2 px-2">
                <span className="font-semibold text-gray-300">Total Expenses</span>
                <span className="font-mono font-semibold text-gray-300">{formatINR(pl.total_expenses)}</span>
              </div>
            </div>

            <div className="mt-8 space-y-2">
              <div className="flex justify-between items-center py-2 px-2 bg-gray-800/50 rounded">
                <span className="font-semibold text-gray-200">Profit Before Tax</span>
                <span className="font-mono font-semibold text-white">{formatINR(pl.profit_before_tax)}</span>
              </div>
              <div className="flex justify-between items-center py-2 px-2">
                <span className="text-gray-400 ml-4">Tax Expense</span>
                <span className="font-mono text-gray-400">{formatINR(pl.tax_expense)}</span>
              </div>
              <div className="flex justify-between items-center py-3 border-t-2 border-purple-500/30 bg-purple-500/5 px-2 rounded mt-2">
                <span className="font-bold text-purple-100">NET PROFIT / (LOSS)</span>
                <span className={cn("font-mono font-bold text-lg", pl.net_profit >= 0 ? "text-green-400" : "text-red-400")}>
                  {formatINR(pl.net_profit)}
                </span>
              </div>
            </div>
            
          </div>
        </div>

      </div>
    </div>
  );
}

function Section({ title }: { title: string }) {
  return <h3 className="font-bold text-white text-md mb-3 border-b border-gray-800 pb-1">{title}</h3>;
}

function Category({ title, items, hideTitle = false }: { title: string, items: Record<string, number>, hideTitle?: boolean }) {
  const keys = Object.keys(items);
  if (keys.length === 0) return null;
  
  return (
    <div className="mb-4">
      {!hideTitle && <h4 className="font-semibold text-gray-300 text-sm mb-2 ml-2">{title}</h4>}
      <div className="space-y-1">
        {keys.map(key => (
          <div key={key} className="flex justify-between items-center py-1.5 px-4 hover:bg-white/5 rounded transition-colors group">
            <span className="text-gray-400 text-sm group-hover:text-gray-300">{key}</span>
            <span className="font-mono text-gray-300 text-sm">{formatINR(items[key])}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
