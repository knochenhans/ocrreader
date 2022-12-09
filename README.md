# OCR Reader

Simple but convenient GUI for Tesseract OCR written in Python, based on Qt6.

OCR Reader’s main scope isn’t batch OCR but making it as painless as possible to prepare (and eventually perform) OCR for documents with complicated layouts that need manual steps and often post-processing. One of the goals is to create export documents as closely aligned to the original as well as possible as allowed by the target medium (for example text reflowing for EPUB and HTML formats).

_This is still in a very early stage of development and contains lots of bugs._

Some of the features currently implemented:
* box editor featuring different box types (text, raw text, image)
* Tesseract’s confidence values within text boxes as well as box text editor
* box sequence can be manually reordered (import for export formats like EPUB or HTML)
* automatic hyphen elimination using dictionary (for German)
* basic font-size approximation
* basic layout-detection
* basic auto-alignment for images
* document-wide header and footer to exclude elements like page numbers from being exported without manually deleting them

![screenshot](https://user-images.githubusercontent.com/5293125/201544960-60702bae-890a-478b-a090-3470a5da97ff.jpg)

# Controls

## General

* Esc - Abort current action (Todo)

## Box Editor

* F1 - Select mode (Click to select, Ctrl + Click to select multiple, Click + Drag to move)
* F2 - Drawing mode
* F3 - Hand mode for scrolling (Todo)
* F4 - Place header
* F5 - Place footer
* F6 - Activate renumbering mode (Click on first box if no box is selected, then click second box to mark it as the next box in sequence)

* I - Set current box type to image
* T - Set current box type to text

* Ctrl + A - Select all boxes

## When one or more boxes are selected

* Alt + A - Auto align current box(es)
* Alt + D - Disable current box(es) from being exported
* Alt + I - Set current box(es) type to image
* Alt + R - Recognize text (will automatically split and create new boxes based on Tesseract’s estimations)
* Alt + T - Set current box(es) type to text