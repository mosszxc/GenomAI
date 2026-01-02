# Idea → Issue → Worktree → Cursor

Напиши идею или опиши баг — всё остальное автоматически.

## Использование

```
/idea Добавить тёмную тему в интерфейс
/idea Баг: краш при пустом вводе
/idea Хочу чтобы API возвращал pagination
```

## Действие

1. Взять `$ARGUMENTS` как описание задачи

2. Определить тип:
   - Содержит "баг", "fix", "crash", "ошибка", "сломал" → `bug`
   - Иначе → `enhancement`

3. Выполнить:

```bash
./scripts/task-new.sh "$ARGUMENTS"
```

Скрипт автоматически:
- Создаёт GitHub issue
- Создаёт изолированный worktree
- Открывает в Cursor

4. Сообщить пользователю:
   - Номер issue
   - Путь к worktree
   - Что Cursor открыт

## Примеры

```
/idea Добавить экспорт в PDF
→ Issue #125 создан (enhancement)
→ Worktree: .worktrees/issue-125-добавить-экспорт-в-pdf
→ Cursor открыт

/idea Баг: кнопка не работает на мобильном
→ Issue #126 создан (bug)
→ Worktree: .worktrees/issue-126-баг-кнопка-не-работает
→ Cursor открыт
```

## После работы

Когда закончишь в Cursor:

```bash
./scripts/task-done.sh <номер-issue>
```

Или скажи Claude:
```
/task done 125
```
