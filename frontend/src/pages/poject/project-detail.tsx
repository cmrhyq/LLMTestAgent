import { useState, useMemo } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { Search, Globe, Plus, MoreHorizontal, Pencil, Trash2 } from "lucide-react";

import { useProject } from "@/hooks/use-projects.ts";
import { useEndpoints, useDeleteEndpoint } from "@/hooks/use-endpoints.ts";
import { useEnvironments, useDeleteEnvironment } from "@/hooks/use-environments.ts";
import { useTestRuns } from "@/hooks/use-test-runs.ts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card.tsx";
import { Button } from "@/components/ui/button.tsx";
import { Badge } from "@/components/ui/badge.tsx";
import { Input } from "@/components/ui/input.tsx";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs.tsx";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu.tsx";
import { DataTable } from "@/components/shared/data-table.tsx";
import { StatusBadge } from "@/components/shared/status-badge.tsx";
import { HttpMethodBadge } from "@/components/shared/http-method-badge.tsx";
import { PassRateBar } from "@/components/shared/pass-rate-bar.tsx";
import { EmptyState } from "@/components/shared/empty-state.tsx";
import { ConfirmDeleteDialog } from "@/components/shared/confirm-delete-dialog.tsx";
import { EndpointFormDialog } from "@/components/endpoint/endpoint-form-dialog.tsx";
import { EnvironmentFormDialog } from "@/components/environment/environment-form-dialog.tsx";
import type { Column } from "@/components/shared/data-table.tsx";
import type { Endpoint, Environment, TestRun } from "@/lib/types.ts";

