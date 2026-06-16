import { useState, useMemo } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { Search, Globe, Plus } from "lucide-react";

import { useProject } from "@/hooks/use-projects";
import { useEndpoints } from "@/hooks/use-endpoints";
import { useEnvironments } from "@/hooks/use-environments";
import { useTestRuns } from "@/hooks/use-test-runs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { DataTable } from "@/components/shared/data-table";
import { StatusBadge } from "@/components/shared/status-badge";
import { HttpMethodBadge } from "@/components/shared/http-method-badge";
import { PassRateBar } from "@/components/shared/pass-rate-bar";
import { EmptyState } from "@/components/shared/empty-state";
import type { Column } from "@/components/shared/data-table";
import type { Endpoint, TestRun } from "@/lib/types";

const PROJECT_STATUS_MAP: Record<number, string> = {
  0: "Inactive",
  1: "Active",
};

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const projectId = id || "";

  const { data: project, isLoading: projectLoading } = useProject(projectId);
  const { data: endpointsData, isLoading: endpointsLoading } = useEndpoints({
    project_id: projectId,
  });
  const { data: environmentsData, isLoading: environmentsLoading } = useEnvironments({
    project_id: projectId,
  });
  const { data: testRunsData, isLoading: testRunsLoading } = useTestRuns({
    project_id: projectId,
  });

  const [endpointSearch, setEndpointSearch] = useState("");

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
      header: "Method",
      className: "w-20",
      render: (_, row) => <HttpMethodBadge method={row.method} />,
    },
    {
      key: "path",
      header: "Path",
      render: (_, row) => (
        <span className="font-mono text-xs text-muted-foreground">{row.path}</span>
      ),
    },
    {
      key: "name",
      header: "Name",
      render: (_, row) => <span className="font-medium text-foreground">{row.name}</span>,
    },
    {
      key: "status",
      header: "Status",
      render: (_, row) => <StatusBadge status={row.status === 1 ? "active" : "inactive"} />,
    },
  ];

  const testRunColumns: Column<TestRun>[] = [
    {
      key: "name",
      header: "Name",
      render: (_, row) => (
        <Link to={`/runs/${row.id}`} className="font-medium text-accent hover:text-accent/80">
          {row.name}
        </Link>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (_, row) => <StatusBadge status={row.status} />,
    },
    {
      key: "pass_rate",
      header: "Pass Rate",
      render: (_, row) => <PassRateBar passed={row.passed_cases} total={row.total_cases} />,
    },
    {
      key: "total_duration",
      header: "Duration",
      render: (_, row) => (
        <span className="text-sm text-muted-foreground">
          {row.total_duration > 0 ? `${(row.total_duration / 1000).toFixed(1)}s` : "--"}
        </span>
      ),
    },
    {
      key: "created_at",
      header: "Created At",
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
        title="Project not found"
        description="The project you are looking for does not exist or has been deleted."
        action={
          <Button variant="outline" onClick={() => navigate("/")}>
            Back to Dashboard
          </Button>
        }
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">{project.name}</h1>
          <div className="mt-2 flex items-center gap-3">
            <span className="flex items-center gap-1 font-mono text-sm text-muted-foreground">
              <Globe className="h-3.5 w-3.5" />
              {project.base_url}
            </span>
            <Badge variant={project.status === 1 ? "default" : "secondary"}>
              {PROJECT_STATUS_MAP[project.status] ?? "Unknown"}
            </Badge>
          </div>
          {project.description && (
            <p className="mt-2 text-sm text-muted-foreground">{project.description}</p>
          )}
        </div>
      </div>

      <Tabs defaultValue="endpoints" className="w-full">
        <TabsList>
          <TabsTrigger value="endpoints">Endpoints</TabsTrigger>
          <TabsTrigger value="environments">Environments</TabsTrigger>
          <TabsTrigger value="test-runs">Test Runs</TabsTrigger>
        </TabsList>

        <TabsContent value="endpoints" className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search endpoints..."
                value={endpointSearch}
                onChange={(e) => setEndpointSearch(e.target.value)}
                className="pl-9"
              />
            </div>
          </div>
          <DataTable
            columns={endpointColumns}
            data={filteredEndpoints}
            loading={endpointsLoading}
            emptyText="No endpoints found for this project."
          />
        </TabsContent>

        <TabsContent value="environments" className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Manage environments for different deployment targets.
            </p>
            <Button size="sm">
              <Plus className="mr-2 h-4 w-4" />
              Add Environment
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
            <EmptyState
              title="No environments"
              description="Add an environment to configure different base URLs and variables."
            />
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {(environmentsData?.items ?? []).map((env) => (
                <Card key={env.id}>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base">{env.name}</CardTitle>
                      {env.is_default === 1 && (
                        <Badge variant="outline" className="text-xs">
                          Default
                        </Badge>
                      )}
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
            emptyText="No test runs found for this project."
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}
