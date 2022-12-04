import os
import re

from ebooklib import epub

from box_data import BOX_DATA_TYPE, BoxData


class Exporter():
    def __init__(self, extension='', filter: str = ''):
        self.extension = extension
        self.filter = filter

    def open(self, filename: str, name: str = '', author: str = ''):
        if os.path.splitext(filename)[1] != '.' + self.extension:
            filename += '.' + self.extension

        self.filename = filename
        self.name = name
        self.author = author

    def close(self):
        pass

    def write_box(self, box_data: BoxData):
        pass

    def new_page(self):
        pass


class ExporterPlainText(Exporter):
    def __init__(self, extension='', filter: str = ''):
        super().__init__(extension, filter)

    def open(self, filename: str, name: str = '', author: str = ''):
        super().open(filename, name, author)

        self.text = ''

    def write_box(self, box_data: BoxData):
        if box_data.type == BOX_DATA_TYPE.TEXT:
            self.text += box_data.text.toPlainText() + '\n\n'

    def new_page(self):
        self.text += '\n'

    def close(self):
        with open(self.filename, 'w') as file:
            file.write(self.text)


class ExporterEPUB(Exporter):
    def __init__(self, extension='', filter: str = ''):
        super().__init__(extension, filter)
        self.book = epub.EpubBook()
        self.current_chapter = epub.EpubHtml(title='Intro', file_name='chap_01.xhtml', lang='de')
        self.current_chapter.content = ''
        self.last_image_hook = 0

    def open(self, filename: str, name: str = '', author: str = ''):
        super().open(filename, name, author)
        with open('resources/epub/nav.css', 'r') as file:
            style = file.read()

            nav_css = epub.EpubItem(uid='style_nav', file_name='style/nav.css', media_type='text/css', content=str.encode(style))
            self.book.add_item(nav_css)
            self.current_chapter.add_item(nav_css)

    def write_box(self, box_data: BoxData):
        text = ''

        if box_data.type == BOX_DATA_TYPE.TEXT:
            content = box_data.text.toPlainText()

            if content:
                # match box_data.style_tag:
                #     case 'h1':
                #         text = f'<h1>{content}</h1>\n\n'
                #     case 'h2':
                #         text = f'<h2>{content}</h2>\n\n'
                #     case 'intro':
                #         text = f'<p class="topic-intro">{content}</p>\n\n'
                #     case 'prod':
                #         text = f'<p class="product">{content}</p>\n\n'
                #     case 'fc':
                #         self.current_chapter.content = str(self.current_chapter.content[:self.last_image_hook]) + \
                #             f'<figcaption>{content}</figcaption>' + str(self.current_chapter.content[self.last_image_hook:])
                #         return
                #     case _:
                # Regular paragraph

                # Check for author
                m = re.match(r'.*\s(\(.*?\))$', content)

                if m:
                    content = f'{content[:m.span(1)[0]]}<span class="author">{content[m.span(1)[0]:]}</span>'

                text = f'<p>{content}</p>\n\n'

            self.current_chapter.content = str(self.current_chapter.content) + text + '\n\n'

    def close(self):
        self.book.add_item(self.current_chapter)
        self.book.add_item(epub.EpubNcx())
        self.book.add_item(epub.EpubNav())

        self.book.spine = ['nav', self.current_chapter]
        epub.write_epub(self.filename, self.book, {})


class ExporterManager():
    def __init__(self):
        self.exporters = {}

    def add_exporter(self, id, exporter: Exporter):
        self.exporters[id] = exporter

    def get_exporter(self, id) -> Exporter:
        return self.exporters[id]
