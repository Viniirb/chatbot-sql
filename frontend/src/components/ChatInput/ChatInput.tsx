import { useState, useCallback, useRef, useEffect } from 'react'; 
import { useDropzone } from 'react-dropzone';
import type { FileRejection } from 'react-dropzone';
import { SendHorizontal, Square, FileCode2, FileText, File } from 'lucide-react';
import ContentEditable from 'react-contenteditable';
import type { CodeSnippet } from '../../core/domain/entities';
import hljs from 'highlight.js';
import toast from 'react-hot-toast';
import { CodeModal } from './CodeModal';
import { AttachmentMenu } from './AttachmentMenu';
import { AttachmentPreview } from './AttachmentPreview';

import { DiJavascript1, DiPython, DiJava, DiCss3, DiHtml5, DiReact, DiGo, DiRuby, DiPhp } from "react-icons/di";
import { SiTypescript, SiSharp, SiKotlin, SiSwift } from "react-icons/si";
import { FaFileWord, FaFileExcel, FaFilePdf, FaFilePowerpoint, FaFileArchive } from 'react-icons/fa';

interface FilePreview extends File {
  preview: string;
  id: string;
}

interface Props {
  onSendMessage: (text: string, files: File[]) => Promise<void>;
  isLoading: boolean;
  onStop?: () => void;
}

const fileExtensionIcons: { [key: string]: React.ElementType } = {
  pdf: FaFilePdf,
  doc: FaFileWord,
  docx: FaFileWord,
  xls: FaFileExcel,
  xlsx: FaFileExcel,
  ppt: FaFilePowerpoint,
  pptx: FaFilePowerpoint,
  txt: FileText,
  
  js: DiJavascript1,
  jsx: DiReact,
  ts: SiTypescript,
  tsx: DiReact,
  py: DiPython,
  java: DiJava,
  cs: SiSharp,
  html: DiHtml5,
  css: DiCss3,
  go: DiGo,
  rb: DiRuby,
  php: DiPhp,
  kt: SiKotlin,
  swift: SiSwift,
  csv: FaFileExcel,
  
  zip: FaFileArchive,
  rar: FaFileArchive,
  '7z': FaFileArchive,
  tar: FaFileArchive,
  gz: FaFileArchive,
  
  json: FileCode2,
};


