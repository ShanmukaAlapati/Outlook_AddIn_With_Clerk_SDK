import { useEffect, useState } from "react";
import { useAuth, useUser } from "@clerk/nextjs";

export default function App() {
  const { isLoaded, isSignedIn, getToken, signOut } = useAuth();
  const { user } = useUser();
  const [verified, setVerified] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) {
      window.location.href = "/sign-in";
      return;
    }
    verify();
  }, [isLoaded, isSignedIn]);

  async function verify() {
    try {
      const token = await getToken();
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";
      const res = await fetch(`${apiUrl}/api/check-user`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      });
      if (!res.ok) throw new Error(`Server error ${res.status}`);
      setVerified(true);
    } catch (err: any) {
      setError(err.message);
    }
  }

  async function handleSignOut() {
    await signOut();
    window.location.href = "/sign-in";
  }

  if (!isLoaded || (isSignedIn && !verified && !error)) {
    return (
      <div style={{ padding: 24, fontFamily: "Arial, sans-serif" }}>
        <p style={{ color: "#555" }}>Loading...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 24, fontFamily: "Arial, sans-serif" }}>
        <h2>Case Counsel</h2>
        <p style={{ color: "red", fontSize: 14 }}>Error: {error}</p>
        <button onClick={verify}>Retry</button>
      </div>
    );
  }

  return (
    <div style={{ padding: 24, fontFamily: "Arial, sans-serif" }}>
      <div style={{
        display: "flex", justifyContent: "space-between",
        alignItems: "center", borderBottom: "1px solid #e5e7eb",
        paddingBottom: 12, marginBottom: 16,
      }}>
        <strong style={{ fontSize: 16 }}>Case Counsel</strong>
        <button
          onClick={handleSignOut}
          style={{
            fontSize: 12, color: "#555", background: "none",
            border: "1px solid #ccc", borderRadius: 4,
            padding: "4px 10px", cursor: "pointer",
          }}
        >
          Sign out
        </button>
      </div>

      <p style={{ color: "#555", fontSize: 13, marginBottom: 16 }}>
        Signed in as <strong>{user?.primaryEmailAddress?.emailAddress}</strong>
      </p>

      <div style={{
        background: "#f9fafb", border: "1px solid #e5e7eb",
        borderRadius: 8, padding: 16,
      }}>
        <p style={{ color: "#555", fontSize: 13 }}>Your workspace is ready.</p>
      </div>
    </div>
  );
}