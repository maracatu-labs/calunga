import { ArrowUpRight, FileText, Landmark, Search, User, Gavel } from "lucide-react";
import type { FeedLink } from "@/lib/actions";

const ICONS: Record<FeedLink["tipo"], typeof ArrowUpRight> = {
  fonte_oficial: Landmark,
  documento: FileText,
  consulta: Search,
  perfil: User,
  processo: Gavel,
};

export function LinkList({ links, compact = false }: { links?: FeedLink[]; compact?: boolean }) {
  if (!links || links.length === 0) return null;
  return (
    <div className={`flex flex-wrap gap-2 ${compact ? "" : "mt-3"}`}>
      {links.map((link, i) => {
        const Icon = ICONS[link.tipo] ?? ArrowUpRight;
        return (
          <a
            key={`${link.url}-${i}`}
            href={link.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full bg-white dark:bg-[#212121] border border-zinc-200 dark:border-zinc-700 text-zinc-600 dark:text-zinc-300 hover:border-zinc-400 dark:hover:border-zinc-500 transition-colors"
          >
            <Icon className="w-3 h-3" />
            <span>{link.label}</span>
            <ArrowUpRight className="w-3 h-3 opacity-60" />
          </a>
        );
      })}
    </div>
  );
}
