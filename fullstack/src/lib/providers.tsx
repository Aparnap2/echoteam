// React Query, tRPC, and Auth providers
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { httpBatchLink } from "@trpc/client";
import { useState } from "react";
import { trpc, trpcClientConfig } from "./trpc";
import { AuthProvider } from "./auth.tsx";

// Combined providers wrapper
export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 5 * 60 * 1000, // 5 minutes
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  const [trpcClient] = useState(() =>
    trpc.createClient(trpcClientConfig)
  );

  return (
    <trpc.Provider client={trpcClient} queryClient={queryClient}>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          {children}
        </AuthProvider>
      </QueryClientProvider>
    </trpc.Provider>
  );
}

// Re-export for backward compatibility
export function TRPCProvider({ children }: { children: React.ReactNode }) {
  return <Providers>{children}</Providers>;
}
