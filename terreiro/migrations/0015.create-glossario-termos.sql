

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS glossario_termos (
    id SERIAL PRIMARY KEY,
    termo VARCHAR(100) NOT NULL UNIQUE,
    aliases TEXT[] NOT NULL DEFAULT '{}',
    categoria VARCHAR(50) NOT NULL,
    definicao TEXT NOT NULL,
    fonte_url TEXT,
    embedding vector(1024),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_glossario_termo_lower
    ON glossario_termos (LOWER(termo));

CREATE INDEX IF NOT EXISTS idx_glossario_categoria
    ON glossario_termos (categoria);

CREATE INDEX IF NOT EXISTS idx_glossario_aliases_gin
    ON glossario_termos USING GIN (aliases);

CREATE INDEX IF NOT EXISTS idx_glossario_embedding
    ON glossario_termos USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 200);

INSERT INTO glossario_termos (termo, aliases, categoria, definicao, fonte_url) VALUES
(
    'LOA',
    ARRAY['Lei Orçamentária Anual'],
    'orcamento',
    'Lei Orçamentária Anual. Fixa todas as despesas e estima as receitas do governo para o ano seguinte. Aprovada anualmente pelo Congresso, ela é o orçamento em si — sem LOA, nenhum gasto público pode acontecer.',
    'https://www12.senado.leg.br/orcamento/glossario'
),
(
    'LDO',
    ARRAY['Lei de Diretrizes Orçamentárias'],
    'orcamento',
    'Lei de Diretrizes Orçamentárias. Define as metas e prioridades que a LOA do ano seguinte deve seguir, inclusive metas fiscais, riscos e regras para novas despesas. Precede a LOA no calendário orçamentário.',
    'https://www12.senado.leg.br/orcamento/glossario'
),
(
    'PPA',
    ARRAY['Plano Plurianual'],
    'orcamento',
    'Plano Plurianual. Estabelece diretrizes, objetivos e metas do governo federal para 4 anos (do 2º ano de um mandato ao 1º do seguinte). LOA e LDO precisam ser compatíveis com o PPA vigente.',
    'https://www.gov.br/planejamento/pt-br/assuntos/planejamento/plano-plurianual'
),
(
    'RCL',
    ARRAY['Receita Corrente Líquida'],
    'fiscal',
    'Receita Corrente Líquida. Soma das receitas correntes do ente público (impostos, transferências, serviços) deduzidas as transferências obrigatórias. É a base de cálculo dos limites de gasto com pessoal, dívida e operações de crédito da LRF.',
    'https://www.tesourotransparente.gov.br/glossario'
),
(
    'CEAP',
    ARRAY['Cota para o Exercício da Atividade Parlamentar', 'cota parlamentar'],
    'transparencia',
    'Cota para o Exercício da Atividade Parlamentar. Valor mensal que cada deputado e senador pode gastar em despesas de mandato (passagens, combustível, aluguel de escritório, divulgação etc.), reembolsado mediante apresentação de nota fiscal. Os limites variam por UF.',
    'https://www.camara.leg.br/cota-parlamentar'
),
(
    'CPGF',
    ARRAY['Cartão de Pagamento do Governo Federal', 'cartão corporativo'],
    'transparencia',
    'Cartão de Pagamento do Governo Federal. Cartão usado por órgãos do Executivo federal para despesas de pronto pagamento (suprimento de fundos e defesa civil). Os gastos são públicos e disponibilizados pelo Portal da Transparência mês a mês.',
    'https://portaldatransparencia.gov.br/cartoes'
),
(
    'Emenda Pix',
    ARRAY['Emenda Individual de Transferência Especial', 'transferência especial'],
    'orcamento',
    'Emenda Individual de Transferência Especial. Modalidade em que o parlamentar transfere dinheiro direto ao estado ou município beneficiário, sem convênio, sem plano de trabalho e com prestação de contas simplificada. Chamada popularmente de ''Emenda Pix'' por causa da agilidade do repasse.',
    'https://www12.senado.leg.br/noticias/glossario-legislativo/emenda-pix'
),
(
    'Emenda de Relator',
    ARRAY['RP9', 'orçamento secreto'],
    'orcamento',
    'Emendas incluídas no orçamento pelo relator-geral da LOA (indicador RP9). Ficaram conhecidas como ''orçamento secreto'' por não identificarem diretamente o parlamentar solicitante. O STF determinou maior transparência sobre esse uso em 2022.',
    'https://www2.camara.leg.br/orcamento-da-uniao/glossario'
),
(
    'Emenda de Bancada',
    ARRAY['emenda de bancada estadual'],
    'orcamento',
    'Emenda apresentada pela bancada estadual (todos os parlamentares de uma UF) ao orçamento, voltada a projetos estruturantes de interesse do estado. Tem execução impositiva parcial.',
    'https://www2.camara.leg.br/orcamento-da-uniao/glossario'
),
(
    'Emenda de Comissão',
    ARRAY[]::TEXT[],
    'orcamento',
    'Emenda apresentada por comissão permanente ou mista ao orçamento, voltada ao tema da comissão. Não tem execução impositiva, depende de disponibilidade financeira.',
    'https://www2.camara.leg.br/orcamento-da-uniao/glossario'
),
(
    'RREO',
    ARRAY['Relatório Resumido da Execução Orçamentária'],
    'fiscal',
    'Relatório Resumido da Execução Orçamentária. Publicado a cada 2 meses por todos os entes (União, estados e municípios), mostra receitas e despesas do período. Base para acompanhar execução do orçamento ao longo do ano.',
    'https://www.tesourotransparente.gov.br/siconfi'
),
(
    'RGF',
    ARRAY['Relatório de Gestão Fiscal'],
    'fiscal',
    'Relatório de Gestão Fiscal. Publicado quadrimestralmente, mostra se o ente cumpriu os limites da Lei de Responsabilidade Fiscal (pessoal, dívida, operações de crédito). Obrigatório para União, estados e municípios.',
    'https://www.tesourotransparente.gov.br/siconfi'
),
(
    'Empenho',
    ARRAY[]::TEXT[],
    'orcamento',
    'Primeira fase da despesa pública. Ato que reserva dotação do orçamento para um compromisso a ser pago futuramente. Empenhar não é pagar — significa garantir que o recurso ficará separado até a entrega do bem ou serviço.',
    'https://www.tesourotransparente.gov.br/glossario'
),
(
    'Liquidação',
    ARRAY[]::TEXT[],
    'orcamento',
    'Segunda fase da despesa pública. Verificação de que o bem ou serviço foi entregue conforme o contrato, gerando direito ao pagamento. Entre empenho e liquidação, nada foi efetivamente gasto ainda.',
    'https://www.tesourotransparente.gov.br/glossario'
),
(
    'Pagamento',
    ARRAY['fase de pagamento'],
    'orcamento',
    'Terceira fase da despesa pública. Saída efetiva de recursos para o fornecedor após empenho e liquidação. Valores no portal ''pago'' refletem dinheiro que saiu do cofre.',
    'https://www.tesourotransparente.gov.br/glossario'
),
(
    'CEIS',
    ARRAY['Cadastro de Empresas Inidôneas e Suspensas'],
    'transparencia',
    'Cadastro Nacional de Empresas Inidôneas e Suspensas. Lista empresas proibidas de contratar com a administração pública por terem sido sancionadas em processo administrativo. Mantida pela CGU.',
    'https://portaldatransparencia.gov.br/sancoes/ceis'
),
(
    'CNEP',
    ARRAY['Cadastro Nacional de Empresas Punidas'],
    'transparencia',
    'Cadastro Nacional de Empresas Punidas. Lista empresas punidas por atos contra a administração pública com base na Lei Anticorrupção (12.846/2013). Mantido pela CGU.',
    'https://portaldatransparencia.gov.br/sancoes/cnep'
),
(
    'CEPIM',
    ARRAY['Cadastro de Entidades Privadas Sem Fins Lucrativos Impedidas'],
    'transparencia',
    'Cadastro de Entidades Privadas Sem Fins Lucrativos Impedidas. Lista ONGs e associações impedidas de firmar convênios e termos de parceria com a União por irregularidades.',
    'https://portaldatransparencia.gov.br/sancoes/cepim'
),
(
    'SICONFI',
    ARRAY['Sistema de Informações Contábeis e Fiscais do Setor Público Brasileiro'],
    'fiscal',
    'Sistema do Tesouro Nacional onde todos os entes públicos (União, estados, municípios) publicam seus relatórios fiscais obrigatórios (RREO, RGF, DCA). Fonte única para comparar finanças entre estados e capitais.',
    'https://siconfi.tesouro.gov.br'
),
(
    'Subcota',
    ARRAY['limite de subcota', 'subcota mensal'],
    'transparencia',
    'Limite mensal por categoria dentro da CEAP (ex: combustível, alimentação). Cada categoria tem teto próprio em reais; ultrapassar o teto em um mês é irregularidade detectada pelos classificadores do Maracatu.',
    'https://www.camara.leg.br/cota-parlamentar'
)
ON CONFLICT (termo) DO NOTHING;
