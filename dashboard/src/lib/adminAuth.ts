export async function adminFetch(path: string, init: RequestInit = {}): Promise<Response> {
  return fetch(`/api/reputation/${path}`, init)
}
