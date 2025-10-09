import { Fragment } from 'react';
import { Dialog, Transition, DialogPanel, DialogTitle } from '@headlessui/react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

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

interface CodeModalProps {
  isOpen: boolean;
  onClose: () => void;
  codeContent: string;
  setCodeContent: (content: string) => void;
  codeLanguage: string;
  setCodeLanguage: (language: string) => void;
  onSubmit: () => void;
  isEditing: boolean;
}

export const CodeModal = ({
  isOpen,
  onClose,
  codeContent,
  setCodeContent,
  codeLanguage,
  setCodeLanguage,
  onSubmit,
  isEditing
}: CodeModalProps) => {
  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child 
          as={Fragment} 
          enter="ease-out duration-300" 
          enterFrom="opacity-0" 
          enterTo="opacity-100" 
          leave="ease-in duration-200" 
          leaveFrom="opacity-100" 
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/80 backdrop-blur-md" />
        </Transition.Child>
        
        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4 text-center">
            <DialogPanel className="w-full max-w-3xl transform overflow-hidden rounded-3xl bg-gradient-to-br from-gray-900/95 via-purple-950/30 to-gray-900/95 backdrop-blur-2xl text-left align-middle shadow-2xl shadow-purple-500/20 transition-all border border-purple-500/30">
              <DialogTitle as="h3" className="text-xl font-bold leading-6 bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent p-6 border-b border-purple-500/30">
                {isEditing ? "Editar Trecho de Código" : "Anexar Trecho de Código"}
              </DialogTitle>
              
              <div className="p-6">
                <div className="mb-4">
                  <label htmlFor="codeLanguage" className="block text-sm font-semibold text-purple-300 mb-2">
                    Linguagem:
                  </label>
                  <select 
                    id="codeLanguage" 
                    value={codeLanguage} 
                    onChange={(e) => setCodeLanguage(e.target.value)} 
                    className="block w-full rounded-xl border border-purple-500/30 bg-gray-900/80 backdrop-blur-sm text-gray-200 shadow-lg shadow-purple-500/10 focus:border-purple-500/50 focus:ring-2 focus:ring-purple-500/30 sm:text-sm py-2.5 px-3 transition-all duration-300"
                  >
                    {SUPPORTED_LANGUAGES.map(lang => (
                      <option key={lang.value} value={lang.value}>{lang.label}</option>
                    ))}
                  </select>
                </div>
                
                <textarea 
                  value={codeContent} 
                  onChange={(e) => setCodeContent(e.target.value)} 
                  className="w-full h-56 p-4 bg-gray-900/80 backdrop-blur-sm text-gray-200 rounded-xl font-mono text-sm border border-purple-500/30 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 custom-scroll shadow-lg shadow-purple-500/10 transition-all duration-300" 
                  placeholder="Cole seu código aqui..."
                />
                
                {codeContent && (
                  <div className="mt-6">
                    <label className="flex items-center gap-2 text-sm font-semibold text-purple-300 mb-3">
                      <span className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-pulse"></span>
                      Preview:
                    </label>
                    <div className="max-h-64 overflow-y-auto rounded-xl bg-gray-900/80 backdrop-blur-sm border border-purple-500/30 shadow-lg shadow-purple-500/10">
                      <SyntaxHighlighter 
                        language={codeLanguage} 
                        style={vscDarkPlus} 
                        customStyle={{ margin: 0, background: 'transparent' }}
                      >
                        {codeContent}
                      </SyntaxHighlighter>
                    </div>
                  </div>
                )}
              </div>
              
              <div className="bg-gradient-to-r from-gray-900/80 to-purple-950/30 backdrop-blur-xl p-6 flex justify-end space-x-3 border-t border-purple-500/30">
                <button 
                  type="button" 
                  onClick={onClose} 
                  className="px-6 py-2.5 text-sm font-semibold text-gray-300 bg-gray-800/80 backdrop-blur-sm border border-gray-700 rounded-xl hover:bg-gray-700 hover:border-gray-600 transition-all duration-300 hover:scale-105 shadow-lg"
                >
                  Cancelar
                </button>
                <button 
                  type="button" 
                  onClick={onSubmit} 
                  className="px-6 py-2.5 text-sm font-semibold text-white bg-gradient-to-r from-purple-600 via-purple-500 to-purple-700 rounded-xl hover:from-purple-500 hover:via-purple-600 hover:to-purple-600 transition-all duration-300 hover:scale-105 shadow-xl shadow-purple-500/50"
                >
                  {isEditing ? "Salvar Alterações" : "Anexar"}
                </button>
              </div>
            </DialogPanel>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
};