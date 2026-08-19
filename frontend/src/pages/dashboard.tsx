import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Folder, Globe, CheckCircle, MoreHorizontal, MessageSquare } from "lucide-react";

import { useProjects, useDeleteProject } from "@/hooks/use-projects";
import { useTestRuns } from "@/hooks/use-test-runs";
import { useEndpoints } from "@/hooks/use-endpoints";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DataTable } from "@/components/shared/data-table";
import { PageHeader } from "@/components/layout/page-header";
import { CreateProjectDialog } from "@/components/project/create-project-dialog";
import { ConfirmDeleteDialog } from "@/components/shared/confirm-delete-dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { Column } from "@/components/shared/data-table";
import type { Project } from "@/lib/types";
import { formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";

const STATUS_MAP: Record<number, string> = {
  0: "未启用",
  1: "已启用",
};

/** 图纸角标：四角十字墨线。 */
function CornerMarks() {
  const base = "pointer-events-none absolute h-3 w-3 border-primary";
  return (
    <span aria-hidden="true">
      <span className={cn(base, "left-0 top-0 border-l-2 border-t-2")} />
      <span className={cn(base, "right-0 top-0 border-r-2 border-t-2")} />
      <span className={cn(base, "bottom-0 left-0 border-b-2 border-l-2")} />
      <span className={cn(base, "bottom-0 right-0 border-b-2 border-r-2")} />
    </span>
  );
}

export default function DashboardPage() {
  const [page, setPage] = useState(1);
  const pageSize = 10;

  const { data: projectsData, isLoading: projectsLoading } = useProjects({
    page,
    page_size: pageSize,
  });
  const { data: testRunsData } = useTestRuns();
  const { data: endpointsData } = useEndpoints();
  const deleteProject = useDeleteProject();

  const [deleteTarget, setDeleteTarget] = useState<Project | null>(null);

  const stats = useMemo(() => {
    const runs = testRunsData?.items ?? [];
    const totalProjects = projectsData?.total ?? 0;
    const totalEndpoints = endpointsData?.total ?? 0;

    const avgPassRate =
      runs.length > 0 ? Math.round(runs.reduce((sum, r) => sum + r.pass_rate, 0) / runs.length) : 0;

    return {
      totalProjects,
      totalEndpoints,
      avgPassRate,
    };
  }, [projectsData, testRunsData, endpointsData]);

  const statItems = [
    { label: "项目总数", value: stats.totalProjects, unit: "", icon: Folder },
    { label: "接口总数", value: stats.totalEndpoints, unit: "", icon: Globe },
    { label: "平均通过率", value: stats.avgPassRate, unit: "%", icon: CheckCircle },
  ];

  const columns: Column<Project>[] = [
    {
      key: "name",
      header: "名称",
      render: (_, row) => (
        <Link to={`/projects/${row.id}`} className="font-medium text-accent hover:text-accent/80">
          {row.name}
        </Link>
      ),
    },
    {
      key: "base_url",
      header: "基础 URL",
      render: (_, row) => (
        <span className="font-mono text-xs text-muted-foreground">{row.base_url}</span>
      ),
    },
    {
      key: "description",
      header: "描述",
      render: (_, row) => (
        <span className="font-mono text-xs text-muted-foreground">{row.description}</span>
      ),
    },
    {
      key: "status",
      header: "状态",
      render: (_, row) => (
        <Badge variant={row.status === 1 ? "default" : "secondary"}>
          {STATUS_MAP[row.status] ?? "未知"}
        </Badge>
      ),
    },
    {
      key: "created_at",
      header: "创建时间",
      render: (_, row) => (
        <span className="font-mono text-xs text-muted-foreground">
          {formatDate(row.created_at)}
        </span>
      ),
    },
    {
      key: "id",
      header: "操作",
      className: "w-12",
      render: (_, row) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="shadow-popover" align="end">
            <DropdownMenuItem asChild>
              <Link to={`/projects/${row.id}`}>编辑</Link>
            </DropdownMenuItem>
            <DropdownMenuItem className="text-destructive" onClick={() => setDeleteTarget(row)}>
              删除
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  return (
    <div className="flex flex-col gap-8">
      {/* Hero 标题块：图纸网格 + 四角标 + 注解式页头 */}
      <div className="relative overflow-hidden rounded-[4px] border border-border bg-card p-6 shadow-xs lg:p-8">
        <div className="bg-blueprint-grid absolute inset-0" aria-hidden="true" />
        <CornerMarks />
        <div className="relative">
          <PageHeader
            title="仪表盘"
            annotation="FIG.01 — OVERVIEW"
            description="API 测试项目概览。"
            actions={
              <Button asChild variant="outline">
                <Link to="/workflows/chat">
                  <MessageSquare className="h-4 w-4" />
                  新建对话
                </Link>
              </Button>
            }
          />
        </div>
      </div>

      {/* 统计读数带：mono 读数 + 竖墨线分隔 */}
      <div className="flex flex-col divide-y divide-border-subtle rounded-[4px] border border-border bg-card shadow-xs sm:flex-row sm:divide-x sm:divide-y-0">
        {statItems.map((item) => {
          const Icon = item.icon;
          return (
            <div key={item.label} className="flex flex-1 items-center gap-4 px-6 py-5">
              <div className="rounded-[2px] border border-border bg-surface-primary p-2">
                <Icon className="h-4 w-4 text-primary" />
              </div>
              <div>
                <div className="font-display text-3xl font-semibold tabular-nums tracking-tight text-foreground">
                  {item.value}
                  {item.unit && (
                    <span className="ml-0.5 font-mono text-sm font-normal text-muted-foreground">
                      {item.unit}
                    </span>
                  )}
                </div>
                <div className="mt-0.5 text-xs text-muted-foreground">{item.label}</div>
              </div>
            </div>
          );
        })}
      </div>

      {/* 项目列表 */}
      <div>
        <div className="mb-4 flex items-center justify-between">
          <div>
            <div className="annotation text-primary">FIG.02 — PROJECTS</div>
            <h2 className="font-display text-lg font-semibold text-foreground">项目</h2>
          </div>
          <CreateProjectDialog />
        </div>
        <DataTable
          columns={columns}
          data={projectsData?.items ?? []}
          loading={projectsLoading}
          emptyText="暂无项目，创建一个开始使用吧。"
          pagination={{
            page,
            pageSize,
            total: projectsData?.total ?? 0,
            onChange: setPage,
          }}
        />
      </div>

      <ConfirmDeleteDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
        onConfirm={() => {
          if (deleteTarget) {
            deleteProject.mutate(deleteTarget.id);
            setDeleteTarget(null);
          }
        }}
        title="删除项目"
        description={
          <span>
            确定要删除项目 <strong>{deleteTarget?.name}</strong> 吗？此操作将永久删除所有关联数据，
            包括环境、接口、测试运行、测试用例和报告。{" "}
            <span className="font-semibold text-destructive">此操作无法撤销。</span>
          </span>
        }
        confirmText="删除项目"
      />
    </div>
  );
}
