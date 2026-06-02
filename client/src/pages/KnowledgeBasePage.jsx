import { useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import {
  UploadCloud,
  Search,
  Globe,
  FileText,
  Filter,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Trash2,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useAgents } from "../hooks/useAgents";
import {
  useDeleteDocument,
  useDocuments,
  useProcessUrl,
  useUploadDocument,
} from "../hooks/useDocuments";
import LoadingSkeleton from "../components/shared/LoadingSkeleton";

function getDocumentSource(document) {
  return document.filename || document.source || "Untitled";
}

function getDocumentType(document) {
  const source = getDocumentSource(document);

  if (source.startsWith("http")) return "Website";

  const extension = source
    .split(".")
    .pop()
    ?.toUpperCase();

  return extension && extension !== source.toUpperCase()
    ? extension
    : "Document";
}

function formatDate(value) {
  if (!value) return "Not available";

  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value));
}

function StatusBadge({ status }) {
  if (status === "completed") {
    return (
      <span
        className="
        inline-flex
        items-center
        gap-2
        px-3
        py-1
        rounded-full
        bg-green-50
        text-green-700
      "
      >
        <CheckCircle2 size={14} />
        Completed
      </span>
    );
  }

  if (status === "failed") {
    return (
      <span
        className="
        inline-flex
        items-center
        gap-2
        px-3
        py-1
        rounded-full
        bg-red-50
        text-red-700
      "
      >
        <AlertCircle size={14} />
        Failed
      </span>
    );
  }

  return (
    <span
      className="
      inline-flex
      items-center
      gap-2
      px-3
      py-1
      rounded-full
      bg-amber-50
      text-amber-700
    "
    >
      <Loader2
        size={14}
        className="animate-spin"
      />
      Processing
    </span>
  );
}

