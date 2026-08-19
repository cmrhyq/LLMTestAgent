import type { Id, PaginatedResponse } from "./common";

export interface Conversation {
  id: Id;
  project_id: Id | null;
  title: string;
  mode: string;
  status: number;
  last_message_at: string | null;
  created_at: string;
  updated_at: string;
}

export type ConversationListResponse = PaginatedResponse<Conversation>;

export interface Message {
  id: Id;
  conversation_id: Id;
  role: "user" | "assistant" | "system";
  content: string;
  meta: string;
  created_at: string;
}

export interface MessageListResponse {
  items: Message[];
  total: number;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}
