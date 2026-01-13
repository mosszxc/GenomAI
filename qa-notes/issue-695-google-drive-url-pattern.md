# Issue #695: Google Drive URL не распознаётся в extract_video_url

## Что изменено
- Добавлен паттерн `https?://drive\.google\.com/\S+` в `extract_video_url()` для распознавания Google Drive ссылок

## Причина
При отправке Google Drive ссылки через Telegram webhook, функция `extract_video_url` не распознавала URL и креатив не создавался.

## Test
```bash
python3 -c "
import re
patterns = [
    r'https?://(?:www\.)?(?:youtube\.com|youtu\.be)/\S+',
    r'https?://(?:www\.)?vimeo\.com/\S+',
    r'https?://drive\.google\.com/\S+',
    r'https?://\S+\.mp4',
]
url = 'https://drive.google.com/file/d/1pCTMewFGP-ypWfx-DAjLXSiYUo5f0Iex/view?usp=share_link'
for p in patterns:
    if re.search(p, url, re.IGNORECASE):
        print('OK: URL matched')
        exit(0)
print('FAIL: URL not matched')
exit(1)
"
```
