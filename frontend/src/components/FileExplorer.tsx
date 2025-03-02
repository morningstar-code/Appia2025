import React, { useState } from 'react';
import { FolderTree, File, ChevronRight, ChevronDown, Code, FileText, Image, FileJson, FileSpreadsheet, Coffee } from 'lucide-react';
import { FileItem } from '../types';

interface FileExplorerProps {
  files: FileItem[];
  onFileSelect: (file: FileItem) => void;
}

interface FileNodeProps {
  item: FileItem;
  depth: number;
  onFileClick: (file: FileItem) => void;
  selectedFile: FileItem | null;
}

// Helper function to determine file type icon based on extension
function getFileIcon(fileName: string) {
  const extension = fileName.split('.').pop()?.toLowerCase();
  switch (extension) {
    case 'js':
    case 'jsx':
    case 'ts':
    case 'tsx':
      return <Code className="w-4 h-4 text-yellow-400" />;
    case 'json':
      return <FileJson className="w-4 h-4 text-green-400" />;
    case 'css':
    case 'scss':
    case 'sass':
      return <FileText className="w-4 h-4 text-blue-400" />;
    case 'html':
      return <FileText className="w-4 h-4 text-orange-400" />;
    case 'png':
    case 'jpg':
    case 'jpeg':
    case 'svg':
    case 'gif':
      return <Image className="w-4 h-4 text-purple-400" />;
    case 'md':
      return <FileText className="w-4 h-4 text-gray-400" />;
    case 'csv':
    case 'xlsx':
      return <FileSpreadsheet className="w-4 h-4 text-green-500" />;
    default:
      return <File className="w-4 h-4 text-gray-400" />;
  }
}

function FileNode({ item, depth, onFileClick, selectedFile }: FileNodeProps) {
  const [isExpanded, setIsExpanded] = useState(depth === 0); // Auto-expand root level
  const isSelected = selectedFile?.path === item.path;

  const handleClick = () => {
    if (item.type === 'folder') {
      setIsExpanded(!isExpanded);
    } else {
      onFileClick(item);
    }
  };

  return (
    <div className="select-none">
      <div
        className={`flex items-center gap-2 p-2 hover:bg-gray-800 rounded-md cursor-pointer ${
          isSelected ? 'bg-gray-700 text-white' : ''
        }`}
        style={{ paddingLeft: `${depth * 1.5}rem` }}
        onClick={handleClick}
      >
        {item.type === 'folder' && (
          <span className="text-gray-400">
            {isExpanded ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
          </span>
        )}
        {item.type === 'folder' ? (
          <FolderTree className="w-4 h-4 text-blue-400" />
        ) : (
          getFileIcon(item.name)
        )}
        <span className={`truncate ${isSelected ? 'font-medium' : 'text-gray-200'}`}>
          {item.name}
        </span>
      </div>
      {item.type === 'folder' && isExpanded && item.children && (
        <div className="border-l border-gray-800 ml-5">
          {item.children.map((child, index) => (
            <FileNode
              key={`${child.path}-${index}`}
              item={child}
              depth={depth + 1}
              onFileClick={onFileClick}
              selectedFile={selectedFile}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function FileExplorer({ files, onFileSelect }: FileExplorerProps) {
  const [selectedFile, setSelectedFile] = useState<FileItem | null>(null);
  
  const handleFileSelect = (file: FileItem) => {
    setSelectedFile(file);
    onFileSelect(file);
  };

  return (
    <div className="bg-gray-900 rounded-lg shadow-lg p-4 h-full overflow-auto">
      <h2 className="text-lg font-semibold mb-4 flex items-center gap-2 text-gray-100">
        <FolderTree className="w-5 h-5" />
        File Explorer
      </h2>
      <div className="space-y-1">
        {files.map((file, index) => (
          <FileNode
            key={`${file.path}-${index}`}
            item={file}
            depth={0}
            onFileClick={handleFileSelect}
            selectedFile={selectedFile}
          />
        ))}
      </div>
    </div>
  );
}
