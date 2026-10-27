import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({
	plugins: [react()],
	server: {
		proxy: {
			'/auth': 'http://localhost:8000',
			'/patients': 'http://localhost:8000',
			'/game-sessions': 'http://localhost:8000',
			'/game-results': 'http://localhost:8000',
			'/sync': 'http://localhost:8000',
			'/reminders': 'http://localhost:8000',
			'/analytics': 'http://localhost:8000',
			'/recommendations': 'http://localhost:8000',
			'/alerts': 'http://localhost:8000',
		},
	},
	build: {
		rollupOptions: {
			output: {
				manualChunks: { icons: ['lucide-react'] },
			},
		},
	},
});
