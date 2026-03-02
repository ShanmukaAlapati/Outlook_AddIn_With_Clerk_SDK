// pages/index.tsx
import { useEffect } from "react";
import { useAuth } from "@clerk/nextjs";

export default function Index() {
  const { isLoaded, isSignedIn } = useAuth();

  useEffect(() => {
    if (!isLoaded) return;
    window.location.href = isSignedIn ? "/app" : "/sign-in";
  }, [isLoaded, isSignedIn]);

  return null;
}
