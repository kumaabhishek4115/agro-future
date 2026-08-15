'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ApiError, apiPost } from '@/lib/apiClient';

type RegisterResponse = {
  message: string;
  user_id: string;
  email_verification_token: string;
};

export default function RegisterPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await apiPost<RegisterResponse>('/auth/register', { email, password });
      setSuccess(`${data.message} (Dev token: ${data.email_verification_token})`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Network error – please try again');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-green-50 p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-md p-8">
        <h1 className="text-2xl font-bold text-green-800 mb-6">
          Farmer Registration
        </h1>

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
            {error && (
              <p className="text-red-600 text-sm bg-red-50 border border-red-200 rounded p-3">
                {error}
              </p>
            )}
            <label className="flex flex-col gap-1 text-sm font-medium text-gray-700">
              Email
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
                placeholder="you@example.com"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm font-medium text-gray-700">
              Password (min 8 characters)
              <input
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
              />
            </label>
            <button
              type="submit"
              disabled={loading}
              className="bg-green-700 text-white py-2 rounded-lg hover:bg-green-800 font-medium disabled:opacity-50"
            >
              {loading ? 'Creating account…' : 'Create Account'}
            </button>
            <p className="text-sm text-center text-gray-600">
              Already have an account?{' '}
              <Link href="/login" className="text-green-700 underline">
                Log in
              </Link>
            </p>
          </form>
        )}
      </div>
    </main>
  );
}
