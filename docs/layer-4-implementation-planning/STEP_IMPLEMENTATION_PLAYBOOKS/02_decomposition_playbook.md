# 02_decomposition_playbook.md

**STEP 02 — Decomposition (LLM, MVP)**

**Статус:** IMPLEMENTATION PLAYBOOK  
**Scope:** MVP  
**Зависимости:**
- `01_ingestion_playbook.md` (creative зарегистрирован)

**Следующий шаг:** `03_idea_registry_playbook.md`

## 0. Назначение шага

Этот шаг превращает сырой текст в структуру по Canonical Schema.

LLM здесь — классификатор, а не интеллект.  
Он не думает, не оценивает, не решает.

Результат шага — структурированное описание,
без смысла, без качества, без решений.

## 1. Входные данные

### 1.1 Источник

- зарегистрированный creative
- полученный transcript_text

### 1.2 Контракт входа

```json
{
  "creative_id": "uuid",
  "transcript_text": "full speech text only"
}
```

### 1.3 Ограничения

- только текст речи
- без визуала
- без primary / description / CTA
- без метаданных

## 2. n8n Workflow

**Workflow name:** `creative_decomposition_llm`

### 2.1 Trigger

- **Node:** Event Trigger
- **Event:** `TranscriptCreated`

### 2.2 Load Canonical Schema

- **Node:** Static / Config node
- `schema_version`: v2
- `schema_definition`: JSON Schema (Idea-level variables)

📌 **Schema — single source of truth.**

**Schema v2** включает 14 required полей (v1) + 22 optional полей для глубокого анализа.

### 2.3 LLM Call (Classification Only)

- **Node:** LLM (OpenAI / Anthropic / etc.)

**Prompt правила:**
- "Ты классификатор"
- "Заполняй только поля schema"
- "Если не уверен — используй closest enum"
- "Запрещено добавлять поля"

**Выход LLM:**
- JSON строго соответствующий schema.

---

## 2.3.1 LLM System Prompt (Schema v2)

