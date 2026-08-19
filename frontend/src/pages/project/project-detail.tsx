import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Globe } from "lucide-react";

import { useProject } from "@/hooks/use-projects.ts";
import { useEndpoints, useDeleteEndpoint } from "@/hooks/use-endpoints.ts";
import { useEnvironments, useDeleteEnvironment } from "@/hooks/use-environments.ts";
import { useTestRuns } from "@/hooks/use-test-runs.ts";
import { Card, CardContent } from "@/components/ui/card.tsx";
import { Button } from "@/components/ui/button.tsx";
import { Badge } from "@/components/ui/badge.tsx";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs.tsx";
import { EmptyState } from "@/components/shared/empty-state.tsx";
import { DetailPageSkeleton } from "@/components/shared/detail-page-skeleton.tsx";
import { EndpointFormDialog } from "@/components/endpoint/endpoint-form-dialog.tsx";
import { EnvironmentFormDialog } from "@/components/environment/environment-form-dialog.tsx";
import type { Endpoint, Environment } from "@/lib/types.ts";
import { EndpointsTab } from "./tabs/endpoints-tab";
import { EnvironmentsTab } from "./tabs/environments-tab";
import { TestRunsTab } from "./tabs/test-runs-tab";

const PROJECT_STATUS_MAP: Record<number, string> = {
  0: "未启用",
  1: "已启用",
};

const PAGE_SIZE = 10;

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const projectId = id || "";

  const { data: project, isLoading: projectLoading } = useProject(projectId);

  const [endpointPage, setEndpointPage] = useState(1);
  const [testRunPage, setTestRunPage] = useState(1);

  const { data: endpointsData, isLoading: endpointsLoading } = useEndpoints({
    project_id: projectId,
    page: endpointPage,
    page_size: PAGE_SIZE,
  });
  const { data: environmentsData, isLoading: environmentsLoading } = useEnvironments({
    project_id: projectId,
  });
  const { data: testRunsData, isLoading: testRunsLoading } = useTestRuns({
    project_id: projectId,
    page: testRunPage,
    page_size: PAGE_SIZE,
  });

  const deleteEndpoint = useDeleteEndpoint();
  const deleteEnvironment = useDeleteEnvironment();

  const [endpointDialogOpen, setEndpointDialogOpen] = useState(false);
  const [editingEndpoint, setEditingEndpoint] = useState<Endpoint | null>(null);
  const [envDialogOpen, setEnvDialogOpen] = useState(false);
  const [editingEnv, setEditingEnv] = useState<Environment | null>(null);

  if (projectLoading) {
    return <DetailPageSkeleton />;
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
          <EndpointsTab
            data={endpointsData?.items ?? []}
            total={endpointsData?.total ?? 0}
            loading={endpointsLoading}
            page={endpointPage}
            pageSize={PAGE_SIZE}
            onPageChange={setEndpointPage}
            onAdd={() => {
              setEditingEndpoint(null);
              setEndpointDialogOpen(true);
            }}
            onEdit={(endpoint) => {
              setEditingEndpoint(endpoint);
              setEndpointDialogOpen(true);
            }}
            onDelete={(endpoint) => deleteEndpoint.mutate(endpoint.id)}
          />
        </TabsContent>

        <TabsContent value="environments" className="space-y-4">
          <EnvironmentsTab
            data={environmentsData?.items ?? []}
            loading={environmentsLoading}
            onAdd={() => {
              setEditingEnv(null);
              setEnvDialogOpen(true);
            }}
            onEdit={(env) => {
              setEditingEnv(env);
              setEnvDialogOpen(true);
            }}
            onDelete={(env) => deleteEnvironment.mutate(env.id)}
          />
        </TabsContent>

        <TabsContent value="test-runs" className="space-y-4">
          <TestRunsTab
            data={testRunsData?.items ?? []}
            total={testRunsData?.total ?? 0}
            loading={testRunsLoading}
            page={testRunPage}
            pageSize={PAGE_SIZE}
            onPageChange={setTestRunPage}
          />
        </TabsContent>
      </Tabs>

      <EndpointFormDialog
        open={endpointDialogOpen}
        onOpenChange={setEndpointDialogOpen}
        projectId={projectId}
        endpoint={editingEndpoint}
      />

      <EnvironmentFormDialog
        open={envDialogOpen}
        onOpenChange={setEnvDialogOpen}
        projectId={projectId}
        environment={editingEnv}
      />
    </div>
  );
}
