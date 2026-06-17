import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api from "@/lib/api";
import type { Endpoint, EndpointListResponse } from "@/lib/types";

interface UseEndpointsParams {
  project_id?: string | number;
  method?: string;
  keyword?: string;
  page?: number;
  page_size?: number;
}

export function useEndpoints(params?: UseEndpointsParams) {
  return useQuery<EndpointListResponse>({
    queryKey: ["endpoints", params],
    queryFn: async () => {
      const { data } = await api.get<EndpointListResponse>("/endpoints/", {
        params,
      });
      return data;
    },
  });
}

export function useEndpoint(id: string | number) {
  return useQuery<Endpoint>({
    queryKey: ["endpoints", id],
    queryFn: async () => {
      const { data } = await api.get<Endpoint>(`/endpoints/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useCreateEndpoint() {
  const queryClient = useQueryClient();

  return useMutation<Endpoint, Error, Partial<Endpoint>>({
    mutationFn: async (payload) => {
      const { data } = await api.post<Endpoint>("/endpoints/", payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["endpoints"] });
      toast.success("Endpoint created successfully");
    },
    onError: (error) => {
      toast.error(error.message || "Failed to create endpoint");
    },
  });
}

export function useUpdateEndpoint() {
  const queryClient = useQueryClient();

  return useMutation<Endpoint, Error, { id: string | number; payload: Partial<Endpoint> }>({
    mutationFn: async ({ id, payload }) => {
      const { data } = await api.put<Endpoint>(`/endpoints/${id}`, payload);
      return data;
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["endpoints"] });
      queryClient.invalidateQueries({ queryKey: ["endpoints", variables.id] });
      toast.success("Endpoint updated successfully");
    },
    onError: (error) => {
      toast.error(error.message || "Failed to update endpoint");
    },
  });
}

export function useDeleteEndpoint() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string | number>({
    mutationFn: async (id) => {
      await api.delete(`/endpoints/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["endpoints"] });
      toast.success("Endpoint deleted successfully");
    },
    onError: (error) => {
      toast.error(error.message || "Failed to delete endpoint");
    },
  });
}
