export interface Project {
  id: string | number;
  name: string;
  base_url: string;
  description: string;
  status: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectListResponse {
  items: Project[];
  total: number;
  page: number;
  page_size: number;
}

export interface Endpoint {
  id: string | number;
  project_id: string | number;
  operation_id: string;
  name: string;
  path: string;
  method: string;
  tags: string;
  summary: string;
  description: string;
  params: string;
  headers: string;
  body: string;
  responses: string;
  security: string;
  content_type: string;
  deprecated: number;
  status: number;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface EndpointListResponse {
  items: Endpoint[];
  total: number;
  page: number;
  page_size: number;
}

export interface Environment {
  id: string | number;
  project_id: string | number;
  name: string;
  base_url: string;
  description: string;
  variables: string;
  is_default: number;
  status: number;
  created_at: string;
  updated_at: string;
}

export interface EnvironmentListResponse {
  items: Environment[];
  total: number;
  page: number;
  page_size: number;
}

export interface TestRun {
  id: string | number;
  project_id: string | number | null;
  environment_id: string | number | null;
  name: string;
  status: string;
  trigger_type: string;
  llm_provider: string;
  llm_model: string;
  total_cases: number;
  passed_cases: number;
  failed_cases: number;
  skipped_cases: number;
  error_cases: number;
  pass_rate: number;
  started_at: string | null;
  finished_at: string | null;
  total_duration: number;
  error_message: string;
  created_at: string;
  updated_at: string;
}

export interface TestRunListResponse {
  items: TestRun[];
  total: number;
  page: number;
  page_size: number;
}

export interface TestCaseBrief {
  id: string | number;
  case_name: string;
  method: string;
  url: string;
  priority: string;
  status: string;
  created_at: string;
}

export interface TestResultBrief {
  id: string | number;
  test_case_id: string | number | null;
  status: string;
  status_code: number | null;
  duration: number;
  assertion_passed: number;
  assertion_failed: number;
  error_message: string;
  created_at: string;
}

export interface TestRunDetail extends TestRun {
  test_cases: TestCaseBrief[];
  test_results: TestResultBrief[];
}

export interface RunTestRequest {
  instruction: string;
  api_doc_path?: string | null;
}

export interface RunTestResponse {
  run_id: string | number;
  status: string;
  message: string;
}

export interface ParseOpenAPIResponse {
  run_id: string | number | null;
  status: string;
  message: string;
  endpoints_count: number;
}

export interface WorkflowStatus {
  run_id: string | number;
  status: string;
  total_cases: number;
  passed_cases: number;
  failed_cases: number;
  pass_rate: number;
  error_message: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface Report {
  id: string | number;
  run_id: string | number;
  format: string;
  file_size: number;
  generated_at: string;
  test_run_name: string;
}

export interface ReportListResponse {
  items: Report[];
  total: number;
  page: number;
  page_size: number;
}

export interface TestResultDetail {
  id: string | number;
  case_id: string;
  case_name: string;
  status: string;
  request_url: string;
  request_method: string;
  request_headers: string;
  request_body: string | null;
  query_params: string | null;
  response_status_code: number | null;
  response_headers: string;
  response_body: string | null;
  response_time: number;
  error_message: string;
  retry_count: number;
  started_at: string | null;
  finished_at: string | null;
}

export interface ReportDetail {
  id: string | number;
  run_id: string | number;
  format: string;
  file_size: number;
  generated_at: string;
  test_run: TestRun;
  test_results: TestResultDetail[];
}
