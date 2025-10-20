import React, {
  FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';
import {
  FileItem,
  Step,
  StepType,
  ChatMessage,
} from '../types';
import { useWebContainer } from '../hooks/useWebContainer';
import { BACKEND_URL } from '../config';
import { parseXml } from '../steps';
import { AppShellHeader } from '../components/AppShellHeader';
import { StepsList } from '../components/StepsList';
import { FileExplorer } from '../components/FileExplorer';
import { CodeEditor } from '../components/CodeEditor';
import {
  PreviewFrame,
  PreviewStatus,
  PREVIEW_STATUS_LABELS,
} from '../components/PreviewFrame';
import { TabView } from '../components/TabView';
import { Terminal } from '../components/Terminal';
import { DatabasePanel } from '../components/DatabasePanel';
import { MessageCircle, Bot, User as UserIcon } from 'lucide-react';

type ApiMessage = { role: 'user' | 'assistant'; content: string };

type IncomingStep = {
  title: string;
  description?: string;
  type: StepType;
  code?: string;
  path?: string;
};

type BuilderVersion = {
  id: string;
  label: string;
  createdAt: number;
  steps: Step[];
  files: FileItem[];
  conversation: ChatMessage[];
  llmMessages: ApiMessage[];
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

const cloneSteps = (items: Step[]): Step[] =>
  items.map((step) => ({ ...step }));

const cloneFiles = (items: FileItem[]): FileItem[] =>
  items.map((item) =>
    item.type === 'folder'
      ? {
          ...item,
          children: item.children ? cloneFiles(item.children) : [],
        }
      : { ...item },
  );

const cloneMessages = (items: ChatMessage[]): ChatMessage[] =>
  items.map((message) => ({ ...message }));

const cloneApiMessages = (items: ApiMessage[]): ApiMessage[] =>
  items.map((message) => ({ ...message }));

export function Builder() {
  const location = useLocation();
  const navigate = useNavigate();
  const routeState = (location.state as { prompt?: string } | null) ?? null;
  const persistedPrompt = sessionStorage.getItem('builderPrompt') ?? '';
  const initialPrompt = routeState?.prompt ?? persistedPrompt;

  const [prompt, setPromptValue] = useState(initialPrompt);
  const [chatInput, setChatInput] = useState('');
  const [steps, setSteps] = useState<Step[]>([]);
  const [files, setFiles] = useState<FileItem[]>([]);
  const [selectedFile, setSelectedFile] = useState<FileItem | null>(null);
  const [activeTab, setActiveTab] = useState<'code' | 'preview'>('code');
  const [currentStep, setCurrentStep] = useState<number | null>(null);
  const [terminalLogs, setTerminalLogs] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [templateSet, setTemplateSet] = useState(false);
  const [conversation, setConversation] = useState<ChatMessage[]>([]);
  const [llmMessages, setLlmMessages] = useState<ApiMessage[]>([]);
  const [previewStatus, setPreviewStatus] = useState<PreviewStatus>('idle');
  const [autoOpenPreview, setAutoOpenPreview] = useState(true);
  const [workspaceMounted, setWorkspaceMounted] = useState(false);
  const [versions, setVersions] = useState<BuilderVersion[]>([]);
  const [activeVersionId, setActiveVersionId] = useState<string | null>(null);
  const [showDatabasePanel, setShowDatabasePanel] = useState(false);
  const [pendingWriteCount, setPendingWriteCount] = useState(0);

  const chatScrollRef = useRef<HTMLDivElement | null>(null);
  const cwdRef = useRef<string>('');
  const processedActionKeysRef = useRef<Set<string>>(new Set());
  const artifactStepAddedRef = useRef(false);
  const waitingForWebContainerLogged = useRef(false);
  const hasInitializedRef = useRef(false);
  const runningScriptRef = useRef(false);
  const webcontainerStatusRef = useRef<'booting' | 'ready' | 'error' | null>(null);
  const pendingFileWritesRef = useRef<Map<string, string>>(new Map());
  const versionCounterRef = useRef(1);
  const templateMessagesRef = useRef<ApiMessage[]>([]);
  const currentWorkingSnapshotRef = useRef<BuilderVersion | null>(null);

  const {
    instance: webcontainer,
    error: webcontainerError,
    isBooting: webcontainerBooting,
  } = useWebContainer();

  const hasPendingSteps = useMemo(
    () => steps.some((step) => step.status !== 'completed'),
    [steps],
  );

  const isViewingHistory = activeVersionId !== null;

  const headerStatusLabel = useMemo(() => {
    if (isViewingHistory) {
      return 'Viewing saved version';
    }
    if (webcontainerError) {
      return 'WebContainer error';
    }
    if (!templateSet || loading) {
      return 'Generating workspace';
    }
    if (hasPendingSteps) {
      return 'Building project';
    }
    return 'Ready';
  }, [webcontainerError, templateSet, loading, hasPendingSteps, isViewingHistory]);

  const headerStatusTone: 'neutral' | 'active' | 'success' | 'warning' | 'error' = useMemo(() => {
    if (isViewingHistory) {
      return 'neutral';
    }
    if (webcontainerError) {
      return 'error';
    }
    if (!templateSet || loading || hasPendingSteps) {
      return 'active';
    }
    return 'success';
  }, [webcontainerError, templateSet, loading, hasPendingSteps, isViewingHistory]);

  const addLog = useCallback((message: string) => {
    setTerminalLogs((prev) => [
      ...prev,
      `[${new Date().toLocaleTimeString()}] ${message}`,
    ]);
  }, []);

  const ensureCurrentStep = useCallback((nextSteps: Step[]) => {
    if (!nextSteps.length) {
      setCurrentStep(null);
      return;
    }
    setCurrentStep((existing) => existing ?? nextSteps[0].id);
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
      let nextNodes = [...nodes];

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

  const writeFileDirect = useCallback(
    async (path: string, contents: string) => {
      if (!webcontainer) {
        return;
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
    },
    [webcontainer],
  );

  const stageFileForWorkspace = useCallback(
    async (path: string, contents: string) => {
      pendingFileWritesRef.current.set(path, contents);
      setPendingWriteCount(pendingFileWritesRef.current.size);
      if (!webcontainer || !workspaceMounted) {
        return false;
      }
      await writeFileDirect(path, contents);
      pendingFileWritesRef.current.delete(path);
      setPendingWriteCount(pendingFileWritesRef.current.size);
      return true;
    },
    [writeFileDirect, webcontainer, workspaceMounted],
  );

  const flushPendingFileWrites = useCallback(async () => {
    if (!webcontainer || !workspaceMounted) {
      return;
    }
    for (const [path, contents] of pendingFileWritesRef.current.entries()) {
      await writeFileDirect(path, contents);
      pendingFileWritesRef.current.delete(path);
      setPendingWriteCount(pendingFileWritesRef.current.size);
      addLog(`✓ File synced: ${path}`);
    }
  }, [writeFileDirect, webcontainer, workspaceMounted, addLog]);

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
        /* fall through */
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

      const contents = JSON.stringify(defaultPackageJson, null, 2);
      const written = await stageFileForWorkspace(packagePath, contents);
      if (written) {
        addLog(`Created default package.json at ${packagePath}`);
      } else {
        addLog(`Queued package.json creation at ${packagePath}`);
      }
    },
    [stageFileForWorkspace, addLog],
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
      } else {
        addLog(`⏳ Queued file for workspace sync: ${normalizedPath}`);
      }
    },
    [addLog, upsertFile, stageFileForWorkspace],
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
        let writer: WritableStreamDefaultWriter<string> | null = null;

        process.output
          .pipeTo(
            new WritableStream({
              async write(data) {
                const raw = decoder.decode(data);
                const text = raw.replace(/\x1B\[[0-9;]*m/g, '').trim();
                if (text) {
                  addLog(text);
                }

                if (/ok to proceed\?/i.test(raw) || /\(y\/n\)/i.test(raw) || /\(y\/N\)/i.test(raw)) {
                  addLog('↩ Auto-confirming prompt with "y"');
                  if (!writer) {
                    writer = process.input.getWriter();
                  }
                  await writer.write('y\n');
                }
              },
            }),
          )
          .catch(() => {
            /* ignore stream errors */
          });

        const exitCode = await process.exit;
        if (writer) {
          writer.releaseLock();
        }

        if (exitCode !== 0) {
          addLog(`✗ Command failed with exit code ${exitCode}`);
          throw new Error(`${commandLabel} failed with exit code ${exitCode}`);
        }
        addLog(`✓ Command completed successfully`);
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
          existingKeys.add(key);
        }

        if (!additions.length) {
          return prev;
        }

        const nextSteps = [...prev, ...additions];
        ensureCurrentStep(nextSteps);
        return nextSteps;
      });
    },
    [ensureCurrentStep],
  );

  const markStepStatus = useCallback((index: number, status: Step['status']) => {
    setSteps((prev) =>
      prev.map((step, idx) =>
        idx === index
          ? {
              ...step,
              status,
            }
          : step,
      ),
    );
  }, []);

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

      const actionRegex = /<boltAction\s+type="([^"]*)"(?:\s+filePath="([^"]*)")?>([\s\S]*?)<\/boltAction>/g;
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
      return;
    }

    try {
      resetStreamingState();
      addLog('Initializing builder...');
      const { data } = await axios.post(`${BACKEND_URL}/template`, {
        prompt: prompt.trim(),
      });

      setTemplateSet(true);
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
  }, [prompt, resetStreamingState, addLog, streamChat]);

  const handleSendMessage = useCallback(
    async (event?: FormEvent) => {
      if (isViewingHistory) {
        return;
      }
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
    [chatInput, llmMessages, streamChat, resetStreamingState, addLog],
  );

  const handleRunAgain = useCallback(() => {
    if (isViewingHistory) {
      return;
    }
    if (!prompt.trim() || templateMessagesRef.current.length === 0) {
      return;
    }

    const snapshotSteps = cloneSteps(steps);
    const snapshotFiles = cloneFiles(files);
    const snapshotConversation = cloneMessages(conversation);
    const snapshotLlm = cloneApiMessages(llmMessages);

    if (
      snapshotSteps.length > 0 ||
      snapshotFiles.length > 0 ||
      snapshotConversation.length > 0
    ) {
      const now = Date.now();
      const versionLabel = `Version ${versionCounterRef.current}`;
      const version: BuilderVersion = {
        id: `${now}-${Math.random().toString(16).slice(2)}`,
        label: versionLabel,
        createdAt: now,
        steps: snapshotSteps,
        files: snapshotFiles,
        conversation: snapshotConversation,
        llmMessages: snapshotLlm,
      };
      setVersions((prev) => [version, ...prev]);
      versionCounterRef.current += 1;
    }

    pendingFileWritesRef.current.clear();
    setPendingWriteCount(0);
    setSteps([]);
    setFiles([]);
    setSelectedFile(null);
    setConversation([]);
    setLlmMessages([]);
    setTerminalLogs([]);
    setCurrentStep(null);
    setTemplateSet(false);
    setChatInput('');
    setPreviewStatus('idle');
    setActiveVersionId(null);
    processedActionKeysRef.current.clear();
    artifactStepAddedRef.current = false;
    currentWorkingSnapshotRef.current = null;
    initialiseWorkspace();
  }, [prompt, steps, files, conversation, llmMessages, initialiseWorkspace]);

  const handleSelectVersion = useCallback(
    (id: string) => {
      if (id === '__current__') {
        if (currentWorkingSnapshotRef.current) {
          const snapshot = currentWorkingSnapshotRef.current;
          setActiveVersionId(null);
          setSteps(cloneSteps(snapshot.steps));
          setFiles(cloneFiles(snapshot.files));
          setConversation(cloneMessages(snapshot.conversation));
          setLlmMessages(cloneApiMessages(snapshot.llmMessages));
          setCurrentStep(snapshot.steps.length ? snapshot.steps[0].id : null);
          setSelectedFile(null);
          setPreviewStatus('idle');
          setShowDatabasePanel(false);
          runningScriptRef.current = false;
          waitingForWebContainerLogged.current = false;
          setPendingWriteCount(0);
        } else {
          setActiveVersionId(null);
        }
        currentWorkingSnapshotRef.current = null;
        return;
      }

      const target = versions.find((version) => version.id === id);
      if (!target || activeVersionId === id) {
        return;
      }

      if (activeVersionId === null) {
        currentWorkingSnapshotRef.current = {
          id: 'current',
          label: 'Current',
          createdAt: Date.now(),
          steps: cloneSteps(steps),
          files: cloneFiles(files),
          conversation: cloneMessages(conversation),
          llmMessages: cloneApiMessages(llmMessages),
        };
      }

      setActiveVersionId(id);
      setSteps(cloneSteps(target.steps));
      setFiles(cloneFiles(target.files));
      setConversation(cloneMessages(target.conversation));
      setLlmMessages(cloneApiMessages(target.llmMessages));
      setCurrentStep(target.steps.length ? target.steps[0].id : null);
      setSelectedFile(null);
      setPreviewStatus('idle');
      setShowDatabasePanel(false);
      runningScriptRef.current = false;
      waitingForWebContainerLogged.current = false;
      setPendingWriteCount(0);
    },
    [versions, activeVersionId, steps, files, conversation, llmMessages],
  );

  useEffect(() => {
    if (!initialPrompt) {
      navigate('/', { replace: true });
    } else {
      sessionStorage.setItem('builderPrompt', initialPrompt);
      setPromptValue(initialPrompt);
    }
  }, [initialPrompt, navigate]);

  useEffect(() => {
    let status: 'booting' | 'ready' | 'error';
    if (webcontainer) {
      status = 'ready';
    } else if (webcontainerError) {
      status = 'error';
    } else {
      status = 'booting';
    }

    if (webcontainerStatusRef.current === status) {
      return;
    }

    webcontainerStatusRef.current = status;

    if (status === 'booting') {
      addLog('⏳ WebContainer is booting...');
    } else if (status === 'ready') {
      addLog('✓ WebContainer booted and ready');
    } else if (status === 'error') {
      addLog(
        `✗ WebContainer failed to boot: ${
          webcontainerError instanceof Error
            ? webcontainerError.message
            : 'Unknown error'
        }`,
      );
    }
  }, [webcontainer, webcontainerError, addLog]);

  useEffect(() => {
    if (!prompt.trim() || hasInitializedRef.current) {
      return;
    }
    hasInitializedRef.current = true;
    initialiseWorkspace();
  }, [prompt, initialiseWorkspace]);

  useEffect(() => {
    if (!webcontainer || webcontainerError) {
      return;
    }

    if (workspaceMounted) {
      return;
    }

    addLog('Mounting WebContainer workspace...');

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
  }, [webcontainer, workspaceMounted, addLog, webcontainerError]);

  useEffect(() => {
    if (workspaceMounted) {
      waitingForWebContainerLogged.current = false;
    }
  }, [workspaceMounted]);

  useEffect(() => {
    if (workspaceMounted) {
      flushPendingFileWrites();
    }
  }, [workspaceMounted, flushPendingFileWrites]);

  useEffect(() => {
    if (webcontainer) {
      flushPendingFileWrites();
    }
  }, [webcontainer, flushPendingFileWrites]);

  useEffect(() => {
    if (webcontainerError) {
      waitingForWebContainerLogged.current = false;
    }
  }, [webcontainerError]);

  useEffect(() => {
    if (isViewingHistory) {
      return;
    }
    steps.forEach((step, index) => {
      if (step.status !== 'pending') {
        return;
      }

      if (step.type === StepType.CreateFolder) {
        markStepStatus(index, 'completed');
        return;
      }

      if (step.type === StepType.CreateFile) {
        markStepStatus(index, 'in-progress');
        (async () => {
          try {
            await addFileStepResult(step);
            markStepStatus(index, 'completed');
          } catch (error) {
            console.error('Failed to process file step:', error);
            addLog(
              `ERROR: Failed to create ${step.path ?? 'file'} - ${
                error instanceof Error ? error.message : 'Unknown error'
              }`,
            );
            markStepStatus(index, 'completed');
          }
        })();
      }
    });
  }, [steps, markStepStatus, addFileStepResult, addLog, isViewingHistory]);

  useEffect(() => {
    if (isViewingHistory) {
      return;
    }
    if (runningScriptRef.current) {
      return;
    }

    const nextIndex = steps.findIndex(
      (step) => step.type === StepType.RunScript && step.status === 'pending',
    );
    if (nextIndex === -1) {
      return;
    }

    const step = steps[nextIndex];
    if (!workspaceMounted || webcontainerError) {
      if (!waitingForWebContainerLogged.current) {
        addLog('⏳ Waiting for WebContainer before executing shell commands...');
        waitingForWebContainerLogged.current = true;
      }
      return;
    }

    waitingForWebContainerLogged.current = false;
    runningScriptRef.current = true;
    markStepStatus(nextIndex, 'in-progress');

    (async () => {
      try {
        await runShellCommands(step.code ?? '');
        markStepStatus(nextIndex, 'completed');
      } catch (error) {
        console.error('Failed to process run script step:', error);
        addLog(
          `ERROR: ${(error as Error)?.message ?? 'Command execution failed'}`,
        );
        markStepStatus(nextIndex, 'completed');
      } finally {
        runningScriptRef.current = false;
      }
    })();
  }, [steps, workspaceMounted, webcontainerError, runShellCommands, markStepStatus, addLog, isViewingHistory]);

  useEffect(() => {
    if (!isViewingHistory && autoOpenPreview && previewStatus === 'ready') {
      setActiveTab('preview');
    }
  }, [autoOpenPreview, previewStatus, isViewingHistory]);

  useEffect(() => {
    if (!chatScrollRef.current) {
      return;
    }
    chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
  }, [conversation]);

  return (
    <div className="flex min-h-screen flex-col overflow-x-hidden bg-appia-background">
      <AppShellHeader
        prompt={prompt}
        statusLabel={headerStatusLabel}
        statusTone={headerStatusTone}
        onRunAgain={handleRunAgain}
        busy={loading || hasPendingSteps || webcontainerBooting || isViewingHistory}
        onDatabaseClick={() => setShowDatabasePanel((prev) => !prev)}
        databaseOpen={showDatabasePanel}
        versions={versions}
        activeVersionId={activeVersionId}
        onSelectVersion={versions.length ? handleSelectVersion : undefined}
      />
      <div className="mx-auto grid w-full max-w-[1680px] flex-1 grid-cols-[360px_320px_minmax(0,1fr)] gap-6 px-6 py-6">
        <div className="flex min-h-0 flex-col gap-4">
          <div className="shrink-0">
            <StepsList
              steps={steps}
              currentStep={currentStep}
              onStepClick={setCurrentStep}
            />
          </div>
          <div className="relative flex min-h-0 flex-1 flex-col overflow-hidden rounded-3xl border border-appia-border/80 bg-appia-surface/90 shadow-appia-card">
            <header className="flex items-center justify-between border-b border-appia-border/70 px-4 py-3">
              <div className="flex items-center gap-2 text-sm font-medium text-appia-foreground/90">
                <MessageCircle className="h-4 w-4 text-appia-accent" />
                Conversation
              </div>
              {loading && (
                <span className="inline-flex h-6 w-6 items-center justify-center rounded-full border border-appia-border/60 bg-appia-surface">
                  <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-appia-accent border-t-transparent" />
                </span>
              )}
            </header>
            <div ref={chatScrollRef} className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
              {conversation.length === 0 ? (
                <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-sm text-appia-muted">
                  <MessageCircle className="h-6 w-6 text-appia-accent" />
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
                          className={`relative max-w-[85%] rounded-3xl border px-4 py-3 text-sm shadow-appia-card ${
                            message.role === 'user'
                              ? 'border-appia-accent/40 bg-appia-accent-soft text-appia-foreground shadow-appia-glow'
                              : 'border-appia-border/70 bg-appia-surface text-appia-foreground/85'
                          }`}
                        >
                          <div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-wide text-appia-muted">
                            {message.role === 'user' ? (
                              <UserIcon className="h-3.5 w-3.5 text-appia-muted" />
                            ) : (
                              <Bot className="h-3.5 w-3.5 text-appia-accent" />
                            )}
                            {message.role === 'user' ? 'You' : 'Appia'}
                            <span className="text-[10px] text-appia-muted/70">{timestamp}</span>
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
              className="sticky bottom-4 mx-4 mb-4 rounded-3xl border border-appia-border/80 bg-appia-surface/95 p-3 shadow-appia-card"
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
                readOnly={isViewingHistory}
                className="w-full resize-none rounded-2xl border border-appia-border/80 bg-appia-sunken px-3 py-2 text-sm text-appia-foreground placeholder:text-appia-muted focus:border-appia-accent focus:outline-none focus:ring-2 focus:ring-appia-accent/30 disabled:cursor-not-allowed disabled:opacity-60"
              />
              <div className="mt-3 flex items-center justify-between">
                <span className="text-xs text-appia-muted">
                  {isViewingHistory ? 'Viewing saved version' : 'Shift + Enter to add a new line'}
                </span>
                <button
                  type="submit"
                  disabled={loading || isViewingHistory}
                  className="inline-flex items-center gap-2 rounded-full border border-appia-accent/40 bg-appia-accent-soft px-4 py-2 text-sm font-semibold text-appia-foreground transition hover:shadow-appia-glow disabled:cursor-not-allowed disabled:border-appia-border disabled:bg-appia-surface disabled:text-appia-muted"
                >
                  Send
                </button>
              </div>
            </form>
          </div>
          <div className="shrink-0 min-h-[220px]">
            <Terminal logs={terminalLogs} />
          </div>
        </div>

        <div className="flex h-full min-h-0 flex-col">
          <FileExplorer
            files={files}
            onFileSelect={setSelectedFile}
            activePath={selectedFile?.path ?? null}
            title="Generated Files"
          />
        </div>

        <div className="flex h-full min-h-0 flex-col gap-4">
          <TabView
            activeTab={activeTab}
            onTabChange={setActiveTab}
            previewStatusLabel={PREVIEW_STATUS_LABELS[previewStatus] ?? 'Preview'}
            autoOpenPreview={autoOpenPreview}
            onAutoOpenPreviewChange={isViewingHistory ? undefined : setAutoOpenPreview}
          />
          <div className="flex-1 overflow-hidden rounded-[28px] border border-appia-border/70 bg-transparent">
            {activeTab === 'code' ? (
              <CodeEditor file={selectedFile} />
            ) : (
              <PreviewFrame
                files={files}
                webContainer={webcontainer}
                isReady={!hasPendingSteps && pendingWriteCount === 0 && !isViewingHistory}
                onStatusChange={setPreviewStatus}
              />
            )}
          </div>
        </div>
      </div>
      <DatabasePanel
        open={showDatabasePanel}
        onClose={() => setShowDatabasePanel(false)}
      />
    </div>
  );
}
