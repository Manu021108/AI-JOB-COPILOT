const TOKEN_KEY = "ai_job_copilot_token";
export const getToken = () => typeof window === "undefined" ? null : sessionStorage.getItem(TOKEN_KEY);
export const setToken = (token: string) => sessionStorage.setItem(TOKEN_KEY, token);
export const clearToken = () => sessionStorage.removeItem(TOKEN_KEY);
