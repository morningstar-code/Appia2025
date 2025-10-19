import React, { useCallback, useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { StepsList } from '../components/StepsList';
import { FileExplorer } from '../components/FileExplorer';
import { TabView } from '../components/TabView';
import { CodeEditor } from '../components/CodeEditor';
import { PreviewFrame } from '../components/PreviewFrame';
import { Step, FileItem, StepType } from '../types';
import axios from 'axios';
import { BACKEND_URL } from '../config';
import { parseXml } from '../steps';
import { useWebContainer } from '../hooks/useWebContainer';
import { FileNode } from '@webcontainer/api';
import { Loader } from '../components/Loader';

const MOCK_FILE_CONTENT = `// This is a sample file content
import React from 'react';

function Component() {
  return <div>Hello World</div>;
}

export default Component;`;

export function Builder() {
  const location = useLocation();
  const { prompt } = location.state as { prompt: string };
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
        throw new Error('WebContainer is not ready.');
      }

      const commands = commandBlock
        .split('\n')
        .flatMap((line) => line.split('&&'))
        .map((line) => line.trim())
        .filter(Boolean);

      let cwdSegments: string[] = [];

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
        const process = await webcontainer.spawn(
          program,
          args,
          cwd === '.' ? undefined : { cwd }
        );
        const exitCode = await process.exit;
        if (exitCode !== 0) {
          throw new Error(`${[program, ...args].join(' ')} failed with exit code ${exitCode}`);
        }
      };

      for (const command of commands) {
        if (command.startsWith('cd ')) {
          const target = command.replace(/^cd\s+/, '').trim();
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
        await execute(program, args);

        if (command.startsWith('npm init') || command.startsWith('npm install')) {
          try {
            const cwd = getCwd();
            const packagePath = cwd === '.' ? 'package.json' : `${cwd}/package.json`;
            const packageJson = await webcontainer.fs.readFile(packagePath, 'utf-8');
            setFiles((prev) => upsertFile(prev, packagePath, packageJson));
            const lockPath = packagePath.replace(/package\.json$/, 'package-lock.json');
            try {
              const packageLock = await webcontainer.fs.readFile(lockPath, 'utf-8');
              setFiles((prev) => upsertFile(prev, lockPath, packageLock));
            } catch {
              // Ignore missing package-lock
            }
          } catch (error) {
            console.warn('package.json not found after command', command, error);
          }
        }
      }
    },
    [webcontainer, upsertFile]
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
        } catch (error) {
          // ignore directory exists errors
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

    if (nextStep.type === StepType.RunScript) {
      if (!webcontainer || !workspaceMounted) {
        return;
      }
    }

    setProcessingStep(true);
    markStepStatus(nextIndex, 'in-progress');

    (async () => {
      try {
        if (nextStep.type === StepType.CreateFolder) {
          markStepStatus(nextIndex, 'completed');
        } else if (nextStep.type === StepType.CreateFile && nextStep.path) {
          const content = nextStep.code || '';
          setFiles((prev) => upsertFile(prev, nextStep.path!, content));
          if (webcontainer && workspaceMounted) {
            await writeFileToWebContainer(nextStep.path, content);
          }
          markStepStatus(nextIndex, 'completed');
        } else if (nextStep.type === StepType.RunScript && nextStep.code) {
          await runShellCommands(nextStep.code);
          markStepStatus(nextIndex, 'completed');
        } else {
          markStepStatus(nextIndex, 'completed');
        }
      } catch (error) {
        console.error('Failed to process step:', error);
        markStepStatus(nextIndex, 'completed');
      } finally {
        setProcessingStep(false);
      }
    })();
  }, [steps, processingStep, findNextPendingStep, markStepStatus, runShellCommands, upsertFile, webcontainer, workspaceMounted, writeFileToWebContainer]);

  useEffect(() => {
    const createMountStructure = (files: FileItem[]): Record<string, any> => {
      const mountStructure: Record<string, any> = {};
  
      const processFile = (file: FileItem, isRootFolder: boolean) => {  
        if (file.type === 'folder') {
          // For folders, create a directory entry
          mountStructure[file.name] = {
            directory: file.children ? 
              Object.fromEntries(
                file.children.map(child => [child.name, processFile(child, false)])
              ) 
              : {}
          };
        } else if (file.type === 'file') {
          if (isRootFolder) {
            mountStructure[file.name] = {
              file: {
                contents: file.content || ''
              }
            };
          } else {
            // For files, create a file entry with contents
            return {
              file: {
                contents: file.content || ''
              }
            };
          }
        }
  
        return mountStructure[file.name];
      };
  
      // Process each top-level file/folder
      files.forEach(file => processFile(file, true));
  
      return mountStructure;
    };
  
    if (!webcontainer || files.length === 0) {
      return;
    }

    if (!webcontainer || files.length === 0 || workspaceMounted) {
      return;
    }

    const mountStructure = createMountStructure(files);

    // Mount the structure if WebContainer is available
    (async () => {
      try {
        await webcontainer.mount(mountStructure);
        setWorkspaceMounted(true);
      } catch (error) {
        console.error('Failed to mount project files in WebContainer:', error);
      }
    })();
  }, [files, webcontainer, workspaceMounted]);

  const hasPendingSteps = steps.some((step) => step.status !== 'completed');

  async function init() {
    try {
      console.log('Calling API:', `${BACKEND_URL}/template`);
      const response = await axios.post(`${BACKEND_URL}/template`, {
        prompt: prompt.trim()
      });
      console.log('API Response:', response.data);
      setTemplateSet(true);
    
    const {prompts, uiPrompts} = response.data;

    setSteps(parseXml(uiPrompts[0]).map((x: Step) => ({
      ...x,
      status: "pending"
    })));

    setLoading(true);
    const stepsResponse = await axios.post(`${BACKEND_URL}/chat`, {
      messages: [...prompts, prompt].map(content => ({
        role: "user",
        content
      }))
    })

    setLoading(false);

    setSteps(s => [...s, ...parseXml(stepsResponse.data.response).map(x => ({
      ...x,
      status: "pending" as "pending"
    }))]);

    setLlmMessages([...prompts, prompt].map(content => ({
      role: "user",
      content
    })));

    setLlmMessages(x => [...x, {role: "assistant", content: stepsResponse.data.response}])
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
          <div className="col-span-1 space-y-6 overflow-auto">
            <div>
              <div className="max-h-[75vh] overflow-scroll">
                <StepsList
                  steps={steps}
                  currentStep={currentStep}
                  onStepClick={setCurrentStep}
                />
              </div>
              <div>
                <div className='flex'>
                  <br />
                  {(loading || !templateSet || hasPendingSteps) && <Loader />}
                  {!(loading || !templateSet || hasPendingSteps) && <div className='flex'>
                    <textarea value={userPrompt} onChange={(e) => {
                    setPrompt(e.target.value)
                  }} className='p-2 w-full'></textarea>
                  <button onClick={async () => {
                    const newMessage = {
                      role: "user" as "user",
                      content: userPrompt
                    };

                    setLoading(true);
                    const stepsResponse = await axios.post(`${BACKEND_URL}/chat`, {
                      messages: [...llmMessages, newMessage]
                    });
                    setLoading(false);

                    setLlmMessages(x => [...x, newMessage]);
                    setLlmMessages(x => [...x, {
                      role: "assistant",
                      content: stepsResponse.data.response
                    }]);
                    
                    setSteps(s => [...s, ...parseXml(stepsResponse.data.response).map(x => ({
                      ...x,
                      status: "pending" as "pending"
                    }))]);

                  }} className='bg-purple-400 px-4'>Send</button>
                  </div>}
                </div>
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
