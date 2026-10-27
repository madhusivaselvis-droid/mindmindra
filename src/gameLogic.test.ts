import { describe, expect, it } from 'vitest';
import { calculateMetrics } from './gameLogic';
import { PATTERN_ROUNDS, patternRoundsForDifficulty } from './PatternGame';

describe('game metrics', () => {
  it('scores a clean completed game at full accuracy', () => {
    expect(calculateMetrics(0, 6, 3200)).toEqual({score: 100, accuracy: 1, response_time: 3.2, attempts: 6, mistakes: 0});
  });
  it('keeps difficult results bounded and meaningful', () => {
    const metrics = calculateMetrics(9, 6, 1000);
    expect(metrics.score).toBe(40);
    expect(metrics.accuracy).toBe(0.4);
    expect(metrics.attempts).toBe(15);
  });
});

describe('pattern recognition rounds', () => {
  it('shows a visible sequence with a valid next-shape answer on every round', () => {
    expect(PATTERN_ROUNDS).toHaveLength(3);
    for (const round of PATTERN_ROUNDS) {
      expect(round.shown.length).toBeGreaterThanOrEqual(4);
      expect(round.choices).toContain(round.answer);
    }
  });
  it('provides different round counts for easy, medium, and hard levels', () => {
    expect(patternRoundsForDifficulty(1)).toHaveLength(2);
    expect(patternRoundsForDifficulty(2)).toHaveLength(3);
    expect(patternRoundsForDifficulty(3)).toHaveLength(4);
  });
});