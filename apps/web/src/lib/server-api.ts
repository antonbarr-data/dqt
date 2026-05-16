const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function serverFetch<T>(path: string, revalidate = 30): Promise<T | null> {
  try {
    const res = await fetch(`${BACKEND}/api/v1${path}`, {
      next: { revalidate },
    });
    if (!res.ok) return null;
    return res.json() as Promise<T>;
  } catch {
    return null;
  }
}
