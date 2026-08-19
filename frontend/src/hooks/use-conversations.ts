import { useQuery } from "@tanstack/react-query";

import { createCrudHooks } from "@/lib/create-crud-hooks";
import api from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import type { Conversation, ConversationListResponse, MessageListResponse } from "@/lib/types";

interface UseConversationsParams {
  project_id?: string | number;
  status?: number;
  page?: number;
  page_size?: number;
}

interface CreateConversationPayload {
  project_id?: string | number | null;
  title?: string;
  mode?: string;
}

interface UpdateConversationPayload {
  title?: string;
  mode?: string;
  status?: number;
}

const {
  useList: useConversations,
  useCreate: useCreateConversation,
  useUpdate: useUpdateConversation,
  useDelete: useDeleteConversation,
} = createCrudHooks<
  Conversation,
  ConversationListResponse,
  UseConversationsParams,
  CreateConversationPayload,
  UpdateConversationPayload
>({
  queryKeys: queryKeys.conversations,
  basePath: "/conversations",
  labels: {
    createSuccess: "会话创建成功",
    createError: "会话创建失败",
    updateSuccess: "会话更新成功",
    updateError: "会话更新失败",
    deleteSuccess: "会话删除成功",
    deleteError: "会话删除失败",
  },
  toastOnCreate: false,
});

export function useConversationMessages(id: string | number | null | undefined) {
  return useQuery<MessageListResponse>({
    queryKey: queryKeys.conversations.messages(id),
    queryFn: async () => {
      const { data } = await api.get<MessageListResponse>(`/conversations/${id}/messages`);
      return data;
    },
    enabled: !!id,
  });
}

export { useConversations, useCreateConversation, useUpdateConversation, useDeleteConversation };
