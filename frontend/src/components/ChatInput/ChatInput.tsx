import { useState, useCallback, useRef, useEffect } from 'react'; 
import { useDropzone } from 'react-dropzone';
import type { FileRejection } from 'react-dropzone';
import { SendHorizontal, Square, Plus, Code, Image, X, Pencil, Trash2, FileCode2, FileText, File } from 'lucide-react';
import { DiJavascript1, DiPython, DiJava, DiCss3, DiHtml5, DiReact, DiGo, DiRuby, DiPhp } from "react-icons/di";
import { SiTypescript, SiSharp, SiKotlin, SiSwift } from "react-icons/si";
import { FaFileWord, FaFileExcel, FaFilePdf, FaFilePowerpoint } from 'react-icons/fa';
import { FaFileZipper } from 'react-icons/fa6';
import ContentEditable from 'react-contenteditable';
import { Dialog, Transition, Menu, MenuButton, MenuItems, MenuItem } from '@headlessui/react';
import { Fragment } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { motion, AnimatePresence } from 'framer-motion';
import type { CodeSnippet } from '../../types';
import { FileBadge } from '../FileBadge/FileBadge';
import hljs from 'highlight.js';
import toast from 'react-hot-toast';

// ... (o restante das suas interfaces e constantes permanece o mesmo) ...
interface FilePreview extends File {
  preview: string;
  id: string;
}

interface Props {
  onSendMessage: (text: string, files: File[]) => void;
  isLoading: boolean;
  onStop?: () => void;
}

const languageIcons: { [key: string]: React.ElementType } = {
  javascript: DiJavascript1, typescript: SiTypescript, python: DiPython,
  java: DiJava, csharp: SiSharp, html: DiHtml5, css: DiCss3,
  jsx: DiReact, tsx: DiReact, go: DiGo, ruby: DiRuby, php: DiPhp,
  kotlin: SiKotlin, swift: SiSwift, sql: FileCode2,
};

