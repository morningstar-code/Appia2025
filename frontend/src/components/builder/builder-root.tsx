'use client';

import { useRouter } from "next/navigation";
import axios from "axios";
import {
  FormEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import {
  FileItem,
  Step,
  StepType,
  ChatMessage,
} from "@/lib/builder/types";
import { useWebContainer } from "@/hooks/use-webcontainer";
import { BACKEND_URL } from "@/lib/builder/config";
import { parseXml } from "@/lib/builder/steps";
import { StepsList } from "./steps-list";
import { FileExplorer } from "./file-explorer";
import { CodeEditor } from "./code-editor";
import {
  PreviewFrame,
  PreviewStatus,
  PREVIEW_STATUS_LABELS,
} from "./preview-frame";
import { TabView } from "./tab-view";
import { Terminal } from "./terminal";
import { MessageCircle, Bot, User as UserIcon, Sparkles } from "lucide-react";

interface BuilderRootProps {
  prompt: string;
}

type ApiMessage = { role: 'user' | 'assistant'; content: string };

type IncomingStep = {
  title: string;
  description?: string;
  type: StepType;
  code?: string;
  path?: string;
};

const summarizeArtifact = (content: string): string => {
  const summaryBits: string[] = [];

  const titleMatch = content.match(/<boltArtifact[^>]*title="([^"]+)"/);
  if (titleMatch?.[1]) {
    summaryBits.push(titleMatch[1]);
  }

  const fileMatches = [...content.matchAll(/<boltAction\s+type="file"\s+filePath="([^"]+)"/g)].map(
    (match) => match[1],
  );
  if (fileMatches.length > 0) {
    const highlighted = fileMatches.slice(0, 3).join(', ');
    summaryBits.push(
      `Files: ${highlighted}${fileMatches.length > 3 ? `, +${fileMatches.length - 3} more` : ''}`,
    );
  }

  const commandMatches = [...content.matchAll(/<boltAction\s+type="shell">([\s\S]*?)<\/boltAction>/g)];
  if (commandMatches.length > 0) {
    const commands = commandMatches
      .map((match) => match[1].trim().split('\n')[0])
      .filter(Boolean)
      .slice(0, 2);
    if (commands.length) {
      summaryBits.push(`Commands: ${commands.join(', ')}`);
    }
  }

  return summaryBits.join(' • ');
};

const formatAssistantSummary = (content: string): string => {
  if (!content.trim()) {
    return '';
  }
  const artifactIndex = content.indexOf('<boltArtifact');
  if (artifactIndex === -1) {
    return content.trim();
  }

  const summaryBeforeArtifact = content.slice(0, artifactIndex).trim();
  if (summaryBeforeArtifact) {
    return summaryBeforeArtifact;
  }

  return summarizeArtifact(content) || 'Generated project files';
};

const createChatMessage = (role: ChatMessage['role'], content: string): ChatMessage => ({
  id: `${role}-${Date.now()}-${Math.random().toString(16).slice(2)}`,
  role,
  content,
  createdAt: Date.now(),
});

const sortFileNodes = (nodes: FileItem[]): FileItem[] => {
  return [...nodes].sort((a, b) => {
    if (a.type !== b.type) {
      return a.type === 'folder' ? -1 : 1;
    }
    return a.name.localeCompare(b.name);
  });
};

