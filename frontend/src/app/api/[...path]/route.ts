import { type NextRequest, NextResponse } from "next/server";

const BACKEND = "https://servicenuwstock-api.onrender.com";

export async function GET(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  const target = `${BACKEND}/api/${path.join("/")}${request.nextUrl.search}`;
  try {
    const resp = await fetch(target, { cache: "no-store" });
    const data = await resp.text();
    return new NextResponse(data, {
      status: resp.status,
      headers: {
        "Content-Type": resp.headers.get("Content-Type") || "application/json",
        "Access-Control-Allow-Origin": "*",
      },
    });
  } catch {
    return NextResponse.json({ error: "Backend unreachable" }, { status: 502 });
  }
}