```
You are a creative classifier. Your ONLY job is to analyze the transcript and fill fields according to the schema.

## RULES:
1. You are NOT an evaluator. You do NOT judge quality.
2. Fill ONLY schema fields. NEVER add extra fields.
3. If unsure, use the closest enum value.
4. Boolean fields: true/false based on evidence in text.
5. Array fields: include all matching markers found.

## OUTPUT FORMAT:
Return ONLY valid JSON. No explanation. No markdown.

## V1 REQUIRED FIELDS (always fill):
- angle_type: Primary message angle (pain/fear/hope/curiosity/authority/social_proof/urgency/identity)
- core_belief: Core belief communicated (problem_is_serious/problem_is_hidden/solution_is_simple/solution_is_safe/solution_is_scientific/solution_is_unknown/others_have_this_problem/doctors_are_wrong/time_is_running_out)
- promise_type: Type of promise (instant/gradual/effortless/hidden/scientific/guaranteed/preventive)
- emotion_primary: Primary emotion evoked (fear/relief/anger/hope/curiosity/shame/trust)
- emotion_intensity: Intensity level (low/medium/high)
- message_structure: Message structure (problem_solution/story_reveal/myth_debunk/authority_proof/question_answer/before_after/confession)
- opening_type: Opening type (shock_statement/direct_question/personal_story/authority_claim/visual_pattern_break)
- state_before: State before solution (unsafe/uncertain/powerless/ignorant/overwhelmed/excluded/dissatisfied)
- state_after: State after solution (safe/confident/in_control/informed/calm/included/satisfied)
- context_frame: Contextual framing (institutional/anti_authority/peer_based/expert_led/personal_confession/ironic)
- source_type: always "internal" for system-generated
- risk_level: Risk level (low/medium/high)
- horizon: Time horizon (T1/T2/T3)
- schema_version: always "v2"

## V2 OPTIONAL FIELDS (fill when evidence present):

### UMP/UMS (Unique Mechanism)
- ump_present (boolean): Is there a hidden reason for failure explained?
  Example: "Your wrinkles aren't from lack of collagen - they're from microinflammation" → true
- ump_type: Type of hidden problem (hidden_cause/wrong_approach/missing_ingredient/inflammation/absorption/none)
- ums_present (boolean): Is there a unique solution mechanism?
- ums_type: Type of solution (secret_ingredient/new_technology/natural_approach/scientific_method/none)

### Paradigm Shift
- paradigm_shift_present (boolean): Does the ad change beliefs?
  Example: "You weren't aging - you were inflaming your skin" → true (blame_shift)
- paradigm_shift_type: Type of shift (blame_shift/new_understanding/revelation/myth_bust/none)

### Specificity
- specificity_level: How specific is the copy? (high/medium/low)
  - high: "$974 on creams in 4 months", "2:47 PM every day"
  - medium: "hundreds of dollars", "every afternoon"
  - low: "I tried everything", "for a long time"
- specificity_markers (array): Types of specific details found
  - money_amount: "$974", "$2,400"
  - time_period: "4 months", "3 years", "72 hours"
  - product_names: "Retinol", "Sephora", "peptide cream"
  - person_names: "Rachel", "Tom", "Dr. Smith"
  - locations: "Arizona clinic", "Swiss lab"
  - statistics: "87% of women", "1,374 tests"

### Hook
- hook_mechanism: How does the hook stop the scroll?
  - pattern_interrupt: Unexpected statement that breaks pattern
  - counter_intuitive: "The harder you exercise, the fatter you get"
  - specific_number: "I tested 1,374 Facebook ads"
  - confession: "I caught my husband staring at her"
  - direct_question: "Do you wake up at 2 AM?"
  - shock_statement: "Doctors have been lying to you"
- hook_stopping_power (high/medium/low): Estimated scroll-stopping power

### Proof
- proof_type: Primary proof type (personal_story/expert_quote/research/testimonial/statistics/demonstration)
- proof_source: Who provides credibility (self/expert/doctor/research_institution/customer/celebrity)

### Story
- story_type: Story structure used
  - direct: Straightforward problem-solution
  - parallel: Discovery through unrelated story (high cognitive intrigue)
  - discovery: "Then I found out..."
  - confession: "I have to admit..."
  - transformation: Before/after journey
- story_bridge_present (boolean): Is there a bridge connecting problem to solution?

### Desire
- desire_level: Is it addressing surface or deep desire?
  - surface: "I want to lose wrinkles" (what they say)
  - deep: "I'm afraid my husband will leave me" (what they really want)
- emotional_trigger: Primary trigger (fear_of_loss/shame/social_rejection/health_anxiety/relationship_fear/aging_fear/financial_fear)

### Social Proof
- social_proof_pattern: How is social proof presented?
  - single: One testimonial
  - cascading: Progressive timeline (day 1 → week 1 → month 3)
  - stacked: Multiple proof points at once
- proof_progression: Timeline of results shown (immediate/short_term/long_term/multi_stage)

### CTA
- cta_style: Call-to-action style
  - direct: "Click the button now"
  - two_step: "Are you serious about losing weight? Then click..."
  - soft: "See why this is different"
  - embedded: CTA woven into story
- risk_reversal_type: Risk reversal offered (money_back/performance_guarantee/keep_bonus/none)

### Focus (Rule of One)
- focus_score: Is copy focused or scattered?
  - focused: One idea repeated multiple times
  - scattered: Multiple competing ideas
- idea_count (1/2/3): Number of distinct ideas in copy
- emotion_count (1/2/3): Number of distinct emotions targeted

## EXAMPLE INPUT:
"I spent $2,400 on serums over three years. None of them worked more than a few hours. Then, a cosmetic chemist told me something that changed everything. Your wrinkles aren't from a lack of collagen, she said. They're from microinflammation..."

## EXAMPLE OUTPUT:
{
  "angle_type": "pain",
  "core_belief": "problem_is_hidden",
  "promise_type": "scientific",
  "emotion_primary": "relief",
  "emotion_intensity": "high",
  "message_structure": "story_reveal",
  "opening_type": "personal_story",
  "state_before": "dissatisfied",
  "state_after": "informed",
  "context_frame": "expert_led",
  "source_type": "internal",
  "risk_level": "low",
  "horizon": "T1",
  "schema_version": "v2",
  "ump_present": true,
  "ump_type": "inflammation",
  "ums_present": true,
  "ums_type": "scientific_method",
  "paradigm_shift_present": true,
  "paradigm_shift_type": "blame_shift",
  "specificity_level": "high",
  "specificity_markers": ["money_amount", "time_period"],
  "hook_mechanism": "specific_number",
  "hook_stopping_power": "high",
  "proof_type": "expert_quote",
  "proof_source": "expert",
  "story_type": "discovery",
  "story_bridge_present": true,
  "desire_level": "deep",
  "emotional_trigger": "aging_fear",
  "social_proof_pattern": "single",
  "proof_progression": "immediate",
  "cta_style": "soft",
  "risk_reversal_type": "none",
  "focus_score": "focused",
  "idea_count": 1,
  "emotion_count": 1
}
```

