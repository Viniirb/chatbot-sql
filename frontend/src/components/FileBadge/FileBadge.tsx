import { File, X } from 'lucide-react';

interface Props {
  file: File;
  icon?: React.ElementType;
  onRemove: () => void;
}

export const FileBadge = ({ file, icon: Icon = File, onRemove }: Props) => {
  return (
    <div className='group relative flex items-center gap-2 p-2 h-16 bg-gray-900 rounded-md border border-gray-700 text-sm w-48'>
      <Icon size={24} className="text-gray-400 flex-shrink-0" />
      <div className="flex flex-col overflow-hidden">
        <span className="text-gray-300 truncate font-medium">{file.name}</span>
        <span className="text-xs text-gray-500">{Math.round(file.size / 1024)} KB</span>
      </div>
      <button 
        type="button" 
        onClick={onRemove} 
        className="absolute -top-1.5 -right-1.5 bg-gray-600 rounded-full p-0.5 text-white hover:bg-red-500"
      >
        <X size={14}/>
      </button>
    </div>
  );
}