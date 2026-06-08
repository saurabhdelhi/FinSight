'use client';

import { useState, useEffect } from 'react';
import api, { Report } from '@/lib/api';
import { FileText, FileSpreadsheet, Download, Loader2 } from 'lucide-react';
import { formatDateTime } from '@/lib/utils';

export function ReportsTab({ clientId }: { clientId: string }) {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');

  const loadReports = async () => {
    try {
      const res = await api.getReports(clientId);
      setReports(res.reports);
    } catch (err: any) {
      setError('Failed to load reports');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReports();
  }, [clientId]);

  const handleGenerate = async (type: string, format: string) => {
    setGenerating(true);
    try {
      await api.generateReport(clientId, type, format);
      await loadReports();
    } catch (err: any) {
      alert(err.message || 'Report generation failed');
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-center text-gray-500 animate-pulse">Loading reports...</div>;
  }

  return (
    <div className="space-y-6 animate-fade-in">
      
      {/* Generation Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* CA Report Package */}
        <div className="glass-card p-6 flex flex-col">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center text-white">
              <FileSpreadsheet className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">Excel Report Package</h2>
              <p className="text-sm text-gray-400">Complete audit working papers</p>
            </div>
          </div>
          <p className="text-sm text-gray-400 mb-6 flex-1">
            Generates a professional Excel workbook containing Cover Page, Schedule III Balance Sheet & P&L, Trial Balance, and Detailed Audit Findings.
          </p>
          <button 
            onClick={() => handleGenerate('combined', 'xlsx')}
            disabled={generating}
            className="btn-primary w-full flex items-center justify-center gap-2"
          >
            {generating ? <Loader2 className="w-5 h-5 animate-spin" /> : <FileSpreadsheet className="w-5 h-5" />}
            Generate Excel Workbook
          </button>
        </div>

        {/* PDF Report */}
        <div className="glass-card p-6 flex flex-col">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-red-500 to-rose-600 flex items-center justify-center text-white">
              <FileText className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">PDF Summary Report</h2>
              <p className="text-sm text-gray-400">Client-facing document</p>
            </div>
          </div>
          <p className="text-sm text-gray-400 mb-6 flex-1">
            Generates a clean PDF document with the Audit Summary, Risk Score, and Financial Statements, perfect for sharing with management.
          </p>
          <button 
            onClick={() => handleGenerate('combined', 'pdf')}
            disabled={generating}
            className="w-full py-2.5 px-4 rounded-lg font-medium text-white bg-gray-800 hover:bg-gray-700 border border-gray-600 transition-colors flex items-center justify-center gap-2"
          >
            {generating ? <Loader2 className="w-5 h-5 animate-spin" /> : <FileText className="w-5 h-5" />}
            Generate PDF Report
          </button>
        </div>

      </div>

      {/* Report History */}
      <div className="glass-card overflow-hidden mt-8">
        <div className="p-4 border-b border-indigo-500/10 bg-indigo-500/5">
          <h3 className="font-bold text-white">Generated Reports History</h3>
        </div>
        
        {reports.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="w-12 h-12 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-400">No reports generated yet.</p>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Report File</th>
                <th>Type</th>
                <th>Generated On</th>
                <th>Size</th>
                <th className="text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {reports.map((report) => (
                <tr key={report.id}>
                  <td>
                    <div className="flex items-center gap-2">
                      {report.report_format === 'xlsx' ? (
                        <FileSpreadsheet className="w-4 h-4 text-green-400" />
                      ) : (
                        <FileText className="w-4 h-4 text-red-400" />
                      )}
                      <span className="text-gray-300 font-medium">{report.file_name}</span>
                    </div>
                  </td>
                  <td className="text-gray-400 capitalize text-sm">
                    {report.report_type.replace('_', ' ')}
                  </td>
                  <td className="text-gray-400 text-sm">
                    {formatDateTime(report.generated_at)}
                  </td>
                  <td className="text-gray-500 text-sm font-mono">
                    {report.file_size_bytes ? `${(report.file_size_bytes / 1024).toFixed(1)} KB` : '-'}
                  </td>
                  <td className="text-right">
                    <a 
                      href={api.getReportDownloadUrl(report.id)}
                      download
                      className="inline-flex items-center gap-1 px-3 py-1.5 rounded-md bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 transition-colors text-sm font-medium"
                    >
                      <Download className="w-4 h-4" />
                      Download
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

    </div>
  );
}
