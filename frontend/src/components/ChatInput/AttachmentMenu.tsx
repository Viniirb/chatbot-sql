import * as Popover from '@radix-ui/react-popover';
import { Plus, Image, FileText, Code } from 'lucide-react';

interface AttachmentMenuProps {
  onOpenFiles: () => void;
  onOpenCodeModal: () => void;
}

export const AttachmentMenu = ({ onOpenFiles, onOpenCodeModal }: AttachmentMenuProps) => {
  return (
    <Popover.Root>
      <Popover.Trigger asChild>
        <button
          type="button"
          className="p-3 h-10 w-10 flex items-center justify-center rounded-full text-gray-400 hover:bg-gray-700 hover:text-gray-200 transition-all duration-200"
          aria-label="Anexar arquivo"
        >
          <Plus size={20} />
        </button>
      </Popover.Trigger>

      <Popover.Portal>
        <Popover.Content
          className="z-[9999] w-56 rounded-2xl bg-gray-900/95 backdrop-blur-xl border border-gray-700/50 shadow-2xl p-2 animate-in fade-in-0 zoom-in-95 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2"
          sideOffset={8}
          align="start"
          side="top"
        >
          <div className="flex flex-col gap-1">
            <Popover.Close asChild>
              <button
                type="button"
                onClick={onOpenFiles}
                className="group flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-white transition-all duration-200 hover:bg-white/10 hover:scale-[1.02]"
              >
                <div className="p-1.5 rounded-lg bg-blue-500/20 group-hover:bg-blue-500/30 transition-colors">
                  <Image size={18} className="text-blue-400" />
                </div>
                <span>Enviar Imagens</span>
              </button>
            </Popover.Close>

            <Popover.Close asChild>
              <button
                type="button"
                onClick={onOpenFiles}
                className="group flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-white transition-all duration-200 hover:bg-white/10 hover:scale-[1.02]"
              >
                <div className="p-1.5 rounded-lg bg-green-500/20 group-hover:bg-green-500/30 transition-colors">
                  <FileText size={18} className="text-green-400" />
                </div>
                <span>Enviar Documentos</span>
              </button>
            </Popover.Close>

            <Popover.Close asChild>
              <button
                type="button"
                onClick={onOpenCodeModal}
                className="group flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-white transition-all duration-200 hover:bg-white/10 hover:scale-[1.02]"
              >
                <div className="p-1.5 rounded-lg bg-purple-500/20 group-hover:bg-purple-500/30 transition-colors">
                  <Code size={18} className="text-purple-400" />
                </div>
                <span>Anexar Código</span>
              </button>
            </Popover.Close>
          </div>

          <Popover.Arrow className="fill-gray-900/95" />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
};
