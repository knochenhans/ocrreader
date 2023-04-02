import os
import re
import tempfile

from bs4 import BeautifulSoup, Tag
from ebooklib import epub
from odf import style
from odf import text as odftext
from odf.draw import Frame, Image, TextBox
from odf.opendocument import OpenDocumentText
from odf.style import (Footer, GraphicProperties, Header, MasterPage,
                       PageLayout, PageLayoutProperties, ParagraphProperties,
                       Style, TextProperties)
from odf.text import A, LineBreak, P, PageNumber, Span
from papersize import SIZES, parse_length
from PySide6 import QtGui, QtWidgets

from box_editor.box_data import BOX_DATA_TYPE, BoxData
from document_helper import DocumentHelper
from project import Page, Project


class Exporter():
    def __init__(self, parent: QtWidgets.QWidget):
        self.parent = parent

    def open(self, temp_dir: tempfile.TemporaryDirectory, project: Project) -> bool:
        self.temp_dir = temp_dir
        self.project = project
        self.name = project.name
        self.author = ''
        self.current_page = None
        self.current_page_nr = 0

        return True

    def finish(self):
        pass

    def open_finished_dialog(self, filename: str):
        response = QtWidgets.QMessageBox.question(self.parent, 'Export Successful', f'File {filename} exported successfully.\nDo you want to open it?',
                                                  QtWidgets.QMessageBox.StandardButton.Ok | QtWidgets.QMessageBox.StandardButton.Cancel, QtWidgets.QMessageBox.StandardButton.Ok)

        if response == QtWidgets.QMessageBox.StandardButton.Open:
            # open the file using the associated application
            os.system(f'xdg-open {filename}')

    def write_box(self, box_data: BoxData):
        pass

    def new_page(self, page: Page, page_nr: int):
        self.current_page = page
        self.current_page_nr = page_nr
        self.current_image = QtGui.QPixmap(self.current_page.image_path)

    def prepare_filename(self, filename, extension) -> str:
        if os.path.splitext(filename)[1] != '.' + extension:
            filename += '.' + extension

        return filename


