"use client";

import React, { createContext, useContext, useState, useCallback } from "react";

type User = { id: string; email: string };

type AuthContextType = {
  user: User | null;
  isAuthenticated: boolean;
  login: (user: User) => void;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children, initialUser }: { children: React.ReactNode; initialUser: User | null }) {
  const [user, setUser] = useState<User | null>(initialUser);

  const login = useCallback((newUser: User) => {
    setUser(newUser);
  }, []);

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, login }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
