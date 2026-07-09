import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Folder, Globe, CheckCircle, MoreHorizontal, Play } from "lucide-react";

import { useProjects, useDeleteProject } from "@/hooks/use-projects";
import { useTestRuns } from "@/hooks/use-test-runs";
import { useEndpoints } from "@/hooks/use-endpoints";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DataTable } from "@/components/shared/data-table";
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

const STATUS_MAP: Record<number, string> = {
  0: "未启用",
  1: "已启用",
};

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
    const projects = projectsData?.items ?? [];
    const runs = testRunsData?.items ?? [];
    const totalEndpoints = endpointsData?.total ?? 0;

    const avgPassRate =
      runs.length > 0 ? Math.round(runs.reduce((sum, r) => sum + r.pass_rate, 0) / runs.length) : 0;

    return {
      totalProjects: projects.length,
      totalEndpoints,
      avgPassRate,
    };
  }, [projectsData, testRunsData, endpointsData]);

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
        <span className="text-sm text-muted-foreground">
          {new Date(row.created_at).toLocaleDateString()}
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
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">仪表盘</h1>
        <p className="mt-1 text-sm text-muted-foreground">API 测试项目概览。</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">项目总数</CardTitle>
            <div className="rounded-lg bg-surface-accent p-2">
              <Folder className="h-4 w-4 text-accent" />
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold tracking-tight">{stats.totalProjects}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">接口总数</CardTitle>
            <div className="rounded-lg bg-surface-primary p-2">
              <Globe className="h-4 w-4 text-primary" />
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold tracking-tight">{stats.totalEndpoints}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">平均通过率</CardTitle>
            <div className="rounded-lg bg-surface-success p-2">
              <CheckCircle className="h-4 w-4 text-success" />
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold tracking-tight">{stats.avgPassRate}%</p>
          </CardContent>
        </Card>
      </div>

      <div>
        <h2 className="mb-3 text-lg font-semibold text-foreground">快捷操作</h2>
        <div className="flex gap-3">
          <Button asChild variant="outline">
            <Link to="/workflows/run">
              <Play className="mr-2 h-4 w-4" />
              新建测试
            </Link>
          </Button>
        </div>
      </div>

      <div>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-foreground">项目</h2>
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
