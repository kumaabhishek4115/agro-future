'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ApiError, apiPost } from '@/lib/apiClient';

export default function VerifyMobilePage() {
  const [mobileNumber, setMobileNumber] = useState('');
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  // Prefill the number carried over from the registration screen.
  useEffect(() => {
    const fromLink = new URLSearchParams(window.location.search).get('mobile');
    if (fromLink) setMobileNumber(fromLink);
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setNotice('');
    setLoading(true);
    try {
      const data = await apiPost<{ message: string }>('/auth/verify-mobile', {
        mobile_number: mobileNumber.trim(),
        code: code.trim(),
      });
      setSuccess(data.message);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Network error – please try again');
    } finally {
      setLoading(false);
    }
  }

  async function handleResend() {
    setError('');
    setNotice('');
    try {
      const data = await apiPost<{ message: string }>('/auth/resend-mobile-code', {
        mobile_number: mobileNumber.trim(),
      });
      setNotice(data.message);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Network error – please try again');
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-green-50 p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-md p-8">
        <h1 className="text-2xl font-bold text-green-800 mb-6">Verify Mobile Number</h1>

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
              Enter the 6-digit code we sent by SMS.
            </p>
            {error && (
              <p className="text-red-600 text-sm bg-red-50 border border-red-200 rounded p-3">
                {error}
              </p>
            )}
            {notice && (
              <p className="text-green-700 text-sm bg-green-50 border border-green-200 rounded p-3">
                {notice}
              </p>
            )}

            <label className="flex flex-col gap-1 text-sm font-medium text-gray-700">
              Mobile number
              <input
                type="tel"
                required
                value={mobileNumber}
                onChange={(e) => setMobileNumber(e.target.value)}
                className="border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
                placeholder="+919876543210"
              />
            </label>

            <label className="flex flex-col gap-1 text-sm font-medium text-gray-700">
              Verification code
              <input
                type="text"
                required
                inputMode="numeric"
                maxLength={6}
                value={code}
                onChange={(e) => setCode(e.target.value)}
                className="border rounded-lg px-3 py-2 font-mono tracking-widest focus:outline-none focus:ring-2 focus:ring-green-500"
                placeholder="123456"
              />
            </label>

            <button
              type="submit"
              disabled={loading}
              className="bg-green-700 text-white py-2 rounded-lg hover:bg-green-800 font-medium disabled:opacity-50"
            >
              {loading ? 'Verifying…' : 'Verify'}
            </button>

            <button
              type="button"
              onClick={handleResend}
              className="text-sm text-green-700 underline"
            >
              Resend code
            </button>
          </form>
        )}
      </div>
    </main>
  );
}
