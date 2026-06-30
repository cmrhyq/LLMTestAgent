import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api from "@/lib/api";
import type { Project, ProjectListResponse } from "@/lib/types";

interface UseProjectsParams {
  keyword?: string;
  status?: number;
  page?: number;
  page_size?: number;
}

export function useProjects(params?: UseProjectsParams) {
  return useQuery<ProjectListResponse>({
    queryKey: ["projects", params],
    queryFn: async () => {
      const { data } = await api.get<ProjectListResponse>("/projects/", {
        params,
      });
      return data;
    },
  });
}

export function useProject(id: string | number) {
  return useQuery<Project>({
    queryKey: ["projects", id],
    queryFn: async () => {
      const { data } = await api.get<Project>(`/projects/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();

  return useMutation<Project, Error, Partial<Project>>({
    mutationFn: async (payload) => {
      const { data } = await api.post<Project>("/projects/", payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      toast.success("项目创建成功");
    },
    onError: (error) => {
      toast.error(error.message || "项目创建失败");
    },
  });
}

export function useUpdateProject() {
  const queryClient = useQueryClient();

  return useMutation<Project, Error, { id: string | number; payload: Partial<Project> }>({
    mutationFn: async ({ id, payload }) => {
      const { data } = await api.put<Project>(`/projects/${id}`, payload);
      return data;
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      queryClient.invalidateQueries({
        queryKey: ["projects", variables.id],
      });
      toast.success("项目更新成功");
    },
    onError: (error) => {
      toast.error(error.message || "项目更新失败");
    },
  });
}

export function useDeleteProject() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string | number>({
    mutationFn: async (id) => {
      await api.delete(`/projects/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      toast.success("项目删除成功");
    },
    onError: (error) => {
      toast.error(error.message || "项目删除失败");
    },
  });
}