export default function KnowledgeBasePage() {
  const fileInputRef = useRef(null);
  const { user } = useAuth();
  const {
    data: agents = [],
    isLoading: isLoadingAgents,
  } = useAgents(user?.id);
  const [activeAgentId, setActiveAgentId] =
    useState("");
  const [url, setUrl] = useState("");
  const [searchTerm, setSearchTerm] =
    useState("");

  const selectedAgentId =
    activeAgentId || agents[0]?.id || "";

  const {
    data: documents = [],
    isError,
    isLoading,
    error,
  } = useDocuments(selectedAgentId);

  const uploadMutation =
    useUploadDocument(selectedAgentId);
  const processUrlMutation =
    useProcessUrl(selectedAgentId);
  const deleteMutation =
    useDeleteDocument(selectedAgentId);

  const filteredDocuments = useMemo(() => {
    const normalizedSearch =
      searchTerm.trim().toLowerCase();

    if (!normalizedSearch) return documents;

    return documents.filter((document) =>
      getDocumentSource(document)
        .toLowerCase()
        .includes(normalizedSearch),
    );
  }, [documents, searchTerm]);

  const isMutating =
    uploadMutation.isPending ||
    processUrlMutation.isPending ||
    deleteMutation.isPending;

  const handleFileChange = async (event) => {
    const file = event.target.files?.[0];

    if (!file) return;

    if (!selectedAgentId) {
      toast.error("Select an agent before uploading.");
      return;
    }

    try {
      await uploadMutation.mutateAsync({
        agentId: selectedAgentId,
        file,
      });
      toast.success("File uploaded for processing");
    } catch (uploadError) {
      toast.error(
        uploadError.message ||
          "Unable to upload file.",
      );
    } finally {
      event.target.value = "";
    }
  };

  const handleProcessUrl = async () => {
    const trimmedUrl = url.trim();

    if (!selectedAgentId) {
      toast.error("Select an agent before scraping.");
      return;
    }

    if (!trimmedUrl) {
      toast.error("Enter a website URL.");
      return;
    }

    try {
      await processUrlMutation.mutateAsync({
        agentId: selectedAgentId,
        url: trimmedUrl,
      });
      setUrl("");
      toast.success("Website queued for processing");
    } catch (urlError) {
      toast.error(
        urlError.message ||
          "Unable to process website.",
      );
    }
  };

  const handleDelete = async (documentId) => {
    try {
      await deleteMutation.mutateAsync(documentId);
      toast.success("Document deleted");
    } catch (deleteError) {
      toast.error(
        deleteError.message ||
          "Unable to delete document.",
      );
    }
  };

  return (
    <div className="p-10">
      <div className="mb-10">
        <h1 className="text-4xl font-bold text-slate-900">
          Knowledge Base
        </h1>

        <p className="text-slate-500 mt-2">
          Upload documents, scrape websites and manage
          your AI knowledge sources.
        </p>
      </div>

      <div className="grid lg:grid-cols-12 gap-6">
        <div className="lg:col-span-4">
          <div className="bg-white border border-slate-200 rounded-[32px] p-6 shadow-sm">
            <h3 className="font-semibold text-lg mb-6">
              Upload Sources
            </h3>

            <label className="font-medium block mb-3">
              Agent
            </label>

            <select
              value={selectedAgentId}
              onChange={(event) =>
                setActiveAgentId(event.target.value)
              }
              disabled={isLoadingAgents || agents.length === 0}
              className="
              w-full
              border
              border-slate-200
              rounded-2xl
              px-4
              py-4
              mb-6
            "
            >
              {agents.length === 0 ? (
                <option value="">
                  No agents available
                </option>
              ) : (
                agents.map((agent) => (
                  <option
                    key={agent.id}
                    value={agent.id}
                  >
                    {agent.name}
                  </option>
                ))
              )}
            </select>

            <div
              className="
              border-2
              border-dashed
              border-indigo-200
              rounded-[28px]
              h-[280px]
              flex
              flex-col
              items-center
              justify-center
              text-center
              bg-indigo-50/40
            "
            >
              <div className="h-16 w-16 rounded-full bg-indigo-100 flex items-center justify-center">
                <UploadCloud
                  size={30}
                  className="text-indigo-600"
                />
              </div>

              <h4 className="font-semibold text-lg mt-5">
                Drop files here
              </h4>

              <p className="text-slate-500 mt-2">
                PDF, DOCX, TXT, CSV
              </p>

              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.txt,.csv"
                className="hidden"
                onChange={handleFileChange}
              />

              <button
                onClick={() =>
                  fileInputRef.current?.click()
                }
                disabled={!selectedAgentId || isMutating}
                className="
                mt-5
                px-5
                py-3
                rounded-2xl
                bg-indigo-600
                text-white
                disabled:opacity-60
              "
              >
                {uploadMutation.isPending
                  ? "Uploading..."
                  : "Browse Files"}
              </button>
            </div>

            <div className="mt-6">
              <label className="font-medium block mb-3">
                Website URL
              </label>

              <div className="relative">
                <Globe
                  size={18}
                  className="
                  absolute
                  left-4
                  top-4
                  text-slate-400
                "
                />

                <input
                  value={url}
                  onChange={(event) =>
                    setUrl(event.target.value)
                  }
                  placeholder="https://example.com"
                  className="
                  w-full
                  border
                  border-slate-200
                  rounded-2xl
                  pl-12
                  py-4
                "
                />
              </div>

              <button
                onClick={handleProcessUrl}
                disabled={!selectedAgentId || isMutating}
                className="
                w-full
                mt-4
                py-3
                rounded-2xl
                border
                border-slate-200
                disabled:opacity-60
              "
              >
                {processUrlMutation.isPending
                  ? "Scraping..."
                  : "Scrape Website"}
              </button>
            </div>
          </div>
        </div>

        <div className="lg:col-span-8">
          <div className="bg-white border border-slate-200 rounded-[32px] shadow-sm overflow-hidden">
            <div className="p-6 border-b border-slate-200">
              <div className="flex flex-wrap gap-4">
                <div className="relative flex-1">
                  <Search
                    size={18}
                    className="
                    absolute
                    left-4
                    top-4
                    text-slate-400
                  "
                  />

                  <input
                    value={searchTerm}
                    onChange={(event) =>
                      setSearchTerm(event.target.value)
                    }
                    placeholder="Search knowledge..."
                    className="
                    w-full
                    border
                    border-slate-200
                    rounded-2xl
                    pl-12
                    py-4
                  "
                  />
                </div>

                <button
                  className="
                  px-4
                  py-3
                  rounded-2xl
                  border
                  border-slate-200
                  flex
                  items-center
                  gap-2
                "
                >
                  <Filter size={16} />
                  Filters
                </button>
              </div>
            </div>

            {isError && (
              <div className="m-6 rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
                {error?.message ||
                  "Unable to load documents."}
              </div>
            )}

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-left border-b border-slate-200">
                    <th className="px-6 py-4 text-sm font-semibold">
                      Source
                    </th>

                    <th className="px-6 py-4 text-sm font-semibold">
                      Type
                    </th>

                    <th className="px-6 py-4 text-sm font-semibold">
                      Status
                    </th>

                    <th className="px-6 py-4 text-sm font-semibold">
                      Added
                    </th>

                    <th className="px-6 py-4"></th>
                  </tr>
                </thead>

                <tbody>
                  {isLoading && (
                    <tr>
                      <td
                        colSpan={5}
                        className="px-6 py-6"
                      >
                        <LoadingSkeleton
                          count={3}
                          className="h-16"
                        />
                      </td>
                    </tr>
                  )}

                  {!isLoading &&
                    filteredDocuments.length === 0 && (
                      <tr>
                        <td
                          colSpan={5}
                          className="px-6 py-10 text-center text-sm text-slate-500"
                        >
                          {selectedAgentId
                            ? "No documents found."
                            : "Select an agent to view documents."}
                        </td>
                      </tr>
                    )}

                  {!isLoading &&
                    filteredDocuments.map((document) => (
                      <tr
                        key={document.id}
                        className="
                        border-b
                        border-slate-100
                        hover:bg-slate-50
                      "
                      >
                        <td className="px-6 py-5">
                          <div className="flex items-center gap-3">
                            <FileText size={18} />

                            <span>
                              {getDocumentSource(document)}
                            </span>
                          </div>
                        </td>

                        <td className="px-6 py-5">
                          {getDocumentType(document)}
                        </td>

                        <td className="px-6 py-5">
                          <StatusBadge
                            status={document.status}
                          />
                        </td>

                        <td className="px-6 py-5">
                          {formatDate(document.created_at)}
                        </td>

                        <td className="px-6 py-5">
                          <button
                            onClick={() =>
                              handleDelete(document.id)
                            }
                            disabled={deleteMutation.isPending}
                            className="
                            p-2
                            rounded-xl
                            hover:bg-red-50
                            hover:text-red-600
                            disabled:opacity-60
                          "
                          >
                            <Trash2 size={16} />
                          </button>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
