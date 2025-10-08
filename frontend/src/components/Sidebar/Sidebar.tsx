import { useState, useEffect, useRef } from 'react';
import { PlusCircle, MessageSquare, Pin, Trash2, PinOff, Search, Pencil, Check, X, Share2, BarChart3 } from 'lucide-react';
import type { ChatSession, SessionStats as NewSessionStats } from '../../core/domain/entities';
import { motion, AnimatePresence } from 'framer-motion';
import { ConfirmModal } from '../ConfirmModal/ConfirmModal';
import { SessionStats } from '../SessionStats/SessionStats';

interface Props {
  sessions: ChatSession[];
  activeSessionId: string | null;
  onNewChat: () => void;
  onSwitchChat: (sessionId: string) => void;
  onDeleteChat: (sessionId: string) => void;
  onTogglePin: (sessionId: string) => void;
  onRenameChat: (sessionId: string, newTitle: string) => void;
  onGetSessionStats?: () => Promise<NewSessionStats | null>;
  isOpen: boolean;
}

export const Sidebar = ({ 
  sessions, 
  activeSessionId, 
  onNewChat, 
  onSwitchChat,
  onDeleteChat,
  onTogglePin, 
  onRenameChat,
  onGetSessionStats,
  isOpen, 
}: Props) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [sessionToDelete, setSessionToDelete] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingText, setEditingText] = useState('');
  const [showStats, setShowStats] = useState(false);
  const editInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editingId && editInputRef.current) {
      editInputRef.current.focus();
      editInputRef.current.select();
    }
  }, [editingId]);

  const allSessions = sessions.sort((a, b) => (a.isPinned === b.isPinned) ? 0 : a.isPinned ? -1 : 1);
  
  const filteredSessions = searchTerm.length > 0
    ? allSessions.filter(session => session.title.toLowerCase().includes(searchTerm.toLowerCase()))
    : allSessions;

  const pinnedSessions = filteredSessions.filter(s => s.isPinned);
  const recentSessions = filteredSessions.filter(s => !s.isPinned);

  const handleDeleteClick = (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    setSessionToDelete(sessionId);
    setIsModalOpen(true);
  }

  const confirmDelete = () => {
    if (sessionToDelete) {
        onDeleteChat(sessionToDelete);
    }
  }

  const handlePin = (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    onTogglePin(sessionId);
  }
  
  const handleRenameStart = (e: React.MouseEvent, session: ChatSession) => {
    e.stopPropagation();
    setEditingId(session.id);
    setEditingText(session.title);
  }

  const handleRenameConfirm = (e: React.MouseEvent | React.KeyboardEvent, sessionId: string) => {
    e.stopPropagation();
    onRenameChat(sessionId, editingText);
    setEditingId(null);
  }

  const handleRenameCancel = (e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(null);
  }

  const renderSessionItem = (session: ChatSession) => (
    <motion.div
      key={session.id}
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.2 }}
      onClick={(e) => { e.preventDefault(); onSwitchChat(session.id); }}
      className={`group flex items-center justify-between gap-2 p-2 rounded-md text-sm cursor-pointer ${
        session.id === activeSessionId 
          ? 'bg-gray-800 text-white' 
          : 'text-gray-400 hover:bg-gray-800 hover:text-white'
      }`}
    >
      <div className="flex items-center gap-2 min-w-0 flex-1 overflow-hidden" title={editingId === session.id ? undefined : session.title}>
        <MessageSquare size={16} className="flex-shrink-0" />
        {editingId === session.id ? (
          <input 
            ref={editInputRef}
            type="text"
            value={editingText}
            onClick={(e) => e.stopPropagation()}
            onChange={(e) => setEditingText(e.target.value)}
            onBlur={() => setEditingId(null)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleRenameConfirm(e, session.id)}}
            className="bg-transparent text-white outline-none ring-1 ring-primary rounded-sm px-1 flex-1 min-w-0"
          />
        ) : (
          <span className="truncate block">{session.title}</span>
        )}
      </div>

      {editingId !== session.id && (
        <div className="flex items-center shrink-0 space-x-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <button onClick={(e) => {e.stopPropagation(); alert('Funcionalidade de compartilhar não implementada.')}} className="hover:text-white"><Share2 size={14} /></button>
          <button onClick={(e) => handlePin(e, session.id)} className="hover:text-white">{session.isPinned ? <PinOff size={14} /> : <Pin size={14} />}</button>
          <button onClick={(e) => handleRenameStart(e, session)} className="hover:text-white"><Pencil size={14} /></button>
          <button onClick={(e) => handleDeleteClick(e, session.id)} className="hover:text-red-500"><Trash2 size={14} /></button>
        </div>
      )}
      {editingId === session.id && (
        <div className="flex items-center shrink-0 space-x-2">
           <button onClick={(e) => handleRenameConfirm(e, session.id)} className="hover:text-green-500"><Check size={14} /></button>
           <button onClick={handleRenameCancel} className="hover:text-red-500"><X size={14} /></button>
        </div>
      )}
    </motion.div>
  );

  return (
    <>
      <motion.aside
        initial={false}
        animate={{ width: isOpen ? 256 : 0, padding: isOpen ? 8 : 0, x: isOpen ? 0 : -256 }}
        transition={{ duration: 0.3, ease: "easeInOut" }}
        className="flex flex-col bg-gray-900/70 backdrop-blur-sm border-r border-white/5 overflow-hidden"
      >
        <div className="p-2 border-b border-white/5">
          <button
            onClick={onNewChat}
            className="flex w-full items-center space-x-2 text-gray-300 hover:text-white p-2 rounded-md hover:bg-white/5"
          >
            <PlusCircle size={20} />
            <span>Nova Conversa</span>
          </button>
        </div>
        
        <div className="p-2 border-b border-white/5 relative">
          <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500" />
          <input 
            type="text" 
            placeholder="Buscar..." 
            className="w-full pl-9 pr-3 py-2 bg-gray-800/50 rounded-md text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-primary"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        {activeSessionId && onGetSessionStats && (
          <div className="p-2 border-b border-white/5">
            <button
              onClick={() => setShowStats(!showStats)}
              className="w-full flex items-center justify-between p-2 text-sm text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 rounded-md transition-colors"
            >
              <span className="flex items-center space-x-2">
                <BarChart3 size={16} />
                <span>Estatísticas da Sessão</span>
              </span>
              <span className={`transform transition-transform ${showStats ? 'rotate-180' : ''}`}>
                ▼
              </span>
            </button>
            
            <SessionStats 
              onGetStats={onGetSessionStats}
              isVisible={showStats}
            />
          </div>
        )}

        <nav className="flex-1 pt-2 space-y-1 overflow-y-auto custom-scroll">
          <AnimatePresence>
              {pinnedSessions.length > 0 && (
                  <div className="px-2 pt-2">
                      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Fixados</h3>
                      <div className="mt-1 space-y-1">
                          {pinnedSessions.map(renderSessionItem)}
                      </div>
                  </div>
              )}
              {recentSessions.length > 0 && (
                  <div className="px-2 pt-4">
                      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Recentes</h3>
                      <div className="mt-1 space-y-1">
                          {recentSessions.map(renderSessionItem)}
                      </div>
                  </div>
              )}
          </AnimatePresence>
        </nav>
      </motion.aside>

      <ConfirmModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onConfirm={confirmDelete}
        title="Apagar Conversa"
        description="Tem certeza que deseja apagar esta conversa? Esta ação não pode ser desfeita."
      />
    </>
  );
};