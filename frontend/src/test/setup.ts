import '@testing-library/jest-dom/vitest';

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: () => ({ matches: false, addEventListener: () => undefined, removeEventListener: () => undefined }),
});
Object.defineProperty(URL, 'createObjectURL', { writable: true, value: () => 'blob:preview' });
Object.defineProperty(URL, 'revokeObjectURL', { writable: true, value: () => undefined });
const storage = new Map<string, string>();
Object.defineProperty(window, 'localStorage', {
  writable: true,
  value: {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => storage.set(key, value),
    removeItem: (key: string) => storage.delete(key),
    clear: () => storage.clear(),
  },
});
