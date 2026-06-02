// client/src/components/DocumentModal.jsx
import { useState } from 'react';
import { X, UploadCloud, Link as LinkIcon, Loader2, FileText, Trash2, Database, CheckCircle2, AlertCircle } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast'; // 🔥 NAYA IMPORT

export default function DocumentModal({ agent, onClose }) {
  const [activeTab, setActiveTab] = useState('file'); 
  const [file, setFile] = useState(null);
  const [url, setUrl] = useState('');
  
  const [isProcessing, setIsProcessing] = useState(false);
  const queryClient = useQueryClient();

  // ==========================================
  // 🔥 FETCH DOCUMENTS
  // ==========================================
  const { data: documents = [], isLoading: loadingDocs, isError } = useQuery({
    queryKey: ['documents', agent.id], 
    queryFn: async () => {
      const res = await fetch(`http://localhost:8000/agents/${agent.id}/documents`);
      if (!res.ok) throw new Error('Network response was not ok');
      const data = await res.json();
      return data.documents || [];
    },
    refetchInterval: (query) => {
      const docs = query.state?.data || [];
      const isAnyProcessing = docs.some(d => d.status === 'processing');
      return isAnyProcessing ? 3000 : false; 
    }
  });

  // ==========================================
  // 🔥 DELETE DOCUMENT
  // ==========================================
  const deleteMutation = useMutation({
    mutationFn: async (docId) => {
      const res = await fetch(`http://localhost:8000/documents/${docId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete');
      return docId;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents', agent.id] });
      toast.success('Document removed! 🗑️'); // 🔥 TOAST
    },
    onError: () => {
      toast.error("Failed to delete document."); // 🔥 TOAST
    }
  });

  const handleDeleteDoc = (docId) => {
    const isConfirmed = window.confirm("Delete this document? The agent will forget this information permanently.");
    if (isConfirmed) deleteMutation.mutate(docId);
  };

  // --- UPLOAD HANDLERS ---
  const handleFileUpload = async (e) => {
    e.preventDefault();
    if (!file) return;
    setIsProcessing(true);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('agent_id', agent.id);

    try {
      const res = await fetch('http://localhost:8000/process-file', {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Upload failed');

      setFile(null); 
      queryClient.invalidateQueries({ queryKey: ['documents', agent.id] });
      toast.success(data.message || 'File uploaded successfully! ⚙️'); // 🔥 TOAST
    } catch (error) {
      toast.error('Upload Error: ' + error.message); // 🔥 TOAST
    } finally {
      setIsProcessing(false);
    }
  };

  const handleUrlSubmit = async (e) => {
    e.preventDefault();

    const trimmedUrl = url.trim();
    if (!trimmedUrl) return;

    try {
      new URL(trimmedUrl);
    } catch {
      toast.error("Please enter a valid URL.");
      return;
    }

    setIsProcessing(true);

    try {
      const res = await fetch('http://localhost:8000/process-url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_id: agent.id, url: trimmedUrl }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'URL processing failed');

      setUrl(''); 
      queryClient.invalidateQueries({ queryKey: ['documents', agent.id] });
      toast.success(data.message || 'URL successfully scraped! 🌐'); // 🔥 TOAST
    } catch (error) {
      toast.error('Scraping Error: ' + error.message); // 🔥 TOAST
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-gray-900/60 backdrop-blur-sm flex items-center justify-center z-50 p-4 sm:p-6">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-5xl overflow-hidden flex flex-col h-[85vh]">
        
        {/* Header */}
        <div className="px-8 py-5 border-b border-gray-200 flex justify-between items-center bg-white shrink-0">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Knowledge Base Manager</h2>
            <p className="text-sm text-gray-500 mt-1">Manage data sources for <span className="font-semibold text-indigo-600">{agent.name}</span></p>
          </div>
          <button onClick={onClose} className="p-2.5 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-full transition-colors">
            <X size={24} />
          </button>
        </div>

        <div className="flex flex-col md:flex-row flex-1 overflow-hidden">
          {/* LEFT SIDE */}
          <div className="w-full md:w-4/12 border-r border-gray-200 bg-gray-50/30 flex flex-col overflow-y-auto">
            <div className="flex border-b border-gray-200 bg-white">
              <button onClick={() => { setActiveTab('file'); }} className={`flex-1 py-4 text-sm font-semibold border-b-2 flex justify-center items-center gap-2 transition-colors ${activeTab === 'file' ? 'border-indigo-600 text-indigo-600 bg-indigo-50/30' : 'border-transparent text-gray-500 hover:bg-gray-50 hover:text-gray-700'}`}>
                <FileText size={18} /> Upload File
              </button>
              <button onClick={() => { setActiveTab('url'); }} className={`flex-1 py-4 text-sm font-semibold border-b-2 flex justify-center items-center gap-2 transition-colors ${activeTab === 'url' ? 'border-indigo-600 text-indigo-600 bg-indigo-50/30' : 'border-transparent text-gray-500 hover:bg-gray-50 hover:text-gray-700'}`}>
                <LinkIcon size={18} /> Paste Link
              </button>
            </div>

            <div className="p-6">
              {activeTab === 'file' ? (
                <form onSubmit={handleFileUpload} className="space-y-6">
                  <div className="border-2 border-dashed border-indigo-200 rounded-2xl p-10 text-center hover:bg-indigo-50/50 hover:border-indigo-300 transition-colors bg-white shadow-sm">
                    <input type="file" accept=".pdf,.txt,.docx,.csv" onChange={(e) => setFile(e.target.files[0])} className="hidden" id="file-upload" />
                    <label htmlFor="file-upload" className="cursor-pointer flex flex-col items-center">
                      <div className="w-16 h-16 bg-indigo-100 text-indigo-600 rounded-full flex items-center justify-center mb-4"><UploadCloud size={32} /></div>
                      <span className="text-base font-semibold text-gray-900 mb-1 px-4 text-center">{file ? file.name : 'Click to browse files'}</span>
                      <span className="text-sm text-gray-500 mt-1">{file ? `${(file.size / (1024 * 1024)).toFixed(2)} MB` : 'Supports: PDF, TXT, DOCX, CSV'}</span>
                    </label>
                  </div>
                  <button type="submit" disabled={!file || isProcessing} className="w-full flex justify-center items-center gap-2 py-3.5 px-4 rounded-xl text-base font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 disabled:text-gray-500 transition-all shadow-md hover:shadow-lg disabled:shadow-none">
                    {isProcessing ? <><Loader2 size={18} className="animate-spin" /> Ingesting to RAG...</> : 'Process Document'}
                  </button>
                </form>
              ) : (
                <form onSubmit={handleUrlSubmit} className="space-y-6">
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">Webpage URL</label>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                        <LinkIcon size={18} className="text-gray-400" />
                      </div>
                      <input type="url" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://example.com/blog..." className="w-full pl-11 pr-4 py-3.5 bg-white border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none text-sm shadow-sm transition-shadow" required />
                    </div>
                  </div>
                  <button type="submit" disabled={!url || isProcessing} className="w-full flex justify-center items-center gap-2 py-3.5 px-4 rounded-xl text-base font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 disabled:text-gray-500 transition-all shadow-md hover:shadow-lg disabled:shadow-none">
                    {isProcessing ? <><Loader2 size={18} className="animate-spin" /> Scraping Webpage...</> : 'Extract Text & Learn'}
                  </button>
                </form>
              )}
            </div>
          </div>

          {/* RIGHT SIDE */}
          <div className="w-full md:w-8/12 bg-gray-50 flex flex-col overflow-y-auto">
            <div className="px-8 py-5 border-b border-gray-200 flex justify-between items-center bg-white sticky top-0 z-10 shadow-sm">
              <h3 className="text-base font-bold text-gray-800">Indexed Sources</h3>
              <span className="text-sm font-semibold bg-indigo-50 text-indigo-700 px-3 py-1 rounded-full border border-indigo-100">{documents.length} sources active</span>
            </div>
            
            <div className="p-6 flex-1">
              {loadingDocs ? (
                <div className="flex justify-center items-center h-40"><Loader2 size={32} className="animate-spin text-indigo-500" /></div>
              ) : isError ? (
                <div className="text-center py-10 text-red-500">Failed to load documents.</div>
              ) : documents.length === 0 ? (
                <div className="text-center py-20 bg-white border-2 border-dashed border-gray-200 rounded-2xl mx-4">
                  <Database size={48} className="mx-auto text-gray-300 mb-4" />
                  <h4 className="text-lg font-medium text-gray-900 mb-1">Knowledge base is empty</h4>
                  <p className="text-sm text-gray-500 max-w-sm mx-auto">Upload a file or paste a link from the left panel to start training your agent.</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-4">
                  {documents.map((doc) => (
                    <div key={doc.id} className="bg-white border border-gray-200 rounded-xl p-4 flex items-center justify-between shadow-sm hover:shadow-md transition-all group">
                      <div className="flex items-center gap-4 overflow-hidden pr-4">
                        <div className={`p-3 rounded-xl flex-shrink-0 ${doc.filename.startsWith('http') ? 'bg-blue-50 text-blue-600' : 'bg-rose-50 text-rose-600'}`}>
                          {doc.filename.startsWith('http') ? <LinkIcon size={20} /> : <FileText size={20} />}
                        </div>
                        <div className="min-w-0">
                          <p className="text-base font-medium text-gray-900 truncate" title={doc.filename}>{doc.filename}</p>
                          <div className="flex items-center gap-3 mt-1.5">
                            {doc.status === 'processing' ? (
                              <span className="inline-flex items-center gap-1.5 text-[11px] uppercase tracking-wider font-bold text-amber-600 bg-amber-50 px-2 py-1 rounded-md border border-amber-200"><Loader2 size={12} className="animate-spin" /> Processing</span>
                            ) : doc.status === 'failed' ? (
                              <span className="inline-flex items-center gap-1.5 text-[11px] uppercase tracking-wider font-bold text-red-600 bg-red-50 px-2 py-1 rounded-md border border-red-200"><AlertCircle size={12} /> Failed</span>
                            ) : (
                              <span className="inline-flex items-center gap-1.5 text-[11px] uppercase tracking-wider font-bold text-emerald-600 bg-emerald-50 px-2 py-1 rounded-md border border-emerald-200"><CheckCircle2 size={12} /> Embedded</span>
                            )}
                            <span className="text-xs text-gray-400 font-medium">ID: #{doc.id}</span>
                          </div>
                        </div>
                      </div>
                      <button 
                        onClick={() => handleDeleteDoc(doc.id)} 
                        disabled={deleteMutation.isPending}
                        className="p-2.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-xl transition-colors shrink-0 opacity-0 group-hover:opacity-100 focus:opacity-100 disabled:opacity-50"
                        title="Delete Source"
                      >
                        {deleteMutation.isPending && deleteMutation.variables === doc.id ? <Loader2 size={20} className="animate-spin text-red-500" /> : <Trash2 size={20} />}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}