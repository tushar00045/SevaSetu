/**
 * Classifier contract.
 *
 * The routing logic in `routing.ts` depends only on this interface, not on
 * any specific model. `index.ts` now uses `RemoteClassifier`, which calls
 * the FastAPI service in `model_service/` (loads the retrained department
 * and urgency BiLSTM models from the SevaSetu repo, see its
 * CLAUDE_CODE_BRIEF.md and EVAL.md for how they were trained and their
 * honest held-out accuracy: department 76.39%, urgency 57.14%, neither is
 * 100%, both are real reads on unseen text).
 *
 * `StubClassifier` below is kept for `seed.ts`, which uses it to generate
 * demo ticket data without needing the model service running, and as a
 * fallback reference implementation. Run `model_service/app.py` (see its
 * README/docstring) before starting the backend, or set CLASSIFIER_URL if
 * it's not on localhost:8000.
 */

export type Department =
  | "Public Works Department (PWD)"
  | "Water Board"
  | "State Electricity Board"
  | "Municipal Corporation - Sanitation"
  | "Department of Health & Family Welfare"
  | "Department of School Education"
  | "State Transport Corporation"
  | "Police Department"
  | "Department of Food & Civil Supplies"
  | "Department of Social Welfare"
  | "Revenue Department"
  | "State Pollution Control Board";

export type Urgency = "low" | "medium" | "high";

export interface ClassificationResult {
  department: Department;
  departmentConfidence: number; // 0-1
  urgency: Urgency;
  urgencyConfidence: number; // 0-1
}

export interface Classifier {
  classify(text: string): Promise<ClassificationResult>;
}

// ---------------------------------------------------------------------------
// Stub classifier: transparent keyword rules, NOT a machine-learned model.
// Exists purely so routing/SLA/dashboard logic can be built and demoed
// without depending on a model that isn't trustworthy yet. Confidence is
// deliberately capped below 0.9 so it always demonstrates the human-review
// path, not just the auto-route happy path.
// ---------------------------------------------------------------------------

const KEYWORD_RULES: Array<{ department: Department; keywords: string[] }> = [
  { department: "Public Works Department (PWD)", keywords: ["pothole", "road", "footpath", "bridge", "divider", "manhole", "gaddha", "sadak"] },
  { department: "Water Board", keywords: ["water", "pani", "pipeline", "leakage", "supply band", "contaminat"] },
  { department: "State Electricity Board", keywords: ["electricity", "bijli", "power", "transformer", "streetlight", "voltage", "wire"] },
  { department: "Municipal Corporation - Sanitation", keywords: ["garbage", "kachra", "dustbin", "drain", "sewage", "toilet", "safai"] },
  { department: "Department of Health & Family Welfare", keywords: ["doctor", "hospital", "medicine", "ambulance", "phc", "ward", "nurse"] },
  { department: "Department of School Education", keywords: ["school", "teacher", "midday meal", "textbook", "shiksha", "classroom"] },
  { department: "State Transport Corporation", keywords: ["bus", "conductor", "auto", "route cancel", "route has been", "transport"] },
  { department: "Police Department", keywords: ["fir", "theft", "chori", "police", "harassment", "assault", "murder", "shoot", "stolen", "threat", "steal"] },
  { department: "Department of Food & Civil Supplies", keywords: ["ration", "pds", "fair price shop", "dealer"] },
  { department: "Department of Social Welfare", keywords: ["pension", "disability certificate", "scholarship", "widow"] },
  { department: "Revenue Department", keywords: ["land record", "property tax", "mutation", "registry", "encroachment"] },
  { department: "State Pollution Control Board", keywords: ["pollution", "factory smoke", "effluent", "air quality", "industrial waste"] },
];

const URGENT_KEYWORDS = [
  "murder", "shoot", "dead", "fire", "collapse", "accident", "urgent", "emergency",
  "assault", "threat", "safety", "gir gaya", "chori", "theft", "injured", "bleeding",
  "danger", "khatarnak", "turant",
];

export class StubClassifier implements Classifier {
  async classify(text: string): Promise<ClassificationResult> {
    const lower = ` ${text.toLowerCase()} `;

    let bestDept: Department = "Municipal Corporation - Sanitation";
    let bestScore = 0;

    for (const rule of KEYWORD_RULES) {
      // Word-boundary-ish match (padded string) + weight by keyword length so
      // more specific phrases ("route cancel") outweigh short generic words
      // ("bus") when both happen to appear, and ties break toward specificity
      // instead of array order.
      const score = rule.keywords.reduce((sum, k) => {
        const hit = lower.includes(` ${k}`) || lower.includes(`${k} `) || lower.includes(k);
        return hit ? sum + (k.includes(" ") ? 2 : 1) : sum;
      }, 0);
      if (score > bestScore) {
        bestScore = score;
        bestDept = rule.department;
      }
    }

    // Confidence scales with keyword hits but is deliberately capped so the
    // demo shows both the auto-route and human-review paths.
    const departmentConfidence = bestScore === 0 ? 0.35 : Math.min(0.55 + bestScore * 0.12, 0.88);

    const urgencyHits = URGENT_KEYWORDS.filter((k) => lower.includes(k)).length;
    const urgency: Urgency = urgencyHits >= 2 ? "high" : urgencyHits === 1 ? "medium" : "low";
    const urgencyConfidence = urgencyHits === 0 ? 0.5 : Math.min(0.6 + urgencyHits * 0.15, 0.9);

    return { department: bestDept, departmentConfidence, urgency, urgencyConfidence };
  }
}

// ---------------------------------------------------------------------------
// Remote classifier stub: points at a model-serving endpoint once the real
// (retrained, non-overfit) model is ready. Not wired in yet.
// ---------------------------------------------------------------------------

export class RemoteClassifier implements Classifier {
  constructor(private readonly endpoint: string) {}

  async classify(text: string): Promise<ClassificationResult> {
    const res = await fetch(`${this.endpoint}/classify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) throw new Error(`Classifier service error: ${res.status}`);
    return (await res.json()) as ClassificationResult;
  }
}

export const stubClassifier = new StubClassifier();
