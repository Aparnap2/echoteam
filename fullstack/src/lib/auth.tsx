// Simple JWT Auth for React frontend
import { useState, useEffect, createContext, useContext, type ReactNode } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:3001";

// User type
interface User {
  id: string;
  email: string;
  name: string;
}

// Auth context
interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  signIn: (email: string, name?: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

// Get token from storage
function getToken(): string | null {
  return localStorage.getItem("echoteam_token");
}

// Set token in storage
function setToken(token: string): void {
  localStorage.setItem("echoteam_token", token);
}

// Remove token from storage
function removeToken(): void {
  localStorage.removeItem("echoteam_token");
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check for existing token
    const checkAuth = async () => {
      const token = getToken();
      if (!token) {
        setIsLoading(false);
        return;
      }

      try {
        const response = await fetch(`${API_URL}/api/auth/verify`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        });

        if (response.ok) {
          const data = await response.json();
          setUser(data.user);
        } else {
          removeToken();
        }
      } catch {
        removeToken();
      }
      setIsLoading(false);
    };

    checkAuth();
  }, []);

  const signIn = async (email: string, name?: string) => {
    const response = await fetch(`${API_URL}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, name }),
    });

    if (!response.ok) {
      throw new Error("Login failed");
    }

    const data = await response.json();
    setToken(data.token);
    setUser(data.user);
  };

  const signOut = async () => {
    removeToken();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
