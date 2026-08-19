import type { Id, PaginatedResponse } from "./common";

export interface Project {
  id: Id;
  name: string;
  base_url: string;
  description: string;
  status: number;
  created_at: string;
  updated_at: string;
}

export type ProjectListResponse = PaginatedResponse<Project>;
