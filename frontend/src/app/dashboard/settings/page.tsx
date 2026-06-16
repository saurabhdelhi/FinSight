'use client';

import { useState } from 'react';
import { useAuth } from '@/hooks/use-auth';
import { User, Shield, Building, Settings as SettingsIcon, Save, Key, Bell } from 'lucide-react';

export default function SettingsPage() {
  const { user } = useAuth();
  
  // Profile settings state
  const [fullName, setFullName] = useState(user?.full_name || '');
  const [email, setEmail] = useState(user?.email || '');
  const [isSavingProfile, setIsSavingProfile] = useState(false);

  // Password settings state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [passwordError, setPasswordError] = useState('');
  const [passwordSuccess, setPasswordSuccess] = useState('');

  // Preference settings state
  const [defaultFY, setDefaultFY] = useState('2025-2026');
  const [defaultPort, setDefaultPort] = useState('9000');
  const [emailNotifications, setEmailNotifications] = useState(true);

  const handleSaveProfile = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingProfile(true);
    // Simulate API call
    setTimeout(() => {
      setIsSavingProfile(false);
      alert('Profile settings updated successfully (simulation)');
    }, 800);
  };

  const handleChangePassword = (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError('');
    setPasswordSuccess('');

    if (newPassword !== confirmPassword) {
      setPasswordError('New passwords do not match');
      return;
    }

    if (newPassword.length < 6) {
      setPasswordError('Password must be at least 6 characters long');
      return;
    }

    setIsChangingPassword(true);
    // Simulate API call
    setTimeout(() => {
      setIsChangingPassword(false);
      setPasswordSuccess('Password updated successfully');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    }, 800);
  };

  return (
    <div className="animate-fade-in space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-white mb-1">Account & Settings</h1>
        <p className="text-gray-400">Manage your profile, organization details, and system preferences</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left: Navigation Tabs info/overview */}
        <div className="lg:col-span-1 space-y-6">
          {/* User Profile Card */}
          <div className="glass-card p-6 border border-indigo-500/10 flex flex-col items-center text-center">
            <div className="w-20 h-20 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-3xl font-bold mb-4">
              {user?.full_name?.charAt(0) || 'U'}
            </div>
            <h2 className="text-xl font-bold text-white">{user?.full_name}</h2>
            <p className="text-sm text-indigo-400 capitalize mb-1">{user?.role} Account</p>
            <p className="text-xs text-gray-500">{user?.email}</p>

            <div className="w-full border-t border-indigo-500/10 my-4 pt-4 text-left space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Organization:</span>
                <span className="text-gray-300 font-medium">{user?.org_name}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Status:</span>
                <span className="text-emerald-400 font-medium flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  Active
                </span>
              </div>
            </div>
          </div>

          {/* Quick Help Card */}
          <div className="glass-card p-6 border border-indigo-500/10">
            <h3 className="font-semibold text-white mb-2 flex items-center gap-2">
              <Shield className="w-4 h-4 text-indigo-400" />
              Need Help?
            </h3>
            <p className="text-sm text-gray-400 leading-relaxed">
              If you need to change your organization name or setup database exports, please contact the administrator.
            </p>
          </div>
        </div>

        {/* Right: Settings Forms */}
        <div className="lg:col-span-2 space-y-8">
          
          {/* Profile settings */}
          <div className="glass-card p-6 border border-indigo-500/10">
            <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <User className="w-5 h-5 text-indigo-400" />
              Profile Details
            </h2>
            <form onSubmit={handleSaveProfile} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-2">
                    Full Name
                  </label>
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className="form-input bg-slate-900 border-indigo-500/20 text-white w-full rounded-md"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-2">
                    Email Address
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="form-input bg-slate-900 border-indigo-500/20 text-white w-full rounded-md"
                    required
                    disabled
                  />
                  <p className="text-xs text-gray-500 mt-1">Contact admin to change email address.</p>
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <button
                  type="submit"
                  disabled={isSavingProfile}
                  className="btn-primary flex items-center gap-2"
                >
                  <Save className="w-4 h-4" />
                  {isSavingProfile ? 'Saving...' : 'Save Profile'}
                </button>
              </div>
            </form>
          </div>

          {/* Change Password */}
          <div className="glass-card p-6 border border-indigo-500/10">
            <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <Key className="w-5 h-5 text-indigo-400" />
              Security Settings
            </h2>
            <form onSubmit={handleChangePassword} className="space-y-4">
              {passwordError && (
                <div className="p-3 rounded-md bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                  {passwordError}
                </div>
              )}
              {passwordSuccess && (
                <div className="p-3 rounded-md bg-green-500/10 border border-green-500/20 text-green-400 text-sm">
                  {passwordSuccess}
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-2">
                    Current Password
                  </label>
                  <input
                    type="password"
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    className="form-input bg-slate-900 border-indigo-500/20 text-white w-full rounded-md"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-2">
                    New Password
                  </label>
                  <input
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="form-input bg-slate-900 border-indigo-500/20 text-white w-full rounded-md"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-2">
                    Confirm New Password
                  </label>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="form-input bg-slate-900 border-indigo-500/20 text-white w-full rounded-md"
                    required
                  />
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <button
                  type="submit"
                  disabled={isChangingPassword}
                  className="btn-primary flex items-center gap-2"
                >
                  <Save className="w-4 h-4" />
                  {isChangingPassword ? 'Updating...' : 'Update Password'}
                </button>
              </div>
            </form>
          </div>

          {/* Preferences */}
          <div className="glass-card p-6 border border-indigo-500/10">
            <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <SettingsIcon className="w-5 h-5 text-indigo-400" />
              Application Preferences
            </h2>
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-2">
                    Default Assessment Year
                  </label>
                  <select
                    value={defaultFY}
                    onChange={(e) => setDefaultFY(e.target.value)}
                    className="form-input bg-slate-900 border-indigo-500/20 text-white w-full rounded-md"
                  >
                    <option value="2024-2025">2024-2025</option>
                    <option value="2025-2026">2025-2026</option>
                    <option value="2026-2027">2026-2027</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-2">
                    Default Tally Port
                  </label>
                  <input
                    type="text"
                    value={defaultPort}
                    onChange={(e) => setDefaultPort(e.target.value)}
                    className="form-input bg-slate-900 border-indigo-500/20 text-white w-full rounded-md"
                  />
                </div>
              </div>

              <div className="flex items-center gap-3 pt-2">
                <input
                  type="checkbox"
                  id="notifications"
                  checked={emailNotifications}
                  onChange={(e) => setEmailNotifications(e.target.checked)}
                  className="h-4 w-4 rounded border-indigo-500/20 bg-slate-900 text-indigo-600 focus:ring-indigo-500"
                />
                <label htmlFor="notifications" className="text-sm font-medium text-gray-300 flex items-center gap-1.5 cursor-pointer">
                  <Bell className="w-4 h-4 text-gray-500" />
                  Receive weekly audit completion reports via email
                </label>
              </div>
            </div>
          </div>

        </div>

      </div>
    </div>
  );
}
