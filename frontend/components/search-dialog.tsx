"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Search, X, ArrowUpRight } from "lucide-react";
import { api } from "@/lib/api";
import type { SearchResult } from "@/types";
export function SearchDialog({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const request = useRef(0);
  useEffect(() => {
    if (open) dialog.current?.showModal();
    else dialog.current?.close();
  }, [open]);
  const search = async (value: string) => {
    setQuery(value);
    setError("");
    const version = ++request.current;
    if (value.trim().length < 2) {
      setResults([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const data = await api.search(value.trim());
      if (version === request.current) setResults(data);
    } catch {
      if (version === request.current) {
        setResults([]);
        setError("Search is unavailable. Please try again.");
      }
    } finally {
      if (version === request.current) setLoading(false);
    }
  };
  return (
    <dialog
      ref={dialog}
      aria-labelledby="search-title"
      onCancel={onClose}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      className="search-dialog"
    >
      <div className="flex items-center gap-3 border-b border-soc-line p-4">
        <Search size={18} />
        <h2 id="search-title" className="sr-only">
          Global search
        </h2>
        <input
          autoFocus
          aria-label="Search SOC entities"
          placeholder="IP, hostname, user, process, hash, incident ID…"
          value={query}
          onChange={(e) => void search(e.target.value)}
          className="min-w-0 flex-1 bg-transparent text-sm"
        />
        <button
          onClick={onClose}
          aria-label="Close search"
          className="icon-button"
        >
          <X size={18} />
        </button>
      </div>
      <div className="max-h-[55vh] overflow-y-auto p-2" aria-live="polite">
        {loading ? (
          <p role="status" className="p-6 text-sm text-soc-muted">
            Searching records…
          </p>
        ) : error ? (
          <p role="alert" className="p-6 text-soc-danger">
            {error}
          </p>
        ) : results.length ? (
          results.map((result) => (
            <Link
              key={result.id}
              href={result.href}
              onClick={onClose}
              className="flex items-center gap-3 rounded-md p-3 hover:bg-soc-surface"
            >
              <div className="min-w-0 flex-1">
                <div className="break-all text-sm font-medium">
                  {result.label}
                </div>
                <div className="text-xs text-soc-muted">
                  {result.description}
                </div>
              </div>
              <span className="badge uppercase">{result.type}</span>
              <ArrowUpRight size={14} />
            </Link>
          ))
        ) : (
          <p className="p-6 text-center text-sm text-soc-muted">
            {query.trim().length < 2
              ? "Type at least 2 characters to search all SOC entities."
              : "No matching records. Try another indicator."}
          </p>
        )}
      </div>
      <div className="border-t border-soc-line px-4 py-3 text-xs text-soc-muted">
        Tab to navigate results · Enter to open · Esc to close
      </div>
    </dialog>
  );
}
