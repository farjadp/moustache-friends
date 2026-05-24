import { useState, useEffect } from "react";
import { RefreshCw, MessageSquare, User } from "lucide-react";
import { fetchLogs, type ChatLog } from "../api";

export default function LogsPage() {
  const [logs, setLogs] = useState<ChatLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<number | null>(null);

  const load = async () => {
    try {
      const data = await fetchLogs(50);
      setLogs(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-white">💬 سوالات کاربران</h2>
        <button
          onClick={load}
          className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
        >
          <RefreshCw size={14} />
          بروزرسانی
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <RefreshCw size={24} className="text-gray-500 animate-spin" />
        </div>
      ) : logs.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <MessageSquare size={48} className="mx-auto mb-3 opacity-30" />
          <p>هنوز سوالی ثبت نشده</p>
        </div>
      ) : (
        <div className="space-y-3">
          {logs.map((log) => (
            <div
              key={log.id}
              className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden"
            >
              <button
                className="w-full text-right px-4 py-3 flex items-start justify-between gap-3 hover:bg-gray-800/30 transition-colors"
                onClick={() => setExpanded(expanded === log.id ? null : log.id)}
              >
                <div className="flex items-start gap-3 flex-1 min-w-0">
                  <div className="w-8 h-8 bg-gray-800 rounded-full flex items-center justify-center shrink-0 mt-0.5">
                    <User size={14} className="text-gray-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-blue-400 text-sm font-medium">
                        {log.username ? `@${log.username}` : log.user_id}
                      </span>
                      <span className="text-gray-600 text-xs">
                        {new Date(log.created_at).toLocaleString("fa-IR")}
                      </span>
                    </div>
                    <p className="text-gray-200 text-sm truncate">{log.question}</p>
                  </div>
                </div>
                <span className="text-gray-600 text-xs mt-1 shrink-0">
                  {expanded === log.id ? "▲" : "▼"}
                </span>
              </button>

              {expanded === log.id && (
                <div className="px-4 pb-4 border-t border-gray-800">
                  <div className="pt-3 space-y-3">
                    <div>
                      <p className="text-xs text-gray-500 mb-1">سوال:</p>
                      <p className="text-gray-300 text-sm bg-gray-800/50 rounded-lg p-3">{log.question}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 mb-1">پاسخ:</p>
                      <p className="text-gray-300 text-sm bg-blue-900/20 border border-blue-900/30 rounded-lg p-3 whitespace-pre-wrap">
                        {log.answer}
                      </p>
                    </div>
                    {log.sources && (
                      <div>
                        <p className="text-xs text-gray-500 mb-1">منابع استفاده شده:</p>
                        <p className="text-green-400 text-xs">{log.sources}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
