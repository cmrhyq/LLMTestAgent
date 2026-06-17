import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Folder, Globe, CheckCircle, MoreHorizontal, FileText, Play } from "lucide-react";

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
  0: "Inactive",
  1: "Active",
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
      header: "Name",
      render: (_, row) => (
        <Link to={`/projects/${row.id}`} className="font-medium text-accent hover:text-accent/80">
          {row.name}
        </Link>
      ),
    },
    {
      key: "base_url",
      header: "Base URL",
      render: (_, row) => (
        <span className="font-mono text-xs text-muted-foreground">{row.base_url}</span>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (_, row) => (
        <Badge variant={row.status === 1 ? "default" : "secondary"}>
          {STATUS_MAP[row.status] ?? "Unknown"}
        </Badge>
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
    {
      key: "id",
      header: "Actions",
      className: "w-12",
      render: (_, row) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem asChild>
              <Link to={`/projects/${row.id}`}>Edit</Link>
            </DropdownMenuItem>
            <DropdownMenuItem className="text-destructive" onClick={() => setDeleteTarget(row)}>
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">Dashboard</h1>
        <p className="mt-1 text-sm text-muted-foreground">Overview of your API testing projects.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Projects
            </CardTitle>
            <Folder className="h-4 w-4 text-accent" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{stats.totalProjects}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Endpoints
            </CardTitle>
            <Globe className="h-4 w-4 text-teal-500" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{stats.totalEndpoints}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Avg Pass Rate
            </CardTitle>
            <CheckCircle className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{stats.avgPassRate}%</p>
          </CardContent>
        </Card>
      </div>

      <div>
        <h2 className="mb-3 text-lg font-semibold text-foreground">Quick Actions</h2>
        <div className="flex gap-3">
          <Button asChild variant="outline">
            <Link to="/workflows/parse">
              <FileText className="mr-2 h-4 w-4" />
              Parse Document
            </Link>
          </Button>
          <Button asChild variant="outline">
            <Link to="/workflows/run">
              <Play className="mr-2 h-4 w-4" />
              Run Test
            </Link>
          </Button>
        </div>
      </div>

      <div>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-foreground">Projects</h2>
          <CreateProjectDialog />
        </div>
        <DataTable
          columns={columns}
          data={projectsData?.items ?? []}
          loading={projectsLoading}
          emptyText="No projects yet. Create one to get started."
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
        title="Delete Project"
        description={
          <span>
            Are you sure you want to delete project <strong>{deleteTarget?.name}</strong>? This will
            permanently delete all associated data including environments, endpoints, test runs,
            test cases, and reports.{" "}
            <span className="font-semibold text-destructive">This action cannot be undone.</span>
          </span>
        }
        confirmText="Delete Project"
      />
    </div>
  );
}
