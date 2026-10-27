import { csrfHeaders } from './auth';
const API_URL = import.meta.env.VITE_API_URL || '';

async function safeJson(response: Response): Promise<Record<string, string>> {
  try { return await response.json(); } catch { return {}; }
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { ...options, credentials: 'include', headers: { 'Content-Type': 'application/json', ...csrfHeaders(), ...(options.headers || {}) } });
  if (!response.ok) throw new Error((await safeJson(response)).detail || 'Request failed');
  return response.status === 204 ? (undefined as T) : response.json();
}

export type Patient = { id: string; name: string; email: string; role: string };
export type Reminder = { id: string; patient_id: string; title: string; reminder_type: string; reminder_time: string; recurrence: string; enabled: boolean };
export type PatternRecommendation = { game_type: string; cps: number; components: {accuracy:number;reaction:number;completion:number;consistency:number}; score: number; accuracy_percent: number; response_time: number; attempts: number; previous_difficulty: number; next_difficulty: number; next_activity: string; model_used: string; caregiver_notification: boolean; explanation: string };

export function createPatient(payload: {name:string;email:string;password:string;preferred_language:string;region?:string}) { return apiRequest<Patient>('/patients', {method:'POST', body:JSON.stringify(payload)}); }
export function getReminders(patientId: string) { return apiRequest<Reminder[]>(`/reminders?patient_id=${patientId}`); }
export function addReminder(payload: {patient_id:string;title:string;reminder_type:string;time:string;recurrence:string}) { return apiRequest<Reminder>('/reminders', {method:'POST', body:JSON.stringify(payload)}); }
export function updateReminder(id: string, payload: {patient_id:string;title:string;reminder_type:string;time:string;recurrence:string}) { return apiRequest<Reminder>(`/reminders/${id}`, {method:'PUT', body:JSON.stringify(payload)}); }
export function completeReminder(id: string) { return apiRequest<{status:string}>(`/reminders/${id}/complete`, {method:'PATCH'}); }
export function disableReminder(id: string) { return apiRequest<{status:string}>(`/reminders/${id}`, {method:'DELETE'}); }
export function getPatternRecommendation(patientId: string) { return apiRequest<PatternRecommendation>(`/recommendations/${patientId}?game_type=PATTERN_RECOGNITION`); }
