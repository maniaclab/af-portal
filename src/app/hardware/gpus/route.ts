import { NextResponse } from "next/server";
import { getGpuAvailability } from "@/lib/kubernetes/notebooks";

export const dynamic = "force-dynamic";

export async function GET() {
  const gpus = await getGpuAvailability();
  return NextResponse.json({ gpus });
}
