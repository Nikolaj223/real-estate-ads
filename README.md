# HomeOffer Real Estate Assignment

Тестовое задание для fullstack-позиции: форма объявления недвижимости на React/Formik/Yup и сервис браузинга Avito-страниц через FastAPI, RabbitMQ и Selenium Grid.

## Что внутри

- `apps/frontend` — Vite + React + TypeScript, Formik-aware поля, Yup-валидация и тесты для `Radio`/`CheckBox`.
- `apps/api` — публичный FastAPI сервис с `POST /browse`, проверкой URL, идемпотентностью и публикацией durable-сообщений в RabbitMQ.
- `apps/worker` — consumer на Python/Selenium, который читает очередь, открывает страницу в Selenium Grid и выводит HTML в logs.
- `docker-compose.yml` — RabbitMQ, Selenium Hub, Chrome node, API и worker. Наружу открыт только `api:8000`.
- `.github/workflows/ci.yml` — проверки фронтенда, API и worker.

## Frontend

Formik-привязка вынесена в `withFormikControl`. UI-компоненты не знают о Formik, а форма использует минимальный код:

```tsx
<FormikTextInput name="name" label="Название объекта" />
<FormikNumberInput name="floor" label="Этаж" />
<FormikCheckbox name="isStudio" label="Студия" />
<FormikRadioGroup name="dealType" label="Тип сделки" options={dealTypeOptions} />
```

Глобальные тексты Yup задаются один раз в `apps/frontend/src/shared/validation/yupLocale.ts`:

- required: `Поле обязательно для заполнения`
- min: `Значение не может быть меньше {{ограничение}}`
- max: `Значение не может быть больше {{ограничение}}`

Локальное правило площади реализовано как расширение Yup:

```ts
Yup.number().moreThanSumOfFields(["livingSquare", "kitchenSquare"])
```

Текст локальной ошибки: `Общая площадь должна быть больше суммы жилой площади и площади кухни`.

## Backend flow

`POST /browse`

```json
{
  "url": "https://www.avito.ru/samara/kvartiry/123"
}
```

Ответ:

```json
{
  "jobId": "1a2b...",
  "status": "queued",
  "deduplicated": false
}
```

После приёма:

1. API принимает только `http/https` URL на домене `avito.ru` или его поддоменах.
2. API строит стабильный `jobId` из URL и `Idempotency-Key`, если заголовок передан.
3. Задача публикуется в RabbitMQ как persistent message.
4. Worker вручную ack/nack-ает сообщение после Selenium-рендера.
5. HTML страницы пишется в `docker compose logs worker`.

## Защиты и production-детали

- SSRF guard: запрещены non-HTTP схемы, credentials в URL и любые host вне `*.avito.ru`.
- Idempotency: повторный URL или повторный `Idempotency-Key` возвращает `duplicate` без повторной публикации.
- RabbitMQ: durable exchange/queue, persistent messages, dead-letter exchange/queue.
- Worker: повторная проверка URL перед Selenium, manual ack/nack, page-load timeout, ожидание Selenium Grid, chunked HTML logs.
- Containers: API и worker запускаются не от root.
- Compose: наружу открыт только порт `8000` публичного API; RabbitMQ и Selenium доступны только внутри сети compose.
- Healthchecks: RabbitMQ, Selenium Hub и FastAPI readiness.

Для горизонтального production-масштабирования in-memory идемпотентность нужно заменить на Redis/PostgreSQL с уникальным ключом `job_id`; интерфейс сервиса уже изолирован.

## Локальный запуск

Frontend:

```bash
bun install
bun run dev:frontend
```

Backend stack:

```bash
docker compose up --build
```

Проверка API:

```bash
curl -X POST http://localhost:8000/browse \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: demo-1" \
  -d '{"url":"https://www.avito.ru/samara/kvartiry/123"}'
```

Логи worker:

```bash
docker compose logs -f worker
```

## Тесты

```bash
bun run test:frontend
cd apps/api
python -m pip install -e ".[test]"
pytest -q
```
