import { Dialog, Transition } from '@headlessui/react'
import { Fragment } from 'react'
import { AlertTriangle } from 'lucide-react'

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  description: string;
}

export const ConfirmModal = ({ isOpen, onClose, onConfirm, title, description }: Props) => {
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
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-md transform overflow-hidden rounded-3xl bg-gray-900/95 backdrop-blur-2xl p-6 text-left align-middle shadow-2xl shadow-purple-500/10 transition-all border border-purple-500/20">
                <div className='flex items-start space-x-4'>
                    <div className='flex h-14 w-14 flex-shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-red-500/20 to-red-700/20 backdrop-blur-sm border border-red-500/30'>
                        <AlertTriangle className='h-7 w-7 text-red-400' aria-hidden="true"/>
                    </div>
                    <div className='mt-0 text-left flex-1'>
                        <Dialog.Title
                        as="h3"
                        className="text-xl font-bold leading-6 text-gray-100 mb-2"
                        >
                        {title}
                        </Dialog.Title>
                        <p className="text-sm text-gray-400 leading-relaxed">
                            {description}
                        </p>
                    </div>
                </div>

                <div className="mt-6 flex justify-end space-x-3">
                  <button
                    type="button"
                    className="inline-flex justify-center rounded-xl border border-gray-700 bg-gray-800/80 backdrop-blur-sm px-6 py-2.5 text-sm font-semibold text-gray-200 hover:bg-gray-700 hover:border-gray-600 focus:outline-none transition-all duration-300 hover:scale-105 shadow-lg"
                    onClick={onClose}
                  >
                    Cancelar
                  </button>
                  <button
                    type="button"
                    className="inline-flex justify-center rounded-xl border border-transparent bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 px-6 py-2.5 text-sm font-semibold text-white focus:outline-none transition-all duration-300 hover:scale-105 shadow-xl shadow-red-500/40"
                    onClick={() => {
                        onConfirm();
                        onClose();
                    }}
                  >
                    Apagar
                  </button>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}