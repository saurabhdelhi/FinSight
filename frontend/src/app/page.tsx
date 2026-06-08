'use client';

/**
 * FinSight Landing Page — premium dark theme with glassmorphism.
 */

import Link from 'next/link';
import { useAuth } from '@/hooks/use-auth';

export default function LandingPage() {
  const { isAuthenticated } = useAuth();

  return (
    <div className="min-h-screen">
      {/* Nav */}
      <nav className="flex items-center justify-between px-8 py-5 border-b border-indigo-500/10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold text-lg">
            F
          </div>
          <span className="text-xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
            FinSight
          </span>
        </div>
        <div className="flex items-center gap-4">
          {isAuthenticated ? (
            <Link href="/dashboard" className="btn-primary">
              Dashboard →
            </Link>
          ) : (
            <>
              <Link href="/login" className="btn-secondary">
                Sign In
              </Link>
              <Link href="/register" className="btn-primary">
                Get Started
              </Link>
            </>
          )}
        </div>
      </nav>

      {/* Hero */}
      <section className="relative px-8 py-24 text-center overflow-hidden">
        {/* Background glow */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-indigo-600/10 rounded-full blur-[120px]" />
        
        <div className="relative max-w-4xl mx-auto animate-fade-in">
          <div className="inline-block mb-6 px-4 py-2 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-sm font-medium">
            🚀 Built for Indian CA Firms
          </div>
          <h1 className="text-5xl md:text-6xl font-bold mb-6 leading-tight">
            <span className="bg-gradient-to-r from-white via-indigo-200 to-purple-300 bg-clip-text text-transparent">
              Smart Audit &<br />Financial Reporting
            </span>
          </h1>
          <p className="text-xl text-gray-400 mb-10 max-w-2xl mx-auto leading-relaxed">
            Connect to Tally Prime, run 200+ audit rules automatically,
            map trial balance to MCA Schedule III, and generate
            CA-ready Excel/PDF reports in minutes — not days.
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link href="/register" className="btn-primary text-lg px-8 py-3">
              Start Free Trial
            </Link>
            <Link href="/login" className="btn-secondary text-lg px-8 py-3">
              View Demo
            </Link>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="px-8 py-20 max-w-6xl mx-auto">
        <h2 className="text-3xl font-bold text-center mb-4 text-white">
          End-to-End Audit Workflow
        </h2>
        <p className="text-gray-400 text-center mb-16 max-w-2xl mx-auto">
          From Tally data extraction to CA-ready reports — one seamless platform.
        </p>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[
            {
              icon: '🔗',
              title: 'Tally Sync',
              desc: 'Connect to Tally Prime via XML HTTP API. Auto-sync ledgers, vouchers, and trial balance.',
              color: 'from-cyan-500 to-blue-500',
            },
            {
              icon: '🔍',
              title: '200+ Audit Rules',
              desc: 'Comprehensive rules covering cash, statutory, revenue, ledger hygiene, and receivables.',
              color: 'from-indigo-500 to-purple-500',
            },
            {
              icon: '📊',
              title: 'Schedule III Mapping',
              desc: 'Auto-map trial balance to MCA Schedule III Balance Sheet and P&L format.',
              color: 'from-purple-500 to-pink-500',
            },
            {
              icon: '📄',
              title: 'Excel & PDF Reports',
              desc: 'Generate professionally formatted, CA-ready audit reports and financial statements.',
              color: 'from-pink-500 to-rose-500',
            },
          ].map((feature, i) => (
            <div
              key={i}
              className="glass-card p-6 animate-fade-in"
              style={{ animationDelay: `${i * 0.1}s` }}
            >
              <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${feature.color} flex items-center justify-center text-2xl mb-4`}>
                {feature.icon}
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">
                {feature.title}
              </h3>
              <p className="text-gray-400 text-sm leading-relaxed">
                {feature.desc}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Stats */}
      <section className="px-8 py-16 max-w-4xl mx-auto">
        <div className="glass-card p-10 grid grid-cols-2 md:grid-cols-4 gap-8 text-center animate-pulse-glow">
          {[
            { value: '200+', label: 'Audit Rules' },
            { value: '30+', label: 'Schedule III Lines' },
            { value: '< 2min', label: 'Sync Time' },
            { value: '100%', label: 'MCA Compliant' },
          ].map((stat, i) => (
            <div key={i}>
              <div className="text-3xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
                {stat.value}
              </div>
              <div className="text-sm text-gray-500 mt-1">{stat.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="px-8 py-10 text-center border-t border-indigo-500/10">
        <p className="text-gray-500 text-sm">
          © 2025 FinSight. Built for Indian CA firms managing 10-30 Tally clients.
        </p>
      </footer>
    </div>
  );
}
