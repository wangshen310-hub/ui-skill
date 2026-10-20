"""Native local shooting notes. No network services or HTML."""
from __future__ import annotations

import argparse
import copy
import errno
import json
import os
from pathlib import Path
import tempfile
from datetime import datetime

from PySide6.QtCore import Qt, QSize, QRect, QTimer
from PySide6.QtGui import QColor, QFont, QKeySequence, QPainter, QPen, QShortcut
from PySide6.QtWidgets import (
    QApplication, QAbstractItemView, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QPlainTextEdit, QPushButton, QSizePolicy, QStackedWidget, QStyledItemDelegate,
    QStyle, QVBoxLayout, QWidget,
)

HERE = Path(__file__).resolve().parent


class DraftStore:
    def __init__(self, directory: Path):
        self.directory = directory
        self.path = directory / "projects.json"

    def read(self):
        if not self.path.exists():
            self.directory.mkdir(parents=True, exist_ok=True)
            samples = json.loads((HERE / "samples.json").read_text(encoding="utf-8"))
            self.write(samples["projects"])
        data = json.loads(self.path.read_text(encoding="utf-8"))
        projects = data["projects"]
        if data.get("schema") != 1 or not isinstance(projects, list):
            raise ValueError("项目文件格式不正确")
        identifiers = set()
        for p in projects:
            if not all(isinstance(p.get(k), str) for k in ("id", "title", "notes")):
                raise ValueError("项目标题或备注格式不正确")
            if p["id"] in identifiers:
                raise ValueError("项目编号重复")
            identifiers.add(p["id"])
        return projects

    def write(self, projects):
        # Write beside the destination then replace it atomically. A failed write
        # never changes the in-memory saved snapshot or reports success.
        raw = json.dumps({"schema": 1, "projects": projects}, ensure_ascii=False, indent=2) + "\n"
        name = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.directory,
                                             prefix=".projects-", suffix=".tmp", delete=False) as f:
                name = f.name
                f.write(raw)
                f.flush()
                os.fsync(f.fileno())
            os.replace(name, self.path)
            name = None
        finally:
            if name is not None:
                Path(name).unlink(missing_ok=True)


class ProjectDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        return QSize(400, 96)

    def paint(self, painter: QPainter, option, index):
        painter.save()
        box = option.rect
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        if selected:
            painter.fillRect(box, QColor("#E8EDE5"))
            painter.fillRect(QRect(box.left(), box.top() + 4, 3, box.height() - 8), QColor("#385748"))
        painter.setPen(QColor("#D5D7D0"))
        painter.drawLine(box.bottomLeft(), box.bottomRight())
        title, _, excerpt = index.data(Qt.ItemDataRole.DisplayRole).partition("\n")
        title_font = QFont("Noto Sans CJK SC")
        title_font.setPixelSize(20)
        title_font.setWeight(QFont.Weight.Medium)
        painter.setFont(title_font)
        painter.setPen(QColor("#272E2B"))
        title_rect = box.adjusted(32, 17, -55, -43)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignVCenter,
                         painter.fontMetrics().elidedText(title, Qt.TextElideMode.ElideRight, title_rect.width()))
        note_font = QFont("Noto Sans CJK SC")
        note_font.setPixelSize(14)
        painter.setFont(note_font)
        painter.setPen(QColor("#626A64"))
        note_rect = box.adjusted(32, 53, -55, -17)
        painter.drawText(note_rect, Qt.AlignmentFlag.AlignVCenter,
                         painter.fontMetrics().elidedText(excerpt, Qt.TextElideMode.ElideRight, note_rect.width()))
        painter.setPen(QPen(QColor("#626A64"), 1.6))
        x, y = box.right() - 27, box.center().y()
        painter.drawLine(x - 4, y - 7, x + 3, y)
        painter.drawLine(x + 3, y, x - 4, y + 7)
        if option.state & QStyle.StateFlag.State_HasFocus:
            painter.setPen(QPen(QColor("#385748"), 1, Qt.PenStyle.DotLine))
            painter.drawRect(box.adjusted(5, 5, -6, -6))
        painter.restore()


