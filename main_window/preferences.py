from PySide6 import QtCore, QtGui, QtWidgets


class Preferences_General(QtWidgets.QWidget):
    def __init__(self, parent, settings: QtCore.QSettings) -> None:
        super().__init__(parent)

        self.name = QtCore.QCoreApplication.translate(
            "Preferences_General", "General", "preferences_page_general"
        )

        layout = QtWidgets.QGridLayout(self)
        self.setLayout(layout)

        self.diagnostic_threshold_edit = QtWidgets.QLineEdit(
            str(settings.value("diagnostics_threshold", 80))
        )
        self.diagnostic_threshold_edit.setValidator(QtGui.QIntValidator(0, 100, self))

        layout.addWidget(
            QtWidgets.QLabel(
                QtCore.QCoreApplication.translate(
                    "diagnostics_threshold", "Diagnostics threshold"
                )
            ),
            0,
            0,
        )
        layout.addWidget(self.diagnostic_threshold_edit, 0, 1)


class Preferences(QtWidgets.QDialog):
    def __init__(self, parent, settings: QtCore.QSettings) -> None:
        super().__init__(parent)

        self.settings = settings

        self.setWindowTitle(
            QtCore.QCoreApplication.translate("preferences", "Preferences")
        )

        self.resize(800, 600)

        stacked_widget = QtWidgets.QStackedWidget()
        self.preferences_general = Preferences_General(self, self.settings)

        pages_list = QtWidgets.QListWidget()
        pages_list.insertItem(0, self.preferences_general.name)

        stacked_widget.addWidget(self.preferences_general)

        vbox_layout = QtWidgets.QVBoxLayout(self)
        hbox_layout = QtWidgets.QHBoxLayout()

        hbox_layout.addWidget(pages_list)
        hbox_layout.addWidget(stacked_widget)
        pages_list.setSizePolicy(
            QtWidgets.QSizePolicy(
                QtWidgets.QSizePolicy.Policy.Minimum,
                QtWidgets.QSizePolicy.Policy.Expanding,
            )
        )

        vbox_layout.addLayout(hbox_layout)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        vbox_layout.addWidget(buttons)

    def accept(self) -> None:
        self.settings.setValue(
            "diagnostics_threshold",
            self.preferences_general.diagnostic_threshold_edit.text(),
        )

        return super().accept()