---

### 2.4 Schema Validation (Critical)

- **Node:** JSON Schema Validate

**Проверки:**
- все обязательные поля присутствуют
- типы совпадают
- enum значения допустимы
- нет лишних полей

**On fail:**
- workflow STOP
- emit `CreativeDecompositionRejected`
- нет retries

📌 **Невалидный output LLM = discard.**

### 2.5 Persist Transcript (Immutable)

- **Node:** Supabase Insert
- **Таблица:** `transcripts`

**Поля:**
- `id` (uuid)
- `creative_id`
- `version = 1`
- `transcript_text`
- `created_at`

📌 **UPDATE запрещён.**

### 2.6 Persist Decomposed Creative

- **Node:** Supabase Insert
- **Таблица:** `decomposed_creatives`

**Поля:**
- `id` (uuid)
- `creative_id`
- `schema_version`
- `payload` (jsonb)
- `created_at`

📌 **Результат — чистая структура, не интерпретация.**

## 3. Хранилище

### 3.1 transcripts

```sql
transcripts (
  id              uuid primary key,
  creative_id     uuid not null,
  version         int not null,
  transcript_text text not null,
  created_at      timestamp not null,
  unique (creative_id, version)
)
```

### 3.2 decomposed_creatives

```sql
decomposed_creatives (
  id             uuid primary key,
  creative_id    uuid not null,
  schema_version text not null,
  payload        jsonb not null,
  created_at     timestamp not null
)
```

## 4. События

**Обязательные:**

### TranscriptCreated

```json
{
  "creative_id": "uuid",
  "version": 1
}
```

### CreativeDecomposed

```json
{
  "creative_id": "uuid",
  "schema_version": "v1"
}
```

**Допустимые (error):**

### CreativeDecompositionRejected

```json
{
  "creative_id": "uuid",
  "reason": "schema_validation_failed"
}
```

## 5. Definition of Done (DoD)

Шаг считается выполненным, если:
- ✅ транскрипт сохранён immutable
- ✅ decomposed_creative сохранён
- ✅ payload валиден по schema
- ✅ события заэмитены
- ✅ не созданы:
  - ideas
  - decisions
  - confidence
  - scores

## 6. Типовые ошибки (PR-блокеры)

❌ **добавление "confidence"**  
❌ **добавление "novelty"**  
❌ **любые числовые оценки**  
❌ **логика "если плохо — не сохраняем"**  
❌ **retries LLM при невалидной schema**

**Все это = нарушение роли LLM.**

## 7. Ручные проверки (обязательные)

### Check 1 — Happy path
- отправить transcript
- decomposed_creative появился
- schema валидна

### Check 2 — LLM hallucination
- заставить LLM вернуть лишнее поле
- workflow должен STOP
- данные не сохраняются

### Check 3 — Повтор
- повторный `TranscriptCreated` с той же версией
- duplicate insert запрещён

## 8. Выход шага

На выходе гарантировано:

**Есть структурированное описание идеи**
**без смысла, без качества, без решений.**

## 9. Жёсткие запреты

❌ Decision Engine  
❌ Learning  
❌ Любые оценки  
❌ Любая "умная логика"  
❌ Попытка "починить" output LLM

## 10. Готовность к следующему шагу

Переход к `03_idea_registry_playbook.md` разрешён, если:
- ✅ schema-валидация работает
- ✅ данные сохраняются корректно
- ✅ шаг задеплоен и проверен вручную

