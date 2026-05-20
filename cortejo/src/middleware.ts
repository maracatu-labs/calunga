import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const COOKIE_NAME = "maracatu_token";
const PROTECTED_PATHS = ["/chat"];
const AUTH_PATHS = ["/login", "/auth/verify"];

export function middleware(request: NextRequest) {
  const token = request.cookies.get(COOKIE_NAME)?.value;
  const { pathname } = request.nextUrl;

  if (PROTECTED_PATHS.some((p) => pathname.startsWith(p))) {
    if (!token) {
      return NextResponse.redirect(new URL("/login", request.url));
    }
  }

  if (AUTH_PATHS.some((p) => pathname.startsWith(p))) {
    if (token) {
      return NextResponse.redirect(new URL("/chat", request.url));
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/chat/:path*", "/login", "/auth/:path*"],
};
