import React, { useRef } from 'react';
import { X, Printer, Download } from 'lucide-react';

export default function InvoicePreviewModal({ isOpen, onClose, invoice, onDownload }) {
  if (!isOpen || !invoice) return null;

  const printRef = useRef();

  const handlePrint = () => {
    const printContent = printRef.current.innerHTML;
    const originalContent = document.body.innerHTML;
    
    document.body.innerHTML = `
      <style>
        @media print {
          body { background: white !important; color: black !important; padding: 20px; }
          .no-print { display: none !important; }
        }
      </style>
      <div>${printContent}</div>
    `;
    window.print();
    document.body.innerHTML = originalContent;
    window.location.reload(); 
  };

  const meta = invoice.invoice_metadata || invoice.metadata || {};
  const isPaid = invoice.status === "Paid";

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 backdrop-blur-sm p-4 sm:p-6 overflow-hidden text-slate-800"
      style={{ colorScheme: 'light' }}
    >
      <div className="!bg-slate-100 border border-slate-300 shadow-2xl rounded-xl w-full max-w-4xl max-h-[95vh] flex flex-col relative animate-in fade-in zoom-in duration-200">
        
        {/* Controls */}
        <div className="flex shrink-0 justify-between items-center px-6 py-4 !bg-white border-b border-slate-200 no-print z-10 shadow-sm rounded-t-xl">
          <span className="text-xs font-bold !text-slate-400 uppercase tracking-wider">Receipt Preview</span>
          <div className="flex items-center gap-2">
            <button onClick={handlePrint} className="inline-flex items-center gap-1.5 px-3 py-1.5 hover:!bg-slate-100 !text-slate-700 text-xs font-semibold rounded-lg transition">
              <Printer size={14} /> Print
            </button>
            <button onClick={() => onDownload(invoice.id || invoice.invoiceDbId, invoice.invoice_number || invoice.invoiceId)} className="inline-flex items-center gap-1.5 px-3 py-1.5 hover:!bg-slate-100 !text-slate-700 text-xs font-semibold rounded-lg transition">
              <Download size={14} /> Download PDF
            </button>
            <div className="w-px h-4 !bg-slate-200 mx-1"></div>
            <button onClick={onClose} className="p-1.5 !text-slate-400 hover:!text-slate-700 hover:!bg-slate-100 rounded-lg transition">
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Paper Area */}
        <div className="flex-1 overflow-y-auto p-4 md:p-8 flex justify-center custom-scrollbar">
          <div 
            ref={printRef} 
            className="!bg-white border !border-slate-200 shadow-[0_8px_30px_rgb(0,0,0,0.08)] w-full max-w-3xl p-10 md:p-14 !text-slate-900 font-sans selection:bg-slate-100 my-auto shrink-0"
            style={{ backgroundColor: '#ffffff', color: '#0f172a' }}
          >
            <div className="space-y-12">
              
              <div className="flex justify-between items-start">
                <div className="flex items-center gap-3 text-left">
                  <img 
                    src="https://www.blinkbot.in/logo1.png" 
                    alt="BlinkBot Logo" 
                    className="w-10 h-10 rounded-lg shadow-sm border !border-slate-100"
                  />
                  <div>
                    <h2 className="text-xl font-bold tracking-tight !text-slate-900">BlinkBot</h2>
                    <span className="text-[10px] font-bold !text-slate-400 tracking-widest uppercase">Tax Invoice</span>
                  </div>
                </div>
                
                <div className="text-right">
                  <div className="text-[10px] !text-slate-400 font-bold uppercase tracking-widest">Invoice Number</div>
                  <div className="text-sm font-mono font-bold !text-slate-900 mt-1">{invoice.invoice_number || invoice.invoiceId}</div>
                  <div className="mt-3">
                    <span className={`inline-flex items-center px-3 py-1 rounded-full text-[10px] tracking-wider font-bold ${
                      isPaid ? '!bg-emerald-50 !text-emerald-700 border !border-emerald-200' : '!bg-amber-50 !text-amber-700 border !border-amber-200'
                    }`}>
                      {invoice.status ? invoice.status.toUpperCase() : "PAID"}
                    </span>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4 border !border-slate-200 !bg-slate-50 p-5 rounded-lg text-xs font-medium text-left">
                <div>
                  <span className="!text-slate-500 uppercase tracking-widest block text-[9px] font-bold">Date Issued</span>
                  <span className="!text-slate-900 font-bold mt-1.5 block">
                    {new Date(invoice.created_at || invoice.date).toLocaleDateString(undefined, {
                      year: 'numeric', month: 'short', day: 'numeric'
                    })}
                  </span>
                </div>
                <div>
                  <span className="!text-slate-500 uppercase tracking-widest block text-[9px] font-bold">Payment Method</span>
                  <span className="!text-slate-900 font-bold mt-1.5 block">Razorpay Payments</span>
                </div>
                {meta.razorpay_payment_id && (
                  <div>
                    <span className="!text-slate-500 uppercase tracking-widest block text-[9px] font-bold">Transaction ID</span>
                    <span className="!text-slate-900 font-mono font-bold mt-1.5 block truncate max-w-[150px]" title={meta.razorpay_payment_id}>
                      {meta.razorpay_payment_id}
                    </span>
                  </div>
                )}
              </div>

              <div className="grid grid-cols-2 gap-8 text-left">
                <div>
                  <h4 className="text-[10px] font-bold !text-slate-400 uppercase tracking-widest mb-3">Billed By</h4>
                  <div className="space-y-1.5 text-xs">
                    <p className="font-bold !text-slate-900">BlinkBot Technologies Pvt Ltd</p>
                    <p className="!text-slate-500">Bengaluru, Karnataka, India</p>
                    <p className="!text-slate-500">support@blinkbot.in · www.blinkbot.in</p>
                  </div>
                </div>
                
                <div>
                  <h4 className="text-[10px] font-bold !text-slate-400 uppercase tracking-widest mb-3">Billed To</h4>
                  <div className="space-y-1.5 text-xs">
                    {invoice.user_email && <p className="font-bold !text-slate-900">{invoice.user_email}</p>}
                    <p className="font-mono text-[10px] !text-slate-500 leading-relaxed">
                      ID: {invoice.user_id || "Customer Account"}
                    </p>
                  </div>
                </div>
              </div>

              <div className="space-y-3 pt-2 text-left">
                <h4 className="text-[10px] font-bold !text-slate-400 uppercase tracking-widest">Line Items</h4>
                <div className="border !border-slate-200 rounded-lg overflow-hidden !bg-white">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="border-b !border-slate-200 !bg-slate-50 !text-slate-500 uppercase text-[9px] tracking-widest font-bold">
                        <th className="px-5 py-4">Item Description</th>
                        <th className="px-5 py-4 text-right">Amount</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y !divide-slate-100 !bg-white">
                      <tr>
                        <td className="px-5 py-5">
                          <div className="font-bold !text-slate-900 text-sm">{invoice.description}</div>
                          
                          <div className="space-y-1 mt-2 text-[10px] !text-slate-500">
                            {meta.credits && <p>Credits Loaded: <span className="font-medium !text-slate-700">+{parseInt(meta.credits).toLocaleString()}</span></p>}
                            {meta.base_inr && <p>Base Price: INR {parseFloat(meta.base_inr).toFixed(2)}</p>}
                            {meta.discount_percent && parseFloat(meta.discount_percent) > 0 && (
                              <p className="!text-emerald-600 font-medium">
                                Bulk Discount ({meta.discount_percent}%): -INR {parseFloat(meta.discount_amount).toFixed(2)}
                              </p>
                            )}
                          </div>
                        </td>
                        <td className="px-5 py-5 text-right font-bold !text-slate-900 text-sm align-top">
                          INR {(invoice.amount_inr || parseFloat(invoice.amount?.replace('₹', '') || 0)).toFixed(2)}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="flex justify-end pt-4">
                <div className="w-1/2">
                  <div className="flex justify-between items-center border-t-2 !border-slate-900 pt-4">
                    <span className="text-[10px] font-bold !text-slate-900 uppercase tracking-widest">Total Paid</span>
                    <span className="text-2xl font-black !text-slate-900 tracking-tight">
                      INR {(invoice.amount_inr || parseFloat(invoice.amount?.replace('₹', '') || 0)).toFixed(2)}
                    </span>
                  </div>
                </div>
              </div>

              <div className="mt-16 pt-6 border-t !border-slate-100 text-center flex flex-col items-center justify-center gap-2">
                <div className="w-8 h-8 rounded-full !bg-emerald-50 flex items-center justify-center mx-auto">
                  <svg className="!text-emerald-500 w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <span className="text-[10px] !text-slate-400 font-bold uppercase tracking-widest">Payment Processed Successfully</span>
              </div>

            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
