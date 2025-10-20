export type SandboxRunResult = {
  stdout: string;
  stderr: string;
  exitCode: number;
};

export async function runInSandbox(commands: string[]): Promise<SandboxRunResult> {
  if (!process.env.E2B_API_KEY) {
    throw new Error("E2B_API_KEY is not configured");
  }

  // TODO: integrate official E2B client once available
  return {
    stdout: `Sandbox execution not yet implemented. Received ${commands.length} commands.`,
    stderr: "",
    exitCode: 0,
  };
}
