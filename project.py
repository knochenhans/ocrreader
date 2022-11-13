import ntpath

from iso639 import Lang
from papersize import SIZES
from PySide6 import QtCore, QtGui


class Page():
    def __init__(self, image_path: str = '', name: str = '', paper_size_str: str = ''):
        self.image_path = image_path
        self.name = name
        self.blocks = []
        self.paper_size = paper_size_str

        if paper_size_str:
            self.px_per_mm = self.calc_px_per_mm(paper_size_str)
        else:
            self.px_per_mm = 0

    def calc_px_per_mm(self, paper_size: str) -> float:
        # TODO: Lets assume 1:1 pixel ratio for now, so ignore height
        width_mm = int(paper_size.split(' x ')[0].split('mm')[0])
        # height_mm = int(paper_size.split(' x ')[1].split('mm')[0])

        return width_mm / QtGui.QImage(self.image_path).size().width()

    def write(self, file: QtCore.QDataStream):
        file.writeString(self.image_path)
        file.writeString(self.name)
        file.writeQVariant(self.paper_size)

    def read(self, file: QtCore.QDataStream):
        self.image_path = file.readString()
        self.name = file.readString()
        self.paper_size = file.readQVariant()


class Project():
    def __init__(self, name='New Project', default_language: Lang = Lang('English'), default_paper_size: str = SIZES['a4']):
        self.name = name
        self.default_language = default_language
        self.default_paper_size = default_paper_size
        self.current_page_idx = 0
        self.pages: list[Page] = []

    # def add_page(self, image_path: str, paper_size: str = SIZES['a4']) -> None:
    #     self.pages.append(Page(image_path, ntpath.basename(image_path), paper_size))

    def add_page(self, page: Page):
        self.pages.append(page)

    def write(self, file: QtCore.QDataStream):
        file.writeString(self.name)
        file.writeString(self.default_language.name)
        file.writeString(self.default_paper_size)
        file.writeInt16(self.current_page_idx)

        file.writeInt16(len(self.pages))
        for page in self.pages:
            page.write(file)

    def read(self, file: QtCore.QDataStream):
        self.name = file.readString()
        self.default_language = Lang(file.readString())
        self.default_paper_size = file.readString()
        self.current_page_idx = file.readInt16()

        page_count = file.readInt16()
        for p in range(page_count):
            page = Page()
            page.read(file)
            self.pages.append(page)
