// localStorage that never throws (private mode, blocked storage).
export const storage = {
  get(key) {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  },
  set(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch {
      /* nothing to do */
    }
  },
  remove(key) {
    try {
      localStorage.removeItem(key);
    } catch {
      /* nothing to do */
    }
  },
};
