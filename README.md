# 🧬 GenomAI

> Autonomous Creative Decision System — полностью автономная система принятия креативных решений в нестабильной рыночной среде

## 📖 О проекте

**GenomAI** — это автономная система принятия креативных решений, предназначенная для:
- **Обнаружения устойчивых связок** креативных переменных
- **Эволюции через контролируемые мутации** существующих паттернов
- **Управления выгоранием аудитории** на уровне кластеров
- **Системного повышения hitrate** решений во времени

GenomAI функционирует как внешний стратегический мозг, где:
- рынок является единственным источником истины
- решения оцениваются по последствиям
- обучение происходит на результатах собственных действий

### 🎯 Основные принципы

1. **Market is the only ground truth**
2. **Survival > short-term revenue**
3. **Decision → Outcome → Learning**
4. **Selection bias признаётся и не «лечится»**
5. **Выгорание — сигнал, а не ошибка**
6. **Автоматизация предпочтительнее ручных решений**
7. **Человек — interrupt, а не участник цикла**

### 🧠 Архитектура принятия решений

```
External Signals (Market / Spy / Context)
            ↓
ML Advisory Layer
(similarity, novelty, fatigue signals)
            ↓
Decision Engine
(rules, policies, constraints)
            ↓
Hypothesis Factory
            ↓
Market Execution
            ↓
Outcome Logging
            ↓
Learning Loop
            ↓
Decision Engine
```

**ML никогда не bypass'ит Decision Engine.**

---

## 📚 Документация

📖 **[Final Architecture & Decision Doctrine](./docs/FINAL_ARCHITECTURE.md)** — Окончательная архитектура и доктрина функционирования системы:
- Определение системы
- Базовые принципы (неизменяемые)
- Роль человека
- Архитектура принятия решений
- Learning Loop (ядро системы)
- Decision Horizon Doctrine
- Hypothesis Death & Resurrection Rules
- Fatigue Doctrine
- Spy Override Doctrine
- Epistemic Shock Doctrine
- Роль машинного обучения
- Критерии идеальности системы

---

## 📁 Структура проекта

```
.
├── docs/                    # 📚 Документация
│   └── FINAL_ARCHITECTURE.md # Финальная архитектура и доктрина
├── .github/                 # ⚙️ GitHub настройки
│   ├── workflows/          # GitHub Actions
│   ├── ISSUE_TEMPLATE.md   # Шаблон для создания Issues
│   └── PULL_REQUEST_TEMPLATE.md # Шаблон для создания PR
├── .gitignore              # Игнорируемые файлы
└── README.md               # 📖 Этот файл
```

---

## 🎯 Статус проекта

- ✅ **Доктрина создана** - [Final Architecture & Decision Doctrine](./docs/FINAL_ARCHITECTURE.md)
- ✅ **GitHub репозиторий** - настроен и готов к работе
- 🚧 **Разработка** - в процессе

---

## 💡 Ключевые концепции

### Decision Horizon Doctrine

Система работает с тремя временными горизонтами:
- **T₁ (0–3 дня)**: первичная реакция рынка, exploration
- **T₂ (3–14 дней)**: устойчивость и повторяемость, основной рабочий горизонт
- **T₃ (14+ дней)**: обновление политик и ограничений

### Hypothesis Death & Resurrection

Система различает три состояния гипотез:
- **Soft Failure**: единичный провал, гипотеза доступна с отрицательным весом
- **Hard Failure**: повторяемый провал, exploit запрещён
- **Dead Hypothesis**: полностью исключается из генерации, логируется в Death Memory

### Fatigue Doctrine

Выгорание детектируется на уровне кластеров:
1. **Skin Exhaustion** → только визуальные мутации
2. **Message Exhaustion** → запрет повторения message-структур
3. **Angle Exhaustion** → exploit полностью запрещён
4. **Forced Novelty** → принудительное exploration

---

## 🎯 Финальный принцип

Идеальная GenomAI — это система, которая зарабатывает, когда человек ей не мешает.

Человек остаётся источником редкого сдвига.

Все остальные решения — ответственность системы.

---

## ❓ Нужна помощь?

Если что-то непонятно:
1. Прочитайте [Final Architecture & Decision Doctrine](./docs/FINAL_ARCHITECTURE.md)
2. Спросите у меня (AI помощника) - я помогу!

---

**Удачи в разработке! 🎉**
