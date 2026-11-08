import { NextResponse } from "next/server";
import { loadGuilds, ServiceError, serviceMessage } from "@/lib/bot-api";
export async function GET() {
  try {
    return NextResponse.json(
      { guilds: await loadGuilds() },
      { headers: { "Cache-Control": "no-store" } },
    );
  } catch (error) {
    return NextResponse.json(
      { error: serviceMessage(error) },
      {
        status: error instanceof ServiceError ? error.status : 500,
        headers: { "Cache-Control": "no-store" },
      },
    );
  }
}
