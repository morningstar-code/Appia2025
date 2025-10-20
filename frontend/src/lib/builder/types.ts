export enum StepType {
  CreateFile = "CreateFile",
  CreateFolder = "CreateFolder",
  EditFile = "EditFile",
  DeleteFile = "DeleteFile",
  RunScript = "RunScript",
}

export type StepStatus = "pending" | "in-progress" | "completed";

export interface Step {
  id: number;
  title: string;
  description: string;
  type: StepType;
  status: StepStatus;
  code?: string;
  path?: string;
}

export interface FileItem {
  name: string;
  type: "file" | "folder";
  children?: FileItem[];
  content?: string;
  path: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: number;
}
