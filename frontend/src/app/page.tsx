import Link from "next/link";
import { auth } from "@clerk/nextjs/server";
import { prisma } from "@/lib/prisma";

export default async function Page() {
  const { userId } = auth();

  if (!userId) {
    return (
      <main className="mx-auto flex min-h-[calc(100vh-64px)] max-w-4xl flex-col items-center justify-center gap-6 text-center">
        <h1 className="text-3xl font-semibold">Welcome to Appia Builder</h1>
        <p className="text-muted-foreground">
          Sign in to start generating projects, managing credits, and collaborating with the AI agent toolkit.
        </p>
        <p className="text-sm text-muted-foreground">
          Use the buttons in the header to authenticate.
        </p>
      </main>
    );
  }

  const projects = await prisma.project.findMany({
    where: { userId },
    orderBy: { updatedAt: "desc" },
    take: 10,
  });

  return (
    <main className="mx-auto flex min-h-[calc(100vh-64px)] w-full max-w-5xl flex-col gap-8 px-6 py-10">
      <section>
        <h1 className="text-3xl font-semibold">Your recent projects</h1>
        <p className="text-muted-foreground">
          Select a project to resume building, or start a fresh build from the command bar.
        </p>
      </section>
      <section className="grid gap-4 md:grid-cols-2">
        {projects.length === 0 ? (
          <div className="rounded-lg border border-dashed p-6 text-center text-muted-foreground">
            No projects yet. Generate your first build to see it appear here.
          </div>
        ) : (
          projects.map((project) => (
            <Link
              key={project.id}
              href={`/builder/${project.id}`}
              className="rounded-lg border bg-card p-5 shadow-sm transition hover:border-primary/60 hover:shadow-md"
            >
              <h2 className="text-lg font-medium">{project.title}</h2>
              <p className="mt-2 line-clamp-3 text-sm text-muted-foreground">
                {project.prompt}
              </p>
              <p className="mt-4 text-xs text-muted-foreground">
                Updated {project.updatedAt.toLocaleString()}
              </p>
            </Link>
          ))
        )}
      </section>
    </main>
  );
}
