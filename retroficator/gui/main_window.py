from __future__ import annotations

from pathlib import Path

from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..core import AssetPipeline, ProcessOptions


class ImagePreview(QLabel):
    def __init__(self, title: str) -> None:
        super().__init__(title)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(360, 360)
        self.setStyleSheet("QLabel { background: #222; color: #aaa; border: 1px solid #444; }")
        self._image: Image.Image | None = None

    def set_pil_image(self, image: Image.Image | None) -> None:
        self._image = image.copy() if image else None
        self._refresh()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._refresh()

    def _refresh(self) -> None:
        if self._image is None:
            return
        qimage = ImageQt(self._image.convert("RGBA"))
        pixmap = QPixmap.fromImage(qimage)
        scaled = pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        self.setPixmap(scaled)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Retroficator v0.1")
        self.resize(1180, 720)
        self.setAcceptDrops(True)

        self.pipeline = AssetPipeline()
        self.source: Image.Image | None = None
        self.result: Image.Image | None = None
        self.source_path: Path | None = None
        self.palette_path: str | None = None

        self.source_preview = ImagePreview("Drop a PNG/JPG here or click Open")
        self.result_preview = ImagePreview("Processed preview")

        open_btn = QPushButton("Open image")
        open_btn.clicked.connect(self.open_image)
        self.process_btn = QPushButton("Process")
        self.process_btn.clicked.connect(self.process_image)
        self.process_btn.setEnabled(False)
        self.save_btn = QPushButton("Export PNG")
        self.save_btn.clicked.connect(self.save_image)
        self.save_btn.setEnabled(False)
        palette_btn = QPushButton("Load palette…")
        palette_btn.clicked.connect(self.load_palette)

        self.auto_grid = QCheckBox("Auto-detect source pixel grid")
        self.auto_grid.setChecked(True)
        self.manual_scale = QSpinBox()
        self.manual_scale.setRange(1, 64)
        self.manual_scale.setValue(8)
        self.force_size = QCheckBox("Force native output size")
        self.target_width = QSpinBox()
        self.target_width.setRange(1, 2048)
        self.target_width.setValue(64)
        self.target_height = QSpinBox()
        self.target_height.setRange(1, 2048)
        self.target_height.setValue(64)
        self.colors = QSpinBox()
        self.colors.setRange(2, 256)
        self.colors.setValue(24)
        self.binary_alpha = QCheckBox("Pixel-perfect binary alpha")
        self.binary_alpha.setChecked(True)
        self.remove_bg = QCheckBox("Remove flat connected background")
        self.bg_tolerance = QDoubleSpinBox()
        self.bg_tolerance.setRange(0.0, 150.0)
        self.bg_tolerance.setValue(24.0)
        self.bg_tolerance.setSingleStep(2.0)

        self.info = QLabel("No image loaded")
        self.info.setWordWrap(True)
        self.info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        form = QFormLayout()
        form.addRow(self.auto_grid)
        form.addRow("Manual scale", self.manual_scale)
        form.addRow(self.force_size)
        form.addRow("Target width", self.target_width)
        form.addRow("Target height", self.target_height)
        form.addRow("Max colors", self.colors)
        form.addRow(self.binary_alpha)
        form.addRow(self.remove_bg)
        form.addRow("Background tolerance", self.bg_tolerance)
        form.addRow("Project palette", palette_btn)

        controls = QVBoxLayout()
        controls.addWidget(open_btn)
        controls.addLayout(form)
        controls.addWidget(self.process_btn)
        controls.addWidget(self.save_btn)
        controls.addSpacing(12)
        controls.addWidget(self.info)
        controls.addStretch(1)

        previews = QHBoxLayout()
        previews.addWidget(self.source_preview, 1)
        previews.addWidget(self.result_preview, 1)

        root = QHBoxLayout()
        root.addLayout(controls, 0)
        root.addLayout(previews, 1)
        wrapper = QWidget()
        wrapper.setLayout(root)
        self.setCentralWidget(wrapper)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        urls = event.mimeData().urls()
        if urls:
            self._load_path(Path(urls[0].toLocalFile()))

    def open_image(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open image",
            "",
            "Images (*.png *.jpg *.jpeg *.webp)",
        )
        if filename:
            self._load_path(Path(filename))

    def _load_path(self, path: Path) -> None:
        try:
            with Image.open(path) as image:
                self.source = image.convert("RGBA")
            self.source_path = path
            self.source_preview.set_pil_image(self.source)
            self.result_preview.clear()
            self.result_preview.setText("Processed preview")
            self.result = None
            self.process_btn.setEnabled(True)
            self.save_btn.setEnabled(False)
            self.info.setText(f"{path.name}\n{self.source.width} × {self.source.height}")
        except Exception as exc:
            QMessageBox.critical(self, "Could not open image", str(exc))

    def load_palette(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load project palette",
            "",
            "Palette/Text (*.txt *.gpl *.hex);;All files (*)",
        )
        if filename:
            self.palette_path = filename
            self.info.setText(self.info.text() + f"\nPalette: {Path(filename).name}")

    def process_image(self) -> None:
        if self.source is None:
            return
        try:
            options = ProcessOptions(
                auto_grid=self.auto_grid.isChecked() and not self.force_size.isChecked(),
                scale_x=self.manual_scale.value(),
                scale_y=self.manual_scale.value(),
                target_width=self.target_width.value() if self.force_size.isChecked() else None,
                target_height=self.target_height.value() if self.force_size.isChecked() else None,
                max_colors=self.colors.value(),
                remove_background=self.remove_bg.isChecked(),
                background_tolerance=self.bg_tolerance.value(),
                palette_path=self.palette_path,
                binary_alpha=self.binary_alpha.isChecked(),
            )
            result = self.pipeline.process(self.source, options)
            self.result = result.image
            self.result_preview.set_pil_image(result.image)
            r = result.report
            self.info.setText(
                f"Source: {self.source.width} × {self.source.height}\n"
                f"Detected grid: {result.grid.scale_x} × {result.grid.scale_y} "
                f"(confidence {result.grid.confidence:.0%})\n"
                f"Output: {r.width} × {r.height}\n"
                f"Colors: {r.opaque_colors}\n"
                f"Alpha levels: {r.alpha_levels}\n"
                f"Tiny components: {r.tiny_components}"
            )
            self.save_btn.setEnabled(True)
        except Exception as exc:
            QMessageBox.critical(self, "Processing failed", str(exc))

    def save_image(self) -> None:
        if self.result is None:
            return
        suggested = "retroficated.png"
        if self.source_path:
            suggested = f"{self.source_path.stem}_retro.png"
        filename, _ = QFileDialog.getSaveFileName(self, "Export PNG", suggested, "PNG (*.png)")
        if filename:
            self.result.save(filename)


def run_gui() -> int:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    return app.exec()
