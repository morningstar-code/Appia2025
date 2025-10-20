import { auth } from "@clerk/nextjs/server";
import { initTRPC } from "@trpc/server";
import superjson from "superjson";

type TrpcContext = {
  userId: string | null;
  getAuth: () => Promise<Awaited<ReturnType<typeof auth>>>;
};

export const createTRPCContext = async () => {
  const authResult = await auth();
  return {
    userId: authResult.userId,
    getAuth: async () => authResult,
  } satisfies TrpcContext;
};

const t = initTRPC.context<TrpcContext>().create({
  transformer: superjson,
});

export const createCallerFactory = t.createCallerFactory;
export const router = t.router;
export const publicProcedure = t.procedure;
