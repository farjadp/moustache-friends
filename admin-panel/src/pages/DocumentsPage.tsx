import { useState, useEffect, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import toast from "react-hot-toast";
import {
  Upload, Trash2, FileText, Music, Video, File, RefreshCw, CheckCircle, XCircle, Clock
} from "lucide-react";
import { fetchDocuments, deleteDocument, uploadDocument, fetchDocumentStatus, type Document } from "../api";

function formatBytes(bytes: number) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

function FileIcon({ type }: { type: string }) {
  if (type === "pdf" || type === "docx" || type === "text") return <FileText size={16} className="text-blue-400" />;
  if (type === "audio") return <Music size={16} className="text-purple-400" />;
  if (type === "video") return <Video size={16} className="text-pink-400" />;
  return <File size={16} className="text-gray-400" />;
}

function StatusBadge({ status }: { status: Document["status"] }) {
  if (status === "ready") return (
    <span className="flex items-center gap-1 text-green-400 text-xs">
      <CheckCircle size={12} /> آماده
    </span>
  );
  if (status === "processing") return (
    <span className="flex items-center gap-1 text-yellow-400 text-xs animate-pulse">
      <Clock size={12} /> در حال پردازش
    </span>
  );
  return (
    <span className="flex items-center gap-1 text-red-400 text-xs">
      <XCircle size={12} /> خطا
    </span>
  );
}

export default function DocumentsPage() {
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [processingIds, setProcessingIds] = useState<Set<number>>(new Set());

  const load = async () => {
    try {
      const data = await fetchDocuments();
      setDocs(data);
      const processing = new Set(data.filter((d) => d.status === "processing").map((d) => d.id));
      setProcessingIds(processing);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (processingIds.size === 0) return;
    const interval = setInterval(async () => {
      const updates = await Promise.all([...processingIds].map((id) => fetchDocumentStatus(id)));
      let changed = false;
      const newProcessing = new Set(processingIds);
      updates.forEach((u) => {
        if (u.status !== "processing") {
          newProcessing.delete(u.id);
          changed = true;
        }
      });
      if (changed) {
        setProcessingIds(newProcessing);
        load();
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [processingIds]);

  const onDrop = useCallback(async (files: File[]) => {
    for (const file of files) {
      setUploading(true);
      setUploadProgress(0);
      try {
        const result = await uploadDocument(file, setUploadProgress);
        toast.success(`✅ ${file.name} آپلود شد`);
        setProcessingIds((prev) => new Set([...prev, result.data.id]));
        await load();
      } catch (err: unknown) {
        const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "خطا در آپلود";
        toast.error(`❌ ${msg}`);
      } finally {
        setUploading(false);
      }
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "text/plain": [".txt", ".md"],
      "audio/*": [".mp3", ".wav", ".ogg", ".m4a", ".opus"],
      "video/*": [".mp4", ".mkv", ".avi", ".mov"],
    },
    maxFiles: 5,
  });

  const handleDelete = async (doc: Document) => {
    if (!confirm(`آیا مطمئن هستید که می‌خواهید "${doc.filename}" را حذف کنید؟`)) return;
    try {
      await deleteDocument(doc.id);
      toast.success("✅ فایل حذف شد");
      await load();
    } catch {
      toast.error("❌ خطا در حذف فایل");
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-white">📚 پایگاه دانش</h2>
        <button
          onClick={load}
          className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
        >
          <RefreshCw size={14} />
          بروزرسانی
        </button>
      </div>

      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors ${
          isDragActive
            ? "border-blue-500 bg-blue-500/10"
            : "border-gray-700 hover:border-gray-500 bg-gray-900/50"
        }`}
      >
        <input {...getInputProps()} />
        <Upload size={36} className="mx-auto mb-3 text-gray-500" />
        {uploading ? (
          <div className="space-y-2">
            <p className="text-gray-300">در حال آپلود... {uploadProgress}%</p>
            <div className="w-full bg-gray-700 rounded-full h-2 max-w-xs mx-auto">
              <div
                className="bg-blue-500 h-2 rounded-full transition-all"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
          </div>
        ) : isDragActive ? (
          <p className="text-blue-400 font-medium">فایل را اینجا رها کنید...</p>
        ) : (
          <>
            <p className="text-gray-300 font-medium">فایل را اینجا بکشید یا کلیک کنید</p>
            <p className="text-gray-500 text-sm mt-1">PDF، Word، TXT، MP3، MP4 و...</p>
          </>
        )}
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <RefreshCw size={24} className="text-gray-500 animate-spin" />
        </div>
      ) : docs.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <File size={48} className="mx-auto mb-3 opacity-30" />
          <p>هیچ فایلی آپلود نشده</p>
        </div>
      ) : (
        <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-gray-400">
                <th className="text-right px-4 py-3 font-medium">نام فایل</th>
                <th className="text-right px-4 py-3 font-medium">نوع</th>
                <th className="text-right px-4 py-3 font-medium">حجم</th>
                <th className="text-right px-4 py-3 font-medium">بخش‌ها</th>
                <th className="text-right px-4 py-3 font-medium">وضعیت</th>
                <th className="text-right px-4 py-3 font-medium">آپلود توسط</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {docs.map((doc) => (
                <tr key={doc.id} className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <FileIcon type={doc.file_type} />
                      <span className="text-gray-200 truncate max-w-[200px]" title={doc.filename}>
                        {doc.filename}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-400 uppercase text-xs">{doc.file_type}</td>
                  <td className="px-4 py-3 text-gray-400">{formatBytes(doc.file_size)}</td>
                  <td className="px-4 py-3 text-gray-400">{doc.chunk_count || "—"}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={doc.status} />
                    {doc.error_message && (
                      <p className="text-red-400 text-xs mt-1 max-w-[150px] truncate" title={doc.error_message}>
                        {doc.error_message}
                      </p>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{doc.uploaded_by || "web"}</td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleDelete(doc)}
                      className="text-gray-600 hover:text-red-400 transition-colors p-1"
                    >
                      <Trash2 size={15} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
