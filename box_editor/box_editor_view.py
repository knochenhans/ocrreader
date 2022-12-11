import cv2
import numpy
from ocr_engine import OCREngineManager
from project import Project, Page
from PySide6 import QtCore, QtGui, QtWidgets

from box_editor.box_editor_scene import HEADER_FOOTER_ITEM_TYPE, BoxEditorScene


class BoxEditorView(QtWidgets.QGraphicsView):
    def __init__(self, parent, engine_manager: OCREngineManager, property_editor, project: Project) -> None:
        super().__init__(parent)

        self.project = project
        self.property_editor = property_editor
        self.current_page = None
        self.custom_scene = BoxEditorScene(self, engine_manager, self.property_editor, self.project, None)
        self.setScene(self.custom_scene)
        self.origin = QtCore.QPoint()
        self.current_scale = 1.0

        self.setTransformationAnchor(QtWidgets.QGraphicsView.NoAnchor)
        self.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform | QtGui.QPainter.TextAntialiasing)
        self.setDisabled(True)

        # Enable so we get mouse move events
        self.setMouseTracking(True)

        # Send rubber band changes to scene for drawing boxes
        self.rubberBandChanged.connect(self.scene().rubber_band_changed)

    def load_page(self, page: Page):
        self.scene().clear()
        self.scene().box_counter = 0
        self.scene().header_item = None
        self.scene().footer_item = None
        # self.scene().current_box = None
        self.scene().set_page_as_background(page)

        self.setEnabled(True)
        self.current_page = page
        self.scene().current_page = self.current_page

        for box_data in page.box_datas:
            # Restore existing boxes for this page
            self.scene().restore_box(box_data)

        # Restore header and footer box
        if self.project:
            if self.project.header_y:
                self.scene().add_header_footer(HEADER_FOOTER_ITEM_TYPE.HEADER, self.project.header_y)
            if self.project.footer_y:
                self.scene().add_header_footer(HEADER_FOOTER_ITEM_TYPE.FOOTER, self.project.footer_y)

        # TODO: Check if there’s a way to avoid checking current_box to find out if box is currently being resized
        self.scene().current_box = None

        self.property_editor.box_widget.reset()
        # self.property_editor.box_widget

        # self.scene().focus

    def scene(self):
        return self.custom_scene

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        '''Handle zooming and scrolling by mouse'''

        if event.modifiers() == QtCore.Qt.KeyboardModifier.ControlModifier:
            scaleFactor = 1.02
            degrees = event.angleDelta().y()
            if degrees > 0:
                self.current_scale *= scaleFactor
            else:
                self.current_scale /= scaleFactor

            self.resetTransform()
            self.scale(self.current_scale, self.current_scale)
        else:
            super().wheelEvent(event)

    def pixmap_to_cv2(self, pixmap: QtGui.QPixmap):
        image = pixmap.toImage().copy()

        # TODO: Works for now but a bit dirty, investigate further
        return numpy.array(image.bits()).reshape((image.height(), image.width(), 4))

    def analyze_layout(self) -> None:
        # TODO: Check for actual page
        # new_boxes = []
        # if self.scene().image:
        #     image = self.pixmap_to_cv2(self.scene().image)

        #     # ret1, th1 = cv2.threshold(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), 0, 255, cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
        #     ret1, th1 = cv2.threshold(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), 100, 255, cv2.THRESH_BINARY_INV)

        #     kernel = numpy.ones((5, 5), 'uint8')
        #     margin_img = cv2.dilate(th1, kernel, iterations=5)

        #     # cv2.imshow("test", margin_img)

        #     (contours, _) = cv2.findContours(margin_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        #     for cnt in reversed(contours):
        #         x, y, w, h = cv2.boundingRect(cnt)

        #         box = QtCore.QRectF(x, y, w, h)

        #         new_boxes.append(self.scene().add_box(box))
        #         self.scene().current_box = None
        # return new_boxes

        self.scene().analyse_layout()
