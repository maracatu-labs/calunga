import { cookies } from "next/headers";
import { redirect } from "next/navigation";

const COOKIE_NAME = "maracatu_token";

export async function GET() {
  const cookieStore = await cookies();
  cookieStore.set(COOKIE_NAME, "", {
    httpOnly: true,
    secure: process.env.COOKIE_SECURE !== "false",
    sameSite: "lax",
    path: "/",
    maxAge: 0,
  });

  redirect("/login");
}
