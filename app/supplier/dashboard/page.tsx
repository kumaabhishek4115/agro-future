'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ApiError, apiGet, apiPost } from '@/lib/apiClient';

type Profile = {
  user_id: string;
  geography: string | null;
  land_size_hectares: number | null;
  crop_or_livestock_type: string | null;
  ownership_status: string | null;
  payout_details_masked: string | null;
  is_complete: boolean;
  completion_percentage: number;
};

type FormState = {
  geography: string;
  land_size_hectares: string;
  crop_or_livestock_type: string;
  ownership_status: string;
  payout_details: string;
};

const EMPTY_FORM: FormState = {
  geography: '',
  land_size_hectares: '',
  crop_or_livestock_type: '',
  ownership_status: '',
  payout_details: '',
};

export default function SupplierDashboardPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const applyProfile = useCallback((p: Profile) => {
    setProfile(p);
    setForm({
      geography: p.geography ?? '',
      land_size_hectares: p.land_size_hectares?.toString() ?? '',
      crop_or_livestock_type: p.crop_or_livestock_type ?? '',
      ownership_status: p.ownership_status ?? '',
      payout_details: '',
    });
  }, []);

  useEffect(() => {
    if (!localStorage.getItem('token')) {
      router.replace('/login');
      return;
    }

    apiGet<Profile>('/supplier/profile')
      .then(applyProfile)
      .catch((e) => {
        if (e instanceof ApiError && e.status === 401) {
          localStorage.removeItem('token');
          router.replace('/login');
        } else if (!(e instanceof ApiError && e.status === 404)) {
          // 404 simply means the profile has not been created yet.
          setError(e instanceof ApiError ? e.message : 'Could not load your profile');
        }
      })
      .finally(() => setLoading(false));
  }, [router, applyProfile]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setNotice('');
    setSaving(true);

    // Send only the fields the farmer filled in; the API accepts partial saves.
    const payload: Record<string, string | number> = {};
    if (form.geography) payload.geography = form.geography;
    if (form.land_size_hectares) payload.land_size_hectares = Number(form.land_size_hectares);
    if (form.crop_or_livestock_type) payload.crop_or_livestock_type = form.crop_or_livestock_type;
    if (form.ownership_status) payload.ownership_status = form.ownership_status;
    if (form.payout_details) payload.payout_details = form.payout_details;

    try {
      applyProfile(await apiPost<Profile>('/supplier/profile', payload));
      setNotice('Profile saved.');
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Network error – please try again');
    } finally {
      setSaving(false);
    }
  }

  function handleLogout() {
    apiPost('/auth/logout', {}).catch(() => undefined);
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    router.replace('/login');
  }

  function update(field: keyof FormState, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  if (loading) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-green-50">
        <p className="text-green-800">Loading your profile…</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-green-50 p-4">
      <div className="mx-auto w-full max-w-2xl">
        <header className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-green-800">Farmer Dashboard</h1>
          <button
            onClick={handleLogout}
            className="text-sm text-green-800 underline hover:text-green-900"
          >
            Log out
          </button>
        </header>

        <section className="bg-white rounded-2xl shadow-md p-6 mb-6">
          <div className="flex items-center justify-between mb-2 text-sm font-medium text-gray-700">
            <span>Profile completion</span>
            <span>{profile?.completion_percentage ?? 0}%</span>
          </div>
          <div className="h-2 w-full rounded-full bg-gray-200">
            <div
              className="h-2 rounded-full bg-green-600 transition-all"
              style={{ width: `${profile?.completion_percentage ?? 0}%` }}
            />
          </div>
          {profile?.is_complete ? (
            <p className="mt-3 text-sm text-green-700">Your profile is complete.</p>
          ) : (
            <p className="mt-3 text-sm text-gray-600">
              Complete every field to finish onboarding. Partial saves are kept.
            </p>
          )}
        </section>

        <section className="bg-white rounded-2xl shadow-md p-6">
          <h2 className="text-lg font-semibold text-green-800 mb-4">Farm details</h2>

          {error && (
            <p className="text-red-600 text-sm bg-red-50 border border-red-200 rounded p-3 mb-4">
              {error}
            </p>
          )}
          {notice && (
            <p className="text-green-700 text-sm bg-green-50 border border-green-200 rounded p-3 mb-4">
              {notice}
            </p>
          )}

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <label className="flex flex-col gap-1 text-sm font-medium text-gray-700">
              Geography
              <input
                type="text"
                value={form.geography}
                onChange={(e) => update('geography', e.target.value)}
                className="border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
                placeholder="Punjab, India"
              />
            </label>

            <label className="flex flex-col gap-1 text-sm font-medium text-gray-700">
              Land size (hectares)
              <input
                type="number"
                min="0"
                step="0.01"
                value={form.land_size_hectares}
                onChange={(e) => update('land_size_hectares', e.target.value)}
                className="border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
                placeholder="12.5"
              />
            </label>

            <label className="flex flex-col gap-1 text-sm font-medium text-gray-700">
              Crop / livestock type
              <input
                type="text"
                value={form.crop_or_livestock_type}
                onChange={(e) => update('crop_or_livestock_type', e.target.value)}
                className="border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
                placeholder="Rice"
              />
            </label>

            <label className="flex flex-col gap-1 text-sm font-medium text-gray-700">
              Ownership status
              <select
                value={form.ownership_status}
                onChange={(e) => update('ownership_status', e.target.value)}
                className="border rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-green-500"
              >
                <option value="">Select…</option>
                <option value="owned">Owned</option>
                <option value="leased">Leased</option>
                <option value="cooperative">Cooperative</option>
              </select>
            </label>

            <label className="flex flex-col gap-1 text-sm font-medium text-gray-700">
              Payout details
              <input
                type="text"
                value={form.payout_details}
                onChange={(e) => update('payout_details', e.target.value)}
                className="border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
                placeholder={profile?.payout_details_masked ?? 'Bank account / UPI'}
              />
              {profile?.payout_details_masked && (
                <span className="text-xs font-normal text-gray-500">
                  Saved: {profile.payout_details_masked} – leave blank to keep unchanged.
                </span>
              )}
            </label>

            <button
              type="submit"
              disabled={saving}
              className="bg-green-700 text-white py-2 rounded-lg hover:bg-green-800 font-medium disabled:opacity-50"
            >
              {saving ? 'Saving…' : 'Save profile'}
            </button>
          </form>
        </section>
      </div>
    </main>
  );
}
