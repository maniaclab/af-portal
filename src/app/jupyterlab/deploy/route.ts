import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth/session";
import { deployNotebook } from "@/lib/kubernetes/notebooks";
import {
  validateNotebookForm,
  InvalidFormError,
} from "@/lib/kubernetes/validation";
import { sanitizeK8sPodName } from "@/lib/kubernetes/utils";

export async function POST(request: NextRequest) {
  const session = await getSession();
  if (!session.is_authenticated || !session.unix_name) {
    return NextResponse.redirect(new URL("/auth/login", request.url));
  }

  const formData = await request.formData();
  const notebookName = (formData.get("notebook-name") as string).trim();
  const image = formData.get("image") as string;
  const cpuRequest = parseInt(formData.get("cpu") as string, 10);
  const memoryRequest = parseInt(formData.get("memory") as string, 10);
  const gpuRequest = parseInt(formData.get("gpu") as string, 10);
  const gpuProduct = (formData.get("gpu-product") as string) ?? "";
  const duration = parseInt(formData.get("duration") as string, 10);

  try {
    await validateNotebookForm({
      notebook_name: notebookName,
      image,
      cpu_request: cpuRequest,
      memory_request: memoryRequest,
      gpu_request: gpuRequest,
      gpu_product: gpuProduct,
    });

    await deployNotebook({
      notebook_name: notebookName,
      notebook_id: sanitizeK8sPodName(notebookName.toLowerCase()),
      image,
      owner: session.unix_name,
      owner_uid: session.unix_id ?? 0,
      globus_id: session.globus_id,
      cpu_request: cpuRequest,
      cpu_limit: cpuRequest * 2,
      memory_request: `${memoryRequest}Gi`,
      memory_limit: `${memoryRequest * 2}Gi`,
      gpu_request: gpuRequest,
      gpu_limit: gpuRequest,
      gpu_product: gpuProduct,
      hours_remaining: duration,
    });
  } catch (err) {
    if (err instanceof InvalidFormError) {
      session.flash = { message: err.message, category: "warning" };
      await session.save();
      return NextResponse.redirect(
        new URL("/jupyterlab/configure", request.url)
      );
    }
    throw err;
  }

  return NextResponse.redirect(new URL("/jupyterlab", request.url));
}
