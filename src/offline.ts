export type GameResult = { event_id: string; patient_id: string; game_type: string; score: number; accuracy: number; difficulty_level: number; response_time: number; attempts: number; mistakes: number; completed: boolean; timestamp: string };
const DB_NAME = 'mindner-offline';
const DEMO_PATIENT_ID = '11111111-1111-1111-1111-111111111111';

export function queueResult(result: GameResult): Promise<void> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = () => request.result.createObjectStore('sync_queue', { keyPath: 'event_id' });
    request.onsuccess = () => { const tx = request.result.transaction('sync_queue', 'readwrite'); tx.objectStore('sync_queue').put(result); tx.oncomplete = () => resolve(); tx.onerror = () => reject(tx.error); };
    request.onerror = () => reject(request.error);
  });
}

export async function pendingCount(): Promise<number> {
  return new Promise((resolve) => { const request = indexedDB.open(DB_NAME, 1); request.onupgradeneeded = () => request.result.createObjectStore('sync_queue', { keyPath: 'event_id' }); request.onsuccess = () => { const count = request.result.transaction('sync_queue').objectStore('sync_queue').count(); count.onsuccess = () => resolve(count.result); }; request.onerror = () => resolve(0); });
}

export async function syncQueuedResults(): Promise<number> {
  if (!navigator.onLine) return 0;
  const request = indexedDB.open(DB_NAME, 1);
  return new Promise((resolve) => {
    request.onupgradeneeded = () => request.result.createObjectStore('sync_queue', { keyPath: 'event_id' });
    request.onsuccess = () => {
      const store = request.result.transaction('sync_queue', 'readonly').objectStore('sync_queue');
      const read = store.getAll();
      read.onsuccess = async () => {
        if (!read.result.length) return resolve(0);
        try {
          const compatible = read.result.map((item: GameResult) => ({...item, patient_id: item.patient_id || DEMO_PATIENT_ID, mistakes: item.mistakes || 0}));
          const csrf = document.cookie.split('; ').find(item => item.startsWith('mindner_csrf='))?.split('=')[1];
          const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/sync`, { method: 'POST', credentials: 'include', headers: {'Content-Type': 'application/json', ...(csrf ? {'X-CSRF-Token': decodeURIComponent(csrf)} : {}), 'X-Demo-User': 'patient-demo'}, body: JSON.stringify(compatible) });
          if (!response.ok) return resolve(0);
          const write = request.result.transaction('sync_queue', 'readwrite');
          read.result.forEach((item: GameResult) => write.objectStore('sync_queue').delete(item.event_id));
          write.oncomplete = () => resolve(read.result.length);
        } catch { resolve(0); }
      };
      read.onerror = () => resolve(0);
    };
    request.onerror = () => resolve(0);
  });
}