export function BuilderRoot({ prompt }: BuilderRootProps) {
  const router = useRouter();

  const [steps, setSteps] = useState<Step[]>([]);
  const [files, setFiles] = useState<FileItem[]>([]);
  const [selectedFile, setSelectedFile] = useState<FileItem | null>(null);
  const [activeTab, setActiveTab] = useState<'code' | 'preview'>('code');
  const [currentStep, setCurrentStep] = useState<number | null>(null);
  const [terminalLogs, setTerminalLogs] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [conversation, setConversation] = useState<ChatMessage[]>([]);
  const [llmMessages, setLlmMessages] = useState<ApiMessage[]>([]);
  const [previewStatus, setPreviewStatus] = useState<PreviewStatus>('idle');
  const [autoOpenPreview, setAutoOpenPreview] = useState(true);
  const [workspaceMounted, setWorkspaceMounted] = useState(false);
  const [hasInitialized, setHasInitialized] = useState(false);
  const [pendingWriteCount, setPendingWriteCount] = useState(0);
  const [chatInput, setChatInput] = useState('');

  const chatScrollRef = useRef<HTMLDivElement | null>(null);
  const cwdRef = useRef<string>('');
  const processedActionKeysRef = useRef<Set<string>>(new Set());
  const artifactStepAddedRef = useRef(false);
  const waitingForWebContainerLogged = useRef(false);
  const runningScriptRef = useRef(false);
  const templateMessagesRef = useRef<ApiMessage[]>([]);

  const { instance: webcontainer, error: webcontainerError } = useWebContainer();

  const addLog = useCallback((message: string) => {
    setTerminalLogs((prev) => [
      ...prev,
      `[${new Date().toLocaleTimeString()}] ${message}`,
    ]);
  }, []);

  const upsertFile = useCallback((tree: FileItem[], path: string, content: string): FileItem[] => {
    if (!path) {
      return tree;
    }

    const segments = path.split('/').filter(Boolean);

    const insert = (nodes: FileItem[], index: number, currentPath: string): FileItem[] => {
      const name = segments[index];
      const fullPath = currentPath ? `${currentPath}/${name}` : name;
      const existingIndex = nodes.findIndex((item) => item.path === fullPath);
      const nextNodes = [...nodes];

      if (index === segments.length - 1) {
        const fileItem: FileItem = {
          name,
          path: fullPath,
          type: 'file',
          content,
        };

        if (existingIndex >= 0) {
          nextNodes[existingIndex] = {
            ...nextNodes[existingIndex],
            ...fileItem,
          };
        } else {
          nextNodes.push(fileItem);
        }
        return sortFileNodes(nextNodes);
      }

      let folder: FileItem;
      if (existingIndex >= 0 && nextNodes[existingIndex].type === 'folder') {
        folder = {
          ...nextNodes[existingIndex],
          children: nextNodes[existingIndex].children
            ? [...nextNodes[existingIndex].children!]
            : [],
        };
      } else {
        folder = {
          name,
          path: fullPath,
          type: 'folder',
          children: [],
        };
      }

      folder.children = insert(folder.children || [], index + 1, fullPath);

      if (existingIndex >= 0) {
        nextNodes[existingIndex] = folder;
      } else {
        nextNodes.push(folder);
      }

      return sortFileNodes(nextNodes);
    };

    return insert(tree, 0, '');
  }, []);

  const stageFileForWorkspace = useCallback(
    async (path: string, contents: string) => {
      if (!webcontainer) {
        return false;
      }

      const segments = path.split('/').filter(Boolean);
      if (segments.length > 1) {
        const directory = segments.slice(0, -1).join('/');
        try {
          await webcontainer.fs.mkdir(directory, { recursive: true });
        } catch {
          /* directory exists */
        }
      }

      await webcontainer.fs.writeFile(path, contents);
      return true;
    },
    [webcontainer],
  );

  const ensurePackageJson = useCallback(
    async (cwd: string) => {
      if (!webcontainer) {
        return;
      }

      const packagePath = cwd === '.' ? 'package.json' : `${cwd}/package.json`;
      try {
        await webcontainer.fs.readFile(packagePath, 'utf-8');
        return;
      } catch {
        // create default package.json
      }

      const defaultPackageJson = {
        name: 'appia-project',
        private: true,
        version: '0.0.0',
        type: 'module',
        scripts: {
          dev: 'vite',
          build: 'vite build',
          preview: 'vite preview',
        },
      };

      await stageFileForWorkspace(packagePath, JSON.stringify(defaultPackageJson, null, 2));
      addLog(`Created default package.json at ${packagePath}`);
    },
    [webcontainer, stageFileForWorkspace, addLog],
  );

  const addFileStepResult = useCallback(
    async (step: Step) => {
      if (!step.path) {
        return;
      }

      const relativePath = step.path.replace(/^\.\//, '');
      const cwd = cwdRef.current;
      const resolvedPath = cwd ? `${cwd.replace(/\/$/, '')}/${relativePath}` : relativePath;
      const normalizedPath = resolvedPath.replace(/^\/+/, '');

     const content = step.code || '';
     setFiles((prev) => upsertFile(prev, normalizedPath, content));
     addLog(`Creating file: ${normalizedPath}`);
      setSelectedFile((prev) => {
        if (prev) {
          return prev;
        }
        return {
          name: normalizedPath.split('/').pop() ?? normalizedPath,
          path: normalizedPath,
          type: 'file',
          content,
        };
      });

     const written = await stageFileForWorkspace(normalizedPath, content);
      if (written) {
        addLog(`✓ File created: ${normalizedPath}`);
      }
      setPendingWriteCount((count) => Math.max(0, count - 1));
    },
    [addLog, stageFileForWorkspace, upsertFile],
  );

  const runShellCommands = useCallback(
    async (commandBlock: string) => {
      if (!webcontainer) {
        addLog('ERROR: WebContainer is not ready');
        throw new Error('WebContainer is not ready.');
      }

      const commands = commandBlock
        .split('\n')
        .flatMap((line) => line.split('&&'))
        .map((line) => line.trim())
        .filter(Boolean);

      addLog(`Running ${commands.length} command(s)`);

      let cwdSegments: string[] = cwdRef.current
        ? cwdRef.current.split('/').filter(Boolean)
        : [];

      const getCwd = () => (cwdSegments.length ? cwdSegments.join('/') : '.');

      const changeDirectory = (target: string) => {
        if (target.startsWith('/')) {
          cwdSegments = [];
        }

        const segments = target.split('/').filter(Boolean);

        for (const segment of segments) {
          if (segment === '..') {
            cwdSegments.pop();
          } else if (segment === '.') {
            continue;
          } else {
            cwdSegments.push(segment);
          }
        }
      };

      const execute = async (program: string, args: string[]) => {
        const cwd = getCwd();
        const commandLabel = [program, ...args].filter(Boolean).join(' ');
        addLog(`$ ${commandLabel}`);

        const process = await webcontainer.spawn(
          program,
          args,
          cwd === '.' ? undefined : { cwd },
        );

        const decoder = new TextDecoder();
        const encoder = new TextEncoder();
        let writer: WritableStreamDefaultWriter<Uint8Array> | null = null;

        (process.output as unknown as ReadableStream<Uint8Array>)
          .pipeTo(
            new WritableStream<Uint8Array>({
              async write(data: Uint8Array) {
                const raw = decoder.decode(data);
                const text = raw.replace(/\x1B\[[0-9;]*m/g, '').trim();
                if (text) {
                  addLog(text);
                }

                if (/ok to proceed\?/i.test(raw) || /\(y\/n\)/i.test(raw) || /\(y\/N\)/i.test(raw)) {
                  addLog('↩ Auto-confirming prompt with "y"');
                  if (!writer) {
                    writer = process.input.getWriter() as unknown as WritableStreamDefaultWriter<Uint8Array>;
                  }
                  await writer.write(encoder.encode('y\n'));
                }
              },
            }),
          )
          .catch(() => {
            /* ignore stream errors */
          });

        const exitCode = await process.exit;
        if (exitCode !== 0) {
          addLog(`✗ Command failed with exit code ${exitCode}`);
          throw new Error(`${commandLabel} failed with exit code ${exitCode}`);
        }
        addLog('✓ Command completed successfully');
      };

      for (const command of commands) {
        if (command.startsWith('cd ')) {
          const target = command.replace(/^cd\s+/, '').trim();
          changeDirectory(target);
          continue;
        }

        if (command.startsWith('npm run dev')) {
          continue;
        }

        if (/^npm\s+init\b/i.test(command)) {
          addLog('Skipping `npm init` – scaffold already exists.');
          continue;
        }

        if (/^npm\s+create\b/i.test(command)) {
          addLog('Skipping `npm create` – scaffold files will be generated by steps.');
          continue;
        }

        if (/^npx\s+tailwindcss\b.*\binit\b/i.test(command)) {
          addLog('Skipping `npx tailwindcss init` – config files generated by steps.');
          continue;
        }

        if (/^npm\s+(install|run)\b/i.test(command)) {
          await ensurePackageJson(getCwd());
        }

        const parts = command.split(/\s+/);
        const program = parts[0];
        const args = parts.slice(1);

        if (program === 'npm' && args[0] === 'create') {
          const hasYesFlag = args.includes('--yes') || args.includes('-y');
          if (!hasYesFlag) {
            args.splice(1, 0, '--yes');
          }
        }

        await execute(program, args);

        if (/^npm\s+(init|install|create)/.test(command)) {
          const cwd = getCwd();
          const packagePathRaw = cwd === '.' ? 'package.json' : `${cwd}/package.json`;
          const packagePath = packagePathRaw.replace(/^\.\//, '');
          try {
            const packageJson = await webcontainer.fs.readFile(packagePath, 'utf-8');
            setFiles((prev) => upsertFile(prev, packagePath, packageJson));
          } catch (error) {
            console.warn('[Builder] package.json not accessible after command', command, error);
          }
          const lockPathRaw = packagePath.replace(/package\.json$/, 'package-lock.json');
          const lockPath = lockPathRaw.replace(/^\.\//, '');
          try {
            const packageLock = await webcontainer.fs.readFile(lockPath, 'utf-8');
            setFiles((prev) => upsertFile(prev, lockPath, packageLock));
          } catch {
            /* ignore missing lock file */
          }
        }
      }

      const finalCwd = getCwd();
      cwdRef.current = finalCwd === '.' ? '' : finalCwd;
    },
    [webcontainer, addLog, ensurePackageJson, upsertFile],
  );

  const appendSteps = useCallback(
    (incoming: IncomingStep[]) => {
      if (!incoming.length) {
        return;
      }

      let fileStepsAdded = 0;
      setSteps((prev) => {
        const existingKeys = new Set(
          prev.map((step) => `${step.type}|${step.title}|${step.path ?? ''}`),
        );

        let nextId = prev.length ? prev[prev.length - 1].id + 1 : 1;
        const additions: Step[] = [];

        for (const entry of incoming) {
          const key = `${entry.type}|${entry.title}|${entry.path ?? ''}`;
          if (existingKeys.has(key)) {
            continue;
          }
          additions.push({
            id: nextId++,
            title: entry.title,
            description: entry.description ?? '',
            type: entry.type,
            status: 'pending',
            code: entry.code,
            path: entry.path,
          });
          if (entry.type === StepType.CreateFile) {
            fileStepsAdded += 1;
          }
          existingKeys.add(key);
        }

        if (!additions.length) {
          return prev;
        }

        const nextSteps = [...prev, ...additions];
        setCurrentStep((existing) => existing ?? nextSteps[0]?.id ?? null);
        return nextSteps;
      });
      if (fileStepsAdded > 0) {
        setPendingWriteCount((count) => count + fileStepsAdded);
      }
    },
    [],
  );

  const handleStreamBuffer = useCallback(
    (buffer: string) => {
      if (!artifactStepAddedRef.current) {
        const titleMatch = buffer.match(/<boltArtifact[^>]*title="([^"]*)"/);
        if (titleMatch) {
          artifactStepAddedRef.current = true;
          appendSteps([
            {
              title: titleMatch[1] || 'Project Files',
              description: '',
              type: StepType.CreateFolder,
            },
          ]);
        }
      }

      const actionRegex = /<boltAction\s+type="([^\"]*)"(?:\s+filePath="([^\"]*)")?>([\s\S]*?)<\/boltAction>/g;
      const newSteps: IncomingStep[] = [];
      let match;
      while ((match = actionRegex.exec(buffer)) !== null) {
        const [, type, filePath = '', rawContent] = match;
        const key = `${match.index}-${type}-${filePath}`;
        if (processedActionKeysRef.current.has(key)) {
          continue;
        }
        processedActionKeysRef.current.add(key);

        if (type === 'file') {
          newSteps.push({
            title: `Create ${filePath || 'file'}`,
            description: '',
            type: StepType.CreateFile,
            code: rawContent.trim(),
            path: filePath,
          });
        } else if (type === 'shell') {
          newSteps.push({
            title: 'Run command',
            description: '',
            type: StepType.RunScript,
            code: rawContent.trim(),
          });
        }
      }

      if (newSteps.length) {
        appendSteps(newSteps);
      }
    },
    [appendSteps],
  );

  const streamChat = useCallback(
    async (messages: ApiMessage[]) => {
      const response = await fetch(`${BACKEND_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ messages }),
      });

      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        const data = await response.json();
        const text = data.response ?? '';
        handleStreamBuffer(text);
        const finalSteps = parseXml(text).map((step) => ({
          title: step.title,
          description: step.description,
          type: step.type,
          code: step.code,
          path: step.path,
        }));
        appendSteps(finalSteps);
        return text;
      }

      if (!response.body) {
        throw new Error('No response body');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullResponse = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          break;
        }

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (!line.startsWith('data: ')) {
            continue;
          }
          const data = line.slice(6).trim();
          if (!data || data === '[DONE]') {
            continue;
          }

          try {
            const parsed = JSON.parse(data);
            if (parsed.text) {
              fullResponse += parsed.text;
              handleStreamBuffer(fullResponse);
            }
          } catch {
            /* ignore malformed chunk */
          }
        }
      }

      const finalSteps = parseXml(fullResponse).map((step) => ({
        title: step.title,
        description: step.description,
        type: step.type,
        code: step.code,
        path: step.path,
      }));
      appendSteps(finalSteps);

      return fullResponse;
    },
    [appendSteps, handleStreamBuffer],
  );

  const resetStreamingState = useCallback(() => {
    processedActionKeysRef.current.clear();
    artifactStepAddedRef.current = false;
  }, []);

  const initialiseWorkspace = useCallback(async () => {
    if (!prompt.trim()) {
      router.push('/');
      return;
    }

    try {
      resetStreamingState();
      addLog('Initializing builder...');
      const { data } = await axios.post(`${BACKEND_URL}/template`, {
        prompt: prompt.trim(),
      });

      const prompts: string[] = data.prompts ?? [];
      const initialMessages: ApiMessage[] = [
        ...prompts.map((content) => ({ role: 'user' as const, content })),
        { role: 'user', content: prompt.trim() },
      ];

      templateMessagesRef.current = initialMessages;
      setLlmMessages(initialMessages);
      addLog('Template set, generating build plan...');
      setLoading(true);

      const fullResponse = await streamChat(initialMessages);

      const assistantMessage: ApiMessage = { role: 'assistant', content: fullResponse };
      setLlmMessages([...initialMessages, assistantMessage]);
      setConversation([
        createChatMessage('user', prompt.trim()),
        createChatMessage('assistant', fullResponse),
      ]);
      addLog('AI response received');
    } catch (error) {
      console.error('API Error:', error);
      addLog('ERROR: Failed to initialize builder');
    } finally {
      setLoading(false);
    }
  }, [prompt, router, resetStreamingState, addLog, streamChat]);

  const handleSendMessage = useCallback(
    async (event?: FormEvent) => {
      event?.preventDefault();
      const trimmed = chatInput.trim();
      if (!trimmed) {
        return;
      }

      resetStreamingState();
      const userMessage: ApiMessage = { role: 'user', content: trimmed };
      const uiMessage = createChatMessage('user', trimmed);
      setConversation((prev) => [...prev, uiMessage]);
      setChatInput('');

      const requestMessages = [...llmMessages, userMessage];
      setLlmMessages(requestMessages);
      setLoading(true);

      try {
        const fullResponse = await streamChat(requestMessages);
        const assistantMessage: ApiMessage = { role: 'assistant', content: fullResponse };
        setLlmMessages((prev) => [...prev, assistantMessage]);
        setConversation((prev) => [
          ...prev,
          createChatMessage('assistant', fullResponse),
        ]);
      } catch (error) {
        console.error('Chat error:', error);
        addLog('ERROR: Failed to stream chat message');
      } finally {
        setLoading(false);
      }
    },
    [chatInput, llmMessages, resetStreamingState, streamChat, addLog],
  );

  useEffect(() => {
    if (!hasInitialized) {
      setHasInitialized(true);
      initialiseWorkspace();
    }
  }, [hasInitialized, initialiseWorkspace]);

  useEffect(() => {
    if (!chatScrollRef.current) {
      return;
    }
    chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
  }, [conversation]);

  useEffect(() => {
    if (!webcontainer) {
      return;
    }

    (async () => {
      try {
        await webcontainer.mount({});
        addLog('✓ WebContainer workspace mounted and ready!');
        setWorkspaceMounted(true);
      } catch (error) {
        console.error('[Builder] Failed to initialize WebContainer workspace:', error);
        addLog(
          `ERROR: Failed to mount workspace - ${
            error instanceof Error ? error.message : 'Unknown error'
          }`,
        );
      }
    })();
  }, [webcontainer, addLog]);

  useEffect(() => {
    const pendingSteps = steps.filter((step) => step.status === 'pending');
    if (!pendingSteps.length) {
      return;
    }

    const nextStep = pendingSteps[0];
    if (nextStep.type === StepType.CreateFolder) {
      setSteps((prev) =>
        prev.map((step) =>
          step.id === nextStep.id
            ? {
                ...step,
                status: 'completed',
              }
            : step,
        ),
      );
      return;
    }

    if (nextStep.type === StepType.CreateFile) {
      setSteps((prev) =>
        prev.map((step) =>
          step.id === nextStep.id
            ? {
                ...step,
                status: 'in-progress',
              }
            : step,
        ),
      );
      (async () => {
        try {
          await addFileStepResult(nextStep);
          setSteps((prev) =>
            prev.map((step) =>
              step.id === nextStep.id
                ? {
                    ...step,
                    status: 'completed',
                  }
                : step,
            ),
          );
        } catch (error) {
          console.error('Failed to process file step:', error);
          addLog(
            `ERROR: Failed to create ${nextStep.path ?? 'file'} - ${
              error instanceof Error ? error.message : 'Unknown error'
            }`,
          );
          setSteps((prev) =>
            prev.map((step) =>
              step.id === nextStep.id
                ? {
                    ...step,
                    status: 'completed',
                  }
                : step,
            ),
          );
        }
      })();
      return;
    }

    if (nextStep.type === StepType.RunScript) {
      if (!workspaceMounted || webcontainerError) {
        if (!waitingForWebContainerLogged.current) {
          addLog('⏳ Waiting for WebContainer before executing shell commands...');
          waitingForWebContainerLogged.current = true;
        }
        return;
      }

      if (runningScriptRef.current) {
        return;
      }

      waitingForWebContainerLogged.current = false;
      runningScriptRef.current = true;
      setSteps((prev) =>
        prev.map((step) =>
          step.id === nextStep.id
            ? {
                ...step,
                status: 'in-progress',
              }
            : step,
        ),
      );

      (async () => {
        try {
          await runShellCommands(nextStep.code ?? '');
          setSteps((prev) =>
            prev.map((step) =>
              step.id === nextStep.id
                ? {
                    ...step,
                    status: 'completed',
                  }
                : step,
            ),
          );
        } catch (error) {
          console.error('Failed to process run script step:', error);
          addLog(
            `ERROR: ${(error as Error)?.message ?? 'Command execution failed'}`,
          );
          setSteps((prev) =>
            prev.map((step) =>
              step.id === nextStep.id
                ? {
                    ...step,
                    status: 'completed',
                  }
                : step,
            ),
          );
        } finally {
          runningScriptRef.current = false;
        }
      })();
    }
  }, [steps, addFileStepResult, addLog, runShellCommands, workspaceMounted, webcontainerError]);

  const hasPendingSteps = steps.some((step) => step.status !== 'completed');

  return (
    <div className="flex min-h-[calc(100vh-64px)] flex-col gap-6">
      <div className="flex items-center justify-between rounded-2xl border bg-card px-6 py-4 shadow">
        <div>
          <h1 className="text-xl font-semibold">Appia Builder</h1>
          <p className="text-sm text-muted-foreground">Prompt: {prompt}</p>
        </div>
        <div className="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs text-muted-foreground">
          <Sparkles className="h-3.5 w-3.5 text-primary" />
          {loading ? 'Generating workspace' : hasPendingSteps ? 'Building project' : 'Ready'}
        </div>
      </div>

      <div className="grid flex-1 grid-cols-1 gap-6 lg:grid-cols-[360px_320px_minmax(0,1fr)]">
        <div className="flex min-h-0 flex-col gap-4">
          <div className="flex min-h-[40vh] flex-col overflow-hidden rounded-3xl border bg-card p-4 shadow">
            <StepsList
              steps={steps}
              currentStep={currentStep}
              onStepClick={setCurrentStep}
            />
          </div>
          <div className="relative flex min-h-0 flex-1 flex-col overflow-hidden rounded-3xl border bg-card shadow">
            <header className="flex items-center justify-between border-b px-4 py-3">
              <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                <MessageCircle className="h-4 w-4 text-primary" />
                Conversation
              </div>
              {loading && (
                <span className="inline-flex h-6 w-6 items-center justify-center rounded-full border border-border bg-card">
                  <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                </span>
              )}
            </header>
            <div ref={chatScrollRef} className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
              {conversation.length === 0 ? (
                <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-sm text-muted-foreground">
                  <MessageCircle className="h-6 w-6 text-primary" />
                  <span>Waiting for Appia to generate your workspace…</span>
                </div>
              ) : (
                conversation.map((message) => (
                  <div
                    key={message.id}
                    className={`flex ${
                      message.role === 'user' ? 'justify-end' : 'justify-start'
                    }`}
                  >
                    {(() => {
                      const displayContent =
                        message.role === 'assistant'
                          ? formatAssistantSummary(message.content)
                          : message.content;
                      const timestamp = new Date(message.createdAt).toLocaleTimeString();
                      return (
                        <div
                          className={`relative max-w-[85%] rounded-3xl border px-4 py-3 text-sm shadow ${
                            message.role === 'user'
                              ? 'border-primary/40 bg-primary/10 text-foreground'
                              : 'border-border bg-card text-foreground'
                          }`}
                        >
                          <div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-wide text-muted-foreground">
                            {message.role === 'user' ? (
                              <UserIcon className="h-3.5 w-3.5 text-muted-foreground" />
                            ) : (
                              <Bot className="h-3.5 w-3.5 text-primary" />
                            )}
                            {message.role === 'user' ? 'You' : 'Appia'}
                            <span className="text-[10px] text-muted-foreground/70">{timestamp}</span>
                          </div>
                          <p className="whitespace-pre-wrap leading-relaxed">
                            {displayContent || 'Generating project artifacts…'}
                          </p>
                        </div>
                      );
                    })()}
                  </div>
                ))
              )}
            </div>
            <form
              onSubmit={handleSendMessage}
              className="sticky bottom-4 mx-4 mb-4 rounded-3xl border bg-card/95 p-3 shadow"
            >
              <textarea
                value={chatInput}
                onChange={(event) => setChatInput(event.target.value)}
                placeholder="Send Appia a follow-up instruction"
                rows={3}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey && !event.ctrlKey) {
                    event.preventDefault();
                    handleSendMessage();
                  }
                }}
                className="w-full resize-none rounded-2xl border bg-muted/40 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground"
              />
              <div className="mt-3 flex items-center justify-between">
                <span className="text-xs text-muted-foreground">Shift + Enter to add a new line</span>
                <button
                  type="submit"
                  disabled={loading}
                  className="inline-flex items-center gap-2 rounded-full border border-primary/40 bg-primary/10 px-4 py-2 text-sm font-semibold text-foreground transition hover:shadow disabled:cursor-not-allowed disabled:opacity-60"
                >
                  Send
                </button>
              </div>
            </form>
          </div>
          <div className="shrink-0 min-h-[180px] max-h-[24vh]">
            <Terminal logs={terminalLogs} />
          </div>
        </div>

        <div className="flex h-full min-h-0 flex-col">
          <div className="flex-1 overflow-hidden rounded-3xl border bg-card p-4 shadow">
            <FileExplorer
              files={files}
              onFileSelect={setSelectedFile}
              activePath={selectedFile?.path ?? null}
              title="Generated Files"
            />
          </div>
        </div>

        <div className="flex h-full min-h-0 flex-col gap-4">
          <TabView
            activeTab={activeTab}
            onTabChange={setActiveTab}
            previewStatusLabel={PREVIEW_STATUS_LABELS[previewStatus] ?? 'Preview'}
            autoOpenPreview={autoOpenPreview}
            onAutoOpenPreviewChange={setAutoOpenPreview}
          />
          <div className="flex-1 overflow-hidden rounded-[28px] border bg-transparent">
            {activeTab === 'code' ? (
              <CodeEditor file={selectedFile} />
            ) : (
              <PreviewFrame
                files={files}
                webContainer={webcontainer}
                isReady={!hasPendingSteps && pendingWriteCount === 0}
                onStatusChange={setPreviewStatus}
                onLog={addLog}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
