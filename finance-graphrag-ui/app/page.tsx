// app/page.tsx
import DocumentUpload from '../components/DocumentUpload';
import ChatWindow from '../components/ChatWindow';

export default function Home() {
    return (
        <main className="min-h-screen bg-gray-100 flex flex-col items-center py-12 px-4">
            <div className="w-full max-w-4xl space-y-8">
                
                {/* Header */}
                <div className="text-center space-y-2">
                    <h1 className="text-4xl font-bold text-gray-900 tracking-tight">
                        Enterprise Finance GraphRAG
                    </h1>
                    <p className="text-gray-600 text-lg">
                        Real-time AI analysis of SEC 10-K filings using LangGraph, PGVector, and Neo4j.
                    </p>
                </div>
                
                {/* Ingestion Section */}
                <DocumentUpload />

                {/* Live Chat Section */}
                <ChatWindow />
                
            </div>
        </main>
    );
}