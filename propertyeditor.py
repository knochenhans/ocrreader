from PySide6 import QtWidgets, QtCore
from boxeditor import BoxOCRProperties

class PropertyEditor(QtWidgets.QToolBox):
    def __init__(self, parent):
        self.box_editor: BoxEditor = None
        super().__init__(parent)

        self.text_edit = QtWidgets.QTextEdit(self)
        self.text_edit.setAcceptRichText(True)
        self.addItem(self.text_edit, 'Recognition')
        self.text_edit.setDisabled(True)
        self.text_edit.setPlaceholderText('No text recognized yet.')

    def select_box(self, box_properties: BoxOCRProperties):
        self.text_edit.setEnabled(True)
        self.text_edit.setText(box_properties.text)
        self.text_edit.update()