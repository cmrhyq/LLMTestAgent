import { useQuery } from "@tanstack/react-query";
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
