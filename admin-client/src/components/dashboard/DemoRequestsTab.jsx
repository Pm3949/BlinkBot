import React, { useState } from 'react';
import { X } from 'lucide-react';

export default function DemoRequestsTab({
  demoRequestsData,
  demoRequestsLoading,
  updateDemoStatusMutation,
  requirePassword,
  scheduleMeetingMutation,
}) {
  return (
    <div className="border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden bg-white dark:bg-slate-900 shadow-sm">
      <div className="p-6 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
        <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">Demo Requests</h2>
        <span className="text-xs font-semibold px-2.5 py-1 bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-100 dark:border-indigo-900 text-indigo-600 dark:text-indigo-400 rounded-full">
          {demoRequestsData?.requests?.length || 0} Total
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="text-xs uppercase font-semibold text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-800/40 border-b border-slate-200 dark:border-slate-800">
            <tr>
              <th className="px-6 py-4">Requester</th>
              <th className="px-6 py-4">Company</th>
              <th className="px-6 py-4">Message</th>
              <th className="px-6 py-4">Status</th>
              <th className="px-6 py-4">Date</th>
              <th className="px-6 py-4">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {demoRequestsLoading && (
              <tr>
                <td colSpan={6} className="p-6">
                  <div className="animate-pulse bg-slate-100 dark:bg-slate-800 rounded-md h-12 w-full"></div>
                </td>
              </tr>
            )}
            {!demoRequestsLoading && (!demoRequestsData?.requests || demoRequestsData.requests.length === 0) && (
              <tr>
                <td colSpan={6} className="p-12 text-center text-slate-400 dark:text-slate-500 font-medium text-sm">
                  No demo requests found.
                </td>
              </tr>
            )}
            {demoRequestsData?.requests?.map((req) => (
              <tr key={req.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/30 transition-colors">
                <td className="px-6 py-4">
                  <div className="font-bold text-slate-900 dark:text-slate-100">{req.name}</div>
                  <div className="text-slate-500 dark:text-slate-400 text-xs">{req.email}</div>
                </td>
                <td className="px-6 py-4 text-slate-600 dark:text-slate-300">{req.company || '-'}</td>
                <td className="px-6 py-4 text-slate-500 dark:text-slate-400 max-w-[200px] truncate" title={req.message}>
                  {req.message || '-'}
                </td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                    req.status === 'completed' ? 'bg-green-500/10 text-green-500 border border-green-500/20' :
                    req.status === 'processing' ? 'bg-blue-500/10 text-blue-500 border border-blue-500/20' :
                    'bg-yellow-500/10 text-yellow-500 border border-yellow-500/20'
                  }`}>
                    {req.status}
                  </span>
                </td>
                <td className="px-6 py-4 text-slate-500 dark:text-slate-400">
                  {new Date(req.created_at).toLocaleDateString()}
                </td>
                <td className="px-6 py-4 flex items-center gap-2">
                  <select
                    className="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs rounded px-2 py-1 font-semibold text-slate-700 dark:text-slate-300 disabled:opacity-50"
                    value={req.status}
                    disabled={updateDemoStatusMutation.isPending}
                    onChange={(e) => requirePassword((pwd) => updateDemoStatusMutation.mutate({ requestId: req.id, newStatus: e.target.value, password: pwd }))}
                  >
                    <option value="pending">Pending</option>
                    <option value="processing">Processing</option>
                    <option value="completed">Completed</option>
                  </select>
                  <ScheduleMeetingButton 
                    requestId={req.id} 
                    requirePassword={requirePassword} 
                    scheduleMeetingMutation={scheduleMeetingMutation} 
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ScheduleMeetingButton({ requestId, requirePassword, scheduleMeetingMutation }) {
  const [modalOpen, setModalOpen] = useState(false);
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");
  const [meetingLink, setMeetingLink] = useState("");

  const handleSchedule = (e) => {
    e.preventDefault();
    setModalOpen(false);
    requirePassword((pwd) => {
      scheduleMeetingMutation.mutate({ requestId, date, time, meeting_link: meetingLink, password: pwd });
    });
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setModalOpen(true)}
        className="px-3 py-1 bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600 text-white text-xs font-semibold rounded transition"
      >
        Schedule
      </button>

      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/80 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 rounded-xl w-full max-w-sm shadow-2xl relative">
            <button 
              onClick={() => setModalOpen(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-slate-900 dark:hover:text-slate-100"
            >
              <X size={20} />
            </button>
            <h3 className="text-lg font-bold mb-1 text-slate-900 dark:text-slate-50">Schedule Meeting</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">Provide a meeting link which will be emailed to the user.</p>
            <form onSubmit={handleSchedule} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Date</label>
                <input
                  type="date"
                  required
                  className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-4 py-2 text-sm text-slate-900 dark:text-slate-100"
                  value={date}
                  onChange={e => setDate(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Time (e.g. 10:00 AM EST)</label>
                <input
                  type="text"
                  required
                  placeholder="10:00 AM EST"
                  className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-4 py-2 text-sm text-slate-900 dark:text-slate-100"
                  value={time}
                  onChange={e => setTime(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Meeting Link</label>
                <input
                  type="url"
                  required
                  placeholder="https://meet.google.com/..."
                  className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-4 py-2 text-sm text-slate-900 dark:text-slate-100"
                  value={meetingLink}
                  onChange={e => setMeetingLink(e.target.value)}
                />
              </div>
              <div className="flex justify-end gap-2 mt-6">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 text-slate-700 dark:text-slate-300 font-medium text-sm transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-750 dark:bg-indigo-500 dark:hover:bg-indigo-600 text-white font-medium text-sm transition"
                >
                  Confirm & Send
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
