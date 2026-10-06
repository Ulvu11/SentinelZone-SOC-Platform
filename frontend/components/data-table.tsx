export interface Column<T> {
  key: string;
  header: string;
  render: (item: T) => React.ReactNode;
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  onRowClick?: (item: T) => void;
  keyExtractor: (item: T) => string;
}

export function DataTable<T>({
  columns,
  data,
  onRowClick,
  keyExtractor,
}: DataTableProps<T>) {
  return (
    <div className="max-w-full overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-soc-line">
            {columns.map((col) => (
              <th
                key={col.key}
                className={`text-left text-xs font-medium text-soc-muted uppercase tracking-wider px-4 py-3 ${col.className ?? ""}`}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-soc-line">
          {data.length === 0 && (
            <tr>
              <td
                colSpan={columns.length}
                className="p-8 text-center text-soc-muted"
              >
                No records match the current selection.
              </td>
            </tr>
          )}
          {data.map((item) => (
            <tr
              key={keyExtractor(item)}
              className={`text-soc-text hover:bg-soc-surface transition-colors ${
                onRowClick ? "cursor-pointer" : ""
              }`}
              tabIndex={onRowClick ? 0 : undefined}
              onKeyDown={
                onRowClick
                  ? (event) => {
                      if (
                        event.target === event.currentTarget &&
                        (event.key === "Enter" || event.key === " ")
                      ) {
                        event.preventDefault();
                        onRowClick(item);
                      }
                    }
                  : undefined
              }
              onClick={
                onRowClick
                  ? (event) => {
                      if (
                        !(event.target as HTMLElement).closest(
                          "a,button,input,select",
                        )
                      )
                        onRowClick(item);
                    }
                  : undefined
              }
            >
              {columns.map((col) => (
                <td
                  key={col.key}
                  className={`px-4 py-3 ${col.className ?? ""}`}
                >
                  {col.render(item)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
