# Alinhamento do MVP do Mittus

O Mittus é um **app web de acompanhamento de saúde para astronautas**. A proposta para a entrega é demonstrar um cenário de **fadiga antes do retorno à Terra**, ligando um check-in diário a um histórico visual, uma previsão experimental e um resumo inteligente.

## Funcionalidades propostas para a entrega

| Parte | O que precisa funcionar |
| --- | --- |
| **Check-in diário** | Registrar horas de sono, humor e fadiga percebida em um formulário curto, inspirado na experiência de registro do Flo. Salvar a entrada e atualizar o histórico. |
| **Corpo 3D e histórico** | Exibir uma figura humana com um ponto interativo que abre o painel de sono e fadiga. No painel, mostrar os registros recentes e o que mudou. Disponibilizar o mesmo painel por botão textual com foco de teclado. |
| **Previsão com ML** | Demonstrar uma única previsão, a chance de o astronauta **relatar fadiga elevada no próximo check-in**, usando o histórico disponível até hoje. Mostrar a saída ao lado dos registros recentes. Identificar a previsão como experimental e os dados como simulados. |
| **Resumo inteligente do check-in** | Gerar em inglês um cartão com o que mudou em relação aos registros anteriores. O backend calcula os fatos e o modelo de linguagem redige o texto. |
| **Contexto da missão** | Alternar entre dois cenários, **em órbita** e **retorno à Terra**. Mostrar fase, localização, destino e temperatura interna simulada da cabine. |
| **Plano de mudança** | A partir da previsão experimental, uma regra versionada sugere acompanhar os registros ou fazer um novo check-in. O modelo de linguagem explica a ação. O astronauta pode reconhecê-la, concluí-la ou dispensá-la. |

As rotas, tabelas e responsabilidades por funcionalidade estão no [FEATURES.md](../../../FEATURES.md).

