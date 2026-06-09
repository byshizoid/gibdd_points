from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

# --- Domain rules ---
# Categories included in points. User asked to EXCLUDE ДТП and "пост 30 минут".
CATEGORIES = {
    "штрафы": {"label": "Штраф", "points": 10},
    "аресты": {"label": "Арест", "points": 15},
    "тонировка": {"label": "Снятие тонировки", "points": 5},
    "поставки": {"label": "Участие в поставке", "points": 25},
    "лишение_ву": {"label": "Лишение В/У", "points": 15},
    "аннулирование_ву": {"label": "Аннулирование В/У", "points": 15},
    "выдача_ву": {"label": "Выдача В/У", "points": 15},
    "выдача_грз": {"label": "Выдача ГРЗ", "points": 15},
    "эвакуация": {"label": "Эвакуация Т/С", "points": 10},
    "гмп": {"label": "Участие в ГМП", "points": 50},
    "мероприятие": {"label": "Участие на мероприятии", "points": 30},
}

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm"}

RANKS = [
    ("Сержант полиции", 300),
    ("Старший сержант полиции", 400),
    ("Старшина полиции", 500),
    ("Прапорщик полиции", 600),
    ("Старший прапорщик полиции", 800),
    ("Младший лейтенант полиции", 1000),
    ("Лейтенант полиции", 1200),
    ("Старший лейтенант полиции", 1500),
]

APP_NAME = "Рапорты ДПС — ARMRP"


def app_data_dir() -> Path:
    # Portable: keep config near executable when possible
    here = Path(__file__).resolve().parent
    portable = here / "_data"
    portable.mkdir(exist_ok=True)
    return portable


def default_config() -> dict:
    return {
        "root_folder": "",
        "employee": {
            "fio": "",
            "discord_id": "",
            "podrazdelenie": "",
            "dolzhnost": "",
            "current_rank": "Прапорщик полиции",
            "target_rank": "Старший прапорщик полиции",
        },
    }


def load_config(path: Path) -> dict:
    if not path.exists():
        return default_config()
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default_config()


def save_config(path: Path, cfg: dict) -> None:
    path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def count_confirmations(folder: Path) -> int:
    if not folder.exists():
        return 0
    c = 0
    for p in folder.rglob("*"):
        if not p.is_file():
            continue
        ext = p.suffix.lower()
        if ext in IMAGE_EXTS or ext in VIDEO_EXTS:
            c += 1
    return c


@dataclass
class CalcLine:
    key: str
    label: str
    confirmations: int
    points_per: int

    @property
    def points(self) -> int:
        return self.confirmations * self.points_per


def calc_points(root: Path) -> tuple[list[CalcLine], int]:
    lines: list[CalcLine] = []
    total = 0
    for key, meta in CATEGORIES.items():
        confirmations = count_confirmations(root / key)
        line = CalcLine(key=key, label=meta["label"], confirmations=confirmations, points_per=meta["points"])
        lines.append(line)
        total += line.points
    return lines, total


def required_points_for_rank(rank_name: str) -> int | None:
    for name, pts in RANKS:
        if name == rank_name:
            return pts
    return None


