#!/bin/bash
# Конвертирует миграции из infrastructure/migrations/ в supabase/migrations/
# Формат: NNN_name.sql -> YYYYMMDDHHMMSS_name.sql
#
# Usage: ./scripts/migrate-to-supabase.sh [--force]

set -e

PROJECT_ROOT="$(git rev-parse --show-toplevel)"
SOURCE_DIR="$PROJECT_ROOT/infrastructure/migrations"
TARGET_DIR="$PROJECT_ROOT/supabase/migrations"

# Base timestamp: 2024-01-01 00:00:00
BASE_YEAR=2024
BASE_MONTH=01
BASE_DAY=01
BASE_HOUR=00
BASE_MIN=00

FORCE=""
if [ "$1" == "--force" ]; then
    FORCE="true"
fi

# Проверка существующих миграций
if [ -d "$TARGET_DIR" ] && [ "$(ls -A $TARGET_DIR 2>/dev/null)" ]; then
    if [ "$FORCE" != "true" ]; then
        echo "Target directory $TARGET_DIR already contains migrations."
        echo "Use --force to overwrite."
        exit 1
    fi
    echo "Removing existing migrations..."
    rm -f "$TARGET_DIR"/*.sql
fi

mkdir -p "$TARGET_DIR"

echo "Converting migrations from:"
echo "  Source: $SOURCE_DIR"
echo "  Target: $TARGET_DIR"
echo ""

count=0

# Получить список миграций в правильном порядке (сортировка по номеру)
for file in $(ls "$SOURCE_DIR"/*.sql 2>/dev/null | sort -V); do
    filename=$(basename "$file")

    # Пропустить reference файлы
    if [[ "$filename" == "000_all_tables.sql" ]] || [[ "$filename" == "create_config_table.sql" ]]; then
        echo "Skipping reference file: $filename"
        continue
    fi

    # Извлечь номер и имя
    # Формат: NNN_name.sql или NN_name.sql
    num=$(echo "$filename" | sed -E 's/^0*([0-9]+)_.*/\1/')
    name=$(echo "$filename" | sed -E 's/^[0-9]+_//')

    # Вычислить timestamp
    # Добавляем минуты к базовому времени
    total_minutes=$((BASE_MIN + num))
    hours=$((BASE_HOUR + total_minutes / 60))
    minutes=$((total_minutes % 60))

    # Форматируем timestamp
    new_timestamp=$(printf "%04d%02d%02d%02d%02d00" $BASE_YEAR $BASE_MONTH $BASE_DAY $hours $minutes)

    new_filename="${new_timestamp}_${name}"

    echo "  $filename -> $new_filename"
    cp "$file" "$TARGET_DIR/$new_filename"

    ((count++))
done

echo ""
echo "Conversion complete!"
echo "Total migrations: $count"
echo ""
echo "Next steps:"
echo "  1. Start local Supabase: supabase start"
echo "  2. Reset database with migrations: supabase db reset"
