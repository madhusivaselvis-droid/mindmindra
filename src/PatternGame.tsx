import { useState } from 'react';
import { X } from 'lucide-react';
import { calculateMetrics } from './gameLogic';

type PatternRound = { shown: string[]; answer: string; choices: string[] };
const EASY_ROUNDS: PatternRound[] = [
  {shown: ['●', '▲', '●'], answer: '▲', choices: ['▲', '■']},
  {shown: ['■', '◆', '■'], answer: '◆', choices: ['●', '◆']},
];
const MEDIUM_ROUNDS: PatternRound[] = [
  {shown: ['●', '▲', '●', '▲'], answer: '●', choices: ['●', '■', '◆']},
  {shown: ['■', '●', '■', '●'], answer: '■', choices: ['▲', '■', '◆']},
  {shown: ['◆', '●', '▲', '◆', '●'], answer: '▲', choices: ['●', '▲', '■']},
];
const HARD_ROUNDS: PatternRound[] = [
  {shown: ['●', '▲', '■', '●', '▲'], answer: '■', choices: ['■', '◆', '●', '▲']},
  {shown: ['◆', '◆', '●', '◆', '◆'], answer: '●', choices: ['▲', '●', '■', '◆']},
  {shown: ['▲', '●', '●', '▲', '●', '●'], answer: '▲', choices: ['▲', '■', '◆', '●']},
  {shown: ['■', '▲', '■', '●', '■', '▲'], answer: '■', choices: ['●', '■', '▲', '◆']},
];
export const PATTERN_ROUNDS: PatternRound[] = MEDIUM_ROUNDS;
export function patternRoundsForDifficulty(level: number): PatternRound[] {
  if (level <= 1) return EASY_ROUNDS;
  if (level >= 3) return HARD_ROUNDS;
  return MEDIUM_ROUNDS;
}

export default function PatternGame({difficultyLevel,onComplete,onCancel}:{difficultyLevel:number;onComplete:(metrics:{score:number;accuracy:number;response_time:number;attempts:number;mistakes:number})=>void;onCancel:()=>void}) {
  const [round, setRound] = useState(0);
  const [mistakes, setMistakes] = useState(0);
  const [feedback, setFeedback] = useState('');
  const [startedAt] = useState(Date.now());
  const rounds = patternRoundsForDifficulty(difficultyLevel);
  const current = rounds[round];

  function choose(shape: string) {
    if (shape !== current.answer) {
      setMistakes(value => value + 1);
      setFeedback('Not that shape. Look at the repeating pattern and try again.');
      return;
    }
    if (round === rounds.length - 1) {
      onComplete(calculateMetrics(mistakes, rounds.length, Date.now() - startedAt));
      return;
    }
    setRound(value => value + 1);
    setFeedback('Correct. Here is the next pattern.');
  }

  return <section className="game-stage pattern-stage" aria-labelledby="pattern-title">
    <button className="close-game" onClick={onCancel} title="Close game"><X size={18}/></button>
    <p className="eyebrow">LEVEL {difficultyLevel} · PATTERN {round + 1} OF {rounds.length}</p>
    <h3 id="pattern-title" className="game-instruction">Which shape comes next?</h3>
    <p className="pattern-sequence" aria-label={`Pattern ${current.shown.join(' ')}, what comes next?`}>
      {current.shown.map((shape, index) => <span className="pattern-shape" key={`${round}-${index}`}>{shape}</span>)}
      <span className="pattern-shape missing" aria-hidden="true">?</span>
    </p>
    <div className="game-progress" role="progressbar" aria-label="Pattern rounds completed" aria-valuemin={0} aria-valuemax={rounds.length} aria-valuenow={round}>
      <i style={{width:`${round / rounds.length * 100}%`}} />
    </div>
    <p className="pattern-prompt">Choose one shape</p>
    <div className="pattern-choices">{current.choices.map(shape => <button className="play-tile" key={shape} onClick={() => choose(shape)} aria-label={`Choose ${shape}`}>{shape}</button>)}</div>
    <p className="pattern-feedback" aria-live="polite">{feedback || 'Take your time. You can try again.'}</p>
    <span className="mistake-count">Mistakes: {mistakes}</span>
  </section>;
}
