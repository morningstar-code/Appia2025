import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { StepsList } from '../components/StepsList';
import { FileExplorer } from '../components/FileExplorer';
import { TabView } from '../components/TabView';
import { CodeEditor } from '../components/CodeEditor';
import { PreviewFrame } from '../components/PreviewFrame';
import { Terminal } from '../components/Terminal';
import { Step, FileItem, StepType } from '../types';
import axios from 'axios';
import { BACKEND_URL } from '../config';
import { parseXml } from '../steps';
import { useWebContainer } from '../hooks/useWebContainer';
import { Loader } from '../components/Loader';

const MOCK_FILE_CONTENT = `// This is a sample file content
import React from 'react';

function Component() {
  return <div>Hello World</div>;
}

export default Component;`;

export function Builder() {
  const location = useLocation();
  const navigate = useNavigate();
  const routeState = (location.state as { prompt?: string } | null) ?? null;
  const persistedPrompt = sessionStorage.getItem('builderPrompt') ?? '';
  const initialPrompt = routeState?.prompt ?? persistedPrompt;

  const [prompt, setPromptValue] = useState(initialPrompt);
  const [userPrompt, setPrompt] = useState("");
  const [llmMessages, setLlmMessages] = useState<{role: "user" | "assistant", content: string;}[]>([]);
  const [loading, setLoading] = useState(false);
  const [templateSet, setTemplateSet] = useState(false);
  const webcontainer = useWebContainer();

  const [currentStep, setCurrentStep] = useState(1);
  const [activeTab, setActiveTab] = useState<'code' | 'preview'>('code');
  const [selectedFile, setSelectedFile] = useState<FileItem | null>(null);
  
  const [steps, setSteps] = useState<Step[]>([]);
  const [files, setFiles] = useState<FileItem[]>([]);
  const [processingStep, setProcessingStep] = useState(false);
  const [workspaceMounted, setWorkspaceMounted] = useState(false);
  const [terminalLogs, setTerminalLogs] = useState<string[]>([]);
  const cwdRef = useRef<string>('');
  const waitingForWebContainerLogged = useRef(false);

  const addLog = useCallback((message: string) => {
    setTerminalLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] ${message}`]);
  }, []);

  useEffect(() => {
    if (!initialPrompt) {
      navigate('/', { replace: true });
    } else {
      sessionStorage.setItem('builderPrompt', initialPrompt);
      setPromptValue(initialPrompt);
    }
  }, [initialPrompt, navigate]);

  const upsertFile = useCallback((tree: FileItem[], path: string, content: string): FileItem[] => {
    if (!path) {
      return tree;
    }

    const segments = path.split('/').filter(Boolean);

    const insert = (nodes: FileItem[], index: number, currentPath: string): FileItem[] => {
      const name = segments[index];
      const fullPath = currentPath ? `${currentPath}/${name}` : name;
      let updated = [...nodes];
      const existingIndex = updated.findIndex((item) => item.path === fullPath);

      if (index === segments.length - 1) {
        const fileItem: FileItem = {
          name,
          path: fullPath,
                type: 'file',
          content
        };

        if (existingIndex >= 0) {
          updated[existingIndex] = {
            ...updated[existingIndex],
            ...fileItem
          };
        } else {
          updated.push(fileItem);
        }
        return updated;
      }

      let folder: FileItem;
      if (existingIndex >= 0 && updated[existingIndex].type === 'folder') {
        folder = {
          ...updated[existingIndex],
          children: updated[existingIndex].children ? [...updated[existingIndex].children!] : []
        };
      } else {
        folder = {
          name,
          path: fullPath,
          type: 'folder',
          children: []
        };
      }

      folder.children = insert(folder.children || [], index + 1, fullPath);

      if (existingIndex >= 0) {
        updated[existingIndex] = folder;
            } else {
        updated.push(folder);
      }

      return updated;
    };

    return insert(tree, 0, '');
  }, []);

  const findNextPendingStep = useCallback(
    () => steps.findIndex((step) => step.status === 'pending'),
    [steps]
  );

  const markStepStatus = useCallback((index: number, status: Step['status']) => {
    setSteps((prev) =>
      prev.map((step, idx) =>
        idx === index
          ? {
              ...step,
              status
            }
          : step
      )
    );
  }, []);

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
        const fullCommand = [program, ...args].join(' ');
        addLog(`$ ${fullCommand}`);
        
        const process = await webcontainer.spawn(
          program,
          args,
          cwd === '.' ? undefined : { cwd }
        );
        
        // Log stdout
        process.output.pipeTo(new WritableStream({
          write(data) {
            addLog(data);
          }
        }));
        
        const exitCode = await process.exit;
        if (exitCode !== 0) {
          addLog(`ERROR: Command failed with exit code ${exitCode}`);
          throw new Error(`${fullCommand} failed with exit code ${exitCode}`);
        }
        addLog(`✓ Command completed successfully`);
      };

      for (const command of commands) {
        if (command.startsWith('cd ')) {
          const target = command.replace(/^cd\s+/, '').trim();
          console.log('[Builder] processing cd', target);
          changeDirectory(target);
          continue;
        }

        if (command.startsWith('npm run dev')) {
          // PreviewFrame will start the dev server, so skip running it here.
          continue;
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

        console.log('[Builder] spawning command', program, args);
        await execute(program, args);
        console.log('[Builder] command completed', program, args);

        if (command.startsWith('npm init') || command.startsWith('npm install') || command.startsWith('npm create')) {
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
            // Ignore missing package-lock
          }
        }
      }

      const finalCwd = getCwd();
      cwdRef.current = finalCwd === '.' ? '' : finalCwd;
      console.log('[Builder] updated cwd', cwdRef.current);
    },
    [webcontainer, upsertFile, addLog]
  );

  const writeFileToWebContainer = useCallback(
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
          // directory already exists
        }
      }

      await webcontainer.fs.writeFile(path, contents);
    },
    [webcontainer]
  );

  useEffect(() => {
    if (processingStep) {
      return;
    }

    const nextIndex = findNextPendingStep();
    if (nextIndex === -1) {
      return;
    }

    const nextStep = steps[nextIndex];

    if ((nextStep.type === StepType.RunScript || nextStep.type === StepType.CreateFile) && !workspaceMounted) {
      if (!waitingForWebContainerLogged.current) {
        addLog(`⏳ Waiting for WebContainer to be ready before executing steps...`);
        waitingForWebContainerLogged.current = true;
      }
      return;
    }

    setProcessingStep(true);
    markStepStatus(nextIndex, 'in-progress');

    (async () => {
      try {
        console.log('[Builder] processing step', nextStep.id, StepType[nextStep.type], nextStep.path);
        if (nextStep.type === StepType.CreateFolder) {
          if (nextStep.path) {
            addLog(`Creating folder: ${nextStep.path}`);
          } else {
            addLog(`Step: ${nextStep.title || 'Artifact created'}`);
          }
          markStepStatus(nextIndex, 'completed');
        } else if (nextStep.type === StepType.CreateFile && nextStep.path) {
          const relativePath = nextStep.path.replace(/^\.\//, '');
          const currentDir = cwdRef.current;
          const resolvedPath = currentDir
            ? `${currentDir.replace(/\/$/, '')}/${relativePath}`
            : relativePath;
          const normalizedPath = resolvedPath.replace(/^\/+/, '');

          addLog(`Creating file: ${normalizedPath}`);
          const content = nextStep.code || '';
          setFiles((prev) => upsertFile(prev, normalizedPath, content));
          if (webcontainer && workspaceMounted) {
            console.log('[Builder] writing file to WebContainer', normalizedPath);
            await writeFileToWebContainer(normalizedPath, content);
            addLog(`✓ File created: ${normalizedPath}`);
          }
          markStepStatus(nextIndex, 'completed');
        } else if (nextStep.type === StepType.RunScript && nextStep.code) {
          console.log('[Builder] executing run script step', nextStep.code);
          await runShellCommands(nextStep.code);
          markStepStatus(nextIndex, 'completed');
        } else {
          markStepStatus(nextIndex, 'completed');
        }
      } catch (error) {
        console.error('Failed to process step:', error);
        addLog(`ERROR: ${error instanceof Error ? error.message : 'Unknown error'}`);
        markStepStatus(nextIndex, 'completed');
      } finally {
        setProcessingStep(false);
      }
    })();
  }, [steps, processingStep, findNextPendingStep, markStepStatus, runShellCommands, upsertFile, webcontainer, workspaceMounted, writeFileToWebContainer, addLog]);

  useEffect(() => {
    if (!webcontainer) {
      addLog('⏳ WebContainer is booting...');
      return;
    }
    
    if (workspaceMounted) {
      return;
    }
    
    addLog('Mounting WebContainer workspace...');

    (async () => {
      try {
        console.log('[Builder] mounting empty workspace');
        await webcontainer.mount({});
        console.log('[Builder] workspace mounted');
        addLog('✓ WebContainer workspace mounted and ready!');
        setWorkspaceMounted(true);
      } catch (error) {
        console.error('[Builder] Failed to initialize WebContainer workspace:', error);
        addLog(`ERROR: Failed to mount workspace - ${error instanceof Error ? error.message : 'Unknown error'}`);
      }
    })();
  }, [webcontainer, workspaceMounted, addLog]);

  useEffect(() => {
    console.log('[Builder] steps state', steps.map((step) => ({
      id: step.id,
      type: StepType[step.type],
      status: step.status,
      path: step.path
    })));
  }, [steps]);

  const hasPendingSteps = steps.some((step) => step.status !== 'completed');

  async function streamChat(messages: {role: string, content: string}[]) {
    const response = await fetch(`${BACKEND_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ messages })
    });

    if (!response.body) {
      throw new Error('No response body');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullResponse = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') {
            return fullResponse;
          }
          try {
            const parsed = JSON.parse(data);
            fullResponse += parsed.text;
            
            // Parse and update steps as they come in
            try {
              const newSteps = parseXml(fullResponse);
              setSteps(s => {
                const existingIds = new Set(s.map(step => step.id));
                const stepsToAdd = newSteps.filter((step: Step) => !existingIds.has(step.id));
                return [...s, ...stepsToAdd.map((x: Step) => ({
                  ...x,
                  status: "pending" as "pending"
                }))];
              });
            } catch (e) {
              // Partial XML, keep going
            }
          } catch (e) {
            // Invalid JSON, skip
          }
        }
      }
    }

    return fullResponse;
  }

  async function init() {
    try {
      addLog('Initializing builder...');
      console.log('Calling API:', `${BACKEND_URL}/template`);
      const response = await axios.post(`${BACKEND_URL}/template`, {
        prompt: prompt.trim()
      });
      console.log('API Response:', response.data);
      setTemplateSet(true);
    
    const {prompts, uiPrompts} = response.data;

    // Don't parse uiPrompts as they're just system prompts, not XML
    // Steps will come from the chat response
    addLog('Template set, waiting for AI to generate steps...');

    setLoading(true);
    addLog('Requesting AI to generate code...');
    const fullResponse = await streamChat([...prompts, prompt].map(content => ({
      role: "user",
      content
    })));

    setLoading(false);
    addLog('AI response received');

    // Final parse to ensure we have all steps
    const finalSteps = parseXml(fullResponse);
    setSteps(s => {
      const existingIds = new Set(s.map(step => step.id));
      const stepsToAdd = finalSteps.filter((step: Step) => !existingIds.has(step.id));
      return [...s, ...stepsToAdd.map((x: Step) => ({
      ...x,
      status: "pending" as "pending"
      }))];
    });

    setLlmMessages([...prompts, prompt].map(content => ({
      role: "user",
      content
    })));

    setLlmMessages(x => [...x, {role: "assistant", content: fullResponse}])
    } catch (error) {
      console.error('API Error:', error);
      setLoading(false);
    }
  }

  useEffect(() => {
    init();
  }, [])

  return (
    <div className="min-h-screen bg-gray-900 flex flex-col">
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <h1 className="text-xl font-semibold text-gray-100">Website Builder</h1>
        <p className="text-sm text-gray-400 mt-1">Prompt: {prompt}</p>
      </header>
      
      <div className="flex-1 overflow-hidden">
        <div className="h-full grid grid-cols-4 gap-6 p-6">
          <div className="col-span-1 space-y-4 overflow-auto">
            <div>
              <div className="max-h-[40vh] overflow-scroll">
                <StepsList
                  steps={steps}
                  currentStep={currentStep}
                  onStepClick={setCurrentStep}
                />
              </div>
            </div>
            <div className="h-[30vh]">
              <Terminal logs={terminalLogs} />
            </div>
            <div>
              <div className='flex'>
                {(loading || !templateSet || hasPendingSteps) && <Loader />}
                {!(loading || !templateSet || hasPendingSteps) && <div className='flex w-full'>
                  <textarea value={userPrompt} onChange={(e) => {
                  setPrompt(e.target.value)
                }} className='p-2 w-full'></textarea>
                <button onClick={async () => {
                    const newMessage = {
                      role: "user" as "user",
                      content: userPrompt
                    };

                    setLoading(true);
                    const fullResponse = await streamChat([...llmMessages, newMessage]);
                    setLoading(false);

                    setLlmMessages(x => [...x, newMessage]);
                    setLlmMessages(x => [...x, {
                      role: "assistant",
                      content: fullResponse
                    }]);
                    
                    const finalSteps = parseXml(fullResponse);
                    setSteps(s => {
                      const existingIds = new Set(s.map(step => step.id));
                      const stepsToAdd = finalSteps.filter((step: Step) => !existingIds.has(step.id));
                      return [...s, ...stepsToAdd.map((x: Step) => ({
                        ...x,
                        status: "pending" as "pending"
                      }))];
                    });

                  }} className='bg-purple-400 px-4'>Send</button>
                </div>}
              </div>
            </div>
          </div>
          <div className="col-span-1">
              <FileExplorer 
                files={files} 
                onFileSelect={setSelectedFile}
              />
            </div>
          <div className="col-span-2 bg-gray-900 rounded-lg shadow-lg p-4 h-[calc(100vh-8rem)]">
            <TabView activeTab={activeTab} onTabChange={setActiveTab} />
            <div className="h-[calc(100%-4rem)]">
              {activeTab === 'code' ? (
                <CodeEditor file={selectedFile} />
              ) : (
                <PreviewFrame webContainer={webcontainer} files={files} isReady={!hasPendingSteps} />
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
