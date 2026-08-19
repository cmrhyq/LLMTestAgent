import { useMemo, useState } from "react";
import { Plus, Search } from "lucide-react";

import { Button } from "@/components/ui/button.tsx";
import { Input } from "@/components/ui/input.tsx";
import { DataTable } from "@/components/shared/data-table.tsx";
import { ConfirmDeleteDialog } from "@/components/shared/confirm-delete-dialog.tsx";
import { buildEndpointColumns } from "../columns";
import type { Endpoint } from "@/lib/types.ts";

export interface EndpointsTabProps {
  data: Endpoint[];
  total: number;
  loading: boolean;
  page: number;
  pageSize: number;
  onPageChange(page: number): void;
  onAdd(): void;
  onEdit(endpoint: Endpoint): void;
  onDelete(endpoint: Endpoint): void;
}

export function EndpointsTab({
  data,
  total,
  loading,
  page,
  pageSize,
  onPageChange,
  onAdd,
  onEdit,
  onDelete,
}: EndpointsTabProps) {
  const [search, setSearch] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<Endpoint | null>(null);

  const filtered = useMemo(() => {
    if (!search.trim()) return data;
    const keyword = search.toLowerCase();
    return data.filter(
      (ep) =>
        ep.name.toLowerCase().includes(keyword) ||
        ep.path.toLowerCase().includes(keyword) ||
        ep.method.toLowerCase().includes(keyword)
    );
  }, [data, search]);

  const columns = buildEndpointColumns({
    onEdit,
    onDelete: (endpoint) => setDeleteTarget(endpoint),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="搜索接口…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Button size="sm" onClick={onAdd}>
          <Plus className="mr-2 h-4 w-4" />
          添加接口
        </Button>
      </div>

      <DataTable
        columns={columns}
        data={filtered}
        loading={loading}
        emptyText="该项目暂无接口。"
        pagination={{
          page,
          pageSize,
          total,
          onChange: onPageChange,
        }}
      />

      <ConfirmDeleteDialog
        open={!!deleteTarget}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
        onConfirm={() => {
          if (deleteTarget) {
            onDelete(deleteTarget);
            setDeleteTarget(null);
          }
        }}
        title="删除接口"
        description={
          <>
            确定要删除接口 <strong>{deleteTarget?.name}</strong> 吗？此操作无法撤销。
          </>
        }
      />
    </div>
  );
}
