/**
 * FinSight API client — typed fetch wrapper for backend communication.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ApiError {
  error: string;
  message: string;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private getToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('finsight_token');
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...((options.headers as Record<string, string>) || {}),
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      cache: 'no-store',
      ...options,
      headers,
    });

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({
        error: 'NetworkError',
        message: `Request failed with status ${response.status}`,
      }));
      throw new Error(error.message);
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return undefined as T;
    }

    return response.json();
  }

  // ── Auth ─────────────────────────────────────────────────────────
  async register(data: {
    email: string;
    password: string;
    full_name: string;
    org_name: string;
  }) {
    return this.request<{ access_token: string; refresh_token: string }>(
      '/api/auth/register',
      { method: 'POST', body: JSON.stringify(data) }
    );
  }

  async login(email: string, password: string) {
    return this.request<{ access_token: string; refresh_token: string }>(
      '/api/auth/login',
      { method: 'POST', body: JSON.stringify({ email, password }) }
    );
  }

  async getMe() {
    return this.request<{
      id: string;
      email: string;
      full_name: string;
      role: string;
      org_id: string;
      org_name: string;
    }>('/api/auth/me');
  }

  // ── Clients ──────────────────────────────────────────────────────
  async getClients() {
    return this.request<{ clients: Client[]; total: number }>('/api/clients');
  }

  async createClient(data: Partial<Client>) {
    return this.request<Client>('/api/clients', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getClient(id: string) {
    return this.request<Client>(`/api/clients/${id}`);
  }

  async updateClient(id: string, data: Partial<Client>) {
    return this.request<Client>(`/api/clients/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteClient(id: string) {
    return this.request<void>(`/api/clients/${id}`, { method: 'DELETE' });
  }

  async testConnection(clientId: string) {
    return this.request<{ success: boolean; message: string; company_name?: string }>(
      `/api/clients/${clientId}/test-connection`,
      { method: 'POST' }
    );
  }

  // ── Sync ─────────────────────────────────────────────────────────
  async triggerSync(clientId: string) {
    return this.request<{ job_id: string; status: string; message: string }>(
      `/api/clients/${clientId}/sync`,
      { method: 'POST' }
    );
  }

  async getSyncStatus(clientId: string) {
    return this.request<SyncJob | null>(`/api/clients/${clientId}/sync/status`);
  }

  async getSyncHistory(clientId: string) {
    return this.request<SyncJob[]>(`/api/clients/${clientId}/sync/history`);
  }

  async getLedgers(clientId: string) {
    return this.request<Ledger[]>(`/api/clients/${clientId}/ledgers`);
  }

  async getTrialBalance(clientId: string) {
    return this.request<TrialBalance>(`/api/clients/${clientId}/trial-balance`);
  }

  // ── Audit ────────────────────────────────────────────────────────
  async runAudit(clientId: string, ruleIds?: string[]) {
    return this.request<AuditRun>(`/api/clients/${clientId}/audit/run`, {
      method: 'POST',
      body: JSON.stringify({ rule_ids: ruleIds || null }),
    });
  }

  async getLatestAudit(clientId: string) {
    return this.request<AuditRun | null>(`/api/clients/${clientId}/audit/latest`);
  }

  async getAuditFindings(clientId: string, severity?: string) {
    const params = severity ? `?severity=${severity}` : '';
    return this.request<AuditFinding[]>(
      `/api/clients/${clientId}/audit/findings${params}`
    );
  }

  async getAuditRules(clientId: string) {
    return this.request<RuleInfo[]>(`/api/clients/${clientId}/audit/rules`);
  }

  // ── Schedule III ─────────────────────────────────────────────────
  async getScheduleIIIMappings(clientId: string) {
    return this.request<ScheduleIIIMapping[]>(
      `/api/clients/${clientId}/schedule-iii/mappings`
    );
  }

  async getBalanceSheet(clientId: string) {
    return this.request<BalanceSheet>(`/api/clients/${clientId}/schedule-iii/balance-sheet`);
  }

  async getProfitAndLoss(clientId: string) {
    return this.request<ProfitAndLoss>(`/api/clients/${clientId}/schedule-iii/profit-and-loss`);
  }

  // ── Reports ──────────────────────────────────────────────────────
  async generateReport(clientId: string, reportType: string, format: string) {
    return this.request<Report>(`/api/clients/${clientId}/reports/generate`, {
      method: 'POST',
      body: JSON.stringify({ report_type: reportType, report_format: format }),
    });
  }

  async getReports(clientId: string) {
    return this.request<{ reports: Report[]; total: number }>(
      `/api/clients/${clientId}/reports`
    );
  }

  getReportDownloadUrl(reportId: string): string {
    return `${this.baseUrl}/api/reports/${reportId}/download`;
  }
}

// ── Types ────────────────────────────────────────────────────────────────

export interface Client {
  id: string;
  company_name: string;
  tally_host: string;
  tally_port: number;
  financial_year: string;
  company_number?: string;
  gstin?: string;
  pan?: string;
  notes?: string;
  last_synced_at?: string;
  created_at: string;
}

export interface SyncJob {
  id: string;
  status: string;
  started_at?: string;
  completed_at?: string;
  groups_synced: number;
  ledgers_synced: number;
  vouchers_synced: number;
  error_message?: string;
  created_at: string;
}

export interface Ledger {
  id: string;
  name: string;
  parent: string;
  opening_balance: number;
  closing_balance: number;
  debit_total: number;
  credit_total: number;
}

export interface TrialBalance {
  client_id: string;
  financial_year: string;
  entries: { ledger_name: string; group: string; opening_balance: number; debit: number; credit: number; closing_balance: number }[];
  total_debit: number;
  total_credit: number;
}

export interface AuditRun {
  id: string;
  run_at: string;
  status: string;
  rules_executed: number;
  total_findings: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  info_count: number;
  risk_score: number;
  duration_seconds?: number;
  findings: AuditFinding[];
}

export interface AuditFinding {
  id: string;
  rule_id: string;
  severity: string;
  category: string;
  title: string;
  description: string;
  ledger_name?: string;
  amount?: number;
  recommendation?: string;
  reference?: string;
}

export interface RuleInfo {
  rule_id: string;
  title: string;
  category: string;
  severity: string;
  description: string;
}

export interface ScheduleIIIMapping {
  id: string;
  ledger_name: string;
  tally_group: string;
  section: string;
  schedule_iii_line: string;
  category: string;
  amount: number;
  is_auto_mapped: boolean;
  mapping_confidence?: number;
}

export interface BalanceSheet {
  client_id: string;
  financial_year: string;
  equity_and_liabilities: Record<string, Record<string, number>>;
  assets: Record<string, Record<string, number>>;
  total_equity_liabilities: number;
  total_assets: number;
  is_balanced: boolean;
}

export interface ProfitAndLoss {
  client_id: string;
  financial_year: string;
  revenue: Record<string, number>;
  expenses: Record<string, number>;
  total_revenue: number;
  total_expenses: number;
  profit_before_tax: number;
  tax_expense: number;
  net_profit: number;
}

export interface Report {
  id: string;
  report_type: string;
  report_format: string;
  file_name: string;
  file_size_bytes?: number;
  generated_at: string;
}

// Singleton
export const api = new ApiClient();
export default api;
