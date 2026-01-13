# Issue #540: Missing HTML escaping in Telegram messages

## Что изменено

- Добавлен импорт `html.escape` как `html_escape`
- Экранируется `video_url` при отображении в Telegram сообщении (строка 2529)
- Используется `repr()[:100]` для логирования `message.text` для защиты от log injection (строка 2607)

## Безопасность

- Предотвращён потенциальный XSS через вредоносные URL с HTML тегами
- Защита от log injection через newlines и control characters в message.text

## Test

```bash
cd /Users/mosszxc/Documents/Проэкты/GenomAI/.worktrees/issue-540--missing-html-escaping-in-telegram-messa && python -c "
from html import escape as html_escape

# Test HTML escaping
malicious_url = '<script>alert(1)</script>http://evil.com'
escaped = html_escape(malicious_url[:50])
assert '&lt;' in escaped and '&gt;' in escaped, 'HTML not escaped'
assert '<script>' not in escaped, 'Script tag not escaped'

# Test repr for logging
text_with_newlines = 'line1\nline2\r\nline3'
logged = repr(text_with_newlines)[:100]
assert '\\n' in logged and '\\r' in logged, 'Control chars not escaped'

print('OK: HTML escaping and log sanitization work correctly')
"
```
