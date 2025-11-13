# Визуализация графа зависимостей (Вариант №3) — Документация

## 1. Общее описание

Проект содержит CLI-утилиты на Python для сбора прямых зависимостей npm-пакета и генерации их визуализации в формате D2 / SVG.

**Цели:** реализовать этап 1 (конфигурация), этап 2 (сбор данных) и этап 5 (визуализация). Для получения зависимостей не используются менеджеры пакетов или сторонние библиотеки — используется только чтение `package.json` (локально) и HTTP-запросы к npm registry.

---

## 2. Содержимое репозитория

- `index.py` — основной CLI для этапов 1 и 2 (чтение XML-конфига, сбор прямых зависимостей, сохранение JSON).
- `to_d2.py` — генерация `.d2` (только прямые зависимости) и попытка рендера `.svg` через d2 CLI; при отсутствии d2 создаётся fallback SVG.
- `config_<pkg>.xml` — XML-конфиги для анализа (создайте вручную).
- `direct_deps_<pkg>.json` — результат этапа 2 (прямые зависимости).
- `graph_<pkg>.d2`, `graph_<pkg>.svg`, `graph_<pkg>_fallback.svg` — артефакты визуализации.
- `README.md` — эта документация.

---

## 3. Установка (требования)

1. Установите Python 3.8+.
2. При `test_mode=false` обеспечьте доступ в интернет (скрипт работает с `https://registry.npmjs.org/`).
3. Опционально: установите `d2` CLI для рендера `.d2` в `.svg`.
   - Если `d2` отсутствует, скрипт создаёт fallback SVG (`graph_<pkg>_fallback.svg`).
   - На Windows `d2` можно установить через Scoop / Chocolatey или скачав релиз с GitHub.

---

## 4. Формат XML-конфигурации

Создайте XML-файл с четырьмя обязательными тегами:

```xml
<config>
  <package>имя-пакета</package>
  <repo>URL_реестра_или_путь_к_папке</repo>
  <test_mode>false</test_mode>
  <max_depth>2</max_depth>
</config>
```

> Примечание: для визуализации D2 отображаются только прямые зависимости, поэтому `max_depth` не влияет на граф прямых зависимостей.

---

## 5. Описание функций и настроек

### `index.py`

- Загружает и валидирует XML-конфиг.
- **Режим 1 (проверка):** при запуске без номера этапа выводит параметры в формате `ключ=значение`.
- **Режим 2 (сбор):** собирает прямые зависимости и сохраняет их в `direct_deps_<pkg>.json`:
  - если `test_mode=true` — читает `package.json` в указанной папке;
  - если `test_mode=false` — запрашивает метаданные из `https://registry.npmjs.org/<package>` и извлекает `dependencies` для `dist-tags.latest`.

### `to_d2.py`

- Читает `direct_deps_<pkg>.json`.
- Формирует корректный D2-текст, содержащий центральный узел (пакет) и его прямые зависимости (узлы + ребра).
- Пытается вызвать `d2` CLI для рендера `.svg`;
  - при отсутствии `d2` создаёт fallback SVG и открывает его.

---

## 6. Команды для работы (инструкция)

1. Создайте конфиги в папке проекта: `config_express.xml`, `config_webpack.xml`, `config_eslint.xml` (см. примеры ниже).

2. **Проверка параметров (этап 1):**

```bash
python index.py config_express.xml
```

3. **Сбор прямых зависимостей и сохранение (этап 2):**

```bash
python index.py config_express.xml 2
```

- В результате появится файл: `direct_deps_express.json`.

4. **Визуализация (этап 5 — только прямые зависимости):**

```bash
python to_d2.py direct_deps_express.json
```

- В результате: `graph_express.d2` и `graph_express.svg` (или `graph_express_fallback.svg`).

5. Повторите для других пакетов:

```bash
python index.py config_webpack.xml 2
python to_d2.py direct_deps_webpack.json

python index.py config_eslint.xml 2
python to_d2.py direct_deps_eslint.json
```

---

## 7. Примеры конфигов (создайте рядом с `index.py`)

**config_express.xml**

```xml
<config>
  <package>express</package>
  <repo>https://registry.npmjs.org/</repo>
  <test_mode>false</test_mode>
  <max_depth>2</max_depth>
</config>
```

**config_webpack.xml**

```xml
<config>
  <package>webpack</package>
  <repo>https://registry.npmjs.org/</repo>
  <test_mode>false</test_mode>
  <max_depth>2</max_depth>
</config>
```

**config_eslint.xml**

```xml
<config>
  <package>eslint</package>
  <repo>https://registry.npmjs.org/</repo>
  <test_mode>false</test_mode>
  <max_depth>2</max_depth>
</config>
```

---

## 8. Примеры использования (демонстрация для трёх пакетов)

1. Создайте указанные `config_<pkg>.xml`.

2. Выполните сбор:

```bash
python index.py config_express.xml 2
python index.py config_webpack.xml 2
python index.py config_eslint.xml 2
```

3. Сгенерируйте визуализации:

```bash
python to_d2.py direct_deps_express.json
python to_d2.py direct_deps_webpack.json
python to_d2.py direct_deps_eslint.json
```

4. Откройте полученные `graph_<pkg>_fallback.svg` или `graph_<pkg>.svg` и продемонстрируйте их.

---

## 9. Сравнение с выводом npm

Получите штатный список зависимостей через npm:

```bash
npm view <package> dependencies --json
```

Сравните пары `имя: версия` с `direct_deps_<pkg>.json`.

**Возможные расхождения и причины:**
- Скрипт использует `dist-tags.latest` у реестра;
- Учитываются только `dependencies` (не `peerDependencies` и не `optionalDependencies`);
- Локальные установки / кеши могут отличаться от текущего реестра.

---

## 10. Коммит результата

Рекомендую сохранять артефакты и выполнять коммит с понятным сообщением. Пример:

```bash
git add direct_deps_express.json graph_express.d2 graph_express_fallback.svg
git commit -m "Stage 5: add D2 visualization for express (direct deps)"
```

---

## 11. Траблшутинг (быстрые инструкции)

- **Если `direct_deps_<pkg>.json` не появился:**
  - запустите `python index.py config_<pkg>.xml 2` и проверьте вывод на строку `Saved direct dependencies to: direct_deps_<pkg>.json`;
  - выполните поиск файла (`dir /s direct_deps_<pkg>.json` на Windows или `find . -name "direct_deps_<pkg>.json"` на Unix);
  - проверьте подключение к интернету при `test_mode=false`.

- **Если `d2` не найден:**
  - установите `d2` (Scoop / Chocolatey / релиз с GitHub) либо используйте автоматически созданный `graph_<pkg>_fallback.svg`.

- **Если возникла ошибка в процессе:**
  - выполните команду ещё раз в терминале, скопируйте вывод с `error:` и пришлите его для диагностики.

---

## 12. Дополнительно (рекомендации и улучшения)

- Можно расширить сбор, добавив обработку `peerDependencies` и `optionalDependencies` по флагу конфигурации.
- Можно добавить режим полного обхода зависимостей с контролем `max_depth` и кешированием запросов к реестру.
- Для улучшения визуализации можно применять группировку по типам зависимостей или использовать разные стили узлов в D2.

