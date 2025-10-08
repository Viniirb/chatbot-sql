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
          <div className="fixed inset-0 bg-black/60" />
        </Transition.Child>
        
        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4 text-center">
            <DialogPanel className="w-full max-w-2xl transform overflow-hidden rounded-2xl bg-gray-800 text-left align-middle shadow-xl transition-all border border-gray-700">
              <DialogTitle as="h3" className="text-lg font-medium leading-6 text-gray-100 p-6 border-b border-gray-700">
                {isEditing ? "Editar Trecho de Código" : "Anexar Trecho de Código"}
              </DialogTitle>
              
              <div className="p-6">
                <div className="mb-4">
                  <label htmlFor="codeLanguage" className="block text-sm font-medium text-gray-300 mb-1">
                    Linguagem:
                  </label>
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
                
                <textarea 
                  value={codeContent} 
                  onChange={(e) => setCodeContent(e.target.value)} 
                  className="w-full h-48 p-2 bg-gray-900 text-gray-200 rounded-md font-mono text-sm border border-gray-700 focus:outline-none focus:ring-1 focus:ring-primary custom-scroll" 
                  placeholder="Cole seu código aqui..."
                />
                
                {codeContent && (
                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-300 mb-2">Preview:</label>
                    <div className="max-h-48 overflow-y-auto rounded-md bg-gray-900 border border-gray-700">
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
              
              <div className="bg-gray-700/50 p-4 flex justify-end space-x-2">
                <button 
                  type="button" 
                  onClick={onClose} 
                  className="px-4 py-2 text-sm font-medium text-gray-300 bg-gray-600 rounded-md hover:bg-gray-500"
                >
                  Cancelar
                </button>
                <button 
                  type="button" 
                  onClick={onSubmit} 
                  className="px-4 py-2 text-sm font-medium text-white bg-primary rounded-md hover:bg-primary-hover"
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