const PROJECT_STATUS_MAP: Record<number, string> = {
  0: "未启用",
  1: "已启用",
};

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const projectId = id || "";

  const { data: project, isLoading: projectLoading } = useProject(projectId);

  const [endpointPage, setEndpointPage] = useState(1);
  const [testRunPage, setTestRunPage] = useState(1);
  const pageSize = 10;

  const { data: endpointsData, isLoading: endpointsLoading } = useEndpoints({
    project_id: projectId,
    page: endpointPage,
    page_size: pageSize,
  });
  const { data: environmentsData, isLoading: environmentsLoading } = useEnvironments({
    project_id: projectId,
  });
  const { data: testRunsData, isLoading: testRunsLoading } = useTestRuns({
    project_id: projectId,
    page: testRunPage,
    page_size: pageSize,
  });

  const deleteEndpoint = useDeleteEndpoint();
  const deleteEnvironment = useDeleteEnvironment();

  const [endpointSearch, setEndpointSearch] = useState("");
  const [endpointDialogOpen, setEndpointDialogOpen] = useState(false);
  const [editingEndpoint, setEditingEndpoint] = useState<Endpoint | null>(null);
  const [deleteEndpointTarget, setDeleteEndpointTarget] = useState<Endpoint | null>(null);

  const [envDialogOpen, setEnvDialogOpen] = useState(false);
  const [editingEnv, setEditingEnv] = useState<Environment | null>(null);
  const [deleteEnvTarget, setDeleteEnvTarget] = useState<Environment | null>(null);

  const filteredEndpoints = useMemo(() => {
    const items = endpointsData?.items ?? [];
    if (!endpointSearch.trim()) return items;
    const keyword = endpointSearch.toLowerCase();
    return items.filter(
      (ep) =>
        ep.name.toLowerCase().includes(keyword) ||
        ep.path.toLowerCase().includes(keyword) ||
        ep.method.toLowerCase().includes(keyword)
    );
  }, [endpointsData, endpointSearch]);

  const endpointColumns: Column<Endpoint>[] = [
    {
      key: "method",
      header: "方法",
      className: "w-20",
      render: (_, row) => <HttpMethodBadge method={row.method} />,
    },
    {
      key: "path",
      header: "路径",
      render: (_, row) => (
        <span className="font-mono text-xs text-muted-foreground">{row.path}</span>
      ),
    },
    {
      key: "name",
      header: "名称",
      render: (_, row) => <span className="font-medium text-foreground">{row.name}</span>,
    },
    {
      key: "status",
      header: "状态",
      render: (_, row) => <StatusBadge status={row.status === 1 ? "active" : "inactive"} />,
    },
    {
      key: "actions",
      header: "",
      className: "w-10",
      render: (_, row) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="shadow-popover" align="end">
            <DropdownMenuItem
              onClick={() => {
                setEditingEndpoint(row);
                setEndpointDialogOpen(true);
              }}
            >
              <Pencil className="mr-2 h-3.5 w-3.5" />
              编辑
            </DropdownMenuItem>
            <DropdownMenuItem
              className="text-destructive"
              onClick={() => setDeleteEndpointTarget(row)}
            >
              <Trash2 className="mr-2 h-3.5 w-3.5" />
              删除
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  const testRunColumns: Column<TestRun>[] = [
    {
      key: "name",
      header: "名称",
      render: (_, row) => (
        <Link to={`/runs/${row.id}`} className="font-medium text-accent hover:text-accent/80">
          {row.name}
        </Link>
      ),
    },
    {
      key: "status",
      header: "状态",
      render: (_, row) => <StatusBadge status={row.status} />,
    },
    {
      key: "pass_rate",
      header: "通过率",
      render: (_, row) => <PassRateBar passed={row.passed_cases} total={row.total_cases} />,
    },
    {
      key: "total_duration",
      header: "耗时",
      render: (_, row) => (
        <span className="text-sm text-muted-foreground">
          {row.total_duration > 0 ? `${(row.total_duration / 1000).toFixed(1)}s` : "--"}
        </span>
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
  ];

  if (projectLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-accent border-t-transparent" />
      </div>
    );
  }

  if (!project) {
    return (
      <EmptyState
        title="未找到项目"
        description="你查找的项目不存在或已被删除。"
        action={
          <Button variant="outline" onClick={() => navigate("/")}>
            返回仪表盘
          </Button>
        }
      />
    );
  }

  return (
    <div className="space-y-6">
      <Card className="bg-surface-accent">
        <CardContent className="pt-6">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-foreground">{project.name}</h1>
              <div className="mt-2 flex items-center gap-3">
                <span className="flex items-center gap-1 font-mono text-sm text-muted-foreground">
                  <Globe className="h-3.5 w-3.5" />
                  {project.base_url}
                </span>
                <Badge variant={project.status === 1 ? "default" : "secondary"}>
                  {PROJECT_STATUS_MAP[project.status] ?? "未知"}
                </Badge>
              </div>
              {project.description && (
                <p className="mt-2 text-sm text-muted-foreground">{project.description}</p>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="endpoints" className="w-full">
        <TabsList>
          <TabsTrigger value="endpoints">接口</TabsTrigger>
          <TabsTrigger value="environments">环境</TabsTrigger>
          <TabsTrigger value="test-runs">测试运行</TabsTrigger>
        </TabsList>

        <TabsContent value="endpoints" className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="搜索接口…"
                value={endpointSearch}
                onChange={(e) => setEndpointSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Button
              size="sm"
              onClick={() => {
                setEditingEndpoint(null);
                setEndpointDialogOpen(true);
              }}
            >
              <Plus className="mr-2 h-4 w-4" />
              添加接口
            </Button>
          </div>
          <DataTable
            columns={endpointColumns}
            data={filteredEndpoints}
            loading={endpointsLoading}
            emptyText="该项目暂无接口。"
            pagination={{
              page: endpointPage,
              pageSize,
              total: endpointsData?.total ?? 0,
              onChange: setEndpointPage,
            }}
          />
        </TabsContent>

        <TabsContent value="environments" className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">为不同的部署目标管理环境。</p>
            <Button
              size="sm"
              onClick={() => {
                setEditingEnv(null);
                setEnvDialogOpen(true);
              }}
            >
              <Plus className="mr-2 h-4 w-4" />
              添加环境
            </Button>
          </div>
          {environmentsLoading ? (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <Card key={i}>
                  <CardContent className="p-6">
                    <div className="h-4 w-2/3 animate-pulse rounded bg-muted" />
                    <div className="mt-3 h-3 w-full animate-pulse rounded bg-muted" />
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (environmentsData?.items ?? []).length === 0 ? (
            <EmptyState title="暂无环境" description="添加环境以配置不同的基础 URL 和变量。" />
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {(environmentsData?.items ?? []).map((env) => (
                <Card key={env.id}>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base">{env.name}</CardTitle>
                      <div className="flex items-center gap-2">
                        {env.is_default === 1 && (
                          <Badge variant="outline" className="text-xs">
                            默认
                          </Badge>
                        )}
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm" className="h-7 w-7 p-0">
                              <MoreHorizontal className="h-3.5 w-3.5" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent className="shadow-popover" align="end">
                            <DropdownMenuItem
                              onClick={() => {
                                setEditingEnv(env);
                                setEnvDialogOpen(true);
                              }}
                            >
                              <Pencil className="mr-2 h-3.5 w-3.5" />
                              编辑
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              className="text-destructive"
                              onClick={() => setDeleteEnvTarget(env)}
                            >
                              <Trash2 className="mr-2 h-3.5 w-3.5" />
                              删除
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="font-mono text-xs text-muted-foreground">{env.base_url}</p>
                    {env.description && (
                      <p className="mt-2 text-sm text-muted-foreground">{env.description}</p>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="test-runs" className="space-y-4">
          <DataTable
            columns={testRunColumns}
            data={testRunsData?.items ?? []}
            loading={testRunsLoading}
            emptyText="该项目暂无测试运行。"
            pagination={{
              page: testRunPage,
              pageSize,
              total: testRunsData?.total ?? 0,
              onChange: setTestRunPage,
            }}
          />
        </TabsContent>
      </Tabs>

      <EndpointFormDialog
        open={endpointDialogOpen}
        onOpenChange={setEndpointDialogOpen}
        projectId={projectId}
        endpoint={editingEndpoint}
      />

      <ConfirmDeleteDialog
        open={!!deleteEndpointTarget}
        onOpenChange={(open) => {
          if (!open) setDeleteEndpointTarget(null);
        }}
        onConfirm={() => {
          if (deleteEndpointTarget) {
            deleteEndpoint.mutate(deleteEndpointTarget.id);
            setDeleteEndpointTarget(null);
          }
        }}
        title="删除接口"
        description={
          <>
            确定要删除接口 <strong>{deleteEndpointTarget?.name}</strong> 吗？此操作无法撤销。
          </>
        }
      />

      <EnvironmentFormDialog
        open={envDialogOpen}
        onOpenChange={setEnvDialogOpen}
        projectId={projectId}
        environment={editingEnv}
      />

      <ConfirmDeleteDialog
        open={!!deleteEnvTarget}
        onOpenChange={(open) => {
          if (!open) setDeleteEnvTarget(null);
        }}
        onConfirm={() => {
          if (deleteEnvTarget) {
            deleteEnvironment.mutate(deleteEnvTarget.id);
            setDeleteEnvTarget(null);
          }
        }}
        title="删除环境"
        description={
          <>
            确定要删除环境 <strong>{deleteEnvTarget?.name}</strong> 吗？此操作无法撤销。
          </>
        }
      />
    </div>
  );
}
