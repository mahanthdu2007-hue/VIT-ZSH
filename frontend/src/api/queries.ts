import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  type AssessmentResult,
  type AssessRequest,
  type Track,
  type WhatIfOverrides,
  type ChatHistory,
  type ChatRequest,
  fetchCareers,
  fetchChatHistory,
  fetchDemoProfiles,
  fetchExplanations,
  fetchHealth,
  fetchQuestions,
  postAssess,
  postChat,
  postWhatIf,
} from "./client";

const STATIC_DATA = { staleTime: Infinity } as const;

export const queryKeys = {
  health: ["health"] as const,
  questions: (track: Track) => ["questions", track] as const,
  demoProfiles: ["demo-profiles"] as const,
  careers: ["careers"] as const,
  assessment: (id: string) => ["assessment", id] as const,
  assessmentInputs: (id: string) => ["assessment-inputs", id] as const,
  explanations: (id: string) => ["explanations", id] as const,
  chat: (id: string) => ["chat", id] as const,
  whatIf: (id: string, overrides: WhatIfOverrides) => ["whatif", id, overrides] as const,
};

export function useHealth() {
  return useQuery({ queryKey: queryKeys.health, queryFn: fetchHealth });
}

export function useQuestions(track: Track) {
  return useQuery({ queryKey: queryKeys.questions(track), queryFn: () => fetchQuestions(track), ...STATIC_DATA });
}

export function useDemoProfiles() {
  return useQuery({ queryKey: queryKeys.demoProfiles, queryFn: fetchDemoProfiles, ...STATIC_DATA });
}

export function useCareers() {
  return useQuery({ queryKey: queryKeys.careers, queryFn: fetchCareers, ...STATIC_DATA });
}

/** POST /api/assess, keep the result in the query cache, then open its dashboard. */
export function useAssess() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  return useMutation({
    mutationFn: (body: AssessRequest) => postAssess(body),
    onSuccess: (result, body) => {
      queryClient.setQueryData(queryKeys.assessment(result.id), result);
      queryClient.setQueryData(queryKeys.assessmentInputs(result.id), body);
      navigate(`/dashboard/${result.id}`);
    },
  });
}

/** A result saved by useAssess. The API has no GET for a saved assessment, so it lives in memory only. */
export function useAssessment(id: string) {
  return useQuery<AssessmentResult>({
    queryKey: queryKeys.assessment(id),
    queryFn: () => Promise.reject(new Error("This result is no longer in memory.")),
    ...STATIC_DATA,
    retry: false,
  });
}

/** The answers behind a saved result, kept by useAssess so What-If can start from them. */
export function useAssessmentInputs(id: string) {
  return useQuery<AssessRequest>({
    queryKey: queryKeys.assessmentInputs(id),
    queryFn: () => Promise.reject(new Error("These answers are no longer in memory.")),
    ...STATIC_DATA,
    retry: false,
  });
}

const EXPLANATION_POLL_MS = 2000;
const EXPLANATION_MAX_POLLS = 45; // stop asking after about 90 s; the template text stays on screen

/** §13 lazy explanations: show the template text from the result, then poll until the AI text is ready. */
export function useExplanations(result: AssessmentResult) {
  return useQuery({
    queryKey: queryKeys.explanations(result.id),
    queryFn: () => fetchExplanations(result.id),
    initialData: result.explanations,
    initialDataUpdatedAt: 0,
    refetchInterval: (query) =>
      query.state.data?.status === "pending" && query.state.dataUpdateCount < EXPLANATION_MAX_POLLS
        ? EXPLANATION_POLL_MS
        : false,
  });
}

/** §11 What-If re-run for changed answers; keeps showing the last result while the next one loads. */
export function useWhatIf(assessmentId: string, overrides: WhatIfOverrides) {
  return useQuery({
    queryKey: queryKeys.whatIf(assessmentId, overrides),
    queryFn: ({ signal }) => postWhatIf({ assessment_id: assessmentId, overrides }, signal),
    enabled: Object.keys(overrides).length > 0,
    placeholderData: keepPreviousData,
    ...STATIC_DATA,
  });
}

/** §17 Ask PRISM history, saved on the server per assessment. */
export function useChatHistory(assessmentId: string) {
  return useQuery({ queryKey: queryKeys.chat(assessmentId), queryFn: () => fetchChatHistory(assessmentId) });
}

/** §17 send one question; the saved history is updated with the question and the reply. */
export function useSendChat(assessmentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: ChatRequest) => postChat(body),
    onSuccess: (reply, body) => {
      queryClient.setQueryData<ChatHistory>(queryKeys.chat(assessmentId), (old) => ({
        assessment_id: assessmentId,
        messages: [
          ...(old?.messages ?? []),
          { who: "user", text: body.message, asking_as: body.asking_as ?? "student", reply: null },
          { who: "assistant", text: reply.answer, asking_as: body.asking_as ?? "student", reply },
        ],
      }));
    },
  });
}
