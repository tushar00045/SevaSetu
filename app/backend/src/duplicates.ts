/**
 * Duplicate detection.
 *
 * This uses token-overlap (Jaccard) similarity against recent open tickets
 * in the same department as a fast, dependency-free approximation.
 * It is NOT semantic similarity — "bijli nahi hai" and "no electricity"
 * won't match each other here. The research/pitch cites IndicSBERT for
 * true cross-lingual semantic duplicate detection; swap this module for
 * an embedding-based cosine-similarity lookup once that service exists.
 * The threshold and candidate pool are exposed as config so that swap is
 * a one-function change (`findDuplicate`), not a rewrite of callers.
 */

import db from "./db.js";
import type { Department } from "./classifier.js";

const SIMILARITY_THRESHOLD = 0.55;
const CANDIDATE_POOL_SIZE = 200; // recent open tickets to compare against, per department

function tokenize(text: string): Set<string> {
  return new Set(
    text
      .toLowerCase()
      .replace(/[^\w\s]/g, " ")
      .split(/\s+/)
      .filter((t) => t.length > 2)
  );
}

function jaccard(a: Set<string>, b: Set<string>): number {
  if (a.size === 0 || b.size === 0) return 0;
  let intersection = 0;
  for (const t of a) if (b.has(t)) intersection++;
  const union = a.size + b.size - intersection;
  return union === 0 ? 0 : intersection / union;
}

export interface DuplicateMatch {
  ticketId: string;
  similarity: number;
}

export function findDuplicate(text: string, department: Department): DuplicateMatch | null {
  const candidates = db
    .prepare(
      `SELECT id, complaint_text FROM tickets
       WHERE department = ? AND status NOT IN ('resolved', 'closed_no_action')
       ORDER BY created_at DESC LIMIT ?`
    )
    .all(department, CANDIDATE_POOL_SIZE) as Array<{ id: string; complaint_text: string }>;

  const inputTokens = tokenize(text);
  let best: DuplicateMatch | null = null;

  for (const c of candidates) {
    const sim = jaccard(inputTokens, tokenize(c.complaint_text));
    if (sim >= SIMILARITY_THRESHOLD && (best === null || sim > best.similarity)) {
      best = { ticketId: c.id, similarity: sim };
    }
  }

  return best;
}
