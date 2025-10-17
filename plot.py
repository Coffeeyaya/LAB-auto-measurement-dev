import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QListWidget, QListWidgetItem, QLabel, QComboBox,
    QMessageBox, QColorDialog, QInputDialog
)
from PyQt5.QtGui import QColor, QPixmap, QPainter, QPen, QIcon
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont



class CSVPlotterVerticalButtons(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CSV Plotter (x vs y)")
        self.resize(900, 500)
        font = QFont()
        font.setPointSize(20)  # set the font size
        self.setFont(font)

        # Data
        self.files = []         # list of full paths
        self.file_colors = {}   # file_path -> color string
        self.file_styles = {}   # file_path -> linestyle string

        # Layouts
        main_layout = QHBoxLayout()
        button_layout = QVBoxLayout()
        right_layout = QVBoxLayout()

        # Buttons
        self.upload_btn = QPushButton("📂 Select CSV Files")
        self.upload_btn.clicked.connect(self.upload_files)
        self.remove_btn = QPushButton("🗑 Remove 'Highlighted' Files")
        self.remove_btn.clicked.connect(self.remove_selected_files)
        self.edit_label_btn = QPushButton("✏️ Edit 'Highlighted' File Name")
        self.edit_label_btn.clicked.connect(self.edit_label_name)

        self.color_btn = QPushButton("🎨 Assign Color to 'Selected' Files")
        self.color_btn.clicked.connect(self.assign_colors)
        self.style_btn = QPushButton("📏 Assign Line Style to 'Selected' Files")
        self.style_btn.clicked.connect(self.assign_line_style)

        self.select_all_btn = QPushButton("✅ Select/Deselect All Files")
        self.select_all_btn.clicked.connect(self.select_all_files)
        
        self.plot_btn = QPushButton("📊 Plot 'Selected' Files")
        self.plot_btn.clicked.connect(self.plot_selected_files)

        for btn in [
            self.upload_btn, self.remove_btn, self.edit_label_btn,
            self.color_btn, self.style_btn, self.select_all_btn, 
            self.plot_btn
        ]:
            button_layout.addWidget(btn)
        button_layout.addStretch()

        # File list
        self.file_list_widget = QListWidget()
        self.file_list_widget.setSelectionMode(QListWidget.MultiSelection)
        right_layout.addWidget(self.file_list_widget)

        # Axis scale controls
        control_layout = QHBoxLayout()
        self.x_scale_combo = QComboBox()
        self.x_scale_combo.addItems(["linear", "log", "log_abs"])
        self.y_scale_combo = QComboBox()
        self.y_scale_combo.addItems(["linear", "log", "log_abs"])
        control_layout.addWidget(QLabel("X-axis scale:"))
        control_layout.addWidget(self.x_scale_combo)
        control_layout.addWidget(QLabel("Y-axis scale:"))
        control_layout.addWidget(self.y_scale_combo)
        right_layout.addLayout(control_layout)

        # Combine layouts
        main_layout.addLayout(button_layout)
        main_layout.addLayout(right_layout)
        self.setLayout(main_layout)

    # ----------------- Helpers -----------------
    def line_style_icon(self, color_str, linestyle="-", size=(40, 20)):
        """Return a QIcon showing a small colored line with the given style."""
        width, height = size
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)

        pen = QPen(QColor(color_str))
        pen.setWidth(2)
        if linestyle == "-":
            pen.setStyle(Qt.SolidLine)
        elif linestyle == "--":
            pen.setStyle(Qt.DashLine)
        elif linestyle == "-.":
            pen.setStyle(Qt.DashDotLine)
        elif linestyle == ":":
            pen.setStyle(Qt.DotLine)
        else:
            pen.setStyle(Qt.SolidLine)

        painter.setPen(pen) 
        painter.drawLine(2, height // 2, width - 2, height // 2)
        painter.end()
        return QIcon(pixmap)

    # ----------------- File Handling -----------------
    def upload_files(self):
        default_dir = "/Users/tsaiyunchen/Desktop/lab/master/measurement_dev/"
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select CSV Files", default_dir , "CSV Files (*.csv)"
        )
        if not files:
            return
        for f in files:
            if f not in self.files:
                self.files.append(f)
                item = QListWidgetItem(Path(f).name)
                item.setCheckState(Qt.Unchecked)
                item.setData(Qt.UserRole, f)
                item.setIcon(self.line_style_icon("#000000", "-"))  # default black solid line
                self.file_list_widget.addItem(item)

    def remove_selected_files(self):
        selected_items = [self.file_list_widget.item(i) for i in range(self.file_list_widget.count())
                          if self.file_list_widget.item(i).isSelected()]
        for item in selected_items:
            path = item.data(Qt.UserRole)
            if path in self.files:
                self.files.remove(path)
            self.file_colors.pop(path, None)
            self.file_styles.pop(path, None)
            self.file_list_widget.takeItem(self.file_list_widget.row(item))

    def select_all_files(self):
        """Toggle all files checked/unchecked."""
        all_checked = all(
            self.file_list_widget.item(i).checkState() == Qt.Checked
            for i in range(self.file_list_widget.count())
        )
        new_state = Qt.Unchecked if all_checked else Qt.Checked
        for i in range(self.file_list_widget.count()):
            self.file_list_widget.item(i).setCheckState(new_state)

    def edit_label_name(self):
        selected_items = [
            self.file_list_widget.item(i)
            for i in range(self.file_list_widget.count())
            if self.file_list_widget.item(i).isSelected()
        ]
        if len(selected_items) != 1:
            QMessageBox.warning(
                self, "Select one file", "Please select exactly one file to edit its label."
            )
            return
        item = selected_items[0]
        current_name = item.text()
        new_name, ok = QInputDialog.getText(
            self, "Edit Label Name", "New label:", text=current_name
        )
        if ok and new_name:
            item.setText(new_name)

    # ----------------- Color & Style -----------------
    def assign_colors(self):
        selected_items = [self.file_list_widget.item(i) for i in range(self.file_list_widget.count())
                          if self.file_list_widget.item(i).checkState() == Qt.Checked]
        if not selected_items:
            QMessageBox.warning(self, "No files selected", "Please check at least one file to assign color.")
            return

        for item in selected_items:
            file_path = item.data(Qt.UserRole)
            color = QColorDialog.getColor()
            if color.isValid():
                # In assign_colors
                self.file_colors[str(file_path)] = color.name()
                linestyle = self.file_styles.get(str(file_path), "-")
                item.setIcon(self.line_style_icon(color.name(), linestyle))

    def assign_line_style(self):
        selected_items = [self.file_list_widget.item(i) for i in range(self.file_list_widget.count())
                          if self.file_list_widget.item(i).checkState() == Qt.Checked]
        if not selected_items:
            QMessageBox.warning(self, "No files selected", "Please check at least one file to assign a line style.")
            return

        styles = ["-", "--", "-.", ":"]
        style, ok = QInputDialog.getItem(self, "Select Line Style", "Line style:", styles, 0, False)
        if ok and style:
            for item in selected_items:   
                file_path = item.data(Qt.UserRole)             
                # In assign_line_style
                self.file_styles[str(file_path)] = style
                color = self.file_colors.get(str(file_path), "#000000")
                item.setIcon(self.line_style_icon(color, style))


    # ----------------- Plotting -----------------
    def plot_selected_files(self):
        selected_items = [self.file_list_widget.item(i) for i in range(self.file_list_widget.count())
                          if self.file_list_widget.item(i).checkState() == Qt.Checked]
        if not selected_items:
            QMessageBox.warning(self, "No files selected", "Please check at least one file to plot.")
            return

        fig, ax = plt.subplots(figsize=(8, 5))

        for item in selected_items:
            file_path = Path(item.data(Qt.UserRole))
            try:
                df = pd.read_csv(file_path)
                if df.shape[1] != 2:
                    QMessageBox.warning(self, "Invalid file", f"{file_path.name} must have exactly 2 columns.")
                    continue
                df = df.apply(pd.to_numeric, errors='coerce').dropna()
                x = df.iloc[:, 0]
                y = df.iloc[:, 1]
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to read {file_path.name}: {e}")
                continue

            color = self.file_colors.get(str(file_path), None)
            linestyle = self.file_styles.get(str(file_path), "-")

            x_scale = self.x_scale_combo.currentText()
            y_scale = self.y_scale_combo.currentText()

            if x_scale == "log_abs":
                x = np.abs(x)
                ax.set_xscale("log")
            elif x_scale != "linear":
                ax.set_xscale(x_scale)

            if y_scale == "log_abs":
                y = np.abs(y)
                ax.set_yscale("log")
            elif y_scale != "linear":
                ax.set_yscale(y_scale)

            ax.plot(x, y, label=item.text(), color=color, linestyle=linestyle)

        # ax.set_xlabel("X")
        # ax.set_ylabel("Y")
        ax.tick_params(axis="y", which="both", direction="in")
        ax.tick_params(axis="x", direction="in")
        ax.grid(True, which="major", linestyle="--", linewidth=0.5, alpha=0.7)
        ax.legend(fontsize=8)
        plt.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CSVPlotterVerticalButtons()
    window.show()
    sys.exit(app.exec_())
