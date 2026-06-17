import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api from "@/lib/api";
import type { Environment, EnvironmentListResponse } from "@/lib/types";

interface UseEnvironmentsParams {
  project_id?: string | number;
  keyword?: string;
  page?: number;
  page_size?: number;
}

export function useEnvironments(params?: UseEnvironmentsParams) {
  return useQuery<EnvironmentListResponse>({
    queryKey: ["environments", params],
    queryFn: async () => {
      const { data } = await api.get<EnvironmentListResponse>("/environments/", { params });
      return data;
    },
  });
}

export function useCreateEnvironment() {
  const queryClient = useQueryClient();

  return useMutation<Environment, Error, Partial<Environment>>({
    mutationFn: async (payload) => {
      const { data } = await api.post<Environment>("/environments/", payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["environments"] });
      toast.success("Environment created successfully");
    },
    onError: (error) => {
      toast.error(error.message || "Failed to create environment");
    },
  });
}

export function useDeleteEnvironment() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string | number>({
    mutationFn: async (id) => {
      await api.delete(`/environments/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["environments"] });
      toast.success("Environment deleted successfully");
    },
    onError: (error) => {
      toast.error(error.message || "Failed to delete environment");
    },
  });
}

export function useUpdateEnvironment() {
  const queryClient = useQueryClient();

  return useMutation<Environment, Error, { id: string | number; payload: Partial<Environment> }>({
    mutationFn: async ({ id, payload }) => {
      const { data } = await api.put<Environment>(`/environments/${id}`, payload);
      return data;
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["environments"] });
      queryClient.invalidateQueries({ queryKey: ["environments", variables.id] });
      toast.success("Environment updated successfully");
    },
    onError: (error) => {
      toast.error(error.message || "Failed to update environment");
    },
  });
}
