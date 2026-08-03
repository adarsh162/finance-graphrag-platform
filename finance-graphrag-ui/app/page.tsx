import DocumentUpload from '@/components/DocumentUpload';
import DocumentList from '@/components/DocumentList';

export default function IngestionPage() {
  return (
    <div className="max-w-6xl mx-auto py-8 px-4">
      <h1 className="text-2xl font-bold mb-6 text-white">Knowledge Base Management</h1>
      
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
        <div className="lg:col-span-3">
          <DocumentUpload />
        </div>
        <div className="lg:col-span-2 pt-2">
          <DocumentList />
        </div>
      </div>
    </div>
  );
}