import type { components } from "./schema";

type Schemas = components["schemas"];

export type HealthResponse = Schemas["HealthResponse"];
export type QuestionSet = Schemas["PublicQuestionSet"];
export type DemoProfile = Schemas["DemoProfile"];
export type CareerSummary = Schemas["CareerSummary"];
export type AssessRequest = Schemas["AssessRequest"];
export type AssessmentResult = Schemas["AssessmentResult"];
export type Explanations = Schemas["Explanations"];
export type CareerExplanation = Schemas["CareerExplanation"];
export type Citation = Schemas["Citation"];
export type SchoolStudentInput = Schemas["SchoolStudentInput"];
export type CollegeStudentInput = Schemas["CollegeStudentInput"];
export type StudentInput = SchoolStudentInput | CollegeStudentInput;
export type ParentInput = Schemas["ParentInput"];
export type Track = QuestionSet["track"];
export type CityId = SchoolStudentInput["home_city"];
export type Level = SchoolStudentInput["risk_tolerance"];
export type Stream = NonNullable<SchoolStudentInput["stream"]>;
export type Domain = CareerSummary["domain"];
export type LoanWillingness = ParentInput["loan_willingness"];
export type LocationPreference = ParentInput["location_preference"];
export type TopPriority = ParentInput["top_priority"];
export type RankedCareer = Schemas["RankedCareer"];
export type CareerDetail = Schemas["CareerDetail"];
export type Confidence = Schemas["Confidence"];
export type ConflictResult = Schemas["ConflictResult"];
export type ConflictDimension = Schemas["ConflictDimension"];
export type MiddlePath = Schemas["MiddlePath"];
export type StretchOption = Schemas["StretchOption"];
export type RiskRadar = Schemas["RiskRadar"];
export type SkillPlan = Schemas["SkillPlan"];
export type Swot = Schemas["Swot"];
export type SwotItem = Schemas["SwotItem"];
export type WhatIfOverrides = Schemas["WhatIfOverrides"];
export type WhatIfRequest = Schemas["WhatIfRequest"];
export type WhatIfResult = Schemas["WhatIfResult"];
export type CareerChange = Schemas["CareerChange"];
export type ChatRequest = Schemas["ChatRequest"];
export type ChatReply = Schemas["ChatReply"];
export type ChatHistory = Schemas["ChatHistory"];
export type ChatMessage = Schemas["ChatMessage"];

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    throw new ApiError(`Request to ${path} failed with status ${response.status}`, response.status);
  }
  return (await response.json()) as T;
}

export function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/api/health");
}

/** §5 the short question set for the student's path; Class 11–12 students pass their stream. */
export function fetchQuestions(track: Track, stream: Stream | null): Promise<QuestionSet> {
  const query = stream === null ? "" : `?stream=${encodeURIComponent(stream)}`;
  return request<QuestionSet>(`/api/questions/${track}${query}`);
}

export function fetchDemoProfiles(): Promise<DemoProfile[]> {
  return request<DemoProfile[]>("/api/demo-profiles");
}

export function fetchCareers(): Promise<CareerSummary[]> {
  return request<CareerSummary[]>("/api/careers");
}

export function fetchExplanations(assessmentId: string): Promise<Explanations> {
  return request<Explanations>(`/api/explanations/${encodeURIComponent(assessmentId)}`);
}

export function postAssess(body: AssessRequest): Promise<AssessmentResult> {
  return request<AssessmentResult>("/api/assess", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function postWhatIf(body: WhatIfRequest, signal?: AbortSignal): Promise<WhatIfResult> {
  return request<WhatIfResult>("/api/whatif", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
}

export function postChat(body: ChatRequest): Promise<ChatReply> {
  return request<ChatReply>("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function fetchChatHistory(assessmentId: string): Promise<ChatHistory> {
  return request<ChatHistory>(`/api/chat/${encodeURIComponent(assessmentId)}`);
}
