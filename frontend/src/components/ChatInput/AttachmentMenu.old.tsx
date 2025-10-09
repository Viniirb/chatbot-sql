import { Fragment } from 'react';
import { Menu, MenuButton, MenuItems, MenuItem, Transition } from '@headlessui/react';
import { Plus, Image, FileText, Code } from 'lucide-react';

interface AttachmentMenuProps {
  onOpenFiles: () => void;
  onOpenCodeModal: () => void;
}

export const AttachmentMenu = ({ onOpenFiles, onOpenCodeModal }: AttachmentMenuProps) => {
  return (
    <Menu as="div" className="relative flex-shrink-0">
      <MenuButton className="p-3 h-10 w-10 flex items-center justify-center rounded-full text-gray-400 hover:bg-gray-700 hover:text-gray-200">
        <Plus size={20}/>
      </MenuButton>
      
      <Transition 
        as={Fragment} 
        enter="transition ease-out duration-100" 
        enterFrom="transform opacity-0 scale-95" 
        enterTo="transform opacity-100 scale-100" 
        leave="transition ease-in duration-75" 
        leaveFrom="transform opacity-100 scale-100" 
        leaveTo="transform opacity-0 scale-95"
      >
        <div className="relative">
          <MenuItems className="absolute bottom-full left-0 mb-2 w-56 origin-bottom-left rounded-2xl bg-gray-900/95 backdrop-blur-xl border border-purple-500/30 text-white shadow-2xl shadow-purple-500/20 focus:outline-none p-2 z-20">
            <div className="absolute -bottom-1 left-3 w-4 h-4 bg-gray-900/95 rotate-45 transform border-r border-b border-purple-500/30" />
            
            <MenuItem>
              {({ focus }) => ( 
                <button 
                  type="button" 
                  onClick={onOpenFiles} 
                  className={`${focus ? 'bg-purple-500/20 scale-105' : ''} group flex w-full items-center rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200`}
                > 
                  <Image className="mr-3 h-5 w-5 group-hover:scale-110 transition-transform" /> 
                  Enviar Imagens 
                </button> 
              )}
            </MenuItem>
            
            <MenuItem>
              {({ focus }) => ( 
                <button 
                  type="button" 
                  onClick={onOpenFiles} 
                  className={`${focus ? 'bg-purple-500/20 scale-105' : ''} group flex w-full items-center rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200`}
                > 
                  <FileText className="mr-3 h-5 w-5 group-hover:scale-110 transition-transform" /> 
                  Enviar Documentos 
                </button> 
              )}
            </MenuItem>
            
            <MenuItem>
              {({ focus }) => ( 
                <button 
                  type="button" 
                  onClick={onOpenCodeModal} 
                  className={`${focus ? 'bg-purple-500/20 scale-105' : ''} group flex w-full items-center rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200`}
                > 
                  <Code className="mr-3 h-5 w-5 group-hover:scale-110 transition-transform" /> 
                  Anexar Código 
                </button> 
              )}
            </MenuItem>
          </MenuItems>
        </div>
      </Transition>
    </Menu>
  );
};