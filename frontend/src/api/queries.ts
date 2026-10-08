import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  type AssessmentResult,
  type AssessRequest,
  type Track,
  fetchCareers,
  fetchDemoProfiles,
  fetchExplanations,
  fetchHealth,
  fetchQuestions,
  postAssess,
} from "./client";

const STATIC_DATA = { staleTime: Infinity } as const;

export const queryKeys = {
  health: ["health"] as const,
  questions: (track: Track) => ["questions", track] as const,
  demoProfiles: ["demo-profiles"] as const,
  careers: ["careers"] as const,
  assessment: (id: string) => ["assessment", id] as const,
  explanations: (id: string) => ["explanations", id] as const,
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
    onSuccess: (result) => {
      queryClient.setQueryData(queryKeys.assessment(result.id), result);
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

/** §13 lazy explanations: start from the template text in the result, then fetch the latest. */
export function useExplanations(result: AssessmentResult) {
  return useQuery({
    queryKey: queryKeys.explanations(result.id),
    queryFn: () => fetchExplanations(result.id),
    initialData: result.explanations,
    initialDataUpdatedAt: 0,
  });
}
