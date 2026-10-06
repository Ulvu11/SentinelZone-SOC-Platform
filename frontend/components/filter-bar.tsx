"use client";

import { Search, X } from "lucide-react";

export interface FilterOption {
  label: string;
  value: string;
}

interface FilterBarProps {
  searchPlaceholder?: string;
  filters?: {
    key: string;
    label: string;
    options: FilterOption[];
  }[];
  onSearchChange?: (value: string) => void;
  onFilterChange?: (key: string, value: string) => void;
  searchValue?: string;
  activeFilters?: Record<string, string>;
}

export function FilterBar({
  searchPlaceholder = "Search...",
  filters = [],
  onSearchChange,
  onFilterChange,
  searchValue = "",
  activeFilters = {},
}: FilterBarProps) {
  const localSearch = searchValue;

  const handleSearchChange = (val: string) => {
    onSearchChange?.(val);
  };

  return (
    <div className="flex flex-wrap items-center gap-3 mb-4">
      <div className="relative flex-1 min-w-[200px] max-w-sm">
        <Search
          size={14}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-soc-muted"
        />
        <input
          type="text"
          aria-label={searchPlaceholder}
          placeholder={searchPlaceholder}
          value={localSearch}
          onChange={(e) => handleSearchChange(e.target.value)}
          className="w-full pl-9 pr-8 py-2 text-sm bg-soc-surface border border-soc-line rounded-lg text-soc-text placeholder:text-soc-muted focus:outline-none focus:border-soc-accent"
        />
        {localSearch && (
          <button
            aria-label="Clear search"
            onClick={() => handleSearchChange("")}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-soc-muted hover:text-soc-text"
          >
            <X size={14} />
          </button>
        )}
      </div>
      {filters.map((filter) => (
        <select
          key={filter.key}
          aria-label={filter.label}
          value={activeFilters[filter.key] ?? ""}
          onChange={(e) => onFilterChange?.(filter.key, e.target.value)}
          className="px-3 py-2 text-sm bg-soc-surface border border-soc-line rounded-lg text-soc-text focus:outline-none focus:border-soc-accent appearance-none cursor-pointer"
        >
          <option value="">{filter.label}</option>
          {filter.options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      ))}
    </div>
  );
}
