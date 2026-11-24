import os, json
from pathlib import Path
import fitz
from PySide6.QtCore import Qt, QSize, QSettings
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QFileDialog, QScrollArea, QSlider, QListWidget, QListWidgetItem,
    QMessageBox, QSpinBox, QSplitter
)

class ReaderWidget(QWidget):
    """Local-first PDF reader widget: page render, thumbnails, navigation, zoom, and search."""
    def __init__(self, language="ar", parent=None):
        super().__init__(parent)
        self.language = language
        self.doc = None
        self.path = ""
        self.page_index = 0
        self.zoom = 1.25
        self.rotation = 0  # Viewer-only; never alters the source PDF.
        self.settings = QSettings("RedaDZ19", "WARAKA")
        self._search_hits = []
        self._hit_cursor = -1
        self._last_search_phrase = ""
        self.build_ui()
        self.set_language(language)

    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        toolbar = QHBoxLayout()
        self.open_btn = QPushButton()
        self.open_btn.clicked.connect(self.open_file)
        self.prev_btn = QPushButton("◀")
        self.prev_btn.clicked.connect(self.previous_page)
        self.next_btn = QPushButton("▶")
        self.next_btn.clicked.connect(self.next_page)
        self.page_spin = QSpinBox()
        self.page_spin.setRange(1, 1)
        self.page_spin.valueChanged.connect(self.go_page)
        self.page_count = QLabel("/ 0")
        self.zoom_out = QPushButton("−")
        self.zoom_out.clicked.connect(lambda: self.set_zoom(self.zoom - 0.15))
        self.zoom_label = QLabel("125%")
        self.zoom_in = QPushButton("+")
        self.zoom_in.clicked.connect(lambda: self.set_zoom(self.zoom + 0.15))
        self.fit_width = QPushButton()
        self.fit_width.clicked.connect(self.fit_to_width)
        self.rotate_left = QPushButton('↶')
        self.rotate_left.setToolTip('Rotate left / تدوير لليسار')
        self.rotate_left.clicked.connect(lambda: self.rotate_page(-90))
        self.rotate_right = QPushButton('↷')
        self.rotate_right.setToolTip('Rotate right / تدوير لليمين')
        self.rotate_right.clicked.connect(lambda: self.rotate_page(90))
        self.search_edit = QLineEdit()
        self.search_edit.returnPressed.connect(self.search_next)
        self.search_next_btn = QPushButton()
        self.search_next_btn.clicked.connect(self.search_next)
        self.search_prev_btn = QPushButton()
        self.search_prev_btn.clicked.connect(self.search_previous)
        for w in [self.open_btn, self.prev_btn, self.page_spin, self.page_count, self.next_btn,
                  self.zoom_out, self.zoom_label, self.zoom_in, self.fit_width,
                  self.rotate_left, self.rotate_right, self.search_edit, self.search_prev_btn, self.search_next_btn]:
            toolbar.addWidget(w)
        toolbar.addStretch(1)
        root.addLayout(toolbar)

        splitter = QSplitter(Qt.Horizontal)
        self.thumbnails = QListWidget()
        self.thumbnails.setMaximumWidth(190)
        self.thumbnails.setMinimumWidth(130)
        self.thumbnails.setIconSize(QSize(92, 130))
        self.thumbnails.setSpacing(5)
        self.thumbnails.currentRowChanged.connect(self.thumbnail_selected)
        self.thumbnails.verticalScrollBar().valueChanged.connect(self.refresh_visible_thumbnails)
        self._thumbnail_ready = set()
        splitter.addWidget(self.thumbnails)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setAlignment(Qt.AlignCenter)
        self.page_view = QLabel()
        self.page_view.setAlignment(Qt.AlignCenter)
        self.page_view.setStyleSheet("background:#dfe6ed;padding:12px;color:#718096;font-size:16pt")
        self.page_view.setText("افتح ملف PDF للبدء بالقراءة")
        self.scroll.setWidget(self.page_view)
        splitter.addWidget(self.scroll)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, 1)
        # Keyboard shortcuts (no plain arrow keys to preserve text-field behavior).
        self.shortcut_open = QShortcut(QKeySequence.Open, self)
        self.shortcut_open.activated.connect(self.open_file)
        self.shortcut_search = QShortcut(QKeySequence.Find, self)
        self.shortcut_search.activated.connect(self.focus_search)
        self.shortcut_next_page = QShortcut(QKeySequence('PageDown'), self)
        self.shortcut_next_page.activated.connect(self.next_page)
        self.shortcut_prev_page = QShortcut(QKeySequence('PageUp'), self)
        self.shortcut_prev_page.activated.connect(self.previous_page)
        self.shortcut_first_page = QShortcut(QKeySequence('Home'), self)
        self.shortcut_first_page.activated.connect(self.first_page)
        self.shortcut_last_page = QShortcut(QKeySequence('End'), self)
        self.shortcut_last_page.activated.connect(self.last_page)
        self.shortcut_zoom_in = QShortcut(QKeySequence('Ctrl++'), self)
        self.shortcut_zoom_in.activated.connect(lambda: self.set_zoom(self.zoom + 0.15))
        self.shortcut_zoom_out = QShortcut(QKeySequence('Ctrl+-'), self)
        self.shortcut_zoom_out.activated.connect(lambda: self.set_zoom(self.zoom - 0.15))
        self.empty = QLabel()
        self.empty.setAlignment(Qt.AlignCenter)
        self.empty.setStyleSheet("color:#718096;font-size:16pt;padding:40px")
        self.empty.setVisible(False)

    def set_language(self, language):
        self.language = language
        ar = language == "ar"
        self.open_btn.setText("فتح ملف PDF" if ar else "Open PDF")
        self.fit_width.setText("ملاءمة العرض" if ar else "Fit width")
        self.search_edit.setPlaceholderText("بحث داخل الملف…" if ar else "Search in PDF…")
        self.search_prev_btn.setText("السابق" if ar else "Previous")
        self.search_next_btn.setText("التالي" if ar else "Next")
        self.page_view.setText("افتح ملف PDF للبدء بالقراءة" if ar else "Open a PDF to start reading")
        self.setLayoutDirection(Qt.RightToLeft if ar else Qt.LeftToRight)

    def open_file(self, path=None):
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF files (*.pdf)")
        if not path:
            return
        try:
            new_doc = fitz.open(path)
            if not new_doc.page_count:
                raise ValueError("This PDF contains no pages.")
            if self.doc:
                self.doc.close()
            self.doc, self.path = new_doc, path
            self.rotation = 0
            self.page_view.setText("")
            self._search_hits = []
            self._hit_cursor = -1
            self._last_search_phrase = ""
            self.page_spin.setRange(1, self.doc.page_count)
            self.page_count.setText(f"/ {self.doc.page_count}")
            saved = int(self.settings.value("last_page/" + path, 0))
            self.page_index = max(0, min(saved, self.doc.page_count - 1))
            self.build_thumbnails()
            self.render_page()
        except Exception as e:
            QMessageBox.warning(self, "WARAKA", str(e))

    def build_thumbnails(self):
        self.thumbnails.blockSignals(True)
        self.thumbnails.clear()
        self._thumbnail_ready = set()
        if not self.doc:
            self.thumbnails.blockSignals(False)
            return
        # Placeholders are cheap; thumbnails are rendered only for visible rows.
        for i in range(self.doc.page_count):
            item = QListWidgetItem(str(i + 1))
            item.setSizeHint(QSize(115, 158))
            item.setTextAlignment(Qt.AlignHCenter)
            self.thumbnails.addItem(item)
        self.thumbnails.setCurrentRow(self.page_index)
        self.thumbnails.blockSignals(False)
        self.refresh_visible_thumbnails()

    def refresh_visible_thumbnails(self, *_):
        if not self.doc or not self.thumbnails.count():
            return
        first = self.thumbnails.indexAt(self.thumbnails.viewport().rect().topLeft()).row()
        if first < 0:
            first = max(0, self.page_index - 3)
        last = min(self.thumbnails.count() - 1, first + 12)
        keep = set(range(first, last + 1))
        # Clear off-screen icons so thumbnail memory stays bounded.
        for idx in self._thumbnail_ready - keep:
            item = self.thumbnails.item(idx)
            if item:
                item.setIcon(QIcon())
        self._thumbnail_ready.intersection_update(keep)
        for idx in keep - self._thumbnail_ready:
            page = self.doc.load_page(idx)
            rect = page.rect
            scale = min(0.16, 100.0 / max(rect.width, rect.height))
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888).copy()
            item = self.thumbnails.item(idx)
            if item:
                item.setIcon(QIcon(QPixmap.fromImage(image)))
                self._thumbnail_ready.add(idx)

    def render_page(self):
        if not self.doc:
            return
        page = self.doc.load_page(self.page_index)
        matrix = fitz.Matrix(self.zoom, self.zoom).prerotate(self.rotation)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888).copy()
        pixmap = QPixmap.fromImage(image)
        if self._search_hits and 0 <= self._hit_cursor < len(self._search_hits):
            hit_page, hit_rect = self._search_hits[self._hit_cursor]
            if hit_page == self.page_index:
                painter = QPainter(pixmap)
                pen = QPen(Qt.red, max(2, int(2.5 * self.zoom)))
                painter.setPen(pen)
                transformed = hit_rect * matrix
                painter.drawRect(int(transformed.x0), int(transformed.y0),
                               max(2, int(transformed.width)), max(2, int(transformed.height)))
                painter.end()
        self.page_view.setPixmap(pixmap)
        self.page_spin.blockSignals(True)
        self.page_spin.setValue(self.page_index + 1)
        self.page_spin.blockSignals(False)
        self.zoom_label.setText(f"{int(self.zoom * 100)}%")
        self.thumbnails.blockSignals(True)
        self.thumbnails.setCurrentRow(self.page_index)
        self.thumbnails.blockSignals(False)
        self.settings.setValue("last_page/" + self.path, self.page_index)

    def focus_search(self):
        self.search_edit.setFocus()
        self.search_edit.selectAll()

    def first_page(self):
        if self.doc:
            self.page_index = 0
            self.render_page()

    def last_page(self):
        if self.doc:
            self.page_index = self.doc.page_count - 1
            self.render_page()

    def go_page(self, value):
        if self.doc:
            self.page_index = max(0, min(value - 1, self.doc.page_count - 1))
            self.render_page()

    def previous_page(self):
        if self.doc and self.page_index > 0:
            self.page_index -= 1
            self.render_page()

    def next_page(self):
        if self.doc and self.page_index < self.doc.page_count - 1:
            self.page_index += 1
            self.render_page()

    def thumbnail_selected(self, row):
        if self.doc and row >= 0 and row != self.page_index:
            self.page_index = row
            self.render_page()

    def set_zoom(self, value):
        self.zoom = max(0.35, min(4.0, value))
        self.render_page()

    def fit_to_width(self):
        if not self.doc:
            return
        page = self.doc.load_page(self.page_index)
        available = max(200, self.scroll.viewport().width() - 40)
        page_width = page.rect.width if self.rotation % 180 == 0 else page.rect.height
        self.zoom = max(0.35, min(4.0, available / page_width))
        self.render_page()

    def rotate_page(self, degrees):
        if not self.doc:
            return
        self.rotation = (self.rotation + degrees) % 360
        self.fit_to_width()

    def search_next(self):
        self._search(True)

    def search_previous(self):
        self._search(False)

    def _search(self, forward=True):
        if not self.doc:
            return
        phrase = self.search_edit.text().strip()
        if not phrase:
            return
        # Re-scan only when the search phrase changes; next/previous reuses cached hits.
        if phrase != self._last_search_phrase:
            self._search_hits = []
            self._hit_cursor = -1
            self._last_search_phrase = phrase
            for i in range(self.doc.page_count):
                for rect in self.doc.load_page(i).search_for(phrase):
                    self._search_hits.append((i, rect))
        if not self._search_hits:
            self._hit_cursor = -1
            QMessageBox.information(self, "WARAKA", "No matches found." if self.language == "en" else "لم يتم العثور على نتائج.")
            return
        if self._hit_cursor < 0:
            self._hit_cursor = 0 if forward else len(self._search_hits) - 1
        else:
            self._hit_cursor = (self._hit_cursor + (1 if forward else -1)) % len(self._search_hits)
        page_num, rect = self._search_hits[self._hit_cursor]
        self.page_index = page_num
        self.render_page()
        # Scroll to the hit position in the rotated rendering coordinate system.
        search_matrix = fitz.Matrix(self.zoom, self.zoom).prerotate(self.rotation)
        transformed_rect = rect * search_matrix
        scaled_y = transformed_rect.y0
        self.scroll.verticalScrollBar().setValue(max(0, int(scaled_y - 80)))