O Human Research Program da NASA associa sono insuficiente e horários irregulares a riscos para o desempenho e a saúde. Use essa fonte para justificar por que o app acompanha sono e fadiga. Registre a origem dos dados, a forma de avaliação do modelo e a diferença entre a pesquisa da NASA e os dados simulados pela equipe. [NASA — Risk from Inadequate Sleep and Irregular Schedules](https://www.nasa.gov/reference/risk-from-inadequate-sleep-and-irregular-schedules/)

## Como demonstrar

1. Abrir o painel de um astronauta fictício em órbita e ver o histórico dos últimos dias.
2. Salvar um check-in com sono, humor e fadiga. Conferir a nova entrada no histórico.
3. Usar o corpo 3D para abrir o painel de sono e fadiga e ver a previsão para o próximo check-in.
4. Selecionar **Retorno à Terra** e conferir a atualização do contexto da missão.
5. Clicar em **Generate insight** e conferir se o resumo compara o último check-in com os registros anteriores.
6. Abrir o plano de mudança, conferir a ação sugerida e marcá-la como concluída. Recarregar e comprovar que o status foi preservado.

## Como validar a entrega

- [ ] O app abre em inglês na URL pública. Um jurado consegue concluir o fluxo em uma janela anônima.
- [ ] O check-in salvo aparece no histórico após recarregar. O painel abre pelo corpo 3D e pelo botão textual. Os estados são legíveis por escrito, com navegação por teclado e leitura em tela pequena.
- [ ] A previsão usa somente dados disponíveis até o check-in atual. Avaliar o modelo em cenários reservados para teste e compará-lo com uma regra simples, como repetir o nível de fadiga do último registro. Se o ML ainda estiver pendente no momento da entrega, demonstrar o fluxo com a regra e descrevê-la como tal.
- [ ] A mudança de fase atualiza localização, destino e temperatura simulada da cabine no painel.
- [ ] O resumo usa o último check-in e até sete anteriores. A comparação exclui o registro atual da média. Se faltarem registros anteriores, o cartão informa que ainda não há histórico para comparar. Em caso de falha do modelo de linguagem, o app exibe um texto com os fatos calculados.
- [ ] Repetir a avaliação e conferir que ela reaproveita a ação. Corrigir o check-in e verificar a substituição de ações pendentes quando a avaliação mudar. Conferir acesso por sessão e o texto padrão quando o provedor falhar.
- [ ] Demo e aba **Project** mostram o fluxo publicado e descrevem o uso da fonte da NASA e do ML conforme implementados. [Requisitos de entrega](../../../REQUISITOS-DE-ENTREGA.md)

## Depois do MVP

Integração com smartwatch, coleta por sensores, telemetria real da nave, mais contextos de missão e modelos para outros indicadores de saúde.

## Pontos de integração

Agenda proposta em **horário de Brasília**, começando no **sábado, 14/11, às 14h**, e retomando no **domingo, 15/11, às 9h30**. A meta é enviar até **18h de domingo**. O prazo de **23h59** é o da plataforma. Rodrigo confere, no início, se Campinas comunicou alguma entrega local que precise acontecer antes. [Requisitos de entrega](../../../REQUISITOS-DE-ENTREGA.md)

### Banco de dados — primeira entrega técnica

- **14h–14h25.** Luis e Neves alinham o contrato da API com o [esquema do Supabase](../../../FEATURES.md#banco-de-dados). Confirmem com Rodrigo e Gabi os campos exibidos no formulário e as escalas de humor e fadiga.
- **14h25–15h15.** Neves configura a conexão no servidor. Luis prepara com Rodrigo um histórico fictício reproduzível. O backend calcula a previsão a partir de `check_ins` e registra o plano em `check_in_actions`. Os cenários da missão ficam na aplicação.
- **Aceite às 15h15.** A migração roda em um banco vazio. O backend conecta, grava e lê um check-in fictício. A leitura pela sessão A encontra o registro e a leitura pela sessão B mantém o histórico isolado. Luis e Neves conferem que as credenciais ficam na configuração do servidor.
- **Em paralelo.** Luigi monta o frontend com o JSON combinado às 14h25. Rodrigo trabalha com históricos sintéticos no mesmo formato. O frontend e a previsão passam a usar os dados do backend na integração.

| Horário | O que o time precisa ter |
| --- | --- |
| **Sáb., 14h–14h25 · 25 min** | Todos fecham o cenário da demo e escolhem a stack que já sabem publicar. Saem da reunião com um exemplo compartilhado no canal da equipe. Luis registra um check-in com data, horas de sono e escalas de humor e fadiga. Rodrigo acrescenta uma saída de previsão fictícia e a indicação de histórico insuficiente. Neves confirma como cada parte chega ao deploy. |
| **Sáb., 15h15** | Luis e Neves verificam a migração, a conexão do backend e a gravação e leitura de um check-in por sessão. A partir desse teste, Luis liga o contrato da API ao banco. |
| **Sáb., 16h** | Gabi entrega o wireframe e o asset 3D. Rodrigo compartilha o histórico fictício ampliado. Luis entrega os exemplos completos de resposta da API e Neves publica a primeira URL de teste. Luigi atualiza o protótipo com os exemplos enquanto a API real fica pronta. |
| **Sáb., 20h** | Primeira versão integrada. Para testar, salvar um check-in, recarregar, abrir o painel 3D, mudar a fase e gerar o resumo inteligente. Cada falha sai com um responsável para domingo. |
| **Dom., 11h30** | O time escolhe a versão da demo pelo que consegue executar na URL pública. Se a previsão falhar, avalia usar a regra de reserva. Até **12h30**, corrige apenas o que impede a jornada. |
| **Dom., 15h30–18h** | Às 15h30, demo e página **Project** prontas para revisão. Teste como jurado até 17h e submissão até 18h. |

No sábado, reservem **17h30–18h** para pausa. No domingo, reservem **12h30–13h30**. Os blocos abaixo vão até a revisão conjunta de domingo. Após as 17h, Rodrigo cuida do envio e cada pessoa fica disponível para corrigir um bloqueio da sua parte.

### Gabi — Design e demo

| Quando | Tarefa e entrega |
| --- | --- |
| **Sáb., 14h25–16h · 1h35** | Desenhar a sequência check-in → corpo 3D → painel de fadiga → contexto da missão → resumo inteligente. Passar para Luigi a estrutura da tela primeiro. Escolher com ele uma figura 3D leve, com licença que permita o uso, e registrar a fonte. Marcar o ponto clicável e o botão textual que abre o mesmo painel. |
| **Sáb., 16h–17h30 · 1h30** | Entregar a copy em inglês, a hierarquia do painel e os estados de formulário inválido, previsão indisponível e carregamento. Esboçar a demo. A proposta é usar slides em inglês com capturas da aplicação. |
| **Sáb., 18h–20h · 2h** | Revisar o fluxo implementado com Luigi, em desktop e tela estreita. Conferir se o estado é legível por texto, se o formulário é rápido de preencher e se o botão **Generate insight** é fácil de achar. |
| **Dom., 9h30–12h30 · 3h** | Revisar as correções visuais e fechar o roteiro da demo com Rodrigo. Validar a sequência e os termos em inglês na versão escolhida às 11h30. |
| **Dom., 13h30–15h30 · 2h** | Capturar telas da versão pública e publicar a demo. Incluir equipe, nomes, desafio, fonte NASA, check-in, painel e resumo inteligente em **até sete slides**. Entregar o link a Rodrigo. |

### Luigi — Frontend

| Quando | Tarefa e entrega |
| --- | --- |
| **Sáb., 14h25–16h · 1h35** | Criar a tela base e o formulário em inglês. Usar o exemplo de Luis para exibir histórico, gráfico e estado da previsão. Passar a URL de teste ou as instruções de execução a Neves. |
| **Sáb., 16h–17h30 · 1h30** | Integrar a figura 3D com um ponto interativo e o botão textual. Montar o seletor de fase e o cartão de contexto da missão. |
| **Sáb., 18h–20h · 2h** | Ligar cadastro e histórico à API de Luis. Após salvar, atualizar o gráfico e a previsão. Carregar o contexto conforme a fase escolhida e mostrar os estados de carregamento e falha. |
| **Dom., 9h30–12h30 · 3h** | Reproduzir os problemas da primeira versão. Testar navegação por teclado, tela estreita, recarregamento, 3D indisponível e atualização do cartão após mudar de fase. Corrigir os bloqueios do fluxo. |
| **Dom., 13h30–15h30 · 2h** | Preparar com Gabi as telas para captura. Acompanhar a versão pública e confirmar que o botão textual mantém o painel acessível se a cena 3D falhar. |

### Luis — API e persistência

| Quando | Tarefa e entrega |
| --- | --- |
| **Sáb., 14h25–15h15 · 50 min** | Verificar `check_ins` e `check_in_actions`. Preparar o histórico fictício com Rodrigo e testar gravação e leitura por sessão com Neves. |
| **Sáb., 15h15–16h · 45 min** | Ligar os endpoints de cadastro e histórico ao banco. Publicar exemplos de respostas, incluindo a estrutura de avaliação e o contexto da missão. |
| **Sáb., 16h–17h30 · 1h30** | Conferir gravação, consulta e entradas inválidas. Preparar o histórico inicial por sessão para que dois jurados possam repetir a demo sem interferir nos registros um do outro. |
| **Sáb., 18h–20h · 2h** | Conectar a saída da previsão ao painel. Testar com Luigi um novo check-in, do envio ao painel atualizado. |
| **Dom., 9h30–12h30 · 3h** | Repetir o teste com duas sessões independentes e uma entrada inválida. Corrigir problemas de persistência e padronizar a resposta quando o histórico ainda for insuficiente para a previsão. |
| **Dom., 13h30–15h30 · 2h** | Documentar como iniciar a API e repetir o cenário. Conferir a documentação com Neves e verificar que o painel exibe a saída da previsão recebida da API. |

### Neves — Integração de serviços e deploy

| Quando | Tarefa e entrega |
| --- | --- |
| **Sáb., 14h25–15h15 · 50 min** | Provisionar o banco de desenvolvimento, configurar a conexão no servidor e testar com Luis a migração e o isolamento entre sessões. |
| **Sáb., 15h15–16h · 45 min** | Publicar a primeira URL de teste. Configurar a conexão com o banco no ambiente publicado e alinhar com Rodrigo como a API executará o modelo de previsão. |
| **Sáb., 16h–17h30 · 1h30** | Preparar o caminho do navegador até a API e testar o carregamento do contexto da missão. Anotar como restaurar a última versão funcional. |
| **Sáb., 18h–20h · 2h** | Publicar frontend, API e serviços disponíveis. Verificar no deploy o acesso ao 3D, o registro, a previsão e o contexto da missão. Compartilhar o link de teste e o commit publicado. |
| **Dom., 9h30–12h30 · 3h** | Testar a versão como visitante e simular a indisponibilidade da previsão. Às 11h30, apresentar ao time a versão funcional e o caminho de reserva testado. Publicar a versão escolhida até 12h30. |
| **Dom., 13h30–15h30 · 2h** | Conferir em janela anônima o app, o acesso ao projeto e o link da demo assim que Gabi entregar. Enviar a Rodrigo os links finais. Usar a URL pública da hospedagem se o domínio próprio ainda estiver pendente. |

### Rodrigo — Machine Learning e submissão

| Quando | Tarefa e entrega |
| --- | --- |
| **Sáb., 14h25–16h · 1h35** | Definir o alvo **fadiga elevada relatada no próximo check-in**. Preparar históricos sintéticos de sono, humor e fadiga, incluindo o exemplo comum da demo. Documentar a fonte NASA que fundamenta a escolha do indicador e informar a Luis o formato da previsão. |
| **Sáb., 16h–17h30 · 1h30** | Treinar um modelo pequeno com dados disponíveis até o check-in atual. Reservar trajetórias simuladas diferentes para teste e comparar com a regra que repete o nível do último registro. Guardar os resultados e explicar as limitações dos dados simulados. |
| **Sáb., 18h–20h · 2h** | Entregar a Luis e Neves a função de previsão, a regra de reserva e exemplos de saída para histórico suficiente e insuficiente. Verificar com Luigi que o painel exibe o resultado esperado. |
| **Dom., 9h30–12h30 · 3h** | Testar o modelo no app, documentar qual abordagem entrou na versão escolhida e revisar o texto do resultado. Confirmar os seis membros e as instruções locais já levantadas no alinhamento de sábado. |
| **Dom., 13h30–18h · 4h30** | Até 15h30, fechar a aba **Project** e o README em inglês, com fontes, links, dados simulados e declaração de uso de IA. Até 17h, testar o fluxo e os links com o time. Até 18h, clicar em **Submit for Judging** e conferir a confirmação. |

### Giulia — Resumo inteligente e plano de mudança

- Preparar casos de teste com histórico suficiente e insuficiente e definir a saída do resumo em inglês com um exemplo para Luigi.
- Implementar o cálculo dos fatos a partir dos check-ins e a geração do resumo comparativo. Combinar com Luis a rota `POST /api/check-in-insights` e com Neves a configuração do provedor no servidor.
- Integrar com Luigi o botão **Generate insight** e verificar números, histórico insuficiente e resposta alternativa em caso de falha do modelo. Entregar a Rodrigo a descrição de uso de IA para a submissão.
- Para o plano, receber do backend a ação, o motivo e a previsão. Preparar a explicação em inglês e o texto padrão de cada ação da demo. Conferir com Luis e Neves a integração e com Luigi a exibição do resultado.

### Revisão conjunta e envio

- **Dom., 15h30–17h · 1h30.** Gabi abre a URL em janela anônima e executa o fluxo sem instruções. Luigi confere a interação. Luis verifica o registro. Neves confere deploy e links. Rodrigo compara previsão e dados. Giulia confere os números do resumo com o histórico. Ajustem os textos da demo e do portal conforme a versão que passou.
- **Dom., 17h–18h · 1h.** Rodrigo submete e guarda a confirmação. Os demais resolvem eventuais falhas da sua parte. Se houver correção depois do envio, Rodrigo reenvia e confirma a versão final antes de 23h59.