class ExporterODT(Exporter):
    def __init__(self, parent: QtWidgets.QWidget):
        super().__init__(parent)

    def open(self, temp_dir: tempfile.TemporaryDirectory, project: Project) -> bool:
        super().open(temp_dir, project)

        self.odf_text = OpenDocumentText()

        self.frame_style = Style(name='FrameStyle', family='graphic')
        self.frame_style.addElement(GraphicProperties(verticalpos='from-top', verticalrel='page', horizontalpos='from-left', horizontalrel='page', stroke='none', fill='none'))
        self.odf_text.automaticstyles.addElement(self.frame_style)

        self.main_p = P()
        self.odf_text.text.addElement(self.main_p)

        return True

    def write_box(self, box_data: BoxData):
        box_id = 'box' + str(self.current_page_nr) + '_' + str(box_data.order)

        if self.current_page:
            unit = 'in'

            x = str(box_data.rect.x() / self.current_page.ppi) + unit
            y = str(box_data.rect.y() / self.current_page.ppi) + unit
            width = str(box_data.rect.width() / self.current_page.ppi) + unit
            heigth = str(box_data.rect.height() / self.current_page.ppi) + unit

            frame = Frame(width=width, height=heigth, x=x, y=y, anchortype='page', stylename=self.frame_style)

            match box_data.type:
                case BOX_DATA_TYPE.TEXT:
                    text_box = TextBox()

                    box_style = Style(name=box_id, family='paragraph')
                    box_style.addElement(TextProperties(attributes={'fontsize': str(box_data.ocr_result_block.get_font_size()) + 'pt'}))
                    self.odf_text.automaticstyles.addElement(box_style)

                    # document_helper = DocumentHelper(box_data.text.clone(), box_data.language.pt1)
                    # paragraphs = document_helper.break_document_into_fragments()

                    paragraphs = box_data.get_paragraphs()

                    for p, paragraph in enumerate(paragraphs):
                        p = P(stylename=box_style)
                        text_box.addElement(p)

                        # for l, line in enumerate(paragraph):
                        for f, fragment in enumerate(paragraph):
                            # format: QtGui.QTextCharFormat = fragment.charFormat()

                            if '\u2028' in fragment.text():
                                # Split at line break character
                                fragment_lines = fragment.text().split('\u2028')
                                for fl, fragment_line in enumerate(fragment_lines):
                                    p.addText(fragment_line)

                                    if fl < len(fragment_lines) - 1:
                                        p.addElement(LineBreak())
                            else:
                                p.addText(fragment.text())

                    frame.addElement(text_box)

                case BOX_DATA_TYPE.IMAGE:
                    image_path = self.temp_dir.name + '/' + box_id + '.png'
                    self.current_image.copy(box_data.rect).save(image_path)

                    frame.addElement(Image(href=self.odf_text.addPicture(image_path)))

            self.main_p.addElement(frame)

    def new_page(self, page: Page, page_nr: int):
        super().new_page(page, page_nr)

        # Set page size

        pl = PageLayout(name='pagelayout')
        pl.addElement(PageLayoutProperties(pagewidth=str(parse_length(SIZES[page.paper_size].split(' x ')[0], 'in')) + 'in',
                      pageheight=str(parse_length(SIZES[page.paper_size].split(' x ')[1], 'in')) + 'in', margin='0pt'))

        self.odf_text.automaticstyles.addElement(pl)
        mp = MasterPage(name='Standard', pagelayoutname=pl)
        self.odf_text.masterstyles.addElement(mp)

    def finish(self):
        # TODO: Generalize file save dialog in base class
        # preview = ExporterPreviewWindow(self.parent, document, self.preview_document_changed)

        # if preview.exec():
        extension = 'odt'
        filename = QtWidgets.QFileDialog.getSaveFileName(self.parent, caption=self.parent.tr('Export to ODT', 'dialog_export_caption_odt'),
                                                         filter=self.parent.tr('ODT file (*.odt)', 'dialog_export_filter_odt'))[0]

        if filename:
            file_extension = os.path.splitext(filename)[1]

            if file_extension != '.' + extension:
                filename += '.' + extension

            self.odf_text.save(filename)

            self.open_finished_dialog(filename)

    def preview_document_changed(self, document: QtGui.QTextDocument):
        self.document = document


class ExporterPlainText(Exporter):
    def __init__(self, parent: QtWidgets.QWidget):
        super().__init__(parent)

    def open(self, temp_dir: tempfile.TemporaryDirectory, project: Project) -> bool:
        super().open(temp_dir, project)

        return True

    def write_box(self, box_data: BoxData, page: Page, page_nr: int):
        if box_data.type is BOX_DATA_TYPE.TEXT:
            self.text += box_data.text.toPlainText() + '\n'

    def new_page(self, page: Page, page_nr: int):
        super().new_page(page, page_nr)
        if page_nr > 1:
            self.text += '\n\n'

    def finish(self):
        document = QtGui.QTextDocument(self.text)
        preview = ExporterPreviewWindow(self.parent, document, self.preview_document_changed)

        if preview.exec():
            extension = 'txt'
            filename = QtWidgets.QFileDialog.getSaveFileName(self.parent, caption=self.parent.tr('Export to Plain Text', 'dialog_export_caption_plain_text'),
                                                             filter=self.parent.tr('Text file (*.txt)', 'dialog_export_filter_plain_text'))[0]
            self.text = ''

            file_extension = os.path.splitext(filename)[1]

            if file_extension != '.' + extension:
                filename += '.' + extension

            with open(self.prepare_filename(filename, extension), 'w') as file:
                file.write(self.text)

            self.open_finished_dialog(filename)

    def preview_document_changed(self, document: QtGui.QTextDocument):
        self.document = document


