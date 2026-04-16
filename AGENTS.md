# AGENTS.md

## Requisitos de Negócio

- Manter o mapa das escolas do Espirito Santo funcional em dois modos: local completo com API/CRUD e GitHub Pages em modo estatico.
- Preservar o contrato dos datasets publicados em `public/data/schools/e_*.json`, porque eles alimentam o mapa e tambem bootstrapam o banco local.
- Garantir que o backend local continue sendo a fonte de verdade para edicao, persistencia SQLite e reexportacao dos snapshots estaticos.
- Tratar `public/` como artefato publicado; backend, scripts, banco e docs ficam no repositorio, fora do deploy do Pages.
- Como o projeto roda em varios sistemas e por diferentes instancias do Codex, manter a documentacao sempre atualizada e coerente com o comportamento real do projeto.

## Detalhes Técnicos

- Frontend estatico em `public/`, com mapa em `public/index.html` e painel administrativo em `public/admin/index.html`.
- Backend local em `backend/server.py`, usando Python da biblioteca padrao e SQLite em `backend/data/`.
- Endpoints principais: `/`, `/admin/` e `/api/`; o frontend local tenta `/api/config` antes do fallback para `public/data/config/app-config.json`.
- Scripts de dados ficam em `scripts/` e geram camadas e arquivos consumidos pelo frontend.
- Suite automatizada em `tests/scripts/`, com runner principal: `python tests/scripts/run_tests.py`.
- Depois de cada mudanca no codigo, executar todos os testes e criar ou ampliar testes quando necessario.
- Instalar e atualizar localmente, dentro do diretorio do projeto sempre que possivel, todas as ferramentas necessarias para nao interferir em outros projetos.

## Estrategia

- Fazer mudancas pequenas, localizadas e alinhadas ao fluxo atual: frontend estatico, backend simples e snapshots versionados.
- Antes de alterar comportamento, confirmar qual contrato sera impactado: API, arquivos `e_*.json`, painel administrativo, scripts de geracao ou documentacao operacional.
- Sempre que uma mudanca afetar uso, operacao, arquitetura, setup, testes ou fluxo de dados, atualizar os docs correspondentes na mesma entrega.
- Priorizar compatibilidade entre os dois modos de execucao: local com backend e publicacao estatica no GitHub Pages.
- Evitar refactors amplos sem necessidade clara; resolver primeiro o problema real com o menor conjunto seguro de alteracoes.

## Diretrizes de Teste

- Escrever codigo testavel: funcoes pequenas, baixo acoplamento, fluxo direto, preferencia por funcoes puras e injecao de dependencias quando isso simplificar mocks, stubs ou fixtures.
- Seguir a piramide de testes: priorizar testes unitarios, usar testes de integracao para contratos entre modulos e reservar E2E para fluxos realmente criticos.
- Nenhuma funcionalidade esta pronta sem teste automatizado proporcional ao risco da mudanca.
- Trabalhar no ciclo Red-Green-Refactor: primeiro reproduzir a regra, bug ou regressao em teste; depois implementar o minimo; por fim refatorar preservando a suite verde.
- Quando surgir um bug, criar antes um teste que falha e reproduz o problema; so depois corrigir o codigo.
- Rodar `python tests/scripts/run_tests.py` depois de cada mudanca em codigo e ampliar a suite sempre que a entrega tocar API, CRUD, scripts, datasets `e_*.json`, painel ou deploy.
- Manter a automacao de testes ativa no GitHub Actions em pushes para `main` e em pull requests. Deploy ou liberacao publica nao deve seguir com teste falhando.
- Cobrir sempre caminho feliz, bordas relevantes e falhas esperadas: entradas vazias, nulas, negativas, limites e mensagens de erro.

## Padrões de Código

- Usar as versoes mais recentes das bibliotecas e abordagens idiomaticas atuais.
- Manter simples: NUNCA superprojetar, SEMPRE simplificar, SEM programacao defensiva desnecessaria. Sem recursos extras; foco total na simplicidade.
- Ser conciso.
- Reutilizar os padroes ja presentes no repositorio antes de introduzir novas abstracoes.
- Preferir nomes claros, funcoes pequenas e fluxo direto.
- Manter frontend, backend, scripts, testes e docs consistentes entre si.
