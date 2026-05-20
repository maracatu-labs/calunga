import type { Metadata } from "next";
import Link from "next/link";
import { Shield, Database, Search, AlertTriangle, Globe, GitBranch, ExternalLink, MessageSquare, Vote, Building2, Landmark, MapPin, Rss } from "lucide-react";
import { fetchFeed } from "@/lib/actions";

export const metadata: Metadata = {
  title: "Maracatu — Controle social dos gastos públicos, no ritmo do povo",
  description: "Pergunte em linguagem natural como o dinheiro público está sendo gasto e receba respostas claras, com dados, fontes oficiais e alertas de irregularidades.",
};

const FONTES = [
  { nome: "Câmara dos Deputados", dados: "Despesas CEAP, deputados, partidos, votações nominais", url: "https://dadosabertos.camara.leg.br", frequencia: "Diária" },
  { nome: "Senado Federal", dados: "Despesas CEAP de senadores, votações nominais", url: "https://www12.senado.leg.br/transparencia", frequencia: "Diária" },
  { nome: "Portal da Transparência", dados: "Cartão corporativo, contratos, viagens, emendas, sanções (CEIS/CNEP/CEPIM), execução orçamentária", url: "https://portaldatransparencia.gov.br", frequencia: "Semanal" },
  { nome: "Receita Federal", dados: "Cadastro Nacional de Pessoa Jurídica (CNPJ)", url: "https://dados.gov.br/dados/conjuntos-dados/cadastro-nacional-da-pessoa-juridica---cnpj", frequencia: "Mensal" },
  { nome: "TSE", dados: "Candidatos, prestação de contas eleitorais (2022, 2024)", url: "https://dadosabertos.tse.jus.br", frequencia: "Pós-eleição" },
  { nome: "SICONFI / Tesouro Nacional", dados: "Dados fiscais de 27 estados e 27 capitais (RREO, RGF)", url: "https://siconfi.tesouro.gov.br", frequencia: "Trimestral" },
];

const CAPACIDADES = [
  { icon: Landmark, titulo: "Congresso Nacional", descricao: "Despesas de 513 deputados e 81 senadores, rankings por gasto, comparações entre parlamentares, votações nominais de PECs e PLs." },
  { icon: Building2, titulo: "Governo Federal", descricao: "Cartão corporativo da Presidência, contratos com fornecedores, viagens a serviço e emendas parlamentares, incluindo Emendas Pix e orçamento secreto." },
  { icon: MapPin, titulo: "Estados e Municípios", descricao: "Dados fiscais de todos os 27 estados e capitais via SICONFI: execução orçamentária, gestão fiscal, receitas e despesas." },
  { icon: Vote, titulo: "Votações e Proposições", descricao: "Como cada parlamentar votou em PECs, PLs, MPVs. Orientação de bancada, resultado da votação, detalhes da proposição." },
];

const CLASSIFICADORES = [
  { nome: "CNPJ/CPF Inválido", descricao: "Valida os dígitos verificadores dos documentos de fornecedores via módulo 11." },
  { nome: "Limite de Subcota", descricao: "Detecta quando um parlamentar ultrapassa o teto mensal de uma categoria (combustível, veículos, alimentação, etc.)." },
  { nome: "Empresa Irregular", descricao: "Cruza o CNPJ do fornecedor com a Receita Federal e sanções CEIS/CNEP/CEPIM. Sinaliza pagamentos a empresas baixadas ou sancionadas." },
  { nome: "Preço de Refeição Anômalo", descricao: "Usa agrupamento estatístico (K-Means) para identificar refeições com valor muito acima do padrão do restaurante." },
  { nome: "Despesa Eleitoral", descricao: "Identifica pagamentos a entidades registradas como campanha eleitoral no TSE." },
  { nome: "Despesa em Fim de Semana", descricao: "Sinaliza despesas de alimentação e combustível realizadas em fins de semana e feriados nacionais." },
  { nome: "Análise de Recibos (OCR)", descricao: "Analisa PDFs de recibos com OCR e IA para identificar inconsistências, como itens não permitidos." },
];

