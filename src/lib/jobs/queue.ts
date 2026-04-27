import PQueue from "p-queue";

export const emailQueue = new PQueue({ concurrency: 1 });
