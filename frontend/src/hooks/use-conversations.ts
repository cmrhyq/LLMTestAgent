import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api from "@/lib/api";
import type {
  Conversation,
  ConversationListResponse,
  MessageListResponse,
} from "@/lib/types";

interface UseConversationsParams {
  project_id?: string | number;
  status?: number;
  page?: number;
  page_size?: number;
}

export function useConversations(params?: UseConversationsParams) {
  return useQuery<ConversationListResponse>({
    queryKey: ["conversations", params],
    queryFn: async () => {
      const { data } = await api.get<ConversationListResponse>("/conversations/", {
        params,
      });
      return data;
    },
  });
}

export function useConversationMessages(id: string | number | null | undefined) {
  return useQuery<MessageListResponse>({
    queryKey: ["conversation-messages", id],
    queryFn: async () => {
      const { data } = await api.get<MessageListResponse>(`/conversations/${id}/messages`);
      return data;
    },
    enabled: !!id,
  });
}

interface CreateConversationPayload {
  project_id?: string | number | null;
  title?: string;
  mode?: string;
}

export function useCreateConversation() {
  const queryClient = useQueryClient();

  return useMutation<Conversation, Error, CreateConversationPayload>({
    mutationFn: async (payload) => {
      const { data } = await api.post<Conversation>("/conversations/", payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
    onError: (error) => {
      toast.error(error.message || "会话创建失败");
    },
  });
}

interface UpdateConversationPayload {
  title?: string;
  mode?: string;
  status?: number;
}

export function useUpdateConversation() {
  const queryClient = useQueryClient();

  return useMutation<
    Conversation,
    Error,
    { id: string | number; payload: UpdateConversationPayload }
  >({
    mutationFn: async ({ id, payload }) => {
      const { data } = await api.put<Conversation>(`/conversations/${id}`, payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      toast.success("会话更新成功");
    },
    onError: (error) => {
      toast.error(error.message || "会话更新失败");
    },
  });
}

export function useDeleteConversation() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string | number>({
    mutationFn: async (id) => {
      await api.delete(`/conversations/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      toast.success("会话删除成功");
    },
    onError: (error) => {
      toast.error(error.message || "会话删除失败");
    },
  });
}
