import { clerkMiddleware } from "@clerk/nextjs/server";

// Minimal — no redirects. Pages handle their own auth.
// Office.js breaks App Router's window.history, so we use Pages Router.
export default clerkMiddleware();

export const config = {
  matcher: ["/((?!_next|.*\\..*).*)"],
};
