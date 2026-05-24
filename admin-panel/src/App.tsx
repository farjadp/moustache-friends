import { useState } from "react";
import { Toaster } from "react-hot-toast";
import { BookOpen, MessageSquare, BarChart3 } from "lucide-react";
import DocumentsPage from "./pages/DocumentsPage";
import LogsPage from "./pages/LogsPage";
import StatsPage from "./pages/StatsPage";

type Page = "documents" | "logs" | "stats";

export default function App() {
  const [page, setPage] = useState<Page>("documents");

  const navItems: { id: Page; label: string; icon: React.ReactNode }[] = [
    { id: "documents", label: "پایگاه دانش", icon: <BookOpen size={18} /> },
    { id: "logs", label: "سوالات کاربران", icon: <MessageSquare size={18} /> },
    { id: "stats", label: "آمار", icon: <BarChart3 size={18} /> },
  ];

  return (
    <div className="min-h-screen flex flex-col" dir="rtl">
      <Toaster position="top-center" toastOptions={{ style: { fontFamily: "Vazirmatn" } }} />

      <header className="bg-gray-900 border-b border-gray-800 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold text-sm">
            🤖
          </div>
          <h1 className="text-lg font-bold text-white">پنل مدیریت ربات تلگرام</h1>
        </div>
        <nav className="flex gap-1">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setPage(item.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                page === item.id
                  ? "bg-blue-600 text-white"
                  : "text-gray-400 hover:text-white hover:bg-gray-800"
              }`}
            >
              {item.icon}
              {item.label}
            </button>
          ))}
        </nav>
      </header>

      <main className="flex-1 p-6">
        {page === "documents" && <DocumentsPage />}
        {page === "logs" && <LogsPage />}
        {page === "stats" && <StatsPage />}
      </main>
    </div>
  );
}
