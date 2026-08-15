'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ApiError, apiPost } from '@/lib/apiClient';

type RegisterResponse = {
  message: string;
  user_id: string;
  verification_channel: 'email' | 'sms';
  email_verification_token: string | null;
  mobile_verification_code: string | null;
};

type Channel = 'email' | 'sms';

export default function RegisterPage() {
  const [channel, setChannel] = useState<Channel>('email');
  const [email, setEmail] = useState('');
  const [mobileNumber, setMobileNumber] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<RegisterResponse | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);

    const mobile = mobileNumber.trim();
    const payload =
      channel === 'email'
        ? { email: email.trim(), password, ...(mobile ? { mobile_number: mobile } : {}) }
        : { mobile_number: mobile, password };

    try {
      setResult(await apiPost<RegisterResponse>('/auth/register', payload));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Network error – please try again');
    } finally {
      setLoading(false);
    }
  }

  const tabClass = (value: Channel) =>
    `flex-1 py-2 text-sm font-medium rounded-lg ${
      channel === value ? 'bg-green-700 text-white' : 'bg-gray-100 text-gray-700'
    }`;

  return (
    <main className="min-h-screen flex items-center justify-center bg-green-50 p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-md p-8">
        <h1 className="text-2xl font-bold text-green-800 mb-6">Farmer Registration</h1>

        {result ? (
          <div className="text-green-700 bg-green-50 border border-green-200 rounded-lg p-4 text-sm">
            {result.message}

            {result.verification_channel === 'email' && result.email_verification_token && (
              <>
                <p className="mt-3 font-medium text-gray-700">Dev verification token:</p>
                <code className="mt-1 block break-all select-all bg-white border rounded p-2 font-mono text-xs text-gray-800">
                  {result.email_verification_token}
                </code>
                <div className="mt-4 flex gap-4">
                  <Link
                    href={`/verify-email?token=${encodeURIComponent(result.email_verification_token)}`}
                    className="underline text-green-800 font-medium"
                  >
                    Verify now
                  </Link>
                  <Link href="/login" className="underline text-green-800 font-medium">
                    Go to Login
                  </Link>
                </div>
              </>
            )}

            {result.verification_channel === 'sms' && (
              <>
                <p className="mt-3 font-medium text-gray-700">Dev SMS code:</p>
                <code className="mt-1 block select-all bg-white border rounded p-2 font-mono text-lg tracking-widest text-gray-800">
                  {result.mobile_verification_code}
                </code>
                <div className="mt-4 flex gap-4">
                  <Link
                    href={`/verify-mobile?mobile=${encodeURIComponent(mobileNumber.trim())}`}
                    className="underline text-green-800 font-medium"
                  >
                    Enter code
                  </Link>
                  <Link href="/login" className="underline text-green-800 font-medium">
                    Go to Login
                  </Link>
                </div>
              </>
            )}
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setChannel('email')}
                className={tabClass('email')}
              >
                Sign up with email
              </button>
              <button
                type="button"
                onClick={() => setChannel('sms')}
                className={tabClass('sms')}
              >
                Sign up with mobile
              </button>
            </div>

            {error && (
              <p className="text-red-600 text-sm bg-red-50 border border-red-200 rounded p-3">
                {error}
              </p>
            )}

            {channel === 'email' ? (
              <>
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
                  Mobile number (optional – can be used to log in)
                  <input
                    type="tel"
                    value={mobileNumber}
                    onChange={(e) => setMobileNumber(e.target.value)}
                    className="border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
                    placeholder="+919876543210"
                  />
                </label>
              </>
            ) : (
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
                <span className="text-xs font-normal text-gray-500">
                  We&apos;ll text you a 6-digit code to confirm this number.
                </span>
              </label>
            )}

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