const fileExtensionIcons: { [key: string]: React.ElementType } = {
  pdf: FaFilePdf,
  doc: FaFileWord,
  docx: FaFileWord,
  xls: FaFileExcel,
  xlsx: FaFileExcel,
  ppt: FaFilePowerpoint,
  pptx: FaFilePowerpoint,
  txt: FileText,
  csv: FaFileExcel,
  
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
  sql: FileCode2,
  
  // Arquivos compactados
  zip: FaFileZipper,
  rar: FaFileZipper,
  '7z': FaFileZipper,
  tar: FaFileZipper,
  gz: FaFileZipper,
  
  // JSON
  json: FileCode2,
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

  // 2. ADICIONAR ESTE useEffect
  // Garante que o input role para baixo conforme o conteúdo aumenta
  useEffect(() => {
    if (editableRef.current) {
      editableRef.current.scrollTop = editableRef.current.scrollHeight;
    }
  }, [html]); // Roda sempre que o conteúdo 'html' mudar

  // ... (o restante das suas funções permanece o mesmo) ...
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
      // PASTE COMO TEXTO PURO (sem estilos)
      e.preventDefault();
      // execCommand ainda é amplamente suportado para inserir texto simples
      document.execCommand('insertText', false, textContent);
      // Sincroniza o estado 'html' com o conteúdo atual do ContentEditable
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

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const currentText = editableRef.current?.innerText || '';
    const formattedCodeSnippets = codeSnippets.map(snippet => `\n\`\`\`${snippet.language}\n${snippet.content}\n\`\`\``).join('');
    const finalText = (currentText.trim() + formattedCodeSnippets).trim();

    if (finalText || files.length > 0) {
      onSendMessage(finalText, files);
      setHtml('');
      files.forEach(file => { if(file.preview) URL.revokeObjectURL(file.preview) });
      setFiles([]);
      setCodeSnippets([]);
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

  // Enviar com Enter, nova linha com Shift+Enter
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
              <AnimatePresence>
                {(files.length > 0 || codeSnippets.length > 0) && (
                  <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className='p-2 border-b border-gray-700'>
                    <div className='flex flex-wrap gap-2'>
                      {files.map(file => (
                        file.type.startsWith('image/') ? (
                          <div key={file.id} className='relative w-16 h-16'>
                            <img src={file.preview} alt={file.name} className='w-full h-full object-cover rounded-md'/>
                            <button type="button" onClick={() => removeFile(file.id)} className="absolute -top-1.5 -right-1.5 bg-gray-600 rounded-full p-0.5 text-white hover:bg-red-500"><X size={14}/></button>
                          </div>
                        ) : ( <FileBadge key={file.id} file={file} icon={getFileIcon(file.name)} onRemove={() => removeFile(file.id)} /> )
                      ))}
                      {codeSnippets.map((snippet) => {
                        const Icon = languageIcons[snippet.language] || Code;
                        return (
                          <div key={snippet.id} className='group relative flex items-center gap-2 px-3 py-2 h-auto bg-gray-900 rounded-md border border-gray-700 text-sm'>
                            <Icon size={16} className="text-gray-400"/>
                            <span className="text-gray-300">{SUPPORTED_LANGUAGES.find(l => l.value === snippet.language)?.label || snippet.language}</span>
                            <div className="absolute -top-2 -right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity bg-gray-800 rounded-md p-1 border border-gray-700">
                                <button type="button" onClick={() => openCodeModal(snippet)} className="p-1 text-gray-400 hover:text-white"><Pencil size={12}/></button>
                                <button type="button" onClick={() => removeCodeSnippet(snippet.id)} className="p-1 text-gray-400 hover:text-red-500"><Trash2 size={12}/></button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
              <form ref={formRef} onSubmit={handleSubmit} className="relative flex items-center space-x-2 p-2">
                <Menu as="div" className="relative flex-shrink-0">
                  <MenuButton className='p-3 h-10 w-10 flex items-center justify-center rounded-full text-gray-400 hover:bg-gray-700 hover:text-gray-200'>
                    <Plus size={20}/>
                  </MenuButton>
                  <Transition as={Fragment} enter="transition ease-out duration-100" enterFrom="transform opacity-0 scale-95" enterTo="transform opacity-100 scale-100" leave="transition ease-in duration-75" leaveFrom="transform opacity-100 scale-100" leaveTo="transform opacity-0 scale-95">
                    <div className="relative">
                      <MenuItems className="absolute bottom-full left-0 mb-2 w-56 origin-bottom-left rounded-xl bg-primary text-white shadow-lg focus:outline-none p-2 z-20">
                        <div className="absolute -bottom-1 left-3 w-4 h-4 bg-primary rotate-45 transform" />
                        <MenuItem>{({ focus }) => ( <button type="button" onClick={open} className={`${focus ? 'bg-white/10' : ''} group flex w-full items-center rounded-md px-3 py-2 text-sm`}> <Image className="mr-3 h-5 w-5" /> Enviar Imagens </button> )}</MenuItem>
                        <MenuItem>{({ focus }) => ( <button type="button" onClick={open} className={`${focus ? 'bg-white/10' : ''} group flex w-full items-center rounded-md px-3 py-2 text-sm`}> <FileText className="mr-3 h-5 w-5" /> Enviar Documentos </button> )}</MenuItem>
                        <MenuItem>{({ focus }) => ( <button type="button" onClick={() => openCodeModal()} className={`${focus ? 'bg-white/10' : ''} group flex w-full items-center rounded-md px-3 py-2 text-sm`}> <Code className="mr-3 h-5 w-5" /> Anexar Código </button> )}</MenuItem>
                      </MenuItems>
                    </div>
                  </Transition>
                </Menu>
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
                  // 3. ADICIONAR ESTAS PROPRIEDADES
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

    {/* ... (o restante do seu componente com o Dialog permanece o mesmo) ... */}
    <Transition appear show={inputMode === 'code'} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={() => setInputMode('text')}>
        <Transition.Child as={Fragment} enter="ease-out duration-300" enterFrom="opacity-0" enterTo="opacity-100" leave="ease-in duration-200" leaveFrom="opacity-100" leaveTo="opacity-0">
            <div className="fixed inset-0 bg-black/60" />
        </Transition.Child>
        <div className="fixed inset-0 overflow-y-auto">
            <div className="flex min-h-full items-center justify-center p-4 text-center">
                <Dialog.Panel className="w-full max-w-2xl transform overflow-hidden rounded-2xl bg-gray-800 text-left align-middle shadow-xl transition-all border border-gray-700">
                    <Dialog.Title as="h3" className="text-lg font-medium leading-6 text-gray-100 p-6 border-b border-gray-700">
                        {editingSnippetId ? "Editar Trecho de Código" : "Anexar Trecho de Código"}
                    </Dialog.Title>
                    <div className="p-6">
                        <div className="mb-4">
                            <label htmlFor="codeLanguage" className="block text-sm font-medium text-gray-300 mb-1">Linguagem:</label>
                            <select 
                                id="codeLanguage" 
                                value={codeLanguage} 
                                onChange={(e) => setCodeLanguage(e.target.value)} 
                                className="block w-full rounded-md border-gray-700 bg-gray-900 text-gray-200 shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
                            >
                                {SUPPORTED_LANGUAGES.map(lang => (
                                    <option key={lang.value} value={lang.value}>{lang.label}</option>
                                ))}
                            </select>
                        </div>
                        <textarea value={codeContent} onChange={(e) => setCodeContent(e.target.value)} className="w-full h-48 p-2 bg-gray-900 text-gray-200 rounded-md font-mono text-sm border border-gray-700 focus:outline-none focus:ring-1 focus:ring-primary custom-scroll" placeholder="Cole seu código aqui..."/>
                        {codeContent && (
                            <div className="mt-4">
                                <label className="block text-sm font-medium text-gray-300 mb-2">Preview:</label>
                                <div className="max-h-48 overflow-y-auto rounded-md bg-gray-900 border border-gray-700">
                                    <SyntaxHighlighter 
                                        language={codeLanguage} 
                                        style={vscDarkPlus} 
                                        customStyle={{ margin: 0, background: 'transparent' }}
                                        children={codeContent}
                                    />
                                </div>
                            </div>
                        )}
                    </div>
                    <div className="bg-gray-700/50 p-4 flex justify-end space-x-2">
                        <button type="button" onClick={() => setInputMode('text')} className="px-4 py-2 text-sm font-medium text-gray-300 bg-gray-600 rounded-md hover:bg-gray-500">Cancelar</button>
                        <button type="button" onClick={handleCodeSubmit} className="px-4 py-2 text-sm font-medium text-white bg-primary rounded-md hover:bg-primary-hover">
                            {editingSnippetId ? "Salvar Alterações" : "Anexar"}
                        </button>
                    </div>
                </Dialog.Panel>
            </div>
        </div>
      </Dialog>
    </Transition>
    </>
  );
};