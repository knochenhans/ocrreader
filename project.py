import ntpath

from iso639 import Lang
from papersize import SIZES
from PySide6 import QtCore, QtGui

from box_editor.box_data import BoxData


class Page():
    def __init__(self, image_path: str = '', name: str = '', paper_size: str = ''):
        self.image_path = image_path
        self.name = name
        #self.blocks = []
        self.box_datas = []

        self.set_paper_size(paper_size)

    def set_paper_size(self, paper_size):
        self.paper_size = paper_size
        if paper_size:
            self.px_per_mm = self.calc_px_per_mm(SIZES[paper_size])
        else:
            self.px_per_mm = 0.0

    def calc_px_per_mm(self, paper_size: str) -> float:
        # TODO: Lets assume 1:1 pixel ratio for now, so ignore height
        width_mm = int(paper_size.split(' x ')[0].split('mm')[0])
        # height_mm = int(paper_size.split(' x ')[1].split('mm')[0])

        return width_mm / QtGui.QImage(self.image_path).size().width()

    def write(self, file: QtCore.QDataStream):
        file.writeString(self.image_path)
        file.writeString(self.name)
        file.writeString(self.paper_size)
        file.writeFloat(self.px_per_mm)

        file.writeInt16(len(self.box_datas))

        for box_datas in self.box_datas:
            box_datas.write(file)

    def read(self, file: QtCore.QDataStream):
        self.image_path = file.readString()
        self.name = file.readString()
        self.paper_size = file.readString()
        self.px_per_mm = file.readFloat()

        box_datas_count = file.readInt16()

        for b in range(box_datas_count):
            box_data = BoxData()
            box_data.read(file)
            self.box_datas.append(box_data)

    def clear(self):
        self.box_datas.clear()


class Project():
    def __init__(self, name='', default_language: Lang = Lang('English'), default_paper_size: str = 'a4'):
        self.name = name
        self.default_language = default_language
        self.default_paper_size = default_paper_size
        self.current_page_idx = 0
        self.pages: list[Page] = []
        self.header_y = 0.0
        self.footer_y = 0.0

        # Save format revision for loading
        self.format_revision = 4

    # def add_page(self, image_path: str, paper_size: str = SIZES['a4']) -> None:
    #     self.pages.append(Page(image_path, ntpath.basename(image_path), paper_size))

    def add_page(self, page: Page):
        self.pages.append(page)

    def write(self, file: QtCore.QDataStream):
        file.writeInt16(self.format_revision)
        file.writeString(self.name)
        file.writeString(self.default_language.name)
        file.writeString(self.default_paper_size)
        file.writeInt16(self.current_page_idx)
        file.writeFloat(self.header_y)
        file.writeFloat(self.footer_y)

        file.writeInt16(len(self.pages))
        for page in self.pages:
            page.write(file)

    def read(self, file: QtCore.QDataStream):
        format_revision = file.readInt16()

        if format_revision != self.format_revision:
            raise ValueError(f'Revision of project file is {format_revision} is incompatible with {self.format_revision}. Project file cannot be loaded')

        self.name = file.readString()
        self.default_language = Lang(file.readString())
        self.default_paper_size = file.readString()
        self.current_page_idx = file.readInt16()
        self.header_y = file.readFloat()
        self.footer_y = file.readFloat()

        page_count = file.readInt16()
        for p in range(page_count):
            page = Page()
            page.read(file)
            self.add_page(page)
