from PySide6 import QtGui, QtWidgets, QtCore
import os

from main_window.main_window import MainWindow


class RecentFilesManager:
    def __init__(self, parent: MainWindow):
        self.parent = parent
        self.recent_files = []
        self.recent_docs = []
        self.recent_projects = []

    def add_recent_doc(self, file_path: str):
        # Add new file path to top of list, remove the last one
        action = QtGui.QAction(file_path)
        action.triggered.connect(self.open_recent_doc)
        self.recent_docs.insert(0, action)

        # Remove any duplicates
        unique_actions = []

        for action in self.recent_docs:
            if action.text() not in [a.text() for a in unique_actions]:
                unique_actions.append(action)

        self.recent_docs = unique_actions

        if len(self.recent_docs) > 5:
            self.recent_docs.pop()

        # Update recent documents menu
        self.parent.recent_docs_menu.clear()
        self.parent.recent_docs_menu.addActions(self.recent_docs)

    def open_recent_doc(self):
        # Get selected recent document and open it
        sender = self.parent.sender()

        if isinstance(sender, QtGui.QAction):
            file_path: str = sender.text()

            if os.path.exists(file_path):
                self.parent.load_images([file_path])
                return True
            else:
                QtWidgets.QMessageBox.warning(
                    self.parent,
                    QtCore.QCoreApplication.translate(
                        "message_box_document_not_found", "File not found"
                    ),
                    QtCore.QCoreApplication.translate(
                        "message_box_document_not_found",
                        f"The document {file_path} could not be opened and will be removed from the recent documents list.",
                    ),
                )
                self.remove_recent_doc(file_path)
        return False

    def remove_recent_doc(self, file_path: str) -> None:
        for recent_doc in self.recent_docs:
            if recent_doc.text() == file_path:
                self.recent_docs.remove(recent_doc)

    def add_recent_project(self, file_path: str):
        # Add new file path to top of list, remove the last one
        action = QtGui.QAction(file_path)
        action.triggered.connect(self.open_recent_project)
        self.recent_projects.insert(0, action)

        # Remove any duplicates
        unique_actions = []

        for action in self.recent_projects:
            if action.text() not in [a.text() for a in unique_actions]:
                unique_actions.append(action)

        self.recent_projects = unique_actions

        if len(self.recent_projects) > 5:
            self.recent_projects.pop()

        for action in self.recent_projects:
            action.setShortcut("")

        self.recent_projects[0].setShortcut(QtGui.QKeySequence("Ctrl+1"))

        # Update recent documents menu
        self.parent.recent_projects_menu.clear()
        self.parent.recent_projects_menu.addActions(self.recent_projects)

    def open_recent_project(self) -> bool:
        # Get selected recent document and open it
        sender = self.parent.sender()

        if isinstance(sender, QtGui.QAction):
            file_path: str = sender.text()

            if os.path.exists(file_path):
                self.parent.open_project_file(file_path)
                return True
            else:
                QtWidgets.QMessageBox.warning(
                    self.parent,
                    QtCore.QCoreApplication.translate(
                        "message_box_project_not_found", "File not found"
                    ),
                    QtCore.QCoreApplication.translate(
                        "message_box_project_not_found",
                        f"The project file {file_path} could not be opened and will be removed from the recent projects list.",
                    ),
                )
                self.remove_recent_project(file_path)
        return False

    def remove_recent_project(self, file_path: str) -> None:
        for recent_project in self.recent_projects:
            if recent_project.text() == file_path:
                self.recent_projects.remove(recent_project)
