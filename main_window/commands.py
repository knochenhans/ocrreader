import os
from pathlib import Path
import ntpath
from PySide6 import QtGui, QtCore
from PySide6.QtGui import QUndoCommand
from pdf2image import convert_from_path

from main_window.main_window import MainWindow
from project import Page


class LoadImageCommand(QtGui.QUndoCommand):
    def __init__(self, main_window: MainWindow, filenames: list[str]):
        super().__init__()
        self.main_window = main_window
        self.filenames: list[str] = filenames
        self.pages: list[Page] = []

    def redo(self) -> None:
        pages: list[Page] = []

        for filename in self.filenames:
            if filename:
                image_filenames: list[str] = []

                # Split PDFs into images and save them in an image folder
                if os.path.splitext(filename)[1] == ".pdf":
                    images = convert_from_path(
                        filename, output_folder=self.main_window.temp_dir.name
                    )

                    for image in images:
                        image_png_filename = os.path.join(
                            self.main_window.temp_dir.name,
                            f"{Path(filename).stem}_{images.index(image)}.png",
                        )
                        image.save(image_png_filename, "PNG")
                        image_filenames.append(image_png_filename)

                        # TODO: Delete images from folder on undo

                else:
                    image_filenames.append(filename)

                for image_filename in image_filenames:
                    page = Page(
                        image_path=image_filename,
                        name=ntpath.basename(filename),
                        paper_size=self.main_window.project.default_paper_size,
                    )
                    self.main_window.project.add_page(page)
                    self.main_window.page_icon_view.load_page(page)
                    pages.append(page)

                    self.main_window.statusBar().showMessage(
                        QtCore.QCoreApplication.translate(
                            "status_image_loaded", "Image loaded", "MainWindow"
                        )
                        + ": "
                        + page.image_path
                    )

                # Add file path to recent documents menu
                self.main_window.recent_files_manager.add_recent_doc(filename)

        if pages:
            self.main_window.project_set_active()

        self.pages = pages

    def undo(self) -> None:
        for page in self.pages:
            self.main_window.project.remove_page(page)
            self.main_window.page_icon_view.remove_page(page)
