export type GameMetrics = { score: number; accuracy: number; response_time: number; attempts: number; mistakes: number };

export function calculateMetrics(mistakes: number, target: number, elapsedMs: number): GameMetrics {
  const safeTarget = Math.max(1, target);
  const attempts = safeTarget + mistakes;
  const accuracy = safeTarget / attempts;
  return { score: Math.round(accuracy * 100), accuracy, response_time: elapsedMs / 1000, attempts, mistakes };
}