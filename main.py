import sys, os, re, json, urllib.request, tempfile, subprocess
from pathlib import Path
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QImage, QPixmap, QIcon
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QLineEdit, QComboBox, QSpinBox, QGroupBox,
    QMessageBox, QProgressBar, QCheckBox, QListWidget, QAbstractItemView,
    QScrollArea, QToolButton, QGridLayout)
from pypdf import PdfReader, PdfWriter
import fitz

APP_VERSION = "1.1.0"
GITHUB_LATEST_RELEASE = "https://api.github.com/repos/Redadz19/PDF-Splitter/releases/latest"

TEXT = {
 "ar": {
  "title":"مقسّم ملفات PDF", "subtitle":"تقسيم ملفات PDF بسهولة وعلى جهازك", "updates":"التحقق من التحديثات", "up_to_date":"أنت تستخدم أحدث إصدار.", "update_found":"يتوفر إصدار جديد: ", "update_confirm":"هل تريد تنزيل التحديث وتطبيقه الآن؟", "update_error":"تعذر التحقق من التحديثات: ", "updater_missing":"ملف التحديث غير موجود. أعد تثبيت أحدث نسخة كاملة.",
  "add":"إضافة ملفات PDF", "remove":"إزالة المحدد", "clear":"مسح القائمة",
  "files":"الملفات المحددة", "mode":"طريقة التقسيم", "ranges":"حسب نطاقات الصفحات",
  "fixed":"عدد صفحات ثابت لكل ملف", "each":"كل صفحة في ملف مستقل",
  "parts":"تقسيم إلى عدد أجزاء", "selected":"الصفحات المحددة من المعاينة",
  "preview":"معاينة الصفحات — انقر لتحديد الصفحات", "no_preview":"اختر ملفاً لعرض صفحاته هنا",
  "range":"نطاقات الصفحات (مثال: 1-3, 5, 8-10)", "size":"عدد الصفحات في كل ملف", "parts_n":"عدد الأجزاء",
  "out":"مجلد الحفظ", "browse":"استعراض", "start":"بدء التقسيم",
  "status":"جاهز", "done":"اكتمل التقسيم بنجاح.", "error":"خطأ",
  "empty":"أضف ملف PDF واحداً على الأقل.", "folder":"اختر مجلد الحفظ",
  "invalid":"تحقق من نطاق الصفحات أو حدد صفحات من المعاينة.",
  "pages":"صفحة", "output":"مجلد الإخراج غير محدد.",
  "finished":"تم إنشاء الملفات في:", "overwrite":"إضافة رقم تسلسلي عند تكرار أسماء الملفات",
  "select":"اختر ملفات PDF", "badpdf":"تعذر فتح الملف: ", "selected_count":"صفحة محددة"
 },
 "en": {
  "title":"PDF Splitter", "subtitle":"Split PDF files easily — processed locally on your computer", "updates":"Check for updates", "up_to_date":"You are using the latest version.", "update_found":"A new version is available: ", "update_confirm":"Download and install this update now?", "update_error":"Could not check for updates: ", "updater_missing":"Updater is missing. Install the latest full version again.",
  "add":"Add PDF files", "remove":"Remove selected", "clear":"Clear list",
  "files":"Selected files", "mode":"Splitting method", "ranges":"By page ranges",
  "fixed":"Fixed pages per file", "each":"Each page as a separate file",
  "parts":"Split into number of parts", "selected":"Selected pages from preview",
  "preview":"Page preview — click thumbnails to select", "no_preview":"Choose a file to preview its pages",
  "range":"Page ranges (e.g. 1-3, 5, 8-10)", "size":"Pages per file", "parts_n":"Number of parts",
  "out":"Output folder", "browse":"Browse", "start":"Start splitting",
  "status":"Ready", "done":"Splitting completed successfully.", "error":"Error",
  "empty":"Add at least one PDF file.", "folder":"Choose output folder",
  "invalid":"Check the page ranges or select pages in the preview.",
  "pages":"pages", "output":"Output folder is not selected.",
  "finished":"Files created in:", "overwrite":"Add a sequence number if filenames repeat",
  "select":"Select PDF files", "badpdf":"Could not open file: ", "selected_count":"selected"
 }
}

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.lang = "ar"
        self.paths = []
        self.selected_pages = {}
        self.resize(1380, 900)
        self.setMinimumSize(1100, 720)
        self.setStyleSheet("""
        QMainWindow,QWidget { background:#f4f7fb; color:#17243a; font-family:'Segoe UI'; font-size:10.5pt; }
        QGroupBox { background:white; border:1px solid #dce4ef; border-radius:12px; margin-top:12px; padding:12px; font-weight:600; }
        QGroupBox::title { subcontrol-origin:margin; left:14px; padding:0 5px; }
        QPushButton { background:#1769aa; color:white; border:0; border-radius:8px; padding:9px 15px; font-weight:600; }
        QPushButton:hover { background:#0f568f; }
        QPushButton:disabled { background:#aab8c8; }
        QLineEdit,QComboBox,QSpinBox,QListWidget { background:white; border:1px solid #d4deea; border-radius:7px; padding:7px; }
        QProgressBar { border:0; background:#e2eaf3; border-radius:5px; height:10px; text-align:center; }
        QProgressBar::chunk { background:#22a06b; border-radius:5px; }
        """)
        self.build_ui()
        self.retranslate()

    def tr(self, key):
        return TEXT[self.lang][key]

    def build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(9)

        top = QHBoxLayout()
        self.heading = QLabel()
        self.heading.setStyleSheet("font-size:23pt;font-weight:700;color:#123b63")
        top.addWidget(self.heading)
        top.addStretch()
        self.update_button = QPushButton()
        self.update_button.clicked.connect(self.check_updates)
        top.addWidget(self.update_button)
        self.language = QComboBox()
        self.language.addItem("العربية", "ar")
        self.language.addItem("English", "en")
        self.language.currentIndexChanged.connect(self.change_language)
        top.addWidget(self.language)
        layout.addLayout(top)

        self.sub = QLabel()
        self.sub.setStyleSheet("color:#63758b")
        layout.addWidget(self.sub)

        # Main workspace is explicitly left-to-right: preview left, settings right.
        workspace = QWidget()
        workspace.setLayoutDirection(Qt.LeftToRight)
        columns = QHBoxLayout(workspace)
        columns.setContentsMargins(0, 0, 0, 0)
        columns.setSpacing(14)

        self.preview_box = QGroupBox()
        self.preview_box.setMinimumWidth(560)
        preview_layout = QVBoxLayout(self.preview_box)
        self.preview_file = QComboBox()
        self.preview_file.currentIndexChanged.connect(self.render_preview)
        preview_layout.addWidget(self.preview_file)
        self.preview_hint = QLabel()
        self.preview_hint.setStyleSheet("color:#63758b")
        preview_layout.addWidget(self.preview_hint)
        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidgetResizable(True)
        self.preview_scroll.setMinimumHeight(500)
        self.preview_content = QWidget()
        self.preview_grid = QGridLayout(self.preview_content)
        self.preview_grid.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.preview_grid.setSpacing(10)
        self.preview_scroll.setWidget(self.preview_content)
        preview_layout.addWidget(self.preview_scroll, 1)

        sidebar = QWidget()
        sidebar.setMinimumWidth(340)
        sidebar.setMaximumWidth(480)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(0, 0, 0, 0)
        side.setSpacing(8)

        self.filebox = QGroupBox()
        file_layout = QVBoxLayout(self.filebox)
        file_buttons = QHBoxLayout()
        self.add = QPushButton()
        self.add.clicked.connect(self.add_files)
        self.remove = QPushButton()
        self.remove.clicked.connect(self.remove_selected)
        self.clear = QPushButton()
        self.clear.clicked.connect(self.clear_files)
        file_buttons.addWidget(self.add)
        file_buttons.addWidget(self.remove)
        file_buttons.addWidget(self.clear)
        file_layout.addLayout(file_buttons)
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.file_list.setMinimumHeight(100)
        self.file_list.setMaximumHeight(170)
        file_layout.addWidget(self.file_list)
        side.addWidget(self.filebox)

        self.options = QGroupBox()
        options_layout = QVBoxLayout(self.options)
        mode_row = QHBoxLayout()
        self.mode_label = QLabel()
        mode_row.addWidget(self.mode_label)
        self.mode = QComboBox()
        mode_row.addWidget(self.mode, 1)
        options_layout.addLayout(mode_row)
        self.mode.currentIndexChanged.connect(self.mode_changed)

        self.range_row = QHBoxLayout()
        self.range_label = QLabel()
        self.ranges = QLineEdit()
        self.range_row.addWidget(self.range_label)
        self.range_row.addWidget(self.ranges, 1)
        options_layout.addLayout(self.range_row)

        self.spin_row = QHBoxLayout()
        self.spin_label = QLabel()
        self.spin = QSpinBox()
        self.spin.setRange(1, 100000)
        self.spin.setValue(10)
        self.spin_row.addWidget(self.spin_label)
        self.spin_row.addWidget(self.spin)
        self.spin_row.addStretch()
        options_layout.addLayout(self.spin_row)
        side.addWidget(self.options)

        output_box = QGroupBox()
        output_layout = QVBoxLayout(output_box)
        self.out_label = QLabel()
        output_layout.addWidget(self.out_label)
        output_row = QHBoxLayout()
        self.output = QLineEdit()
        self.browse = QPushButton()
        self.browse.clicked.connect(self.choose_output)
        output_row.addWidget(self.output, 1)
        output_row.addWidget(self.browse)
        output_layout.addLayout(output_row)
        side.addWidget(output_box)

        self.unique = QCheckBox()
        self.unique.setChecked(True)
        side.addWidget(self.unique)
        side.addStretch(1)

        columns.addWidget(self.preview_box, 7)
        columns.addWidget(sidebar, 4)
        layout.addWidget(workspace, 1)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        bottom = QHBoxLayout()
        self.status = QLabel()
        self.start = QPushButton()
        self.start.setMinimumWidth(180)
        self.start.clicked.connect(self.run_split)
        bottom.addWidget(self.status, 1)
        bottom.addWidget(self.start)
        layout.addLayout(bottom)

    def retranslate(self):
        t=self.tr
        self.setWindowTitle(t("title")); self.heading.setText("PDF Splitter" if self.lang=="en" else "PDF Splitter | مقسّم PDF")
        self.sub.setText(t("subtitle")); self.update_button.setText(t("updates")); self.filebox.setTitle(t("files")); self.preview_box.setTitle(t("preview"))
        self.add.setText(t("add")); self.remove.setText(t("remove")); self.clear.setText(t("clear"))
        self.preview_hint.setText(t("no_preview")); self.options.setTitle(t("mode")); self.mode_label.setText(t("mode")+":")
        current=self.mode.currentData() if self.mode.count() else "ranges"
        self.mode.blockSignals(True); self.mode.clear()
        for key in ("ranges","fixed","each","parts","selected"):
            self.mode.addItem(t(key),key)
        self.mode.setCurrentIndex(max(0,self.mode.findData(current))); self.mode.blockSignals(False)
        self.range_label.setText(t("range")); self.spin_label.setText(t("size"))
        self.out_label.setText(t("out")); self.browse.setText(t("browse")); self.unique.setText(t("overwrite"))
        self.start.setText(t("start")); self.status.setText(t("status")); self.mode_changed()

    def check_updates(self):
        try:
            request = urllib.request.Request(
                GITHUB_LATEST_RELEASE,
                headers={"User-Agent": "PDF-Splitter-Updater", "Accept": "application/vnd.github+json"}
            )
            with urllib.request.urlopen(request, timeout=12) as response:
                release = json.loads(response.read().decode("utf-8"))
            latest = str(release.get("tag_name", "")).lstrip("v")
            def version_tuple(value):
                return tuple(int(part) for part in re.findall(r"\d+", value)[:3])
            if not latest or version_tuple(latest) <= version_tuple(APP_VERSION):
                QMessageBox.information(self, self.tr("title"), self.tr("up_to_date"))
                return
            answer = QMessageBox.question(
                self, self.tr("title"),
                self.tr("update_found") + latest + "\n" + self.tr("update_confirm"),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )
            if answer != QMessageBox.Yes:
                return
            assets = release.get("assets", [])
            asset = next((item for item in assets if item.get("name") == "PDF-Splitter-Update.zip"), None)
            if not asset:
                raise RuntimeError("Update package is not attached to this release.")
            updater = Path(sys.executable).resolve().parent / "PDF Splitter Updater.exe"
            if not updater.exists():
                QMessageBox.warning(self, self.tr("title"), self.tr("updater_missing"))
                return
            self.update_button.setEnabled(False)
            self.status.setText(self.tr("update_found") + latest)
            QApplication.processEvents()
            fd, package_path = tempfile.mkstemp(prefix="pdfsplitter-update-", suffix=".zip")
            os.close(fd)
            download_request = urllib.request.Request(
                asset["browser_download_url"], headers={"User-Agent": "PDF-Splitter-Updater"}
            )
            with urllib.request.urlopen(download_request, timeout=60) as response, open(package_path, "wb") as target:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    target.write(chunk)
            subprocess.Popen([
                str(updater), "--pid", str(os.getpid()),
                "--app-dir", str(Path(sys.executable).resolve().parent),
                "--package", package_path
            ], close_fds=True)
            self.close()
        except Exception as exc:
            self.update_button.setEnabled(True)
            QMessageBox.warning(self, self.tr("title"), self.tr("update_error") + str(exc))

    def change_language(self):
        self.lang=self.language.currentData()
        self.setLayoutDirection(Qt.RightToLeft if self.lang=="ar" else Qt.LeftToRight)
        self.retranslate(); self.refresh_file_labels(); self.render_preview()

    def refresh_file_labels(self):
        for i,path in enumerate(self.paths):
            try: count=len(PdfReader(path).pages)
            except Exception: count=0
            self.file_list.item(i).setText(f"{Path(path).name} — {count} {self.tr('pages')}")

    def mode_changed(self):
        mode=self.mode.currentData()
        self.range_label.setVisible(mode=="ranges"); self.ranges.setVisible(mode=="ranges")
        self.spin_label.setVisible(mode in ("fixed","parts")); self.spin.setVisible(mode in ("fixed","parts"))
        self.spin_label.setText(self.tr("parts_n") if mode=="parts" else self.tr("size"))

    def add_files(self):
        paths,_=QFileDialog.getOpenFileNames(self,self.tr("select"),"","PDF files (*.pdf)")
        for path in paths:
            if path in self.paths: continue
            try:
                count=len(PdfReader(path).pages)
                self.paths.append(path); self.selected_pages[path]=set()
                self.file_list.addItem(f"{Path(path).name} — {count} {self.tr('pages')}")
                self.preview_file.addItem(Path(path).name,path)
            except Exception as exc:
                QMessageBox.warning(self,self.tr("error"),self.tr("badpdf")+str(exc))

    def remove_selected(self):
        for item in reversed(self.file_list.selectedItems()):
            index=self.file_list.row(item); self.file_list.takeItem(index)
            path=self.paths.pop(index); self.selected_pages.pop(path,None)
            combo_index=self.preview_file.findData(path)
            if combo_index>=0: self.preview_file.removeItem(combo_index)
        self.render_preview()

    def clear_files(self):
        self.paths=[]; self.selected_pages={}; self.file_list.clear(); self.preview_file.clear(); self.render_preview()

    def choose_output(self):
        folder=QFileDialog.getExistingDirectory(self,self.tr("folder"))
        if folder: self.output.setText(folder)

    def render_preview(self):
        while self.preview_grid.count():
            item=self.preview_grid.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        path=self.preview_file.currentData()
        if not path or not os.path.exists(path):
            self.preview_hint.setText(self.tr("no_preview")); return
        try:
            doc=fitz.open(path); chosen=self.selected_pages.setdefault(path,set())
            self.preview_hint.setText(f"{len(doc)} {self.tr('pages')} — {len(chosen)} {self.tr('selected_count')}")
            for page_index,page in enumerate(doc):
                pix=page.get_pixmap(matrix=fitz.Matrix(0.22,0.22),alpha=False)
                image=QImage(pix.samples,pix.width,pix.height,pix.stride,QImage.Format_RGB888).copy()
                button=QToolButton(); button.setCheckable(True); button.setChecked(page_index in chosen)
                button.setIcon(QIcon(QPixmap.fromImage(image))); button.setIconSize(QSize(112,154))
                button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon); button.setText(str(page_index+1)); button.setFixedSize(138,190)
                button.setStyleSheet("QToolButton{background:white;border:1px solid #d4deea;border-radius:7px;padding:5px} QToolButton:checked{border:3px solid #1769aa;background:#e6f2fc}")
                button.clicked.connect(lambda checked, n=page_index, file_path=path: self.toggle_page(file_path,n,checked))
                self.preview_grid.addWidget(button,page_index//4,page_index%4)
            doc.close()
        except Exception as exc:
            self.preview_hint.setText(self.tr("badpdf")+str(exc))

    def toggle_page(self,path,page_index,checked):
        chosen=self.selected_pages.setdefault(path,set())
        if checked: chosen.add(page_index)
        else: chosen.discard(page_index)
        self.preview_hint.setText(f"{len(chosen)} {self.tr('selected_count')}")

    def parse_ranges(self,total):
        groups=[]
        for part in self.ranges.text().split(","):
            part=part.strip()
            if not part: continue
            match=re.fullmatch(r"(\d+)\s*(?:-\s*(\d+))?",part)
            if not match: raise ValueError(self.tr("invalid"))
            first=int(match.group(1)); last=int(match.group(2) or first)
            if first<1 or last<first or last>total: raise ValueError(self.tr("invalid"))
            groups.append(list(range(first-1,last)))
        if not groups: raise ValueError(self.tr("invalid"))
        return groups

    def run_split(self):
        if not self.paths:
            QMessageBox.warning(self,self.tr("error"),self.tr("empty")); return
        outdir=self.output.text().strip()
        if not outdir:
            QMessageBox.warning(self,self.tr("error"),self.tr("output")); return
        os.makedirs(outdir,exist_ok=True)
        mode=self.mode.currentData(); created=[]
        self.start.setEnabled(False); self.progress.setValue(0)
        try:
            total_jobs=len(self.paths)
            for file_number,path in enumerate(self.paths,1):
                reader=PdfReader(path); total=len(reader.pages); stem=Path(path).stem
                if mode=="ranges": groups=self.parse_ranges(total)
                elif mode=="selected":
                    chosen=sorted(self.selected_pages.get(path,set()))
                    if not chosen: raise ValueError(self.tr("invalid"))
                    groups=[chosen]
                elif mode=="each": groups=[[i] for i in range(total)]
                elif mode=="fixed":
                    size=self.spin.value(); groups=[list(range(i,min(i+size,total))) for i in range(0,total,size)]
                else:
                    count=min(self.spin.value(),total); groups=[]
                    for j in range(count):
                        a=(j*total)//count; b=((j+1)*total)//count
                        if a<b: groups.append(list(range(a,b)))
                for part_number,pages in enumerate(groups,1):
                    writer=PdfWriter()
                    for page_number in pages: writer.add_page(reader.pages[page_number])
                    if mode=="ranges": suffix=f"_pages_{pages[0]+1}-{pages[-1]+1}"
                    elif mode=="selected": suffix="_selected_pages"
                    else: suffix=f"_part_{part_number:03d}"
                    target=Path(outdir)/(stem+suffix+".pdf")
                    if self.unique.isChecked():
                        serial=2
                        while target.exists():
                            target=Path(outdir)/(stem+suffix+f"_{serial}.pdf"); serial+=1
                    with open(target,"wb") as output: writer.write(output)
                    created.append(str(target))
                self.progress.setValue(int(file_number/total_jobs*100))
            QMessageBox.information(self,self.tr("done"),self.tr("finished")+"\n"+outdir)
            self.status.setText(f"{len(created)} PDF")
        except Exception as exc:
            QMessageBox.critical(self,self.tr("error"),str(exc))
        finally:
            self.start.setEnabled(True)

if __name__=="__main__":
    app=QApplication(sys.argv); app.setApplicationName("PDF Splitter")
    window=App(); window.show(); sys.exit(app.exec())