def build_raport(cfg: dict, total_points: int) -> str:
    emp = cfg.get("employee", {})
    fio = emp.get("fio", "")
    discord_id = emp.get("discord_id", "")
    pod = emp.get("podrazdelenie", "")
    dol = emp.get("dolzhnost", "")
    cur = emp.get("current_rank", "")
    target = emp.get("target_rank", "")

    need = required_points_for_rank(target)
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    # This is a generic template. Adjust wording to your server format if needed.
    parts = []
    parts.append("РАПОРТ НА ПОВЫШЕНИЕ")
    parts.append(f"Дата/время: {date_str}")
    parts.append("")
    parts.append(f"ФИО: {fio}")
    if discord_id:
        parts.append(f"Discord ID: {discord_id}")
    if pod:
        parts.append(f"Подразделение: {pod}")
    if dol:
        parts.append(f"Должность: {dol}")
    parts.append(f"Текущее звание: {cur}")
    parts.append(f"Прошу повысить до: {target}")
    parts.append("")

    if need is not None:
        parts.append(f"Баллы: {total_points} / {need} ({int((total_points/need)*100) if need else 0}%)")
        if total_points >= need:
            parts.append("Статус: ГОТОВ")
        else:
            parts.append("Статус: НЕ ГОТОВ")
    else:
        parts.append(f"Баллы: {total_points}")

    return "\n".join(parts) + "\n"


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1100, 700)

        self.cfg_path = app_data_dir() / "config.json"
        self.cfg = load_config(self.cfg_path)

        # Layout
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root_layout = QtWidgets.QHBoxLayout(central)

        # Left navigation
        self.nav = QtWidgets.QListWidget()
        self.nav.addItems(["Сотрудник", "Папки", "Рапорт", "Настройки"])
        self.nav.setFixedWidth(180)
        self.nav.setCurrentRow(0)
        root_layout.addWidget(self.nav)

        # Pages
        self.pages = QtWidgets.QStackedWidget()
        root_layout.addWidget(self.pages, 1)

        self.page_employee = self._build_employee_page()
        self.page_folders = self._build_folders_page()
        self.page_raport = self._build_raport_page()
        self.page_settings = self._build_settings_page()

        self.pages.addWidget(self.page_employee)
        self.pages.addWidget(self.page_folders)
        self.pages.addWidget(self.page_raport)
        self.pages.addWidget(self.page_settings)

        # Top actions
        tb = QtWidgets.QToolBar()
        tb.setMovable(False)
        self.addToolBar(QtCore.Qt.ToolBarArea.TopToolBarArea, tb)
        act_refresh = QtGui.QAction("Обновить", self)
        act_save = QtGui.QAction("Сохранить", self)
        tb.addAction(act_refresh)
        tb.addAction(act_save)
        act_refresh.triggered.connect(self.refresh)
        act_save.triggered.connect(self.save)

        # Signals
        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex)

        # First refresh
        self.refresh()

    # --- Pages ---
    def _build_employee_page(self):
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)

        title = QtWidgets.QLabel("Данные сотрудника")
        f = title.font()
        f.setPointSize(16)
        f.setBold(True)
        title.setFont(f)
        lay.addWidget(title)

        form = QtWidgets.QFormLayout()
        lay.addLayout(form)

        self.inp_fio = QtWidgets.QLineEdit()
        self.inp_discord = QtWidgets.QLineEdit()
        self.inp_pod = QtWidgets.QLineEdit()
        self.inp_dol = QtWidgets.QLineEdit()

        self.sel_cur = QtWidgets.QComboBox()
        self.sel_target = QtWidgets.QComboBox()
        for name, _ in RANKS:
            self.sel_cur.addItem(name)
            self.sel_target.addItem(name)

        form.addRow("ФИО", self.inp_fio)
        form.addRow("Discord ID", self.inp_discord)
        form.addRow("Подразделение", self.inp_pod)
        form.addRow("Должность", self.inp_dol)
        form.addRow("Текущее звание", self.sel_cur)
        form.addRow("Повышение до", self.sel_target)

        lay.addStretch(1)
        return w

    def _build_folders_page(self):
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)

        title = QtWidgets.QLabel("Папки и подсчёт")
        f = title.font()
        f.setPointSize(16)
        f.setBold(True)
        title.setFont(f)
        lay.addWidget(title)

        row = QtWidgets.QHBoxLayout()
        lay.addLayout(row)
        self.inp_root = QtWidgets.QLineEdit()
        btn_pick = QtWidgets.QPushButton("Выбрать папку")
        row.addWidget(QtWidgets.QLabel("Папка со скринами"))
        row.addWidget(self.inp_root, 1)
        row.addWidget(btn_pick)

        btn_pick.clicked.connect(self.pick_root_folder)

        self.table = QtWidgets.QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Категория (папка)", "Подтверждений (файлов)", "Баллы за 1", "Итого"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        lay.addWidget(self.table, 1)

        self.lbl_total = QtWidgets.QLabel("Итого: 0 баллов")
        ft = self.lbl_total.font()
        ft.setPointSize(14)
        ft.setBold(True)
        self.lbl_total.setFont(ft)
        lay.addWidget(self.lbl_total)

        return w

    def _build_raport_page(self):
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)

        title = QtWidgets.QLabel("Рапорт")
        f = title.font()
        f.setPointSize(16)
        f.setBold(True)
        title.setFont(f)
        lay.addWidget(title)

        self.txt_raport = QtWidgets.QPlainTextEdit()
        self.txt_raport.setReadOnly(True)
        lay.addWidget(self.txt_raport, 1)

        btns = QtWidgets.QHBoxLayout()
        lay.addLayout(btns)
        btn_copy = QtWidgets.QPushButton("Скопировать")
        btn_export = QtWidgets.QPushButton("Сохранить в файл…")
        btns.addWidget(btn_copy)
        btns.addWidget(btn_export)
        btns.addStretch(1)

        btn_copy.clicked.connect(lambda: QtWidgets.QApplication.clipboard().setText(self.txt_raport.toPlainText()))
        btn_export.clicked.connect(self.export_raport)

        return w

    def _build_settings_page(self):
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)

        title = QtWidgets.QLabel("Настройки")
        f = title.font()
        f.setPointSize(16)
        f.setBold(True)
        title.setFont(f)
        lay.addWidget(title)

        note = QtWidgets.QLabel(
            "Категории считаются по подпапкам в выбранной папке.\n"
            "Имена папок сейчас: " + ", ".join(CATEGORIES.keys()) + "\n\n"
            "ДТП и пост 30 минут намеренно НЕ учитываются (по твоей просьбе)."
        )
        note.setWordWrap(True)
        lay.addWidget(note)

        lay.addStretch(1)
        return w

    # --- Actions ---
    def pick_root_folder(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(self, "Выбери папку со скринами")
        if d:
            self.inp_root.setText(d)
            self.refresh()

    def export_raport(self):
        suggested = f"raport_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Сохранить рапорт", suggested, "Text (*.txt)")
        if not path:
            return
        Path(path).write_text(self.txt_raport.toPlainText(), encoding="utf-8")

    def _sync_ui_from_cfg(self):
        emp = self.cfg.get("employee", {})
        self.inp_root.setText(self.cfg.get("root_folder", ""))

        self.inp_fio.setText(emp.get("fio", ""))
        self.inp_discord.setText(emp.get("discord_id", ""))
        self.inp_pod.setText(emp.get("podrazdelenie", ""))
        self.inp_dol.setText(emp.get("dolzhnost", ""))

        cur = emp.get("current_rank", RANKS[0][0])
        target = emp.get("target_rank", RANKS[-1][0])

        self.sel_cur.setCurrentText(cur)
        self.sel_target.setCurrentText(target)

    def _sync_cfg_from_ui(self):
        self.cfg["root_folder"] = self.inp_root.text().strip()
        self.cfg.setdefault("employee", {})
        emp = self.cfg["employee"]
        emp["fio"] = self.inp_fio.text().strip()
        emp["discord_id"] = self.inp_discord.text().strip()
        emp["podrazdelenie"] = self.inp_pod.text().strip()
        emp["dolzhnost"] = self.inp_dol.text().strip()
        emp["current_rank"] = self.sel_cur.currentText()
        emp["target_rank"] = self.sel_target.currentText()

    def save(self):
        self._sync_cfg_from_ui()
        save_config(self.cfg_path, self.cfg)

    def refresh(self):
        # Load cfg into UI first (first run)
        self._sync_ui_from_cfg()
        self._sync_cfg_from_ui()

        root_str = self.cfg.get("root_folder", "").strip()
        root = Path(root_str) if root_str else None

        lines: list[CalcLine] = []
        total = 0
        if root and root.exists():
            lines, total = calc_points(root)

        # update table
        self.table.setRowCount(len(lines))
        for i, ln in enumerate(lines):
            self.table.setItem(i, 0, QtWidgets.QTableWidgetItem(f"{ln.label}  ({ln.key})"))
            self.table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(ln.confirmations)))
            self.table.setItem(i, 2, QtWidgets.QTableWidgetItem(str(ln.points_per)))
            self.table.setItem(i, 3, QtWidgets.QTableWidgetItem(str(ln.points)))

        self.lbl_total.setText(f"Итого: {total} баллов")

        # raport
        self.txt_raport.setPlainText(build_raport(self.cfg, total))


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
