import Link from 'next/link';

export default function HomePage() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-6 p-8 bg-green-50">
      <h1 className="text-4xl font-bold text-green-800">Agro Future</h1>
      <p className="text-lg text-green-700 text-center max-w-xl">
        Farmer Carbon Credit Marketplace – connecting sustainable farmers with
        carbon credit buyers.
      </p>
      <div className="flex gap-4">
        <Link
          href="/register"
          className="px-6 py-3 bg-green-700 text-white rounded-lg hover:bg-green-800 font-medium"
        >
          Register as Farmer
        </Link>
        <Link
          href="/login"
          className="px-6 py-3 border-2 border-green-700 text-green-700 rounded-lg hover:bg-green-100 font-medium"
        >
          Log In
        </Link>
      </div>
    </main>
  );
}
