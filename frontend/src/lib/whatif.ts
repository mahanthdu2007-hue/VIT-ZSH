import type { AssessRequest, WhatIfOverrides } from "../api/client";

/** Every §11 What-If control, filled in. */
export type WhatIfControls = Required<{ [K in keyof WhatIfOverrides]: NonNullable<WhatIfOverrides[K]> }>;

export function controlsFrom({ student, parent }: AssessRequest): WhatIfControls {
  return {
    budget: parent.education_budget_inr,
    loan_willingness: parent.loan_willingness,
    home_city: student.home_city,
    willing_to_relocate: student.willing_to_relocate,
    risk_tolerance: student.risk_tolerance,
    risk_appetite: parent.risk_appetite,
    wants_higher_studies: student.wants_higher_studies,
    top_priority: parent.top_priority,
  };
}

/** Only the controls that differ from the original answers; empty means "no change". */
export function overridesBetween(original: WhatIfControls, current: WhatIfControls): WhatIfOverrides {
  const keys = Object.keys(original) as (keyof WhatIfControls)[];
  return Object.fromEntries(keys.filter((k) => original[k] !== current[k]).map((k) => [k, current[k]]));
}
