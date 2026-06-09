# gibdd_points

Скрипт для подсчёта баллов ГИБДД по папкам со скриншотами/видео (ARMRP / GTA V).

## Как работает
- Берёт корневую папку (где у тебя подпапки `штрафы`, `аресты`, `тонировка`, `поставки` и т.п.)
- Считает файлы изображений/видео в этих подпапках
- Умножает на стоимость категории и формирует `report.txt`

## Установка
Нужен Python 3.10+ (на Windows удобно ставить через Microsoft Store).

## Запуск
Пример:

```powershell
python gibdd_points.py --root "D:\\otkat\\Grand Theft Auto V" --include-root-files
```

За конкретную дату:

```powershell
python gibdd_points.py --root "D:\\otkat\\Grand Theft Auto V" --date 2026-06-09 --include-root-files
```

## Настройка категорий
Категории настраиваются в словаре `CATEGORIES` внутри `gibdd_points.py`.