export default async function HomePage() {
  const { eventos } = await fetchFeed({ limit: 3 });
  return (
    <div className="min-h-screen bg-white dark:bg-[#212121] text-zinc-900 dark:text-zinc-100">
      {}
      <header className="h-14 flex items-center justify-between px-4 sm:px-6 bg-white/80 dark:bg-[#212121]/80 backdrop-blur-md sticky top-0 z-10 border-b border-zinc-100 dark:border-zinc-800">
        <div className="flex items-center gap-3">
          <div className="bg-black dark:bg-white text-white dark:text-black w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold">M</div>
          <span className="font-semibold text-lg text-zinc-800 dark:text-zinc-200">Maracatu</span>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/feed"
            className="text-sm font-medium px-4 py-2 text-zinc-600 dark:text-zinc-300 hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors"
          >
            Feed
          </Link>
          <Link
            href="/login"
            className="text-sm font-medium px-4 py-2 bg-black dark:bg-white text-white dark:text-black rounded-full hover:opacity-80 transition-opacity"
          >
            Entrar
          </Link>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-12 sm:py-20">
        {}
        <section className="mb-12">
          <h1 className="text-3xl sm:text-4xl font-bold mb-4 leading-tight">
            Controle social da administração pública brasileira, no ritmo do povo.
          </h1>
          <p className="text-lg text-zinc-600 dark:text-zinc-400 leading-relaxed mb-8">
            O Maracatu usa inteligência artificial para tornar os gastos públicos acessíveis a qualquer cidadão. Fiscalize deputados, senadores, ministérios, estados e municípios. Basta perguntar.
          </p>
          <Link
            href="/chat"
            className="inline-flex items-center justify-center gap-2 bg-black dark:bg-white text-white dark:text-black py-3.5 px-6 rounded-full font-medium hover:opacity-80 transition-opacity"
          >
            <MessageSquare className="w-4 h-4" />
            Fazer uma consulta
          </Link>
        </section>

        {}
        <section className="mb-16">
          <h2 className="text-xl font-semibold mb-6">O que você pode fiscalizar</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {CAPACIDADES.map((cap) => (
              <div key={cap.titulo} className="p-5 bg-[#f4f4f4] dark:bg-[#2f2f2f] rounded-2xl">
                <cap.icon className="w-5 h-5 text-emerald-500 mb-3" />
                <h3 className="font-medium mb-2 text-sm">{cap.titulo}</h3>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">{cap.descricao}</p>
              </div>
            ))}
          </div>
        </section>

        {}
        <section className="mb-16">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <Shield className="w-5 h-5 text-emerald-500" />
            Por que o Maracatu existe
          </h2>
          <div className="space-y-4 text-zinc-600 dark:text-zinc-400 leading-relaxed">
            <p>
              Os dados de gastos públicos no Brasil são abertos, mas estão espalhados em dezenas de portais governamentais, em formatos diferentes, com interfaces complexas e linguagem burocrática. Na prática, a transparência existe no papel, mas não na experiência do cidadão.
            </p>
            <p>
              O Maracatu resolve isso colocando uma IA conversacional entre os dados e o cidadão. Você pergunta em português e a <strong>Calunga</strong>, nossa guardiã do dinheiro público, busca nos dados oficiais e responde com clareza, fontes e alertas.
            </p>
            <p>
              O nome vem do <strong>Maracatu</strong>, manifestação cultural afro-brasileira de resistência nascida em Pernambuco. Cada componente do sistema carrega um nome do cortejo: a Calunga protege, o Baque nunca para, o Gonguê alerta.
            </p>
          </div>
        </section>

        {}
        <section className="mb-16">
          <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
            <GitBranch className="w-5 h-5 text-emerald-500" />
            Como funciona
          </h2>
          <div className="grid gap-4">
            <div className="p-5 bg-[#f4f4f4] dark:bg-[#2f2f2f] rounded-2xl">
              <h3 className="font-medium mb-2">1. Você pergunta</h3>
              <p className="text-sm text-zinc-600 dark:text-zinc-400">
                Digite qualquer pergunta em linguagem natural. "Quanto gastou o deputado X?", "Quais emendas pix foram para meu estado?", "Mostre os contratos desse ministério."
              </p>
            </div>
            <div className="p-5 bg-[#f4f4f4] dark:bg-[#2f2f2f] rounded-2xl">
              <h3 className="font-medium mb-2">2. A Calunga busca nos dados oficiais</h3>
              <p className="text-sm text-zinc-600 dark:text-zinc-400">
                Nossa IA usa 13 ferramentas especializadas para consultar dados reais de 6 fontes governamentais. Ela nunca inventa números e sempre vai à fonte.
              </p>
            </div>
            <div className="p-5 bg-[#f4f4f4] dark:bg-[#2f2f2f] rounded-2xl">
              <h3 className="font-medium mb-2">3. Você recebe a resposta com fontes</h3>
              <p className="text-sm text-zinc-600 dark:text-zinc-400">
                Respostas com tabelas, gráficos, valores formatados e a fonte oficial citada. Se algo parece suspeito, a Calunga destaca e explica por quê.
              </p>
            </div>
          </div>
        </section>

        {}
        <section className="mb-16">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <Rss className="w-5 h-5 text-emerald-500" />
            Últimas descobertas
          </h2>
          <p className="text-zinc-600 dark:text-zinc-400 mb-6 leading-relaxed">
            Irregularidades e eventos detectados automaticamente pela análise diária e por cidadãos investigando no chat.
          </p>

          {eventos.length > 0 ? (
            <div className="space-y-3 mb-6">
              {eventos.map((e) => (
                <div key={e.id} className="p-4 bg-[#f4f4f4] dark:bg-[#2f2f2f] rounded-xl">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="mb-1">
                        <h3 className="font-medium text-sm truncate">{e.titulo}</h3>
                      </div>
                      <p className="text-xs text-zinc-500 dark:text-zinc-400 line-clamp-2">{e.descricao}</p>
                    </div>
                    <span className="text-xs text-zinc-400 dark:text-zinc-500 whitespace-nowrap shrink-0">
                      {new Date(e.created_at).toLocaleDateString("pt-BR", { day: "2-digit", month: "short" })}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-6 bg-[#f4f4f4] dark:bg-[#2f2f2f] rounded-2xl text-center mb-6">
              <p className="text-sm text-zinc-500 dark:text-zinc-400">
                Os primeiros eventos aparecerão após a primeira rodada de análise automática.
              </p>
            </div>
          )}

          <div className="flex flex-col sm:flex-row gap-3">
            <Link
              href="/feed"
              className="inline-flex items-center justify-center gap-2 text-sm font-medium px-6 py-3 bg-black dark:bg-white text-white dark:text-black rounded-full hover:opacity-80 transition-opacity"
            >
              <Rss className="w-4 h-4" />
              Ver feed completo
            </Link>
            <Link
              href="/chat"
              className="inline-flex items-center justify-center gap-2 text-sm font-medium px-6 py-3 border border-zinc-300 dark:border-zinc-700 text-zinc-700 dark:text-zinc-300 rounded-full hover:bg-zinc-50 dark:hover:bg-[#2f2f2f] transition-colors"
            >
              <MessageSquare className="w-4 h-4" />
              Investigar no chat
            </Link>
          </div>
        </section>

        {}
        <section className="mb-16">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <Database className="w-5 h-5 text-emerald-500" />
            Arquitetura técnica
          </h2>
          <p className="text-zinc-600 dark:text-zinc-400 leading-relaxed mb-4">
            O Maracatu é composto por cinco componentes que trabalham juntos:
          </p>
          <div className="overflow-x-auto rounded-xl border border-zinc-200 dark:border-zinc-800">
            <table className="min-w-full divide-y divide-zinc-200 dark:divide-zinc-800">
              <thead>
                <tr>
                  <th className="px-4 py-3 bg-[#f9f9f9] dark:bg-[#171717] text-left text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase whitespace-nowrap">Componente</th>
                  <th className="px-4 py-3 bg-[#f9f9f9] dark:bg-[#171717] text-left text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase whitespace-nowrap">Função</th>
                  <th className="px-4 py-3 bg-[#f9f9f9] dark:bg-[#171717] text-left text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase whitespace-nowrap">Tecnologia</th>
                </tr>
              </thead>
              <tbody>
                {[
                  ["Calunga", "Agente IA com 13 ferramentas de consulta", "LangGraph + Claude"],
                  ["Baque", "Pipeline de ingestão contínua de 10+ fontes", "Dagster"],
                  ["Gonguê", "7 classificadores de detecção de anomalias", "Regras + K-Means + OCR"],
                  ["Terreiro", "API REST com busca semântica", "FastAPI + PostgreSQL + pgvector"],
                  ["Cortejo", "Interface web conversacional", "Next.js + Tailwind"],
                ].map(([nome, funcao, tech], i, arr) => (
                  <tr key={nome}>
                    <td className={`px-4 py-3 text-sm font-medium ${i < arr.length - 1 ? "border-b border-zinc-100 dark:border-zinc-800/50" : ""}`}>{nome}</td>
                    <td className={`px-4 py-3 text-sm text-zinc-600 dark:text-zinc-400 ${i < arr.length - 1 ? "border-b border-zinc-100 dark:border-zinc-800/50" : ""}`}>{funcao}</td>
                    <td className={`px-4 py-3 text-sm text-zinc-500 whitespace-nowrap ${i < arr.length - 1 ? "border-b border-zinc-100 dark:border-zinc-800/50" : ""}`}>{tech}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {}
        <section className="mb-16">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <Globe className="w-5 h-5 text-emerald-500" />
            De onde vêm os dados
          </h2>
          <p className="text-zinc-600 dark:text-zinc-400 mb-6 leading-relaxed">
            Todos os dados vêm de fontes oficiais do governo brasileiro, públicas e gratuitas. Você pode verificar qualquer informação diretamente no portal original.
          </p>
          <div className="space-y-3">
            {FONTES.map((fonte) => (
              <div key={fonte.nome} className="p-4 bg-[#f4f4f4] dark:bg-[#2f2f2f] rounded-xl flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="font-medium text-sm">{fonte.nome}</h3>
                    <span className="text-xs text-zinc-400 dark:text-zinc-500">{fonte.frequencia}</span>
                  </div>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">{fonte.dados}</p>
                </div>
                <a
                  href={fonte.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400 hover:underline shrink-0"
                >
                  Verificar fonte <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            ))}
          </div>
        </section>

        {}
        <section className="mb-16">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-emerald-500" />
            Como detectamos irregularidades
          </h2>
          <p className="text-zinc-600 dark:text-zinc-400 mb-6 leading-relaxed">
            O Gonguê usa 7 classificadores automáticos, baseados em regras matemáticas e estatísticas (não opinião), para sinalizar despesas que merecem atenção. Toda suspeita pode ser verificada nos dados originais.
          </p>
          <div className="space-y-3">
            {CLASSIFICADORES.map((c) => (
              <div key={c.nome} className="p-4 bg-[#f4f4f4] dark:bg-[#2f2f2f] rounded-xl">
                <h3 className="font-medium text-sm mb-1">{c.nome}</h3>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">{c.descricao}</p>
              </div>
            ))}
          </div>
        </section>

        {}
        <section className="mb-16">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <Search className="w-5 h-5 text-emerald-500" />
            Como verificar as informações
          </h2>
          <div className="space-y-4 text-zinc-600 dark:text-zinc-400 leading-relaxed">
            <p>
              Toda resposta da Calunga cita a fonte oficial dos dados. Você pode, e deve, verificar:
            </p>
            <ul className="space-y-2 ml-4">
              <li className="flex gap-2"><span className="text-emerald-500 shrink-0">1.</span>Clique nos links das fontes citadas na resposta para acessar o portal oficial</li>
              <li className="flex gap-2"><span className="text-emerald-500 shrink-0">2.</span>Compare os valores apresentados com os dados do portal original</li>
              <li className="flex gap-2"><span className="text-emerald-500 shrink-0">3.</span>Suspeitas sinalizadas incluem o motivo e os critérios usados, não é opinião</li>
              <li className="flex gap-2"><span className="text-emerald-500 shrink-0">4.</span>Os classificadores usam regras públicas e auditáveis com base em legislação vigente</li>
            </ul>
            <p>
              A IA pode cometer erros de interpretação. Os dados são reais, mas a análise é assistida por máquina. Use o Maracatu como ponto de partida para investigação, não como veredicto final.
            </p>
          </div>
        </section>

        {}
        <section className="mb-16 p-6 bg-[#f4f4f4] dark:bg-[#2f2f2f] rounded-2xl text-center">
          <h2 className="text-lg font-semibold mb-2">Comece a fiscalizar agora</h2>
          <p className="text-sm text-zinc-600 dark:text-zinc-400 mb-4">
            Pergunte sobre qualquer gasto público brasileiro.
          </p>
          <Link
            href="/chat"
            className="inline-flex items-center justify-center gap-2 text-sm font-medium px-6 py-3 bg-black dark:bg-white text-white dark:text-black rounded-full hover:opacity-80 transition-opacity"
          >
            <MessageSquare className="w-4 h-4" />
            Fazer uma consulta
          </Link>
        </section>

        {}
        <footer className="text-center text-xs text-zinc-400 dark:text-zinc-500 pt-8 pb-12 border-t border-zinc-100 dark:border-zinc-800">
          <p>Maracatu — Controle social da administração pública brasileira, no ritmo do povo.</p>
        </footer>
      </main>
    </div>
  );
}
