import { notebookNameAvailable, supportedImages, getGpuAvailability } from "./notebooks";

export class InvalidFormError extends Error {}

export async function validateNotebookForm(form: {
  notebook_name: string;
  image: string;
  cpu_request: number;
  memory_request: number;
  gpu_request: number;
  gpu_product: string;
}): Promise<void> {
  const VALID_CHARS = /^[a-zA-Z0-9._-]+$/;
  if (/\s/.test(form.notebook_name)) {
    throw new InvalidFormError("The notebook name cannot have whitespace characters.");
  }
  if (form.notebook_name.length > 30) {
    throw new InvalidFormError("The notebook name cannot exceed 30 characters.");
  }
  if (!VALID_CHARS.test(form.notebook_name)) {
    throw new InvalidFormError("Valid characters are [a-zA-Z0-9._-]");
  }
  if (!(await notebookNameAvailable(form.notebook_name))) {
    throw new InvalidFormError(`The name ${form.notebook_name} is already taken.`);
  }
  if (!supportedImages().includes(form.image)) {
    throw new InvalidFormError(`Docker image ${form.image} is not supported.`);
  }
  if (form.cpu_request < 1 || form.cpu_request > 16) {
    throw new InvalidFormError("Requests must be between 1 and 16 CPUs.");
  }
  if (form.memory_request < 1 || form.memory_request > 256) {
    throw new InvalidFormError("Requests must be between 1 and 256 GB RAM.");
  }
  if (form.gpu_request < 0 || form.gpu_request > 7) {
    throw new InvalidFormError("Requests must be between 0 and 7 GPUs.");
  }
  if (form.gpu_request > 0) {
    const gpus = await getGpuAvailability(form.gpu_product);
    if (gpus.length === 0) {
      throw new InvalidFormError(`GPU product ${form.gpu_product} not found.`);
    }
    const gpu = gpus[0];
    if (gpu.available < form.gpu_request) {
      if (gpu.available === 0) {
        throw new InvalidFormError(`The ${gpu.product} is currently not available.`);
      }
      if (gpu.available === 1) {
        throw new InvalidFormError(`The ${gpu.product} has only 1 instance available.`);
      }
      throw new InvalidFormError(
        `The ${gpu.product} has only ${gpu.available} instances available.`
      );
    }
    if (form.cpu_request > gpu.cpu_request_max) {
      throw new InvalidFormError(
        `The request of ${form.cpu_request} CPUs is more than maximum available (${gpu.cpu_request_max}) for the selected GPU type.`
      );
    }
    if (form.memory_request > gpu.mem_request_max) {
      throw new InvalidFormError(
        `The request of ${form.memory_request} GB Mem is more than maximum available (${gpu.mem_request_max}) for the selected GPU type.`
      );
    }
  }
}
