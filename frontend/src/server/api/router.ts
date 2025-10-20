import { z } from "zod";
import { prisma } from "@/lib/prisma";
import { publicProcedure, router } from "./trpc";

export const appRouter = router({
  getProjects: publicProcedure.query(async ({ ctx }) => {
    if (!ctx.userId) {
      return [];
    }

    const projects = await prisma.project.findMany({
      where: { userId: ctx.userId },
      orderBy: { updatedAt: "desc" },
      take: 50,
    });
    return projects;
  }),
  createProject: publicProcedure
    .input(
      z.object({
        title: z.string().min(1),
        prompt: z.string().min(1),
      }),
    )
    .mutation(async ({ input, ctx }) => {
      if (!ctx.userId) {
        throw new Error("Unauthorized");
      }

      const project = await prisma.project.create({
        data: {
          userId: ctx.userId,
          title: input.title,
          prompt: input.prompt,
        },
      });
      return project;
    }),
});

export type AppRouter = typeof appRouter;
