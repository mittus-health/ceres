# Features do MVP do Mittus

O Mittus é um app web em inglês para registrar indicadores de saúde, acompanhar a fadiga e visualizar o contexto da missão. A demo usa um astronauta fictício e dados de saúde simulados.

## Banco de dados

**Supabase PostgreSQL · projeto `mittus`.** Project Ref `ynxlbpmhdfaofcyamejf`. [Dashboard do projeto Mittus](https://supabase.com/dashboard/project/ynxlbpmhdfaofcyamejf)

- **`public.check_ins`** stores `id`, `session_id`, `check_in_date`, `sleep_hours`, `fatigue`, `mood_level`, `stress_level`, `team_conflict_level`, `description`, `created_at` and `updated_at`. The implemented API requires all numeric indicators; `description` is optional. There is one record per session and UTC date.
- **`public.check_in_actions`** guarda `id`, `check_in_id`, `evaluation_key`, `action_code`, `reason_code`, `ruleset_version`, `forecast_snapshot`, `status`, `created_at`, `acknowledged_at` e `resolved_at`. Cada ação aponta para o check-in que motivou a avaliação. [Migração SQL](supabase/migrations/20261114192439_create_check_in_actions.sql)

- **Mission registry** stores the departure and destination of each leg, not the craft's live position. [Model and decisions](docs/missions-database.md) · [SQL migration](supabase/migrations/20261114220000_create_missions.sql)
  - **`public.missions`** — mission identity, demo selection, launch identifiers and references.
  - **`public.mission_legs`** — one leg per phase, with departure place/time/source and destination place/description.
  - **`public.mission_places`** — reusable tracked objects or fixed coordinates with provenance and simulation flags.
  - **`public.session_missions`** — an optional mission link per signed demo session; unlinked sessions use the demo mission.

The server validates the session cookie and reads the database using `DATABASE_URL`. Action operations check `check_ins.session_id` through `check_in_id`; the mission-context route resolves `session_missions` using the same signed session. RLS is enabled and public API role grants are revoked on action and mission tables.

## Funcionalidades e dependências

As APIs de check-in diário e Check-in Actions estão implementadas em NestJS e Prisma. O Check-in Actions usa o pacote do Eres localmente, com opção de configurar um provedor HTTP via `FATIGUE_FORECAST_URL`. O resultado `ok` do modelo vira `ready` no contrato de ações. As ações atuais são sugeridas por regras fixas. A recomendação da IA, a geração das tarefas e a integração com as telas seguem no escopo do MVP. [Contrato do backend](backend/README.md#check-in-actions)

| Feature | O que o astronauta faz | API e dependências | Tabela |
| --- | --- | --- | --- |
| **Check-in diário** | Registra estresse, humor, conflito na equipe e fadiga com ícones Lucide nas escalas. A etapa de fadiga inclui sono e **Other hours** para digitar um valor. A descrição opcional vem antes da revisão. A confirmação mostra **Back to home** e **Edit this check-in** lado a lado. | `PUT /api/check-ins/{date}` recebe `sleep_hours`, `fatigue`, `mood_level`, `stress_level`, `team_conflict_level` e `description` opcional. **Other hours** usa `sleep_hours`, de 0 a 24, com até duas casas decimais. | Grava em `check_ins`. |
| **Home, corpo 3D e histórico** | Abre o checklist pela Home, consulta a recomendação de desconforto na região selecionada no corpo e vê os gráficos de sono e fadiga no histórico. | `GET /api/check-ins?limit=7` carrega o histórico. O ponto no corpo ajuda a registrar o desconforto na descrição do check-in. Usar a escala de fadiga de 1 a 7 do contrato ao exibir dados reais da API. | Lê `check_ins`. |
| **Previsão experimental de fadiga — Eres** | Vê a chance de relatar fadiga elevada no próximo check-in no cartão de previsão abaixo da recomendação da IA. | Check-in Actions chama `predictFatigue` do pacote `@mittus/fatigue-model` com o histórico completo em ordem cronológica. Com menos de três registros, o resultado é `insufficient_history`. O treino usa dados sintéticos. A rota avulsa `GET /api/eres-forecast` segue proposta. | Lê `check_ins`. |
| **Recomendação e checklist gerados pela IA** | Em **Make sense of the changes**, lê uma recomendação curta em inglês no primeiro cartão e usa **Open task checklist** para ver as tarefas. | A IA da Giulia recebe os dados do check-in e o resultado do Eres. Ela gera a recomendação e as tarefas. O Check-in Actions do Neves registra as ações e controla seus estados. | Lê `check_ins` e usa a previsão do Eres. |
| **Mission context** | Sees departure, current position, destination and cabin temperature for each phase. | The Next.js `GET /api/mission-context?phase=...` route uses the shared signed session and mission registry. Docked position comes from wheretheiss.at; free flight uses CelesTrak/SGP4 when `norad_id` exists, otherwise the labeled simulated point. Database failure uses the built-in demo; a missing phase returns `404`. | Reads mission tables; position responses identify live, snapshot, TLE or simulated provenance. |
| **Cadastro de missão** | O ícone de missão abre **Register a mission** direto do menu. O formulário mostra os dados da missão e os campos dos trechos de ida e retorno. | A tela do Figma usa os campos do cadastro e dos trechos do banco. A rota de gravação ainda está pendente. | `missions` e `mission_legs`. Origem e destino referenciam `mission_places`. |
| **Check-in Actions** | Vê as tarefas no checklist de **My plan** e usa **Got it**, **Mark complete** ou **Dismiss**. | `POST /api/check-ins/{id}/actions/evaluate` avalia a ação, `GET /api/check-ins/{id}/actions` lista os registros e `PATCH /api/check-in-actions/{id}` atualiza o status. **Got it** envia `acknowledged`. | Lê `check_ins` e grava em `check_in_actions`. |

Para implementar as telas, consulte [Home](https://www.figma.com/design/7yzLD5bpQkWcU42c7Jsfs1/Mittus?node-id=30-2), [Descrição do check-in](https://www.figma.com/design/7yzLD5bpQkWcU42c7Jsfs1/Mittus?node-id=108-2039), [Horas de sono personalizadas](https://www.figma.com/design/7yzLD5bpQkWcU42c7Jsfs1/Mittus?node-id=108-2221), [Make sense of the changes](https://www.figma.com/design/7yzLD5bpQkWcU42c7Jsfs1/Mittus?node-id=30-274), [Checklist](https://www.figma.com/design/7yzLD5bpQkWcU42c7Jsfs1/Mittus?node-id=30-371) e [Cadastro de missão](https://www.figma.com/design/7yzLD5bpQkWcU42c7Jsfs1/Mittus?node-id=111-1728).

## Fluxo do Check-in Actions

1. O usuário salva o check-in. O frontend atualiza o histórico e pede a avaliação do plano para o `id` do registro mais recente. Se uma correção no histórico alterar os dados da previsão, a API reavalia esse registro mais recente.
2. The backend calls the shared Eres predictor with the complete session history. Its `ok` result is adapted to `ready` for the persisted action contract, alongside `probability_high_fatigue`, `model_version` and UTC `predicted_at`. With fewer than three records, the plan is unavailable without inserting a fake probability. An explicit HTTP provider override may also report an unavailable prediction. The saved check-in remains visible.
3. Uma regra versionada escolhe `action_code` e `reason_code`. A demo usa `monitor` para acompanhar os registros e `recheck` para fazer um novo check-in. `contact_crew` e `contact_medical` ficam reservados para fluxos com procedimento da missão definido. A regra de demonstração usa uma previsão experimental, com dados sintéticos. As ações do MVP tratam do acompanhamento de registros e são exibidas para decisão do astronauta.
4. O backend monta `evaluation_key` com os dados e as revisões dos check-ins usados na previsão e as versões do modelo e das regras. Uma revisão muda quando os valores usados pelo preditor mudam. `forecast_snapshot` guarda `probability_high_fatigue` entre 0 e 1, `model_version` e `predicted_at`. A mesma avaliação reaproveita a ação registrada. Ao aceitar uma avaliação nova, o backend grava a ação e marca as anteriores pendentes do check-in como `superseded` na mesma transação. Se a previsão ficar indisponível após uma correção, a ação antiga sai do cartão atual. Serializar a atualização por sessão e conferir antes da gravação se a avaliação ainda corresponde ao histórico evita publicar uma sugestão atrasada.
5. A avaliação atual devolve a ação registrada e o texto padrão da regra. Na integração planejada, a IA da Giulia usa o check-in e a previsão para gerar a recomendação e as tarefas. O Check-in Actions recebe as tarefas para registrá-las e acompanhar seu status.
6. O astronauta usa **Got it**, **Mark complete** ou **Dismiss** para mudar o status de uma ação pendente. A API registra os horários. Ações concluídas, dispensadas ou substituídas ficam no histórico do backend. Um pedido para alterar uma ação substituída pode retornar `409` e atualizar o cartão com a ação vigente.

As rotas de avaliação e de listagem identificam o check-in pelo UUID na URL e verificam a sessão. A avaliação recebe o contexto do servidor e pode aceitar um corpo vazio. A resposta inclui `status`, `action` quando disponível e `explanation` para a tela. A listagem pode devolver `actions` com os estados registrados. Para atualizar, o frontend envia, por exemplo, `{"status":"completed"}`. O servidor controla `acknowledged_at`, `resolved_at` e as transições a partir do estado atual. Um ID ausente ou de outra sessão recebe `404`.

## Responsáveis por funcionalidade

| Feature | Responsável | Entrega dos demais |
| --- | --- | --- |
| **Check-in diário** | **Luis** implementa validação, gravação por sessão e resposta da API. | **Gabi** define o formulário e os rótulos. **Luigi** implementa o formulário e conecta a rota. **Neves** configura o acesso ao banco no deploy. **Rodrigo** prepara registros fictícios. |
| **Home, corpo 3D e histórico** | **Luigi** conecta o modelo 3D e os gráficos aos dados do check-in. | **Gabi** escolhe o modelo com licença e define o painel. **Luis** retorna dados ordenados por data. **Neves** verifica o carregamento do arquivo no deploy. **Rodrigo** valida os indicadores exibidos. |
| **Previsão experimental** | **Rodrigo** treina e avalia o Eres. | **Luis** integra a previsão. **Neves** disponibiliza o modelo no ambiente publicado. **Luigi** exibe a previsão e seus estados. **Gabi** define como apresentar o caráter experimental. |
| **Recomendação e tarefas do checklist** | **Giulia** gera a recomendação e as tarefas com os dados do check-in e a previsão do Eres. | **Luigi** exibe a recomendação em **Make sense of the changes** e as tarefas em **My plan**. |
| **Contexto da missão** | **Neves** prepara as amostras da NASA e os dois cenários. | **Luis** serve o JSON da rota. **Luigi** implementa a seleção e atualiza o cartão. **Gabi** desenha os rótulos que identificam fonte, horário e dados simulados. |
| **Check-in Actions** | **Neves** integra as tarefas geradas, registra as ações e gerencia as mudanças de status. | **Rodrigo** entrega previsões de teste e o contrato do modelo. **Gabi** desenha o checklist e os estados. **Luigi** liga a tela às rotas de ações. |

## Fontes e integrações externas

- **Indicadores de saúde.** O enunciado sugere pressão arterial, frequência cardíaca, glicemia, temperatura corporal, horas de sono e humor. O Mittus usa horas de sono e humor e adiciona fadiga percebida como autorrelato. O Human Research Program fundamenta a escolha de acompanhar sono e fadiga. Registre o uso no campo **NASA Data**. [Enunciado do desafio](https://www.spaceappschallenge.org/2026/challenges/health-monitoring-software/?tab=details) · [Pesquisa da NASA sobre sono](https://www.nasa.gov/reference/risk-from-inadequate-sleep-and-irregular-schedules/)
- **Posição da ISS.** `GET https://api.wheretheiss.at/v1/satellites/25544`. A API calcula a posição atual a partir do TLE mais recente da ISS (NORAD) e devolve latitude, longitude, altitude e horário. Não exige chave e pede no máximo uma requisição por segundo, por isso o backend reutiliza a resposta por 5 segundos. Cite o serviço em **Space Agency Partner Data and Other References**. [Where the ISS at? — documentação](https://wheretheiss.at/w/developer)
- **Ponto de partida.** `GET https://ll.thespacedevs.com/2.3.0/launches/{id}/` (Launch Library 2, The Space Devs) informa a plataforma de lançamento com latitude e longitude e o horário do lançamento. Esses dados são copiados uma vez para `mission_places` e `mission_legs` ao cadastrar a missão, porque o plano gratuito permite poucas chamadas por hora. Cite em **Other References**. [Documentação da Launch Library 2](https://ll.thespacedevs.com/docs/)
- **Posição da nave em voo livre.** `GET https://celestrak.org/NORAD/elements/gp.php?CATNR={norad}&FORMAT=json` devolve os elementos orbitais mais recentes da nave. O backend calcula a posição com o modelo SGP4 (`satellite.js`) e baixa os elementos no máximo a cada 2 horas, como a CelesTrak pede. Cite em **Other References**. [CelesTrak — GP data](https://celestrak.org/NORAD/documentation/gp-data-formats.php)
- **Temperatura da cabine.** O cenário orbital pode usar uma amostra histórica baixada na aba **Data Tables**. Guardar a medição com sua data e fonte no arquivo do cenário. [NASA — Environmental Data App](https://visualization.osdr.nasa.gov/eda/)
- **Modelo de linguagem.** O provedor proposto é Gemini. A entrada da geração é o check-in e a previsão do Eres. As saídas são a recomendação em inglês e as tarefas do checklist. [Referência da API Gemini](https://ai.google.dev/api)

## Validação para a entrega

- [ ] Completar as seis etapas do check-in usando **Other hours** e uma descrição opcional. Recarregar e conferir os valores no histórico. Confirmar o isolamento entre duas sessões.
- [ ] Abrir a recomendação pelo ponto de desconforto no corpo e conferir os gráficos de sono e fadiga. Usar a escala de fadiga de 1 a 7 da API.
- [ ] Conferir se a recomendação e as tarefas da IA refletem o check-in e a previsão do Eres. Em **Make sense of the changes**, verificar a previsão e abrir o checklist pelo botão **Open task checklist**.
- [ ] Abrir o cadastro pelo ícone de missão e conferir os campos da missão, da ida e do retorno. Testar a gravação quando a rota estiver disponível e mudar a fase no mapa.
- [ ] Repetir uma avaliação do plano e conferir que não duplica a ação. Corrigir um check-in, atualizar a previsão e verificar o histórico e a troca das ações pendentes. Conferir o isolamento por sessão ao consultar e alterar uma ação.
- [ ] Abrir o checklist pela Home e verificar que **Got it**, **Mark complete** e **Dismiss** gravam o status esperado. Testar os estados de histórico insuficiente e indisponibilidade da previsão.
- [ ] Na aba **Project**, explicar onde a fonte da NASA foi usada, identificar os dados simulados e citar o arquivo 3D, sua licença e as demais referências. Declarar o uso efetivo de IA e identificar os materiais gerados conforme o guia.
- [ ] Testar os links públicos do app e da demo em janela anônima. Mostrar o fluxo publicado em até sete slides em inglês ou em um vídeo de até 30 segundos, com legendas em inglês se o áudio estiver em outro idioma.

[Requisitos de entrega](REQUISITOS-DE-ENTREGA.md) · [Plano do MVP e responsáveis](docs/superpowers/plans/2026-11-14-mittus-mvp.md)
