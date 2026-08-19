import { createCrudHooks } from "@/lib/create-crud-hooks";
import { queryKeys } from "@/lib/query-keys";
import type { Project, ProjectListResponse } from "@/lib/types";

interface UseProjectsParams {
  keyword?: string;
  status?: number;
  page?: number;
  page_size?: number;
}

const {
  useList: useProjects,
  useDetail: useProject,
  useCreate: useCreateProject,
  useUpdate: useUpdateProject,
  useDelete: useDeleteProject,
} = createCrudHooks<Project, ProjectListResponse, UseProjectsParams>({
  queryKeys: queryKeys.projects,
  basePath: "/projects",
  labels: {
    createSuccess: "项目创建成功",
    createError: "项目创建失败",
    updateSuccess: "项目更新成功",
    updateError: "项目更新失败",
    deleteSuccess: "项目删除成功",
    deleteError: "项目删除失败",
  },
});

export { useProjects, useProject, useCreateProject, useUpdateProject, useDeleteProject };
