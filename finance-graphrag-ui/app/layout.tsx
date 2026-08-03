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
        </nav>

        <main className="flex-1 flex flex-col">
          {children}
        </main>
      </body>
    </html>
  );
}