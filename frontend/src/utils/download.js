import { authHeaders } from "../stores/auth";

export async function downloadProtectedFile(url, fallbackName) {
  const response = await fetch(url, {
    method: "GET",
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }

  const contentDisposition = response.headers.get("content-disposition") || "";
  const matched = contentDisposition.match(/filename="?([^"]+)"?/i);
  const fileName = matched?.[1] || fallbackName;
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}
