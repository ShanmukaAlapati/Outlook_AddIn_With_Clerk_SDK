// pages/sign-out.tsx
"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";

export default function SignOutPage() {
    const { isLoaded, isSignedIn, signOut } = useAuth();
    const [signingOut, setSigningOut] = useState(false);

    useEffect(() => {
        if (!isLoaded) return;
        if (!isSignedIn) window.location.href = "/sign-in";
    }, [isLoaded, isSignedIn]);

    async function handleSignOut() {
        setSigningOut(true);
        try {
            await signOut();
            window.location.href = "/sign-in";
        } catch {
            setSigningOut(false);
        }
    }

    if (!isLoaded || !isSignedIn) {
        return (
            <div style={{ padding: 24, fontFamily: "Arial, sans-serif" }}>
                <p style={{ color: "#6b7280", fontSize: 13 }}>Redirecting…</p>
            </div>
        );
    }

    return (
        <div style={{
            minHeight: "100vh", display: "flex", alignItems: "center",
            justifyContent: "center", background: "#f9fafb", fontFamily: "Arial, sans-serif",
        }}>
            <div style={{
                background: "#fff", border: "1px solid #e5e7eb", borderRadius: 12,
                padding: "32px 28px", width: "100%", maxWidth: 360, textAlign: "center",
                boxShadow: "0 4px 24px rgba(0,0,0,0.06)",
            }}>
                <div style={{
                    width: 48, height: 48, borderRadius: "50%", background: "#fef2f2",
                    border: "1px solid #fecaca", display: "flex", alignItems: "center",
                    justifyContent: "center", margin: "0 auto 16px", fontSize: 22,
                }}>🔒</div>

                <h2 style={{ fontSize: 17, fontWeight: 700, color: "#111", margin: "0 0 8px" }}>
                    Sign out of Case Counsel?
                </h2>
                <p style={{ fontSize: 13, color: "#6b7280", margin: "0 0 24px", lineHeight: 1.5 }}>
                    You will be returned to the sign-in page.
                </p>

                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    <button
                        onClick={handleSignOut}
                        disabled={signingOut}
                        style={{
                            width: "100%", padding: "10px 0", fontSize: 13, fontWeight: 600,
                            background: signingOut ? "#9ca3af" : "#ef4444", color: "#fff",
                            border: "none", borderRadius: 7, cursor: signingOut ? "not-allowed" : "pointer",
                        }}
                    >
                        {signingOut ? "Signing out…" : "Yes, sign me out"}
                    </button>

                    <button
                        onClick={() => window.location.href = "/app"}
                        disabled={signingOut}
                        style={{
                            width: "100%", padding: "10px 0", fontSize: 13,
                            background: "#fff", color: "#374151",
                            border: "1px solid #e5e7eb", borderRadius: 7, cursor: "pointer",
                        }}
                    >
                        Cancel
                    </button>
                </div>
            </div>
        </div>
    );
}
