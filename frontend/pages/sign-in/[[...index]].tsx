import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
  return (
    <div style={{
      minHeight: "100vh",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      fontFamily: "Arial, sans-serif",
      background: "#fff",
    }}>
      <h2 style={{ marginBottom: 24 }}>Case Counsel</h2>
      <SignIn
        routing="path"
        path="/sign-in"
        fallbackRedirectUrl="/app"
        signUpUrl="/sign-in"
      />
    </div>
  );
}