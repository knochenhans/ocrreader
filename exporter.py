import os
import re
import tempfile

from ebooklib import epub
from PySide6 import QtWidgets, QtGui

from box_data import BOX_DATA_TYPE, BoxData
from project import Page


class Exporter():
    def __init__(self, parent: QtWidgets.QWidget):
        self.parent = parent

    def open(self, temp_dir: tempfile.TemporaryDirectory, name: str = '', author: str = '') -> bool:
        self.temp_dir = temp_dir
        self.name = name
        self.author = author

        return True

    def close(self):
        pass

    def write_box(self, box_data: BoxData, page: Page, page_nr: int):
        pass

    def new_page(self):
        pass

    def prepare_filename(self, filename, extension):
        if os.path.splitext(filename)[1] != '.' + extension:
            filename += '.' + extension

        self.filename = filename


class ExporterPlainText(Exporter):
    def __init__(self, parent: QtWidgets.QWidget):
        super().__init__(parent)

    def open(self, temp_dir: tempfile.TemporaryDirectory, name: str = '', author: str = '') -> bool:
        super().open(temp_dir, name, author)

        extension = 'txt'
        filename = QtWidgets.QFileDialog.getSaveFileName(self.parent, caption=self.parent.tr('Export to Plain Text', 'dialog_export_caption_plain_text'),
                                                         filter=self.parent.tr('Text file (*.text)', 'dialog_export_filter_plain_text'))[0]
        self.text = ''

        self.prepare_filename(filename, extension)

        return True

    def write_box(self, box_data: BoxData, page: Page, page_nr: int):
        if box_data.type == BOX_DATA_TYPE.TEXT:
            self.text += box_data.text.toPlainText() + '\n'

    def new_page(self):
        self.text += '\n\n'

    def close(self):
        with open(self.filename, 'w') as file:
            file.write(self.text)


class ExporterEPUB_OptionWindow(QtWidgets.QDialog):
    def __init__(self, parent, callback):
        super().__init__(parent)

        self.callback = callback

        layout = QtWidgets.QGridLayout(self)
        self.setLayout(layout)

        self.css_edit = QtWidgets.QPlainTextEdit(self)
        self.css_edit.textChanged.connect(self.css_edited)

        layout.addWidget(self.css_edit, 0, 0)

        self.setWindowTitle(self.tr('EPUB Export Options', 'dialog_export_window_title_epub_options'))

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(buttons)

    def css_edited(self):
        self.callback(self.css_edit.toPlainText())


class ExporterEPUB(Exporter):
    def __init__(self, parent: QtWidgets.QWidget):
        super().__init__(parent)
        self.book = epub.EpubBook()
        self.current_chapter = epub.EpubHtml(title='Intro', file_name='chap_01.xhtml', lang='de')
        self.current_chapter.content = ''
        self.css = ''

    def open(self, temp_dir: tempfile.TemporaryDirectory, name: str = '', author: str = '') -> bool:
        super().open(temp_dir, name, author)

        extension = 'epub'
        filename = QtWidgets.QFileDialog.getSaveFileName(self.parent, caption=self.parent.tr('Export to EPUB', 'dialog_export_caption_epub'),
                                                         filter=self.parent.tr('EPUB file (*.epub)', 'dialog_export_filter_epub'))[0]
        self.text = ''

        self.prepare_filename(filename, extension)

        options = ExporterEPUB_OptionWindow(self.parent, self.update_css)

        if options.exec():
            # with open('resources/epub/nav.css', 'r') as file:
            #     style = file.read()

            if self.css:
                nav_css = epub.EpubItem(uid='style_nav', file_name='style/nav.css', media_type='text/css', content=str.encode(self.css))
                self.book.add_item(nav_css)
                self.current_chapter.add_item(nav_css)
            return True
        else:
            return False

    def write_box(self, box_data: BoxData, page: Page, page_nr: int):
        text = ''
        classes = ''

        if box_data.type == BOX_DATA_TYPE.TEXT:
            if box_data.tag:
                if box_data.class_str:
                    classes = f' class="{box_data.class_str}"'

                text += f'<{box_data.tag + classes}>'

            text += box_data.text.toPlainText()

            if box_data.tag:
                text += f'</{box_data.tag}>'

            self.current_chapter.content = str(self.current_chapter.content) + text + '\n\n'
        elif box_data.type == BOX_DATA_TYPE.IMAGE:
            format = 'JPEG'
            image_uid = f'page_{page_nr}_{box_data.order}.{format}'
            image_path = self.temp_dir.name + '/' + image_uid
            QtGui.QPixmap(page.image_path).copy(box_data.rect).save(image_path, format)

            image = epub.EpubImage()
            image_content = open(image_path, 'rb').read()

            image.uid = image_uid
            image.file_name = 'images/' + image_uid
            image.media_type = 'image/jpeg'
            image.content = image_content

            self.book.add_item(image)
            # TODO: Calculate height based on ppi
            self.current_chapter.content = str(self.current_chapter.content) + f'''<figure><img style="height: {box_data.rect.height() / 15}em" src="{image.file_name}" alt="{image.file_name}"/>'''
            self.current_chapter.content = str(self.current_chapter.content) + '</figure>\n\n'

    def close(self):
        self.book.add_item(self.current_chapter)
        self.book.add_item(epub.EpubNcx())
        self.book.add_item(epub.EpubNav())

        self.book.spine = ['nav', self.current_chapter]
        epub.write_epub(self.filename, self.book, {})

    def update_css(self, css: str):
        self.css = css


class ExporterManager():
    def __init__(self):
        self.exporters = {}

    def add_exporter(self, id, exporter: Exporter):
        self.exporters[id] = exporter

    def get_exporter(self, id) -> Exporter:
        return self.exporters[id]