export const ChatInput = ({ onSendMessage, isLoading, onStop }: Props) => {
  const [files, setFiles] = useState<FilePreview[]>([]);
  const [codeSnippets, setCodeSnippets] = useState<CodeSnippet[]>([]);
  const [html, setHtml] = useState<string>('');
  const [inputMode, setInputMode] = useState<'text' | 'code'>('text');
  const [codeContent, setCodeContent] = useState('');
  const [codeLanguage, setCodeLanguage] = useState('plaintext');
  const [editingSnippetId, setEditingSnippetId] = useState<string | null>(null);
  const editableRef = useRef<HTMLDivElement | null>(null);
  const formRef = useRef<HTMLFormElement | null>(null);

  useEffect(() => {
    if (editableRef.current) {
      editableRef.current.scrollTop = editableRef.current.scrollHeight;
    }
  }, [html]);

  const addCodeSnippet = (content: string, language: string) => {
    const newSnippet: CodeSnippet = { id: Math.random().toString(36).substring(2, 9), content, language };
    setCodeSnippets(prev => [...prev, newSnippet]);
  };

  const getFileIcon = (fileName: string) => {
    const extension = fileName.split('.').pop()?.toLowerCase();
    return fileExtensionIcons[extension || ''] || File;
  };

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFilesWithId = acceptedFiles.map(file => Object.assign(file, {
      preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : '',
      id: Math.random().toString(36).substring(2, 9)
    }));
    setFiles(prev => [...prev, ...newFilesWithId]);
  }, []);
  
  const onDropRejected = useCallback((fileRejections: FileRejection[]) => {
    fileRejections.forEach(({ file, errors }) => {
      errors.forEach(error => {
        if (error.code === 'file-too-large') {
          toast.error(`Erro: O arquivo "${file.name}" é muito grande. O limite é 10MB.`);
        }
        if (error.code === 'file-invalid-type') {
          toast.error(`Erro: O tipo do arquivo "${file.name}" não é suportado.`);
        }
      });
    });
  }, []);

  const { getRootProps, getInputProps, open } = useDropzone({
    onDrop, onDropRejected, noClick: true, noKeyboard: true, maxFiles: 5,
    maxSize: 10 * 1024 * 1024,
    accept: { 
      'image/*': ['.png', '.jpg', '.jpeg', '.gif', '.webp'],
      'application/pdf': ['.pdf'], 'text/plain': ['.txt', '.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc'], 
      'application/json': ['.json'],
      'application/zip': ['.zip', '.rar', '.7z', '.tar', '.gz']
    }
  });

  const handlePasteEditable = (e: React.ClipboardEvent<HTMLDivElement>) => {
    if (inputMode !== 'text') return;
    const clipboard = e.clipboardData;
    if (!clipboard) return;

    const textContent = clipboard.getData('text/plain');
    const imageItems = Array.from(clipboard.items).filter(item => item.type.indexOf('image') !== -1);

    if (textContent) {
      const autoDetection = hljs.highlightAuto(textContent);
      if (autoDetection.relevance > 10 && autoDetection.language) {
        e.preventDefault();
        addCodeSnippet(textContent, autoDetection.language);
        return;
      }
      e.preventDefault();
      document.execCommand('insertText', false, textContent);
      setTimeout(() => {
        if (editableRef.current) {
          setHtml(editableRef.current.innerHTML);
        }
      }, 0);
      return;
    }

    if (imageItems.length > 0) {
      e.preventDefault();
      const imageFiles = imageItems.map(item => item.getAsFile()).filter((file): file is File => file !== null);
      if (imageFiles.length > 0) onDrop(imageFiles);
    }
  };

  const removeFile = (fileIdToRemove: string) => {
    setFiles(prev => {
      const fileToRemove = prev.find(f => f.id === fileIdToRemove);
      if (fileToRemove && fileToRemove.preview) URL.revokeObjectURL(fileToRemove.preview);
      return prev.filter(file => file.id !== fileIdToRemove);
    });
  };

  const removeCodeSnippet = (snippetIdToRemove: string) => {
    setCodeSnippets(prev => prev.filter(s => s.id !== snippetIdToRemove));
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (isLoading) return;
    
    const currentText = editableRef.current?.innerText || '';
    const formattedCodeSnippets = codeSnippets.map(snippet => `\n\`\`\`${snippet.language}\n${snippet.content}\n\`\`\``).join('');
    const finalText = (currentText.trim() + formattedCodeSnippets).trim();

    if (finalText || files.length > 0) {
      // Limpa o input IMEDIATAMENTE antes de enviar
      setHtml('');
      const currentFiles = [...files];
      files.forEach(file => { if(file.preview) URL.revokeObjectURL(file.preview) });
      setFiles([]);
      setCodeSnippets([]);
      
      try {
        await onSendMessage(finalText, currentFiles);
      } catch {
        // Erro já é tratado no chat com botão de reenvio
        // Não precisa mostrar toast
      }
    }
  };
  
  const openCodeModal = (snippet: CodeSnippet | null = null) => {
    if (snippet) {
      setEditingSnippetId(snippet.id);
      setCodeContent(snippet.content);
      setCodeLanguage(snippet.language);
    } else {
      setEditingSnippetId(null);
      setCodeContent('');
      setCodeLanguage('plaintext');
    }
    setInputMode('code');
  };

  const handleCodeSubmit = () => {
    if (!codeContent.trim()) return;
    if (editingSnippetId) {
      setCodeSnippets(prev => prev.map(s => s.id === editingSnippetId ? { ...s, content: codeContent, language: codeLanguage } : s));
    } else {
      addCodeSnippet(codeContent, codeLanguage);
    }
    setInputMode('text');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (isLoading) return;
      const currentText = editableRef.current?.innerText || '';
      const canSend = currentText.trim() || files.length > 0 || codeSnippets.length > 0;
      if (canSend) {
        formRef.current?.requestSubmit();
      }
    }
  };

  return (
    <>
      <div {...getRootProps({ className: 'dropzone w-full p-4' })}>
        <input {...getInputProps()} />
        <div className='relative'>
          <div className={`relative bg-gray-800 border border-gray-700 rounded-2xl focus-within:ring-2 focus-within:ring-primary`}>
              <AttachmentPreview
                files={files}
                codeSnippets={codeSnippets}
                onRemoveFile={removeFile}
                onRemoveCodeSnippet={removeCodeSnippet}
                onEditCodeSnippet={openCodeModal}
                getFileIcon={getFileIcon}
              />
              <form ref={formRef} onSubmit={handleSubmit} className="relative flex items-center space-x-2 p-2">
                <AttachmentMenu
                  onOpenFiles={open}
                  onOpenCodeModal={() => openCodeModal()}
                />
                <ContentEditable
                  innerRef={(current: HTMLDivElement | null) => (editableRef.current = current)}
                  html={html}
                  onChange={(e) => setHtml(e.target.value)}
                  onPaste={handlePasteEditable}
                  onKeyDown={handleKeyDown}
                  tagName="div"
                  className="flex-1 min-h-[40px] max-h-48 overflow-y-auto px-4 py-2 text-gray-200 focus:outline-none custom-scroll [&:empty:not(:focus)]:before:content-[attr(data-placeholder)] [&:empty:not(:focus)]:before:text-gray-500"
                  data-placeholder="Pergunte algo ou cole uma imagem..."
                  disabled={isLoading}
                  spellCheck={false}
                  autoCorrect="off"
                  autoCapitalize="off"
                />
                {isLoading && onStop ? (
                  <button type="button" onClick={onStop} className="flex-shrink-0 flex items-center justify-center w-10 h-10 text-white bg-gray-600 rounded-full transition-colors hover:bg-gray-500 z-10"><Square size={20} /></button>
                ) : (
                  <button type="submit" disabled={isLoading || (!html.trim() && files.length === 0 && codeSnippets.length === 0)} className="flex-shrink-0 flex items-center justify-center w-10 h-10 text-white bg-primary rounded-full transition-colors hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed z-10">
                    <SendHorizontal size={20} />
                  </button>
                )}
              </form>
          </div>
        </div>
      </div>

      <CodeModal
        isOpen={inputMode === 'code'}
        onClose={() => setInputMode('text')}
        codeContent={codeContent}
        setCodeContent={setCodeContent}
        codeLanguage={codeLanguage}
        setCodeLanguage={setCodeLanguage}
        onSubmit={handleCodeSubmit}
        isEditing={editingSnippetId !== null}
      />
    </>
  );
};