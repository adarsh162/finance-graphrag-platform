// components/DocumentUpload.tsx
'use client';

import { useState } from 'react';

export default function DocumentUpload() {
    const [company, setCompany] = useState('');
    const [year, setYear] = useState('');
    const [file, setFile] = useState<File | null>(null);
    const [isUploading, setIsUploading] = useState(false);
    const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if(!file) return;
        // if (!file || !company.trim() || !year.trim()) return;

        setIsUploading(true);
        setStatusMessage(null);

        // Prepare multipart form data for FastAPI
        const formData = new FormData();
        if(company.trim()){
            formData.append('company_name', company);
        }
        if(year.trim()){
            formData.append('fiscal_year', year);
        }
        formData.append('file', file);

        try {
            const response = await fetch('http://localhost:8000/api/ingest', {
                method: 'POST',
                body: formData,
            });

            const data = await response.json();

            if (response.ok) {
                setStatusMessage({
                    type: 'success',
                    text: `Ingestion started for ${company} (${year}). Chunks and graph entities are processing in the background.`
                });
                // Reset form fields
                setCompany('');
                setYear('');
                setFile(null);
            } else {
                setStatusMessage({
                    type: 'error',
                    text: data.detail || 'Failed to upload document.'
                });
            }
        } catch (error) {
            console.error('Upload Error:', error);
            setStatusMessage({
                type: 'error',
                text: 'Could not connect to the ingestion API.'
            });
        } finally {
            setIsUploading(false);
        }
    };

    return (
        <div className="w-full max-w-3xl mx-auto border rounded-lg p-6 bg-white shadow-sm mb-8">
            <h2 className="text-xl font-semibold text-gray-800 mb-4">
                Ingest SEC 10-K Filing
            </h2>
            
            <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Company Name
                        </label>
                        <input
                            type="text"
                            placeholder="e.g., Apple Inc."
                            value={company}
                            onChange={(e) => setCompany(e.target.value)}
                            className="w-full p-2.5 border rounded-lg focus:ring-2 focus:ring-blue-500 text-gray-800"
                            
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Fiscal Year
                        </label>
                        <input
                            type="text"
                            placeholder="e.g., 2026"
                            value={year}
                            onChange={(e) => setYear(e.target.value)}
                            className="w-full p-2.5 border rounded-lg focus:ring-2 focus:ring-blue-500 text-gray-800"
                            
                        />
                    </div>
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        Select 10-K PDF Document
                    </label>
                    <input
                        type="file"
                        accept=".pdf, .json, application/pdf, application/json"
                        onChange={(e) => setFile(e.target.files?.[0] || null)}
                        className="w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 cursor-pointer"
                        required
                    />
                </div>

                <button
                    type="submit"
                    disabled={isUploading || !file}
                    className="w-full py-3 bg-gray-900 text-white font-medium rounded-lg hover:bg-gray-800 transition disabled:opacity-50"
                >
                    {isUploading ? 'Processing & Uploading...' : 'Upload & Process Filing'}
                </button>
            </form>

            {statusMessage && (
                <div className={`mt-4 p-3 rounded-lg text-sm ${
                    statusMessage.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
                }`}>
                    {statusMessage.text}
                </div>
            )}
        </div>
    );
}