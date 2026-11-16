# Especificação de dados — Check-ins diários

**Status:** proposta para alinhamento com o data manager
**Banco:** PostgreSQL (Supabase)
**Objetivo:** armazenar um check-in de saúde por dia e por sessão de demonstração, permitindo consultar os registros em um calendário e alimentar o histórico de indicadores.

Os nomes de tabelas, colunas e valores técnicos estão em inglês. As informações usadas na demonstração são simuladas.

## Modelo proposto

Tabela: `check_ins`

| Coluna | Tipo PostgreSQL | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `id` | `uuid` | Sim | Identificador único do registro, gerado pelo banco. |
| `session_id` | `uuid` | Sim | Identificador da sessão de demonstração à qual o registro pertence. |
| `check_in_date` | `date` | Sim | Dia de referência do check-in, sem horário. |
| `sleep_hours` | `numeric(4,2)` | Sim | Horas de sono informadas, de 0 a 24; aceita valores decimais. |
| `stress_level` | `smallint` | Sim | Nível de estresse, de 1 a 5. |
| `mood_level` | `smallint` | Sim | Estado emocional, de 1 a 5. |
| `team_conflict_level` | `smallint` | Sim | Nível de conflito na equipe, de 1 a 5. |
| `fatigue` | `smallint` | Sim | Nível de fadiga, de 1 a 7. |
| `created_at` | `timestamptz` | Sim | Momento de criação do registro. |
| `updated_at` | `timestamptz` | Sim | Momento da última alteração; atualizado pelo backend. |

`sleep_hours` registra horas em formato decimal: por exemplo, `7.50` representa 7 horas e 30 minutos. O limite de 0 a 24 e a precisão de duas casas decimais são propostas para validação com a equipe.

### Escalas de humor

Cada dimensão é registrada independentemente, usando números inteiros de 1 a 5. Os valores 2, 3 e 4 representam posições intermediárias entre os extremos.

| Coluna | Valor 1 | Valor 5 |
| --- | --- | --- |
| `stress_level` | Very calm | Very stressed |
| `mood_level` | Very happy / positive | Very sad / negative |
| `team_conflict_level` | No team conflict | High team conflict |

Em todas essas dimensões, valores maiores representam mais estresse, estado emocional mais negativo ou mais conflito, respectivamente.

### Escala de fadiga

| Valor | Descrição para a interface |
| --- | --- |
| 1 | Fully alert and wide awake |
| 2 | Very active and responsive, but not at peak alertness |
| 3 | Feeling well and ready |
| 4 | A little tired and less energetic |
| 5 | Moderately tired and fatigued |
| 6 | Extremely tired, with great difficulty concentrating |
| 7 | Completely exhausted and unable to function effectively |

## Regras de integridade e acesso

- Existe **no máximo um registro por `session_id` e `check_in_date`**. Uma nova gravação para a mesma combinação atualiza o registro existente.
- Todos os indicadores são obrigatórios no check-in completo. As restrições do banco também impedem valores fora das escalas definidas.
- A sessão é identificada pelo backend a partir do cookie emitido pelo servidor. O cliente não escolhe o `session_id` do registro; todas as consultas e alterações devem ser filtradas pela sessão identificada.
- Esta proposta não cria tabela de sessões nem chave estrangeira para `session_id`. O mecanismo de emissão e persistência das sessões deve ser definido na implementação; caso exista uma tabela de sessões, o relacionamento poderá ser acrescentado.
- `check_in_date` é uma data de calendário, não um instante. **UTC é a proposta** para determinar o dia atual; o fuso da missão ainda precisa ser confirmado.
- A permissão para criar ou alterar check-ins de datas passadas ainda está em aberto e deve ser aplicada pelo backend depois da decisão de produto.
- `created_at` e `updated_at` representam instantes. Nesta proposta, o backend deve atualizar `updated_at` em cada alteração; o banco não o atualiza automaticamente.

## SQL proposto

O SQL abaixo é uma proposta de migração para PostgreSQL. A restrição única também cria um índice útil para consultas por sessão e data.

```sql
CREATE TABLE check_ins (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL,
    check_in_date date NOT NULL,
    sleep_hours numeric(4, 2) NOT NULL,
    stress_level smallint NOT NULL,
    mood_level smallint NOT NULL,
    team_conflict_level smallint NOT NULL,
    fatigue smallint NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT check_ins_session_date_unique
        UNIQUE (session_id, check_in_date),
    CONSTRAINT check_ins_sleep_hours_range
        CHECK (sleep_hours >= 0 AND sleep_hours <= 24),
    CONSTRAINT check_ins_stress_level_range
        CHECK (stress_level BETWEEN 1 AND 5),
    CONSTRAINT check_ins_mood_level_range
        CHECK (mood_level BETWEEN 1 AND 5),
    CONSTRAINT check_ins_team_conflict_level_range
        CHECK (team_conflict_level BETWEEN 1 AND 5),
    CONSTRAINT check_ins_fatigue_range
        CHECK (fatigue BETWEEN 1 AND 7)
);
```

## Exemplos de operações

### Criar ou atualizar um check-in

Os valores posicionais são parâmetros fornecidos pelo backend; `$1` é o identificador da sessão obtido no servidor.

```sql
INSERT INTO check_ins (
    session_id, check_in_date, sleep_hours, stress_level,
    mood_level, team_conflict_level, fatigue
)
VALUES ($1, $2, $3, $4, $5, $6, $7)
ON CONFLICT (session_id, check_in_date)
DO UPDATE SET
    sleep_hours = EXCLUDED.sleep_hours,
    stress_level = EXCLUDED.stress_level,
    mood_level = EXCLUDED.mood_level,
    team_conflict_level = EXCLUDED.team_conflict_level,
    fatigue = EXCLUDED.fatigue,
    updated_at = now()
RETURNING *;
```

### Consultar um mês no calendário

Usar intervalo com início inclusivo e fim exclusivo. Por exemplo, para novembro de 2026, `$2` é `2026-11-01` e `$3` é `2026-12-01`.

```sql
SELECT check_in_date, sleep_hours, stress_level, mood_level,
       team_conflict_level, fatigue
FROM check_ins
WHERE session_id = $1
  AND check_in_date >= $2
  AND check_in_date < $3
ORDER BY check_in_date;
```

Dias sem registro não aparecem no resultado; a interface pode representá-los como dias sem check-in.

## Exemplo de registro

| Campo | Valor fictício |
| --- | --- |
| `id` | `e14510ab-9d7f-4dc3-b166-10e77900ce21` |
| `session_id` | `2c03cc75-f572-4e85-a96d-26fa60dc8e1b` |
| `check_in_date` | `2026-11-14` |
| `sleep_hours` | `7.50` |
| `stress_level` | `2` |
| `mood_level` | `1` |
| `team_conflict_level` | `1` |
| `fatigue` | `3` |

## Pontos para alinhamento

1. Confirmar o intervalo de `sleep_hours`, a precisão e se todos os indicadores devem ser obrigatórios.
2. Confirmar o fuso usado para determinar o dia atual e a política para datas passadas e futuras.
3. Definir como a sessão será criada, quanto tempo durará e se haverá uma tabela própria de sessões.
4. Alinhar com a equipe de ML os nomes, as escalas e o sentido dos valores antes de gerar o histórico sintético.
5. Atualizar o contrato em `FEATURES.md` após a aprovação: a proposta anterior contém apenas um campo `mood`, agora substituído pelas três dimensões acima.
