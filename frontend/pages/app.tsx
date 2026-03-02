"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth, useUser } from "@clerk/nextjs";

interface AuthInfo {
  user_id: string;
  org_id: string;
  org_role: "org:admin" | "org:member" | string;
}

type Status = "idle" | "loading" | "success" | "error";

export default function App() {
  const { getToken, signOut } = useAuth();
  const { user } = useUser();

  const [authInfo, setAuthInfo] = useState<AuthInfo | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState("");

  const verify = useCallback(async () => {
    setStatus("loading");
    setError("");
    try {
      const token = await getToken();
      if (!token) throw new Error("Session not ready. Please sign in again.");

      const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:5000";
      const res = await fetch(`${apiUrl}/api/check-user`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      });

      const body = await res.json();
      if (!res.ok) throw new Error(body.error ?? `Server error ${res.status}`);

      setAuthInfo(body.user_info);
      setStatus("success");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("error");
    }
  }, [getToken]);

  useEffect(() => {
    verify();
  }, [verify]);

  async function handleSignOut() {
    await signOut({ redirectUrl: "/sign-in" }); // ✅ Clerk-native redirect
  }

  if (status === "idle" || status === "loading") {
    return (
      <div style={{ padding: 24, fontFamily: "Arial, sans-serif" }}>
        <p style={{ color: "#6b7280", fontSize: 13 }}>Loading…</p>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div style={{ padding: 24, fontFamily: "Arial, sans-serif" }}>
        <h2 style={{ fontSize: 16, marginBottom: 8 }}>Case Counsel</h2>
        <p style={{ color: "#ef4444", fontSize: 13 }}>Error: {error}</p>
        <button
          onClick={verify}
          style={{
            marginTop: 8,
            fontSize: 12,
            padding: "6px 14px",
            borderRadius: 6,
            border: "1px solid #d1d5db",
            cursor: "pointer",
            background: "#fff",
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  const isAdmin = authInfo?.org_role === "org:admin";

  return (
    <div style={{ padding: 24, fontFamily: "Arial, sans-serif" }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderBottom: "1px solid #e5e7eb",
          paddingBottom: 12,
          marginBottom: 16,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <strong style={{ fontSize: 16 }}>Case Counsel</strong>
          {isAdmin && (
            <span
              style={{
                fontSize: 9,
                fontWeight: 700,
                background: "#7c3aed22",
                color: "#7c3aed",
                border: "1px solid #7c3aed44",
                borderRadius: 8,
                padding: "2px 7px",
                textTransform: "uppercase",
                letterSpacing: 0.5,
              }}
            >
              Admin
            </span>
          )}
        </div>
        <button
          onClick={handleSignOut}
          style={{
            fontSize: 12,
            color: "#555",
            background: "none",
            border: "1px solid #ccc",
            borderRadius: 4,
            padding: "4px 10px",
            cursor: "pointer",
          }}
        >
          Sign out
        </button>
      </div>

      {/* User info */}
      <p style={{ color: "#555", fontSize: 13, marginBottom: 16 }}>
        Signed in as{" "}
        <strong>{user?.primaryEmailAddress?.emailAddress}</strong>
      </p>

      {/* Workspace */}
      <div
        style={{
          background: "#f9fafb",
          border: "1px solid #e5e7eb",
          borderRadius: 8,
          padding: 16,
        }}
      >
        <p style={{ color: "#555", fontSize: 13, margin: 0 }}>
          {isAdmin ? "Your admin workspace is ready." : "Your workspace is ready."}
        </p>
        {authInfo?.org_id && (
          <p style={{ color: "#9ca3af", fontSize: 11, marginTop: 6 }}>
            Organisation: <code>{authInfo.org_id}</code>
          </p>
        )}
      </div>
    </div>
  );
}