class ExporterPreviewWindow(QtWidgets.QDialog):
    def __init__(self, parent, document: QtGui.QTextDocument, callback):
        super().__init__(parent)

        self.callback = callback

        self.resize(1000, 800)

        layout = QtWidgets.QGridLayout(self)
        self.setLayout(layout)

        self.preview = QtWidgets.QTextEdit(self)
        self.preview.textChanged.connect(self.preview_edited)
        self.preview.setDocument(document)

        layout.addWidget(self.preview, 0, 0)

        self.setWindowTitle(self.tr('Export Preview', 'dialog_export_window_title_preview'))

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(buttons)

    def preview_edited(self):
        self.callback(self.preview.document())


class ExporterEPUB_OptionWindow(QtWidgets.QDialog):
    def __init__(self, parent, callback):
        super().__init__(parent)

        self.callback = callback

        layout = QtWidgets.QGridLayout(self)
        self.setLayout(layout)

        self.css_edit = QtWidgets.QPlainTextEdit(self)
        self.css_edit.textChanged.connect(self.css_edited)
        self.css_edit.setPlaceholderText('Enter CSS code to include in exported EPUB file here.')

        layout.addWidget(self.css_edit, 0, 0)

        self.setWindowTitle(self.tr('EPUB Export Options', 'dialog_export_window_title_epub_options'))

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
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
        self.preview_document = QtGui.QTextDocument()

    def open(self, temp_dir: tempfile.TemporaryDirectory, project: Project) -> bool:
        super().open(temp_dir, project)

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

        if box_data.type is BOX_DATA_TYPE.TEXT:
            document_helper = DocumentHelper(box_data.text.clone(), box_data.language.pt1)
            paragraphs = document_helper.break_document_into_fragments()

            if not box_data.tag:
                box_data.tag = 'div'

            if box_data.class_:
                classes = f' class="{box_data.class_}"'

            text += f'<{box_data.tag + classes}>'

            for p, paragraph in enumerate(paragraphs):
                for l, line in enumerate(paragraph):
                    for f, fragment in enumerate(line):
                        format: QtGui.QTextCharFormat = fragment.charFormat()
                        text += fragment.text()

            if box_data.tag:
                text += f'</{box_data.tag}>'

            self.current_chapter.content = str(self.current_chapter.content) + text + '\n\n'
        elif box_data.type is BOX_DATA_TYPE.IMAGE:
            image_format = 'JPEG'
            image_uid = f'page_{page_nr}_{box_data.order}.{image_format}'
            image_path = self.temp_dir.name + '/' + image_uid
            QtGui.QPixmap(page.image_path).copy(box_data.rect).save(image_path, image_format)

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

    def finish(self):
        self.book.add_item(self.current_chapter)
        self.book.add_item(epub.EpubNcx())
        self.book.add_item(epub.EpubNav())

        self.book.spine = ['nav', self.current_chapter]

        cursor = QtGui.QTextCursor(self.preview_document)
        cursor.insertHtml(str(self.current_chapter.content))

        preview = ExporterPreviewWindow(self.parent, self.preview_document, self.preview_document_changed)

        if preview.exec():
            extension = 'epub'
            filename = QtWidgets.QFileDialog.getSaveFileName(self.parent, caption=self.parent.tr('Export to EPUB', 'dialog_export_caption_epub'),
                                                             filter=self.parent.tr('EPUB file (*.epub)', 'dialog_export_filter_epub'))[0]
            self.text = ''

            file_extension = os.path.splitext(filename)[1]

            if file_extension != '.' + extension:
                filename += '.' + extension

            epub.write_epub(self.prepare_filename(filename, extension), self.book, {})

            self.open_finished_dialog(filename)

    def update_css(self, css: str):
        self.css = css

    def preview_document_changed(self, document: QtGui.QTextDocument):
        self.preview_document = document


class ExporterManager():
    def __init__(self):
        self.exporters = {}

    def add_exporter(self, id, exporter: Exporter):
        self.exporters[id] = exporter

    def get_exporter(self, id) -> Exporter:
        return self.exporters[id]
