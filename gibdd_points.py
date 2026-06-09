from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm"}

# Папка -> (баллы за 1 подтверждение, человеко-читаемое название)
CATEGORIES = {
    "штрафы": (10, "Штраф"),
    "аресты": (15, "Арест"),
    "тонировка": (5, "Снятие тонировки"),
    "поставки": (25, "Участие в поставке"),
    # добавишь потом при желании:
    # "эвакуация": (10, "Эвакуация Т/С"),
    # "посты": (30, "Пост 30 минут"),
    # "лишение_ву": (15, "Лишение В/У"),
    # "аннулирование_ву": (15, "Аннулирование В/У"),
    # "выдача_ву": (15, "Выдача В/У"),
    # "выдача_грз": (15, "Выдача ГРЗ"),
}

# Если скрины/видео называются как GTA: "Grand Theft Auto V 2026.06.09-00.54.01.12"
GTA_DT_RE = re.compile(r"(\d{4})\.(\d{2})\.(\d{2})-(\d{2})\.(\d{2})\.(\d{2})")


@dataclass
class CountResult:
    count_images: int = 0
    count_videos: int = 0


def parse_gta_datetime_from_name(name: str):
    m = GTA_DT_RE.search(name)
    if not m:
        return None
    y, mo, d, hh, mm, ss = map(int, m.groups())
    return datetime(y, mo, d, hh, mm, ss)


def file_matches_date(p: Path, date_yyyy_mm_dd: str | None) -> bool:
    if not date_yyyy_mm_dd:
        return True

    # 1) пробуем взять дату из имени (как у GTA)
    dt = parse_gta_datetime_from_name(p.name)
    if dt:
        return dt.strftime("%Y-%m-%d") == date_yyyy_mm_dd

    # 2) иначе берём дату изменения файла
    ts = p.stat().st_mtime
    dt2 = datetime.fromtimestamp(ts)
    return dt2.strftime("%Y-%m-%d") == date_yyyy_mm_dd


def count_files(folder: Path, date_yyyy_mm_dd: str | None, recursive: bool = True) -> CountResult:
    res = CountResult()
    if not folder.exists():
        return res

    it = folder.rglob("*") if recursive else folder.glob("*")
    for p in it:
        if not p.is_file():
            continue
        ext = p.suffix.lower()
        if ext not in IMAGE_EXTS and ext not in VIDEO_EXTS:
            continue
        if not file_matches_date(p, date_yyyy_mm_dd):
            continue
        if ext in IMAGE_EXTS:
            res.count_images += 1
        elif ext in VIDEO_EXTS:
            res.count_videos += 1
    return res


def main():
    ap = argparse.ArgumentParser(
        description="Подсчет баллов ГИБДД по папкам со скриншотами/видео (ARMRP / GTA V)."
    )
    ap.add_argument(
        "--root",
        required=True,
        help=r'Путь к папке, например: D:\\otkat\\Grand Theft Auto V',
    )
    ap.add_argument(
        "--date",
        default=None,
        help="Фильтр по дате YYYY-MM-DD (например 2026-06-09). Если не задано — считаем всё.",
    )
    ap.add_argument("--no-recursive", action="store_true", help="Не заходить во вложенные папки.")
    ap.add_argument(
        "--include-root-files",
        action="store_true",
        help="Отдельно посчитать файлы в корне root (не в подпапках). В баллы не входит, просто для справки.",
    )
    args = ap.parse_args()

    root = Path(args.root)
    recursive = not args.no_recursive

    lines: list[str] = []
    lines.append(f"Папка: {root}")
    lines.append(f"Дата: {args.date or 'всё время'}")
    lines.append("")

    total_points = 0
    total_images = 0
    total_videos = 0

    for folder_name, (points_per, label) in CATEGORIES.items():
        folder = root / folder_name
        r = count_files(folder, args.date, recursive=recursive)

        # Логика: 1 файл (скрин/видео) = 1 подтверждение действия
        confirmations = r.count_images + r.count_videos
        points = confirmations * points_per

        total_points += points
        total_images += r.count_images
        total_videos += r.count_videos

        lines.append(f"{label}: {confirmations} шт.  × {points_per} = {points} баллов")
        if confirmations:
            lines.append(f"  (картинки: {r.count_images}, видео: {r.count_videos})")

    lines.append("")
    lines.append(f"ИТОГО: {total_points} баллов")
    lines.append(f"Файлов учтено: {total_images} картинок, {total_videos} видео")
    lines.append("")

    if args.include_root_files:
        rroot = count_files(root, args.date, recursive=False)
        lines.append("Справка (корень папки, не подпапки):")
        lines.append(
            f"  файлов в корне: {rroot.count_images + rroot.count_videos} (картинки: {rroot.count_images}, видео: {rroot.count_videos})"
        )
        lines.append("")

    report_text = "\n".join(lines)
    print(report_text)

    out_path = root / "report.txt"
    out_path.write_text(report_text, encoding="utf-8")


if __name__ == "__main__":
    main()
