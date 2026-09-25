# GigaAM STT service

Локальный асинхронный HTTP-сервис без авторизации. Аудио сохраняется во временном
Docker volume, операция ставится в Redis и обрабатывается одним CPU worker. После
завершения аудиофайл удаляется, результат остаётся в Redis на 24 часа.

## API

```bash
curl -F "file=@order.mp3" http://localhost:5001/v1/transcriptions
```

Ответ `202`:

```json
{"id":"...","done":false,"status":"queued"}
```

```bash
curl http://localhost:5001/v1/operations/<id>
```

Финальный ответ содержит `done=true`, `status=done` и
`response.{text,segments,model}`. При ошибке возвращается `status=error` и
`error.message`.

## Настройки

- `GIGAAM_MODEL` — модель, по умолчанию `v3_rnnt`;
- `GIGAAM_THREADS` — число CPU-потоков;
- `GIGAAM_CHUNK_SEC` — длина основной части, по умолчанию 22 секунды;
- `GIGAAM_OVERLAP_SEC` — перекрытие частей, по умолчанию 0,8 секунды;
- `GIGAAM_RESULT_TTL_SEC` — время хранения результата, по умолчанию 86400 секунд;
- `GIGAAM_MAX_UPLOAD_MB` — максимальный файл, по умолчанию 100 МБ.

MinIO не используется: при прямой загрузке в один локальный worker файловый volume
проще и надёжнее. S3-совместимое хранилище имеет смысл добавлять при нескольких
хостах или независимых worker-контейнерах.
