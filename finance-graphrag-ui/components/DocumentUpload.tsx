"use client";

import { useState, useRef } from "react";

export default function DocumentUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [companyName, setCompanyName] = useState("");
  const [fiscalYear, setFiscalYear] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [status, setStatus] = useState<{ type: "success" | "error" | null; message: string }>({
    type: null,
    message: "",
  });
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
      setStatus({ type: null, message: "" });
    }
  };

  // Reset function to clear all state & file inputs
  const handleClear = () => {
    setFile(null);
    setCompanyName("");
    setFiscalYear("");
    setStatus({ type: null, message: "" });
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setStatus({ type: "error", message: "Please select a file to upload." });
      return;
    }

    setIsUploading(true);
    setStatus({ type: null, message: "" });

    const formData = new FormData();
    formData.append("file", file);

    if (companyName.trim()) {
      formData.append("company_name", companyName);
    }
    if (fiscalYear.trim()) {
      formData.append("fiscal_year", fiscalYear);
    }

    try {
      const res = await fetch("http://localhost:8000/api/ingest", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error("Upload failed.");

      setStatus({
        type: "success",
        message: `${file.name} successfully ingested! Processing in background.`,
      });
      
      handleClear(); // Auto-clear after successful upload
      
    } catch (err) {
      setStatus({ type: "error", message: "Failed to connect to the ingestion server." });
    } finally {
      setIsUploading(false);
    }
  };

  const hasFormContent = file || companyName || fiscalYear;

  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-120px)] w-full text-slate-100">
      <div className="max-w-xl w-full bg-slate-900/60 backdrop-blur-sm border border-slate-800 rounded-3xl p-8 shadow-2xl">
        
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-14 h-14 bg-blue-600/20 text-blue-400 rounded-2xl flex items-center justify-center mx-auto mb-4 border border-blue-500/30">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-white">Upload SEC Filing</h2>
          <p className="text-slate-400 text-sm mt-2">
            Upload a 10-K PDF or JSON file to vectorize and ingest into the knowledge graph.
          </p>
        </div>

        <form onSubmit={handleUpload} className="space-y-5">
          {/* File Upload Area */}
          <div 
            className="relative border-2 border-dashed border-slate-700 hover:border-blue-500 bg-slate-800/30 rounded-2xl p-8 text-center transition-colors cursor-pointer group"
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              type="file"
              accept=".pdf, .json, application/pdf, application/json"
              className="hidden"
              ref={fileInputRef}
              onChange={handleFileChange}
            />
            
            {file ? (
              <div className="flex items-center justify-between bg-slate-800 border border-slate-700/80 rounded-xl p-3 text-sm">
                <div className="flex items-center space-x-2 text-blue-400 font-medium truncate pr-2">
                  <svg className="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span className="truncate">{file.name}</span>
                </div>
                
                {/* Quick File Clear Button */}
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation(); // Stop triggering file picker
                    setFile(null);
                    if (fileInputRef.current) fileInputRef.current.value = "";
                  }}
                  className="p-1 hover:bg-slate-700 text-slate-400 hover:text-white rounded-lg transition-colors"
                  title="Remove file"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ) : (
              <div>
                <span className="text-blue-400 font-medium">Click to upload</span>
                <span className="text-slate-500"> or drag and drop</span>
                <p className="text-xs text-slate-500 mt-1">PDF or JSON files only</p>
              </div>
            )}
          </div>

          {/* Optional Metadata Inputs */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-400 pl-1">Company Name (Optional)</label>
              <input
                type="text"
                placeholder="e.g. Apple Inc."
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                className="w-full bg-slate-800/50 border border-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-xl px-4 py-2.5 text-sm text-slate-200 placeholder-slate-500 transition-all outline-none"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-400 pl-1">Fiscal Year (Optional)</label>
              <input
                type="text"
                placeholder="e.g. 2023"
                value={fiscalYear}
                onChange={(e) => setFiscalYear(e.target.value)}
                className="w-full bg-slate-800/50 border border-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-xl px-4 py-2.5 text-sm text-slate-200 placeholder-slate-500 transition-all outline-none"
              />
            </div>
          </div>

          {/* Status Message */}
          {status.type && (
            <div className={`p-3 rounded-xl text-sm text-center ${status.type === "success" ? "bg-green-500/10 text-green-400 border border-green-500/20" : "bg-red-500/10 text-red-400 border border-red-500/20"}`}>
              {status.message}
            </div>
          )}

          {/* Form Action Buttons */}
          <div className="flex space-x-3 pt-2">
            {hasFormContent && (
              <button
                type="button"
                onClick={handleClear}
                disabled={isUploading}
                className="w-1/3 bg-slate-800 hover:bg-slate-700/80 text-slate-300 font-medium py-3 rounded-xl transition-all border border-slate-700/80"
              >
                Clear
              </button>
            )}

            <button
              type="submit"
              disabled={!file || isUploading}
              className={`flex-1 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:hover:bg-blue-600 text-white font-medium py-3 rounded-xl transition-all shadow-lg shadow-blue-900/20 flex items-center justify-center`}
            >
              {isUploading ? (
                <span className="flex items-center space-x-2">
                  <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <span>Processing...</span>
                </span>
              ) : (
                "Ingest Document"
              )}
            </button>
          </div>
        </form>

      </div>
    </div>
  );
}