'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ApiError, apiPost } from '@/lib/apiClient';

export default function VerifyEmailPage() {
  const [token, setToken] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  // Prefill from the ?token= link sent in the verification email.
  useEffect(() => {
    const fromLink = new URLSearchParams(window.location.search).get('token');
    if (fromLink) setToken(fromLink);
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await apiPost<{ message: string }>('/auth/verify-email', {
        token: token.trim(),
      });
      setSuccess(data.message);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Network error – please try again');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-green-50 p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-md p-8">
        <h1 className="text-2xl font-bold text-green-800 mb-6">Verify Email</h1>

        {success ? (
          <div className="text-green-700 bg-green-50 border border-green-200 rounded-lg p-4 text-sm">
            {success}
            <div className="mt-4">
              <Link href="/login" className="underline text-green-800 font-medium">
                Go to Login
              </Link>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <p className="text-sm text-gray-600">
              Enter the verification token from your registration email.
            </p>
            {error && (
              <p className="text-red-600 text-sm bg-red-50 border border-red-200 rounded p-3">
                {error}
              </p>
            )}
            <label className="flex flex-col gap-1 text-sm font-medium text-gray-700">
              Verification Token
              <input
                type="text"
                required
                value={token}
                onChange={(e) => setToken(e.target.value)}
                className="border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500 font-mono text-xs"
                placeholder="paste token here"
              />
            </label>
            <button
              type="submit"
              disabled={loading}
              className="bg-green-700 text-white py-2 rounded-lg hover:bg-green-800 font-medium disabled:opacity-50"
            >
              {loading ? 'Verifying…' : 'Verify Email'}
            </button>
          </form>
        )}
      </div>
    </main>
  );
}
