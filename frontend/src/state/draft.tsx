import { type ReactNode, createContext, useContext, useState } from "react";
import type { CityId, Level, Stream, StudentInput, Track } from "../api/client";

/** The student's answers while the forms are being filled in; kept in memory only. */
export type StudentDraft = {
  track: Track;
  current_class: number | null;
  stream: Stream | null;
  degree: string;
  year: number | null;
  marks_percent: number | null;
  favourite_subjects: string[];
  home_city: CityId | null;
  dream_career_id: string | null;
  aptitude_answers: Record<string, number>;
  riasec_answers: Record<string, number>;
  workstyle_answers: Record<string, number>;
  free_text_1: string;
  free_text_2: string;
  preferred_cities: CityId[];
  willing_to_relocate: boolean | null;
  wants_higher_studies: boolean | null;
  risk_tolerance: Level | null;
  self_rated_skills: Record<string, number>;
};

export function emptyDraft(track: Track): StudentDraft {
  return {
    track,
    current_class: null,
    stream: null,
    degree: "",
    year: null,
    marks_percent: null,
    favourite_subjects: [],
    home_city: null,
    dream_career_id: null,
    aptitude_answers: {},
    riasec_answers: {},
    workstyle_answers: {},
    free_text_1: "",
    free_text_2: "",
    preferred_cities: [],
    willing_to_relocate: null,
    wants_higher_studies: null,
    risk_tolerance: null,
    self_rated_skills: {},
  };
}

/** Builds the §6 student input from a draft whose steps all passed validation; null if anything required is missing. */
export function toStudentInput(draft: StudentDraft): StudentInput | null {
  const { home_city, willing_to_relocate, wants_higher_studies, risk_tolerance } = draft;
  if (home_city === null || willing_to_relocate === null || wants_higher_studies === null || risk_tolerance === null) {
    return null;
  }
  const common = {
    aptitude_answers: draft.aptitude_answers,
    riasec_answers: draft.riasec_answers,
    workstyle_answers: draft.workstyle_answers,
    marks_percent: draft.marks_percent,
    favourite_subjects: draft.favourite_subjects,
    home_city,
    preferred_cities: draft.preferred_cities,
    willing_to_relocate,
    wants_higher_studies,
    risk_tolerance,
    dream_career_id: draft.dream_career_id,
    free_text_1: draft.free_text_1.trim(),
    free_text_2: draft.free_text_2.trim(),
  };
  if (draft.track === "school") {
    if (draft.current_class === null) return null;
    return { ...common, track: "school", current_class: draft.current_class, stream: draft.stream };
  }
  if (draft.year === null || draft.degree.trim() === "") return null;
  return {
    ...common,
    track: "college",
    degree: draft.degree.trim(),
    year: draft.year,
    self_rated_skills: draft.self_rated_skills,
  };
}

type DraftContextValue = { draft: StudentDraft | null; setDraft: (draft: StudentDraft | null) => void };

const DraftContext = createContext<DraftContextValue | null>(null);

export function DraftProvider({ children }: { children: ReactNode }) {
  const [draft, setDraft] = useState<StudentDraft | null>(null);
  return <DraftContext.Provider value={{ draft, setDraft }}>{children}</DraftContext.Provider>;
}

export function useDraft(): DraftContextValue {
  const value = useContext(DraftContext);
  if (!value) throw new Error("useDraft must be used inside DraftProvider");
  return value;
}
