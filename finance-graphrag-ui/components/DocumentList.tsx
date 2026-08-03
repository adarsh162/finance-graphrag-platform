"use client";

import { useState, useEffect } from "react";

interface Document {
  id: string;
  name: string;
  uploadDate: string;
  status: "completed" | "processing" | "failed";
}

export default function DocumentList() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchDocuments = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/documents");
      if (res.ok) {
        const data = await res.json();
        setDocuments(data.documents);
      }
    } catch (error) {
      console.error("Failed to fetch documents", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleDelete = async (id: string) => {
    // Optimistic UI update
    setDocuments((prev) => prev.filter((doc) => doc.id !== id));
    
    try {
      const res = await fetch(`http://localhost:8000/api/documents/${id}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Deletion failed");
    } catch (error) {
      console.error("Failed to delete document", error);
      fetchDocuments(); // Revert on failure
    }
  };

  if (isLoading) {
    return <div className="text-slate-400 text-sm">Loading documents...</div>;
  }

  return (
    <div className="w-full bg-slate-900/60 backdrop-blur-sm border border-slate-800 rounded-3xl p-6 shadow-2xl">
      <h3 className="text-lg font-bold text-white mb-4">Ingested Documents</h3>
      
      {documents.length === 0 ? (
        <p className="text-slate-500 text-sm">No documents ingested yet.</p>
      ) : (
        <ul className="space-y-3">
          {documents.map((doc) => (
            <li key={doc.id} className="flex items-center justify-between bg-slate-800/50 border border-slate-700/50 rounded-xl p-3">
              <div className="flex flex-col overflow-hidden">
                <span className="text-slate-200 text-sm font-medium truncate">{doc.name}</span>
                <span className="text-slate-500 text-xs mt-0.5">
                  {new Date(doc.uploadDate).toLocaleDateString()} • {doc.status}
                </span>
              </div>
              
              <button
                onClick={() => handleDelete(doc.id)}
                className="ml-3 p-2 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors shrink-0"
                title="Delete Document"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}