import { motion, AnimatePresence } from 'framer-motion';
import { X, Pencil, Trash2, Code } from 'lucide-react';
import { DiJavascript1, DiPython, DiJava, DiCss3, DiHtml5, DiReact, DiGo, DiRuby, DiPhp } from "react-icons/di";
import { SiTypescript, SiSharp, SiKotlin, SiSwift } from "react-icons/si";
import { FileCode2 } from 'lucide-react';
import { FileBadge } from '../FileBadge/FileBadge';
import type { CodeSnippet } from '../../core/domain/entities';

interface FilePreview extends File {
  preview: string;
  id: string;
}

interface AttachmentPreviewProps {
  files: FilePreview[];
  codeSnippets: CodeSnippet[];
  onRemoveFile: (fileId: string) => void;
  onRemoveCodeSnippet: (snippetId: string) => void;
  onEditCodeSnippet: (snippet: CodeSnippet) => void;
  getFileIcon: (fileName: string) => React.ElementType;
}

const languageIcons: { [key: string]: React.ElementType } = {
  javascript: DiJavascript1, typescript: SiTypescript, python: DiPython,
  java: DiJava, csharp: SiSharp, html: DiHtml5, css: DiCss3,
  jsx: DiReact, tsx: DiReact, go: DiGo, ruby: DiRuby, php: DiPhp,
  kotlin: SiKotlin, swift: SiSwift, sql: FileCode2,
};

const SUPPORTED_LANGUAGES = [
  { value: 'plaintext', label: 'Texto Simples' }, 
  { value: 'javascript', label: 'JavaScript' },
  { value: 'typescript', label: 'TypeScript' }, 
  { value: 'python', label: 'Python' },
  { value: 'java', label: 'Java' }, 
  { value: 'csharp', label: 'C#' }, 
  { value: 'sql', label: 'SQL' },
  { value: 'html', label: 'HTML' },
  { value: 'css', label: 'CSS' },
  { value: 'jsx', label: 'JSX' },
  { value: 'go', label: 'Go' },
];

export const AttachmentPreview = ({ 
  files, 
  codeSnippets, 
  onRemoveFile, 
  onRemoveCodeSnippet, 
  onEditCodeSnippet,
  getFileIcon 
}: AttachmentPreviewProps) => {
  if (files.length === 0 && codeSnippets.length === 0) {
    return null;
  }

  return (
    <AnimatePresence>
      <motion.div 
        initial={{ height: 0, opacity: 0 }} 
        animate={{ height: 'auto', opacity: 1 }} 
        exit={{ height: 0, opacity: 0 }} 
        className="p-2 border-b border-gray-700"
      >
        <div className="flex flex-wrap gap-2">
          {files.map(file => (
            file.type.startsWith('image/') ? (
              <div key={file.id} className="relative w-16 h-16">
                <img src={file.preview} alt={file.name} className="w-full h-full object-cover rounded-md"/>
                <button 
                  type="button" 
                  onClick={() => onRemoveFile(file.id)} 
                  className="absolute -top-1.5 -right-1.5 bg-gray-600 rounded-full p-0.5 text-white hover:bg-red-500"
                >
                  <X size={14}/>
                </button>
              </div>
            ) : ( 
              <FileBadge 
                key={file.id} 
                file={file} 
                icon={getFileIcon(file.name)} 
                onRemove={() => onRemoveFile(file.id)} 
              /> 
            )
          ))}
          
          {codeSnippets.map((snippet) => {
            const Icon = languageIcons[snippet.language] || Code;
            return (
              <div key={snippet.id} className="group relative flex items-center gap-2 px-3 py-2 h-auto bg-gray-900 rounded-md border border-gray-700 text-sm">
                <Icon size={16} className="text-gray-400"/>
                <span className="text-gray-300">
                  {SUPPORTED_LANGUAGES.find(l => l.value === snippet.language)?.label || snippet.language}
                </span>
                <div className="absolute -top-2 -right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity bg-gray-800 rounded-md p-1 border border-gray-700">
                  <button 
                    type="button" 
                    onClick={() => onEditCodeSnippet(snippet)} 
                    className="p-1 text-gray-400 hover:text-white"
                  >
                    <Pencil size={12}/>
                  </button>
                  <button 
                    type="button" 
                    onClick={() => onRemoveCodeSnippet(snippet.id)} 
                    className="p-1 text-gray-400 hover:text-red-500"
                  >
                    <Trash2 size={12}/>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </motion.div>
    </AnimatePresence>
  );
};