class NotesWindow(QMainWindow):
    def __init__(self, directory: Path):
        super().__init__()
        self.setObjectName("notesWindow")
        self.store = DraftStore(directory)
        self.projects = []
        self.current_id = None
        self.original = None
        self._loading = False
        self.save_error = ""
        self.setWindowTitle("拍摄备注")
        self.resize(1180, 780)
        self.setMinimumSize(640, 480)
        self.setStyleSheet(STYLE)
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self._build_list()
        self._build_editor()
        self._build_loading_error()
        self.save_shortcut = QShortcut(QKeySequence.StandardKey.Save, self)
        self.save_shortcut.activated.connect(self.save_draft)
        self.back_shortcut = QShortcut(QKeySequence("Alt+Left"), self)
        self.back_shortcut.activated.connect(self.back_to_list)
        self.escape_shortcut = QShortcut(QKeySequence("Escape"), self)
        self.escape_shortcut.activated.connect(self.back_to_list)
        self.load_projects()

    def _build_list(self):
        self.list_page = QWidget()
        self.list_outer = QVBoxLayout(self.list_page)
        self.list_outer.setContentsMargins(0, 0, 0, 0)
        self.list_outer.setSpacing(0)
        self.list_content = QWidget()
        self.list_body = QVBoxLayout(self.list_content)
        self.list_body.setContentsMargins(76, 54, 76, 30)
        self.list_body.setSpacing(0)
        heading = QLabel("拍摄项目")
        heading.setObjectName("pageHeading")
        subtitle = QLabel("本地示例项目 · 仅保存在此设备")
        subtitle.setObjectName("muted")
        self.list_body.addWidget(heading)
        self.list_body.addSpacing(8)
        self.list_body.addWidget(subtitle)
        self.list_body.addSpacing(30)
        self.project_list = QListWidget()
        self.project_list.setObjectName("projectList")
        self.project_list.setAccessibleName("拍摄项目清单")
        self.project_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.project_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.project_list.setItemDelegate(ProjectDelegate(self.project_list))
        self.project_list.itemActivated.connect(self.open_selected)
        self.project_list.itemDoubleClicked.connect(self.open_selected)
        self.project_list.currentRowChanged.connect(lambda _: self.open_button.setEnabled(self.project_list.currentRow() >= 0))
        self.list_body.addWidget(self.project_list, 1)
        self.list_outer.addWidget(self.list_content, 1)
        footer = QFrame()
        footer.setObjectName("footer")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(36, 18, 36, 18)
        hint = QLabel("↑ ↓ 选择 · Enter 打开")
        hint.setObjectName("muted")
        footer_layout.addWidget(hint)
        footer_layout.addStretch()
        self.open_button = QPushButton("打开项目")
        self.open_button.setObjectName("primary")
        self.open_button.clicked.connect(self.open_selected)
        footer_layout.addWidget(self.open_button)
        self.list_outer.addWidget(footer)
        self.stack.addWidget(self.list_page)

    def _build_editor(self):
        self.editor_page = QWidget()
        outer = QVBoxLayout(self.editor_page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.toolbar = QFrame()
        self.toolbar.setObjectName("toolbar")
        self.toolbar_layout = QGridLayout(self.toolbar)
        self.toolbar_layout.setContentsMargins(24, 14, 24, 14)
        self.toolbar_layout.setHorizontalSpacing(20)
        self.toolbar_layout.setVerticalSpacing(8)
        self.back_button = QPushButton("←  返回项目清单")
        self.back_button.setObjectName("quiet")
        self.back_button.setToolTip("返回项目清单（Alt+Left）")
        self.back_button.clicked.connect(self.back_to_list)
        self.save_button = QPushButton("保存草稿  Ctrl+S")
        self.save_button.setObjectName("primary")
        self.save_button.clicked.connect(self.save_draft)
        self.state_label = QLabel()
        self.state_label.setObjectName("saveState")
        self.state_label.setMinimumWidth(165)
        self.state_label.setAccessibleName("草稿保存状态")
        self.toolbar_layout.addWidget(self.back_button, 0, 0)
        self.toolbar_layout.setColumnStretch(1, 1)
        self.toolbar_layout.addWidget(self.save_button, 0, 2)
        self.toolbar_layout.addWidget(self.state_label, 0, 3)
        outer.addWidget(self.toolbar)
        self.error_frame = QFrame()
        self.error_frame.setObjectName("errorFrame")
        error_layout = QHBoxLayout(self.error_frame)
        error_layout.setContentsMargins(24, 13, 24, 13)
        self.error_label = QLabel()
        self.error_label.setObjectName("errorText")
        self.error_label.setWordWrap(True)
        self.error_label.setTextFormat(Qt.TextFormat.PlainText)
        error_layout.addWidget(self.error_label, 1)
        self.retry_button = QPushButton("重试保存")
        self.retry_button.setObjectName("retrySave")
        self.retry_button.clicked.connect(self.save_draft)
        error_layout.addWidget(self.retry_button)
        self.error_frame.hide()
        outer.addWidget(self.error_frame)
        self.editor_content = QWidget()
        self.editor_body = QVBoxLayout(self.editor_content)
        self.editor_body.setContentsMargins(76, 38, 76, 36)
        self.editor_body.setSpacing(10)
        title_label = QLabel("项目标题")
        self.title_edit = QLineEdit()
        self.title_edit.setObjectName("titleEdit")
        self.title_edit.setAccessibleName("项目标题")
        self.title_edit.setMaxLength(400)
        title_label.setBuddy(self.title_edit)
        self.editor_body.addWidget(title_label)
        self.editor_body.addWidget(self.title_edit)
        self.editor_body.addSpacing(13)
        notes_label = QLabel("拍摄备注")
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setObjectName("notesEdit")
        self.notes_edit.setAccessibleName("拍摄备注")
        self.notes_edit.setTabChangesFocus(True)
        notes_label.setBuddy(self.notes_edit)
        self.editor_body.addWidget(notes_label)
        self.editor_body.addWidget(self.notes_edit, 1)
        outer.addWidget(self.editor_content, 1)
        footer = QFrame()
        footer.setObjectName("footer")
        bottom = QHBoxLayout(footer)
        bottom.setContentsMargins(24, 12, 24, 12)
        location = QLabel("本地示例项目 · 仅保存在此设备")
        location.setObjectName("muted")
        location.setToolTip(str(self.store.path))
        bottom.addWidget(location)
        outer.addWidget(footer)
        self.title_edit.textChanged.connect(self.edited)
        self.notes_edit.textChanged.connect(self.edited)
        QWidget.setTabOrder(self.back_button, self.save_button)
        QWidget.setTabOrder(self.save_button, self.title_edit)
        QWidget.setTabOrder(self.title_edit, self.notes_edit)
        QWidget.setTabOrder(self.notes_edit, self.back_button)
        self.stack.addWidget(self.editor_page)

    def _build_loading_error(self):
        self.load_error_page = QWidget()
        layout = QVBoxLayout(self.load_error_page)
        layout.setContentsMargins(60, 60, 60, 60)
        layout.addStretch()
        title = QLabel("无法打开本地项目")
        title.setObjectName("pageHeading")
        layout.addWidget(title)
        self.load_error_label = QLabel()
        self.load_error_label.setWordWrap(True)
        self.load_error_label.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.load_error_label)
        row = QHBoxLayout()
        retry = QPushButton("重新读取")
        retry.clicked.connect(self.load_projects)
        close = QPushButton("关闭")
        close.clicked.connect(self.close)
        row.addWidget(retry)
        row.addWidget(close)
        row.addStretch()
        layout.addLayout(row)
        layout.addStretch()
        self.stack.addWidget(self.load_error_page)

    def load_projects(self):
        try:
            self.projects = self.store.read()
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.load_error_label.setText(f"未修改原文件。请检查项目文件后重新读取。\n{error}")
            self.stack.setCurrentWidget(self.load_error_page)
            return
        self.refresh_list(self.current_id)
        self.stack.setCurrentWidget(self.list_page)
        QTimer.singleShot(0, self.project_list.setFocus)

    def refresh_list(self, selected_id=None):
        previous = self.project_list.currentItem()
        if selected_id is None and previous:
            selected_id = previous.data(Qt.ItemDataRole.UserRole)
        self.project_list.clear()
        selected_row = 0
        for row, project in enumerate(self.projects):
            excerpt = next((line.strip() for line in project["notes"].splitlines() if line.strip()), "还没有拍摄备注")
            item = QListWidgetItem(project["title"] + "\n" + excerpt)
            item.setData(Qt.ItemDataRole.UserRole, project["id"])
            item.setToolTip(project["title"])
            self.project_list.addItem(item)
            if project["id"] == selected_id:
                selected_row = row
        if self.projects:
            self.project_list.setCurrentRow(selected_row)
        self.open_button.setEnabled(bool(self.projects))

    def open_selected(self, *_):
        if self.stack.currentWidget() is not self.list_page:
            return
        item = self.project_list.currentItem()
        if item is None:
            return
        self.current_id = item.data(Qt.ItemDataRole.UserRole)
        self.original = copy.deepcopy(next(p for p in self.projects if p["id"] == self.current_id))
        self._loading = True
        self.title_edit.setText(self.original["title"])
        self.title_edit.setCursorPosition(0)
        self.notes_edit.setPlainText(self.original["notes"])
        self.notes_edit.moveCursor(self.notes_edit.textCursor().MoveOperation.Start)
        self.notes_edit.verticalScrollBar().setValue(0)
        self._loading = False
        self.save_error = ""
        self.error_frame.hide()
        self.stack.setCurrentWidget(self.editor_page)
        self.update_state()
        self.title_edit.setFocus()

    def is_dirty(self):
        return bool(self.original is not None and (
            self.title_edit.text() != self.original["title"] or
            self.notes_edit.toPlainText() != self.original["notes"]))

    def edited(self):
        if not self._loading:
            self.update_state()

    def update_state(self):
        dirty = self.is_dirty()
        if self.save_error:
            self.state_label.setText("保存失败 · 修改未保存")
            self.state_label.setProperty("state", "error")
        elif dirty:
            self.state_label.setText("● 有未保存的修改")
            self.state_label.setProperty("state", "dirty")
        elif self.original and self.original.get("saved_at"):
            self.state_label.setText("已保存到本机 · " + self.original["saved_at"][11:16])
            self.state_label.setProperty("state", "saved")
        else:
            self.state_label.setText("本地示例 · 尚未修改")
            self.state_label.setProperty("state", "saved")
        self.state_label.style().unpolish(self.state_label)
        self.state_label.style().polish(self.state_label)
        self.setWindowTitle("拍摄备注" + (" · 未保存" if dirty else ""))

    def save_draft(self):
        if self.stack.currentWidget() is not self.editor_page or self.original is None:
            return False
        title = self.title_edit.text().strip()
        if not title:
            self.error_label.setText("请填写项目标题，当前修改尚未保存。")
            self.error_frame.show()
            self.title_edit.setFocus()
            return False
        candidate = copy.deepcopy(self.projects)
        project = next(p for p in candidate if p["id"] == self.current_id)
        project.update(title=title, notes=self.notes_edit.toPlainText(), saved_at=datetime.now().astimezone().isoformat(timespec="seconds"))
        try:
            self.store.write(candidate)
        except OSError as error:
            self.save_error = str(error)
            reasons = {
                errno.EISDIR: "保存位置被同名文件夹占用。移走该文件夹后重试。",
                errno.EACCES: "没有写入权限。检查保存文件夹的权限后重试。",
                errno.EPERM: "没有写入权限。检查保存文件夹的权限后重试。",
                errno.EROFS: "保存位置只读。恢复写入权限后重试。",
                errno.ENOSPC: "设备空间不足。清出一些空间后重试。",
                errno.ENOENT: "保存文件夹不存在。恢复文件夹后重试。",
            }
            reason = reasons.get(error.errno, "请检查本地保存位置，然后重试。")
            self.error_label.setText("草稿未保存，修改仍保留在编辑器中。\n" + reason)
            self.error_label.setToolTip(str(self.store.path) + "\n" + self.save_error)
            self.error_frame.show()
            self.update_state()
            return False
        self.projects = candidate
        self.original = copy.deepcopy(project)
        self._loading = True
        cursor = self.title_edit.cursorPosition()
        self.title_edit.setText(title)
        self.title_edit.setCursorPosition(min(cursor, len(title)))
        self._loading = False
        self.save_error = ""
        self.error_frame.hide()
        self.update_state()
        return True

    def confirm_leave(self, closing=False):
        if not self.is_dirty():
            return True
        box = QMessageBox(self)
        box.setObjectName("unsavedDialog")
        box.setWindowTitle("有未保存的修改")
        box.setText("关闭前保存草稿？" if closing else "返回清单前保存草稿？")
        box.setInformativeText("标题和拍摄备注的修改还未写入本机。放弃后将恢复上次保存的内容。")
        box.setIcon(QMessageBox.Icon.Warning)
        save = box.addButton("保存并关闭" if closing else "保存并返回", QMessageBox.ButtonRole.AcceptRole)
        discard = box.addButton("放弃修改", QMessageBox.ButtonRole.DestructiveRole)
        cancel = box.addButton("继续编辑", QMessageBox.ButtonRole.RejectRole)
        save.setObjectName("saveAndLeave")
        discard.setObjectName("discardChanges")
        cancel.setObjectName("continueEditing")
        box.setDefaultButton(cancel)
        box.setEscapeButton(cancel)
        box.exec()
        if box.clickedButton() is save:
            return self.save_draft()
        return box.clickedButton() is discard

    def back_to_list(self):
        if self.stack.currentWidget() is not self.editor_page:
            return
        prior_focus = QApplication.focusWidget()
        if not self.confirm_leave():
            if prior_focus:
                self.restore_focus(prior_focus)
            return
        selected = self.current_id
        self.original = None
        self.save_error = ""
        self.refresh_list(selected)
        self.stack.setCurrentWidget(self.list_page)
        self.setWindowTitle("拍摄备注")
        self.restore_focus(self.project_list)
        self.project_list.scrollToItem(self.project_list.currentItem())

    def restore_focus(self, widget):
        self.activateWindow()
        widget.setFocus(Qt.FocusReason.OtherFocusReason)
        QTimer.singleShot(0, widget.setFocus)

    def closeEvent(self, event):
        prior_focus = QApplication.focusWidget()
        if self.stack.currentWidget() is self.editor_page and not self.confirm_leave(closing=True):
            event.ignore()
            if prior_focus:
                self.restore_focus(prior_focus)
        else:
            event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not hasattr(self, "state_label"):
            return
        narrow = self.width() < 900
        margin = 24 if narrow else 76
        self.list_body.setContentsMargins(margin, 32 if narrow else 54, margin, 24)
        self.editor_body.setContentsMargins(margin, 24 if narrow else 38, margin, 24 if narrow else 36)
        self.toolbar_layout.removeWidget(self.state_label)
        if narrow:
            self.toolbar_layout.addWidget(self.state_label, 1, 0, 1, 4)
        else:
            self.toolbar_layout.addWidget(self.state_label, 0, 3)


