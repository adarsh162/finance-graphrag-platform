import Link from 'next/link';
import './globals.css';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-950 text-slate-100 min-h-screen flex flex-col antialiased">
        {/* Sleek Dark Header */}
        <nav className="flex space-x-6 border-b border-slate-800/80 px-8 py-3.5 bg-slate-900/60 backdrop-blur-md sticky top-0 z-50">
          <Link 
            href="/" 
            className="text-slate-300 hover:text-white font-medium text-sm transition-colors flex items-center gap-2"
          >
            📄 Ingestion
          </Link>
          <Link 
            href="/chat" 
            className="text-slate-300 hover:text-white font-medium text-sm transition-colors flex items-center gap-2"
          >
            💬 Chat
          </Link>
          <Link 
            href="/observability" 
            className="flex items-center gap-3 px-4 py-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 002 2h2a2 2 0 002-2z" />
            </svg>
            <span>Observability</span>
          </Link>
        </nav>

        <main className="flex-1 flex flex-col">
          {children}
        </main>
      </body>
    </html>
  );
}