// tRPC client setup for React frontend
import { createTRPCReact } from "@trpc/react-query";
import { httpBatchLink } from "@trpc/client";
import type { AppRouter } from "../../server/router";

// Create tRPC client
export const trpc = createTRPCReact<AppRouter>();

// Get auth token from storage
function getAuthToken(): string | null {
  if (typeof window !== "undefined") {
    return localStorage.getItem("echoteam_token");
  }
  return null;
}

// tRPC links with auth headers
const getLinks = () => {
  const url = import.meta.env.PROD
    ? `${import.meta.env.VITE_API_URL}/trpc`
    : "http://localhost:3001/trpc";

  return [
    httpBatchLink({
      url,
      headers() {
        const token = getAuthToken();
        return token ? { Authorization: `Bearer ${token}` } : {};
      },
    }),
  ];
};

// tRPC configuration
export const trpcClientConfig = {
  links: getLinks(),
};