STYLE = """
QWidget { background: #F6F4EF; color: #272E2B; font-family: 'Noto Sans CJK SC'; font-size: 16px; }
QLabel { background: transparent; }
QLabel#pageHeading { font-size: 30px; font-weight: 600; }
QLabel#muted { color: #626A64; font-size: 14px; }
QPushButton { border: 1px solid #BCC4BA; border-radius: 6px; padding: 10px 20px; min-height: 24px; background: #FAFBF7; }
QPushButton:hover { background: #E8EDE5; border-color: #758B78; }
QPushButton:pressed { background: #DDE5D9; }
QPushButton:focus { border: 2px solid #536D57; padding: 9px 19px; }
QPushButton:disabled { color: #8F968E; background: #E6E8E1; }
QPushButton#primary { background: #385748; color: white; border-color: #385748; }
QPushButton#primary:hover { background: #294B39; }
QPushButton#primary:focus { border: 2px solid #9FB69D; padding: 9px 19px; }
QPushButton#quiet { background: transparent; border-color: transparent; padding-left: 6px; padding-right: 6px; }
QPushButton#quiet:hover { background: #E8EDE5; }
QPushButton#quiet:focus { border-color: #536D57; padding-left: 5px; padding-right: 5px; }
QListWidget#projectList { border: none; outline: none; background: transparent; }
QLineEdit, QPlainTextEdit { background: #FFFFFF; border: 1px solid #BFC4BB; border-radius: 5px; selection-background-color: #C8DBC7; selection-color: #243329; }
QLineEdit:focus, QPlainTextEdit:focus { border: 2px solid #607D65; }
QLineEdit#titleEdit { font-size: 26px; font-weight: 500; padding: 12px 15px; min-height: 38px; }
QPlainTextEdit#notesEdit { font-size: 18px; padding: 15px; }
QFrame#toolbar { border-bottom: 1px solid #D5D7D0; }
QFrame#footer { border-top: 1px solid #D5D7D0; }
QLabel#saveState { font-size: 14px; color: #53665A; }
QLabel#saveState[state='dirty'] { color: #80611B; }
QLabel#saveState[state='error'] { color: #9C392B; }
QFrame#errorFrame { background: #FAEBE4; border-bottom: 1px solid #D8B4A7; }
QLabel#errorText { color: #8A3527; font-size: 14px; }
QMessageBox QLabel#qt_msgbox_label { min-width: 280px; }
QMessageBox QLabel#qt_msgbox_informativelabel { min-width: 280px; }
QScrollBar:vertical { width: 12px; background: #F0F0EA; }
QScrollBar::handle:vertical { background: #C8CFC4; min-height: 24px; border-radius: 5px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""


def main():
    parser = argparse.ArgumentParser(description="本地拍摄备注")
    parser.add_argument("--data-dir", type=Path, default=Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "shooting-notes")
    args = parser.parse_args()
    app = QApplication([])
    app.setStyle("Fusion")
    app.setApplicationName("拍摄备注")
    app.setOrganizationName("LocalStudio")
    window = NotesWindow(args.data_dir)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
