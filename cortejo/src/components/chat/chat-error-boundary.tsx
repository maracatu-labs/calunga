"use client";

import { Component, type ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

type Props = {
  children: ReactNode;
};

type State = {
  error: Error | null;
};

/**
 * Captura erros de renderizacao na area do chat e exibe um fallback amigavel
 * com opcao de recarregar. Nao captura erros de rede (esses vem pelo stream
 * como evento type=error e sao tratados pelo useChat).
 */
export default class ChatErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: unknown) {
    // eslint-disable-next-line no-console
    console.error("[ChatErrorBoundary]", error, info);
  }

  handleReload = () => {
    this.setState({ error: null });
    if (typeof window !== "undefined") window.location.reload();
  };

  render() {
    if (this.state.error) {
      return (
        <div className="flex flex-col items-center justify-center h-full p-8 text-center">
          <AlertTriangle className="w-10 h-10 text-red-500 mb-3" />
          <h3 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
            Algo deu errado no chat
          </h3>
          <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1 mb-4 max-w-md">
            A Calunga encontrou um erro ao carregar esta conversa. Você pode recarregar a página para tentar de novo.
          </p>
          <button
            onClick={this.handleReload}
            className="flex items-center gap-2 px-4 py-2 rounded-full bg-black dark:bg-white text-white dark:text-black text-sm font-medium hover:opacity-80 transition-opacity"
          >
            <RefreshCw className="w-4 h-4" />
            Recarregar
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
