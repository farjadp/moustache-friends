import { useState, useEffect } from "react";
import { BarChart3, Users, MessageSquare, RefreshCw } from "lucide-react";
import { fetchStats, type Stats } from "../api";

export default function StatsPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const data = await fetchStats();
      setStats(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-white">📊 آمار</h2>
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
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 flex items-center gap-4">
            <div className="w-12 h-12 bg-blue-600/20 rounded-xl flex items-center justify-center">
              <MessageSquare size={22} className="text-blue-400" />
            </div>
            <div>
              <p className="text-gray-400 text-sm">کل سوالات</p>
              <p className="text-3xl font-bold text-white mt-1">{stats?.total_questions ?? 0}</p>
            </div>
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 flex items-center gap-4">
            <div className="w-12 h-12 bg-purple-600/20 rounded-xl flex items-center justify-center">
              <Users size={22} className="text-purple-400" />
            </div>
            <div>
              <p className="text-gray-400 text-sm">کاربران منحصربه‌فرد</p>
              <p className="text-3xl font-bold text-white mt-1">{stats?.unique_users ?? 0}</p>
            </div>
          </div>

          <div className="md:col-span-2 bg-gray-900 border border-gray-800 rounded-xl p-6 flex items-center gap-4">
            <div className="w-12 h-12 bg-green-600/20 rounded-xl flex items-center justify-center">
              <BarChart3 size={22} className="text-green-400" />
            </div>
            <div>
              <p className="text-gray-400 text-sm">میانگین سوال به ازای هر کاربر</p>
              <p className="text-3xl font-bold text-white mt-1">
                {stats && stats.unique_users > 0
                  ? (stats.total_questions / stats.unique_users).toFixed(1)
                  : "0"}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
