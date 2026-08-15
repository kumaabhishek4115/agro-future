'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ApiError, apiPost } from '@/lib/apiClient';

type TokenResponse = {
  access_token: string;
  token_type: string;
  user_id: string;
  email: string;
  role: string;
};

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await apiPost<TokenResponse>('/auth/login', { email, password });
      // Store JWT in localStorage for MVP (use httpOnly cookies in production)
      localStorage.setItem('token', data.access_token);
      localStorage.setItem(
        'user',
        JSON.stringify({ id: data.user_id, email: data.email, role: data.role }),
      );
      router.push('/supplier/dashboard');
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Network error – please try again');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-green-50 p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-md p-8">
        <h1 className="text-2xl font-bold text-green-800 mb-6">Farmer Login</h1>
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
            Password
            <input
              type="password"
              required
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
            {loading ? 'Logging in…' : 'Log In'}
          </button>
          <div className="flex justify-between text-sm text-gray-600">
            <Link href="/register" className="text-green-700 underline">
              Create account
            </Link>
            <Link href="/verify-email" className="text-green-700 underline">
              Verify email
            </Link>
          </div>
        </form>
      </div>
    </main>
  );
}
