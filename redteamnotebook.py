# TODO: error checks for insert nodes (text + parentid should be unique)
# TODO: better markdown editing
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtPrintSupport import *

#import settings
import sqlalchemy
import catalog

from libnmap.parser import NmapParser
import hashlib
import json
import os
import shutil
import sys
import uuid

from math import ceil

APP_PATH = os.path.dirname(os.path.realpath(__file__))+'/'
#FONT_SIZES = [8, 12, 14, 18, 24, 36, 48, 64, 72]
TEXT_STYLES = ['Title', 'Heading', 'Subheading', 'Body']
TEXT_LEVEL = {"Body": 0, "Title": 1, "Heading": 2, "Subheading": 3}
TEXT_SIZE = {"Body": 14, "Title": 26, "Heading": 20, "Subheading": 14}
TEXT_WEIGHT = {"Body": 50, "Title": 75, "Heading": 75, "Subheading": 75}
IMAGE_EXTENSIONS = ['.jpg','.png','.bmp']
HTML_EXTENSIONS = ['.htm', '.html']
NODE_ICON_PATH = os.path.abspath(APP_PATH+'/images/nodes')
ROLE_NODE_UUID = Qt.UserRole + 1
NOTEBOOK_PATH = os.path.abspath(os.path.expanduser('~/default.notebook'))
SETTINGS = os.path.abspath(os.path.expanduser('~/.local/redteamnotebook.cfg'))
OS_ICONS = {'Windows': 'os_win.png', 'Linux': 'os_linux.png', 'Mac OS X': 'os_apple.png', 'FreeBSD': 'os_freebsd.png' }

##
settings = {
'last_open_notebook': NOTEBOOK_PATH
}

## initialize Session for the db
Session = None


def hexuuid():
  return uuid.uuid4().hex

def splitext(p):
  return os.path.splitext(p)[1].lower()

class StandardItem(QStandardItem):
  def __init__(self, txt='', font_size=14, fullref=None, uuid=None, set_bold=False, color=QColor(0, 0, 0)):
    super().__init__()

    fnt = QFont('Helvetica', font_size)
    fnt.setBold(set_bold)

    self.setEditable(True)
    self.setForeground(color)
    self.setFont(fnt)
    self.setText(txt)
    self.setToolTip(txt)
    self.setIcon(QIcon(os.path.join(NODE_ICON_PATH, 'folder.png')))
    self.setEditable(True)
    self.setData(fullref, Qt.UserRole)

    if not uuid:
      uuid = hexuuid()
    self.setData(uuid, ROLE_NODE_UUID)

class CAction(QWidgetAction):
  colorSelected = pyqtSignal(QColor)

  def __init__(self, parent):
    QWidgetAction.__init__(self, parent)
    widget = QWidget(parent)
    layout = QGridLayout(widget)
    layout.setSpacing(0)
    layout.setContentsMargins(2, 2, 2, 2)
    #palette = self.palette()

    ## grab icons from our node path
    icons = os.listdir(NODE_ICON_PATH)
    icons.sort(reverse=True)
    count = len(icons)
    rows = count // round(count ** .5)
    for row in range(rows):
      #for column in range(ceil(count / rows)):
      for column in range(5):
        if not len(icons): break
        icon = ""
        while len(icons) and not icon.endswith('.png'):
          icon = icons.pop()
        button = QToolButton(widget)
        button.setAutoRaise(True)
        button.clicked.connect(lambda : self.handleButton(button))
        button.setIcon(QIcon(os.path.join(NODE_ICON_PATH, icon)))
        button.setText(icon)
        layout.addWidget(button, row, column)
    self.setDefaultWidget(widget)

  def handleButton(self, button):
    ## close the context menu
    self.parent().hide()

    ## grab the item
    window = self.parent().parent()
    treeView = window.treeView
    treeModel = window.treeModel
    idx = treeView.selectedIndexes()
    if not idx: return
    item = treeModel.itemFromIndex(idx[0])
    uuid = item.data(ROLE_NODE_UUID)

    ## change the icon
    item.setIcon(self.sender().icon())

    ## fetch the node from the catalog
    db = Session()
    node = db.query(catalog.NodeGraph).get(uuid)
    ## update the icon in the catalog
    if node:
      node.icon = self.sender().text()
      db.add(node)
      db.commit()
    else:
      print ('[Err] Unable to find node in catalog.')

  #def palette(self):
  #  palette = []
  #  for g in range(4):
  #    for r in range(4):
  #      for b in range(3):
  #        palette.append(QColor(
  #          r * 255 // 3, g * 255 // 3, b * 255 // 2))
  #  return palette

class CMenu(QMenu):
  def __init__(self, parent):
    QMenu.__init__(self, parent)
    self.colorAction = CAction(self)
    self.colorAction.colorSelected.connect(self.handleColorSelected)
    self.addAction(self.colorAction)
    self.addSeparator()

  def handleColorSelected(self, color):
    print(color.name())

class TextEdit(QTextEdit):
  def canInsertFromMimeData(self, source):

    if source.hasImage():
      return True
    else:
      return super(TextEdit, self).canInsertFromMimeData(source)

  def insertFromMimeData(self, source):

    cursor = self.textCursor()
    document = self.document()
    max_width = self.size().width()
    staging_file = 'images/stage.png'

    if source.hasUrls():

      for u in source.urls():
        file_ext = splitext(str(u.toLocalFile()))
        if u.isLocalFile() and file_ext in IMAGE_EXTENSIONS:
          image = QImage(u.toLocalFile())
          image.save(os.path.abspath(staging_file))
          ## get a file hash to rename the staging file
          img_hash = hashlib.md5(open(staging_file,'rb').read()).hexdigest()
          ## save the file in the notebook
          saved_file = f"images/{img_hash}.png"
          shutil.move(staging_file, saved_file)
          # TODO: Resize is broken
          ## resize img if it's larger than the editor
          if image.width() > max_width:
            image = image.scaledToWidth(max_width)
          ## add image to the doc
          document.addResource(QTextDocument.ImageResource, u, image)
          #cursor.insertImage(u.toLocalFile())
          cursor.insertImage(saved_file)

        else:
          ## If we hit a non-image or non-local URL break the loop and fall out
          ## to the super call & let Qt handle it
          break

      else:
        ## If all were valid images, finish here.
        return


    elif source.hasImage():
      ## clipboard content will be processed here
      image = source.imageData()
      uuid = hexuuid()
      document.addResource(QTextDocument.ImageResource, int(uuid, 16), image)
      cursor.insertImage(uuid)
      return

    super(TextEdit, self).insertFromMimeData(source)

  def keyPressEvent(self, event):
    if (event.key() == Qt.Key_Return):
      # we want to insert a regular formatted block when enter is pressed
      cursor = self.textCursor()
      blockFormat = QTextBlockFormat()
      blockFormat.setHeadingLevel(0)
      charFormat = QTextCharFormat()
      charFormat.setFontPointSize(14)
      cursor.insertBlock(blockFormat, charFormat)
    elif (event.key() == Qt.Key_Escape):
      cursor = self.textCursor()
      block = cursor.blockNumber()
      bf = cursor.blockFormat()
      cf = cursor.charFormat()

      print ('block: '+ str(block))
      print ('weight: '+ str(cf.fontWeight()))
    else:
      QTextEdit.keyPressEvent(self, event)

  def onContentsChanged(self):
    if self.updating: return
    self.save_doc = True
    self.updating = True

    ## we can do some format checking here later if we want to

    self.updating = False

    return

  def set_style(self, style):
    if style not in TEXT_STYLES:
      return
    
    ## set our cursor
    cursor = self.textCursor()
    cursor.movePosition(QTextCursor.StartOfBlock)
    cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)

    ## set our formatting
    blockFormat = QTextBlockFormat()
    blockFormat.setHeadingLevel(TEXT_LEVEL[style])
    charFormat = QTextCharFormat()
    charFormat.setFontPointSize(TEXT_SIZE[style])
    charFormat.setFontWeight(TEXT_WEIGHT[style])
    cursor.setBlockFormat(blockFormat)
    cursor.setCharFormat(charFormat)

class CDialog(QDialog):

  def __init__(self, *args, **kwargs):
    super(CDialog, self).__init__(*args, **kwargs)
    
    self.setWindowTitle("Add port")
    
    QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
    
    self.buttonBox = QDialogButtonBox(QBtn)
    self.buttonBox.accepted.connect(self.accept)
    self.buttonBox.rejected.connect(self.reject)

    self.port = QLineEdit(self)
    self.proto = QComboBox(self)
    self.state = QComboBox(self)

    ## set our protocols
    self.proto.addItem('tcp')
    self.proto.addItem('udp')

    ## set our states
    self.state.addItem('open')
    self.state.addItem('closed')
    self.state.addItem('filtered')

    ## set up our layout
    self.layout = QFormLayout()
    self.layout.addRow("Port", self.port)
    self.layout.addRow("Protocol", self.proto)
    self.layout.addRow("State", self.state)

    self.layout.addWidget(self.buttonBox)
    self.setLayout(self.layout)

class MainWindow(QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        #layout = QVBoxLayout()
        layout = QGridLayout()
        layout.setColumnStretch(1,1)
        layout.setSpacing(0)
        layout.setContentsMargins(0,0,0,0)

        self.docs = {}
        #self.doc1 = QTextDocument()
        #self.doc2 = QTextDocument()

        self.editor = TextEdit()
        self.editor.updating = False
        self.editor.new_line = False
        # Setup the QTextEdit editor configuration
        self.editor.setAutoFormatting(QTextEdit.AutoAll)
        self.editor.selectionChanged.connect(self.update_format)
        self.editor.cursorPositionChanged.connect(self.monitor_style)
        #self.editor.textChanged.connect(self.editor.onTextChanged)
        #self.editor.contentsChange.connect(self.editor.onContentsChanged)
        # Initialize default font size.
        font = QFont('Helvetica', 14)
        self.editor.setFont(font)
        # We need to repeat the size to init the current format.
        self.editor.setFontPointSize(14)
        ## start editor disabled, until we click a node
        self.editor.setReadOnly(True)

        # self.path holds the path of the currently open file.
        # If none, we haven't got a file open yet (or creating new).
        self.path = None

        self.treeView = QTreeView()
        self.treeView.setStyleSheet("QTreeView { selection-background-color: #c3e3ff;} ")

        self.treeModel = QStandardItemModel()
        self.treeModel.setHorizontalHeaderLabels(['Targets'])
        rootNode = self.treeModel.invisibleRootItem()

        ## populate our tree
        self.load_nodes_from_catalog(clean=True)

        ## use the model with our view
        self.treeView.setModel(self.treeModel)
        self.treeView.clicked.connect(self.fetch_note)
        self.treeView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.treeView.customContextMenuRequested.connect(self.show_context_menu)

        layout.addWidget(self.treeView,1,0)
        layout.addWidget(self.editor,1,1)

        self.treeModel.dataChanged.connect(self.tree_changed)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.status = QStatusBar()
        self.setStatusBar(self.status)

        # Uncomment to disable native menubar on Mac

        file_toolbar = QToolBar("File")
        file_toolbar.setIconSize(QSize(14, 14))
        self.addToolBar(file_toolbar)
        file_menu = self.menuBar().addMenu("&File")

        open_file_action = QAction(QIcon(os.path.join(APP_PATH+'images', 'blue-folder-open-document.png')), "Open file...", self)
        open_file_action.setStatusTip("Open file")
        open_file_action.triggered.connect(self.file_open)
        file_menu.addAction(open_file_action)
        file_toolbar.addAction(open_file_action)

        new_root_node_action = QAction(QIcon(os.path.join(APP_PATH+'images', 'add-root-node.png')), "New Root Node", self)
        new_root_node_action.setStatusTip("New Root Node")
        new_root_node_action.triggered.connect(self.add_root_node)
        file_menu.addAction(new_root_node_action)
        file_toolbar.addAction(new_root_node_action)

        new_node_action = QAction(QIcon(os.path.join(APP_PATH+'images', 'add-node.png')), "New Node", self)
        new_node_action.setStatusTip("New Node")
        new_node_action.triggered.connect(self.add_node)
        file_menu.addAction(new_node_action)
        file_toolbar.addAction(new_node_action)

        import_nmap_action =  QAction(QIcon(os.path.join(APP_PATH+'images', 'zenmap.png')), "Import NMap", self)
        import_nmap_action.setStatusTip("Import NMap")
        import_nmap_action.triggered.connect(self.import_nmap)
        file_menu.addAction(import_nmap_action)
        file_toolbar.addAction(import_nmap_action)

        #save_file_action = QAction(QIcon(os.path.join('images', 'disk.png')), "Save", self)
        #save_file_action.setStatusTip("Save current page")
        #save_file_action.triggered.connect(self.file_save)
        #file_menu.addAction(save_file_action)
        #file_toolbar.addAction(save_file_action)

        #saveas_file_action = QAction(QIcon(os.path.join('images', 'disk--pencil.png')), "Save As...", self)
        #saveas_file_action.setStatusTip("Save current page to specified file")
        #saveas_file_action.triggered.connect(self.file_saveas)
        #file_menu.addAction(saveas_file_action)
        #file_toolbar.addAction(saveas_file_action)

        print_action = QAction(QIcon(os.path.join(APP_PATH+'images', 'printer.png')), "Print...", self)
        print_action.setStatusTip("Print current page")
        print_action.triggered.connect(self.file_print)
        file_menu.addAction(print_action)
        file_toolbar.addAction(print_action)

        edit_toolbar = QToolBar("Edit")
        edit_toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(edit_toolbar)
        edit_menu = self.menuBar().addMenu("&Edit")

        undo_action = QAction(QIcon(os.path.join(APP_PATH+'images', 'arrow-curve-180-left.png')), "Undo", self)
        undo_action.setStatusTip("Undo last change")
        undo_action.triggered.connect(self.editor.undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction(QIcon(os.path.join(APP_PATH+'images', 'arrow-curve.png')), "Redo", self)
        redo_action.setStatusTip("Redo last change")
        redo_action.triggered.connect(self.editor.redo)
        edit_toolbar.addAction(redo_action)
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        cut_action = QAction(QIcon(os.path.join(APP_PATH+'images', 'scissors.png')), "Cut", self)
        cut_action.setStatusTip("Cut selected text")
        cut_action.setShortcut(QKeySequence.Cut)
        cut_action.triggered.connect(self.editor.cut)
        edit_toolbar.addAction(cut_action)
        edit_menu.addAction(cut_action)

        copy_action = QAction(QIcon(os.path.join(APP_PATH+'images', 'document-copy.png')), "Copy", self)
        copy_action.setStatusTip("Copy selected text")
        cut_action.setShortcut(QKeySequence.Copy)
        copy_action.triggered.connect(self.editor.copy)
        edit_toolbar.addAction(copy_action)
        edit_menu.addAction(copy_action)

        paste_action = QAction(QIcon(os.path.join(APP_PATH+'images', 'clipboard-paste-document-text.png')), "Paste", self)
        paste_action.setStatusTip("Paste from clipboard")
        cut_action.setShortcut(QKeySequence.Paste)
        paste_action.triggered.connect(self.editor.paste)
        edit_toolbar.addAction(paste_action)
        edit_menu.addAction(paste_action)

        select_action = QAction(QIcon(os.path.join(APP_PATH+'images', 'selection-input.png')), "Select all", self)
        select_action.setStatusTip("Select all text")
        cut_action.setShortcut(QKeySequence.SelectAll)
        select_action.triggered.connect(self.editor.selectAll)
        edit_menu.addAction(select_action)

        edit_menu.addSeparator()

        wrap_action = QAction(QIcon(os.path.join(APP_PATH+'images', 'arrow-continue.png')), "Wrap text to window", self)
        wrap_action.setStatusTip("Toggle wrap text to window")
        wrap_action.setCheckable(True)
        wrap_action.setChecked(True)
        wrap_action.triggered.connect(self.edit_toggle_wrap)
        edit_menu.addAction(wrap_action)

        format_toolbar = QToolBar("Format")
        format_toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(format_toolbar)
        format_menu = self.menuBar().addMenu("&Format")

        # We need references to these actions/settings to update as selection changes, so attach to self.
        self.fonts = QFontComboBox()
        self.fonts.currentFontChanged.connect(self.editor.setCurrentFont)
        #format_toolbar.addWidget(self.fonts)

        self.stylebox = QComboBox()
        self.stylebox.addItems(TEXT_STYLES)

        #self.fontsize = QComboBox()
        #self.fontsize.addItems([str(s) for s in FONT_SIZES])

        ## Connect to the signal producing the text of the current selection. Convert the string to float
        ## and set as the pointsize. We could also use the index + retrieve from FONT_SIZES.
        #self.fontsize.currentIndexChanged[str].connect(lambda s: self.editor.setFontPointSize(float(s)) )
        #format_toolbar.addWidget(self.fontsize)

        self.stylebox.setCurrentIndex(3)
        self.stylebox.currentIndexChanged[str].connect(lambda s: self.setStyle(s) )
        format_toolbar.addWidget(self.stylebox)

        self.bold_action = QAction(QIcon(os.path.join(APP_PATH+'images', 'edit-bold.png')), "Bold", self)
        self.bold_action.setStatusTip("Bold")
        self.bold_action.setShortcut(QKeySequence.Bold)
        self.bold_action.setCheckable(True)
        self.bold_action.toggled.connect(lambda x: self.editor.setFontWeight(QFont.Bold if x else QFont.Normal))
        format_toolbar.addAction(self.bold_action)
        format_menu.addAction(self.bold_action)

        self.italic_action = QAction(QIcon(os.path.join(APP_PATH+'images', 'edit-italic.png')), "Italic", self)
        self.italic_action.setStatusTip("Italic")
        self.italic_action.setShortcut(QKeySequence.Italic)
        self.italic_action.setCheckable(True)
        self.italic_action.toggled.connect(self.editor.setFontItalic)
        format_toolbar.addAction(self.italic_action)
        format_menu.addAction(self.italic_action)

        self.underline_action = QAction(QIcon(os.path.join(APP_PATH+'images', 'edit-underline.png')), "Underline", self)
        self.underline_action.setStatusTip("Underline")
        self.underline_action.setShortcut(QKeySequence.Underline)
        self.underline_action.setCheckable(True)
        self.underline_action.toggled.connect(self.editor.setFontUnderline)
        format_toolbar.addAction(self.underline_action)
        format_menu.addAction(self.underline_action)

        format_menu.addSeparator()

        self.alignl_action = QAction(QIcon(os.path.join(APP_PATH+'images', 'edit-alignment.png')), "Align left", self)
        self.alignl_action.setStatusTip("Align text left")
        self.alignl_action.setCheckable(True)
        self.alignl_action.triggered.connect(lambda: self.editor.setAlignment(Qt.AlignLeft))
        #format_toolbar.addAction(self.alignl_action)
        #format_menu.addAction(self.alignl_action)

        self.alignc_action = QAction(QIcon(os.path.join(APP_PATH+'images', 'edit-alignment-center.png')), "Align center", self)
        self.alignc_action.setStatusTip("Align text center")
        self.alignc_action.setCheckable(True)
        self.alignc_action.triggered.connect(lambda: self.editor.setAlignment(Qt.AlignCenter))
        #format_toolbar.addAction(self.alignc_action)
        #format_menu.addAction(self.alignc_action)

        self.alignr_action = QAction(QIcon(os.path.join(APP_PATH+'images', 'edit-alignment-right.png')), "Align right", self)
        self.alignr_action.setStatusTip("Align text right")
        self.alignr_action.setCheckable(True)
        self.alignr_action.triggered.connect(lambda: self.editor.setAlignment(Qt.AlignRight))
        #format_toolbar.addAction(self.alignr_action)
        #format_menu.addAction(self.alignr_action)

        self.alignj_action = QAction(QIcon(os.path.join(APP_PATH+'images', 'edit-alignment-justify.png')), "Justify", self)
        self.alignj_action.setStatusTip("Justify text")
        self.alignj_action.setCheckable(True)
        self.alignj_action.triggered.connect(lambda: self.editor.setAlignment(Qt.AlignJustify))
        #format_toolbar.addAction(self.alignj_action)
        #format_menu.addAction(self.alignj_action)

        format_group = QActionGroup(self)
        format_group.setExclusive(True)
        format_group.addAction(self.alignl_action)
        format_group.addAction(self.alignc_action)
        format_group.addAction(self.alignr_action)
        format_group.addAction(self.alignj_action)

        format_menu.addSeparator()

        # A list of all format-related widgets/actions, so we can disable/enable signals when updating.
        self._format_actions = [
            self.fonts,
        #    self.fontsize,
            self.bold_action,
            self.italic_action,
            self.underline_action,
            # We don't need to disable signals for alignment, as they are paragraph-wide.
        ]

        ## change toolbar styles
        toolbar_style = "windows"
        #self.setStyleSheet("background: white;")
        #file_toolbar.setStyle(QStyleFactory.create(toolbar_style))
        file_toolbar.setMovable(False)
        #edit_toolbar.setStyle(QStyleFactory.create(toolbar_style))
        edit_toolbar.setMovable(False)
        #format_toolbar.setStyle(QStyleFactory.create(toolbar_style))
        self.status.setStyle(QStyleFactory.create(toolbar_style))

        # Initialize.
        self.update_format()
        self.update_title()
        self.resize(700,400)
        self.show()

        ## set flag for auto saves
        self.editor.save_doc = False

        ## setup our timer to auto save docs
        timer = QTimer(self)
        timer.timeout.connect(self.timeout_save)
        timer.start(5000)

    def monitor_style(self):
      if self.editor.updating == True:
        return
      ## set our cursor
      cursor = self.editor.textCursor()
      blockFormat = cursor.blockFormat()
      
      ## lock updates before we change the style
      self.editor.updating = True
      ## make sure our style box reflects the style under the cursor
      for level in TEXT_LEVEL:
        if (blockFormat.headingLevel() == TEXT_LEVEL[level]):
          self.stylebox.setCurrentText(level)
      self.editor.updating = False
      
    def setStyle(self, style):
      self.editor.set_style(style)

    def timeout_save(self):
      if self.editor.save_doc:
        ## save editor content to catalog
        db = Session()
        note = catalog.Note()
        note.nodeid = self.get_nodeid()
        note.content = self.editor.toMarkdown()
        ## only save if the nodeid is valid
        if (not note.nodeid):
          self.editor.save_doc = False
          return
        db.add(note)
        db.commit()
        print ("[Info] Saved.")
        self.editor.save_doc = False

    def tree_changed(self, signal):
      ## see what changed
      root = self.treeView.model().invisibleRootItem()
      node = self.treeView.selectedIndexes()
      if not node:
        print ('[Err] Unable to find selectedIndexes().')
        return
      basename = node[0].data(Qt.DisplayRole)
      uuid =  node[0].data(ROLE_NODE_UUID)
      ## fetch the node from the catalog
      db = Session()
      node = db.query(catalog.NodeGraph).get(uuid)
      ## update the basename in the catalog
      if node:
        node.basename = basename
        db.add(node)
        db.commit()
      else:
        print (f'[Err] Unable to find node ({uuid}) in catalog.')
      return

    def show_context_menu(self, position):
      ## do we have a selection?
      node = self.treeView.selectedIndexes()

      ## build our menu
      menu = CMenu(self)

      if node:
        #remove_action = menu.addAction("&Change Icon")
        new_port_action = QAction("&Add Port")
        new_port_action.triggered.connect(self.add_port)
        menu.addAction(new_port_action)

        delete_node_action = QAction("&Remove Node")
        delete_node_action.triggered.connect(self.delete_node)
        menu.addAction(delete_node_action)

      ## show our menu
      menu.exec_(self.sender().viewport().mapToGlobal(position))


    def add_port(self):
      node = self.treeView.selectedIndexes()[0]
      if not node: return None

      ## grab our id for later
      parentid = node.data(ROLE_NODE_UUID)

      dlg = CDialog(self)
      dlg.setWindowTitle("Add a port")
      accepted = dlg.exec_()
      if not accepted: return

      port = dlg.port.text()
      proto = dlg.proto.currentText()
      state = dlg.state.currentText()

      ## init our node vars
      proto_node = None
      # TODO: map desc to service name
      desc = ''

      if node.data(Qt.DisplayRole) == proto:
        proto_node = self.treeModel.itemFromIndex(node)
      else:
        ## find our protocol node
        rootNode = self.treeModel.itemFromIndex(node)
        for item in self.iterItems(rootNode):
          if item.data(Qt.DisplayRole) == proto:
            proto_node = item

      if not proto_node:
        ## add a node if we couldn't find one
        uuid = self.add_node(name=proto, parentid=parentid)
      else:
        uuid = proto_node.data(ROLE_NODE_UUID)

      ## set our node icon
      if state == 'closed':
        icon = 'stat_red.png'
      elif state == 'filtered':
        icon = 'stat_yellow.png'
      else:
        icon = 'stat_green.png'

      ## add port to protocol node
      portid = self.add_node(name=f'{port} {desc} [{state}]', parentid=uuid, icon=icon)

    def delete_node(self):
      node = self.treeView.selectedIndexes()[0]
      if not node: return None
      confirmed = QMessageBox.question(self, "Delete", f"Are you sure you want to delete '{node.data(Qt.DisplayRole)}'?", QMessageBox.Yes|QMessageBox.No)
      if confirmed == QMessageBox.No:
        return

      node = self.treeView.selectedIndexes()[0]
      if not node: return None

      db = Session()
      rootNode = self.treeModel.itemFromIndex(node)

      ## remove children from catalog
      for item in self.iterItems(rootNode):
        ## remove node graph
        db_node = db.query(catalog.NodeGraph).get(item.data(ROLE_NODE_UUID))
        if db_node:
          db.delete(db_node)
        ## remove note
        db_node = db.query(catalog.Note).get(item.data(ROLE_NODE_UUID)) 
        if db_node:
          db.delete(db_node)


      ## remove node from catalog
      db_node = db.query(catalog.NodeGraph).get(rootNode.data(ROLE_NODE_UUID)) 
      if db_node:
        db.delete(db_node)
      db_node = db.query(catalog.Note).get(rootNode.data(ROLE_NODE_UUID)) 
      if db_node:
        db.delete(db_node)

      db.commit()

      ## remove node from tree
      self.treeModel.removeRow(node.row(), parent=node.parent())

    def iterItems(self, root):
      def recurse(parent):
        for row in range(parent.rowCount()):
          for column in range(parent.columnCount()):
            child = parent.child(row, column)
            yield child
            if child.hasChildren():
              yield from recurse(child)
      if root is not None:
        yield from recurse(root)

    def load_nodes_from_catalog(self, parentid=None, clean=False):
      ## if clean is set, clear out tree and docs before loading catalog
      if clean:
        self.docs = {}
        #self.treeView.reset()
        rootNode = self.treeModel.invisibleRootItem()
        if (rootNode.hasChildren()):
          rootNode.removeRows(0, rootNode.rowCount())

      ## load data from sql
      db = Session()
      nodes = db.query(catalog.NodeGraph).filter_by(parentid=parentid).all()
      for node in nodes:
        if not parentid:
          self.add_root_node(name=node.basename, uuid=node.nodeid, icon=node.icon)
        else:
          self.add_node(name=node.basename, uuid=node.nodeid, parentid=parentid, icon=node.icon)
        ## add child nodes, recursively
        self.load_nodes_from_catalog(node.nodeid)
        ## set content of this node
        ## TODO: maybe we implement lazy loading?
        note = db.query(catalog.Note).get(node.nodeid)
        if note:
          self.docs[node.nodeid].setMarkdown(note.content)
      return

    def get_nodeid(self):
      node = self.treeView.selectedIndexes()
      if not node: return None
      fullref = node[0].data(Qt.UserRole)
      uuid = node[0].data(ROLE_NODE_UUID)
      return uuid
      
    def itemFromUUID(self, uuid):
      rootNode = self.treeModel.invisibleRootItem()
      for item in self.iterItems(rootNode):
        if item.data(ROLE_NODE_UUID) == uuid:
          return item
      return None

    def fetch_note(self, signal):
      uuid = self.get_nodeid()

      #if not uuid return
      if not uuid: return

      ## make sure we don't write the text we just loaded
      self.editor.updating = True
      ## display the proper doc
      self.editor.setDocument(self.docs[uuid])
      ## make sure we can edit
      self.editor.setReadOnly(False)
      ## allow saving changes again
      self.editor.updating = False

    def add_root_node(self, name='Node', uuid=None, icon=None):
      record_catalog = False
      if not name:
        name = 'Node'
      if not uuid:
        uuid = hexuuid()
        record_catalog = True
        print ('[Info] Recording in catalog...')
      rootNode = self.treeModel.invisibleRootItem()
      fullref = '/'+name
      new_node = StandardItem(name, 14, fullref=fullref, uuid=uuid)
      if icon:
        new_node.setIcon(QIcon(os.path.join(NODE_ICON_PATH, icon)))
      rootNode.appendRow(new_node)
      idx = self.itemFromUUID(uuid)
      ## select the new node in the tree
      if idx:
        self.treeView.setCurrentIndex(idx.index())
      self.docs[uuid] = QTextDocument()
      doc = self.docs[uuid]
      doc.contentsChange.connect(self.editor.onContentsChanged)

      if record_catalog:
        ## record in catalog
        db = Session()
        node = catalog.NodeGraph()
        node.nodeid = uuid
        node.parentid = None
        node.basename = name
        db.add(node)
        db.commit()

    def add_node(self, name='Node', uuid=None, parentid=None, icon=None):
      record_catalog = False
      if not name:
        name = 'Node'
      if not uuid:
        uuid = hexuuid()
        record_catalog = True

      ## we will either be given a parent id or check for the selected item in the tree
      idx = None
      if parentid:
        rootNode = self.treeModel.invisibleRootItem()
        for item in self.iterItems(rootNode):
          if item.data(ROLE_NODE_UUID) == parentid:
            parent_node = item
            break
        ## if we got here, the parentid is bad
        #return
      else:
        idx = self.treeView.selectedIndexes()
        if not idx: return
        parent_node = self.treeModel.itemFromIndex(idx[0])

      parent_fullref = parent_node.data(Qt.UserRole)
      fullref = f'{parent_fullref}/Node'

      new_node = StandardItem(name, 14, fullref=fullref, uuid=uuid)
      if icon:
        new_node.setIcon(QIcon(os.path.join(NODE_ICON_PATH, icon)))
      parent_node.appendRow(new_node)
      self.docs[uuid] = QTextDocument()
      if idx:
        self.treeView.setExpanded(idx[0], True)

      if record_catalog:
        print ('[Info] Recording in catalog...')
        ## record in catalog
        db = Session()
        node = catalog.NodeGraph()
        node.nodeid = uuid
        node.parentid = parent_node.data(ROLE_NODE_UUID)
        node.basename = name
        node.icon = icon
        db.add(node)
        db.commit()

      return uuid

    def block_signals(self, objects, b):
        for o in objects:
            o.blockSignals(b)

    def update_format(self):
        """
        Update the font format toolbar/actions when a new text selection is made. This is neccessary to keep
        toolbars/etc. in sync with the current edit state.
        :return:
        """
        # Disable signals for all format widgets, so changing values here does not trigger further formatting.
        self.block_signals(self._format_actions, True)

        self.fonts.setCurrentFont(self.editor.currentFont())
        # Nasty, but we get the font-size as a float but want it was an int
        #self.fontsize.setCurrentText(str(int(self.editor.fontPointSize())))

        self.italic_action.setChecked(self.editor.fontItalic())
        self.underline_action.setChecked(self.editor.fontUnderline())
        self.bold_action.setChecked(self.editor.fontWeight() == QFont.Bold)

        self.alignl_action.setChecked(self.editor.alignment() == Qt.AlignLeft)
        self.alignc_action.setChecked(self.editor.alignment() == Qt.AlignCenter)
        self.alignr_action.setChecked(self.editor.alignment() == Qt.AlignRight)
        self.alignj_action.setChecked(self.editor.alignment() == Qt.AlignJustify)

        self.block_signals(self._format_actions, False)

    def dialog_critical(self, s):
        dlg = QMessageBox(self)
        dlg.setText(s)
        dlg.setIcon(QMessageBox.Critical)
        dlg.show()

    def file_open(self):
        global NOTEBOOK_PATH

        ## lock updates
        self.save_doc = False
        self.updating = True

        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.DirectoryOnly)
        dialog.exec()
        path = dialog.selectedFiles()

        if not path:
          return

        ## don't reopen the same notebook
        new_path = os.path.abspath(os.path.expanduser(path[0]))
        if NOTEBOOK_PATH == new_path:
          return

        ## we should init the notebook here
        NOTEBOOK_PATH = new_path
        print (f'[Info] Opening notebook "{NOTEBOOK_PATH}"')

        ## change the session to match the new file
        set_session()

        ## init the notebook
        init_notebook()

        self.load_nodes_from_catalog(clean=True)
        self.update_title()
        self.editor.setDocument(None)
        self.editor.setReadOnly(True)

        ## update configs
        settings['last_open_notebook'] = NOTEBOOK_PATH
        save_settings()

        ## unlock
        self.updating = False

    #def file_save(self):
    #    if self.path is None:
    #        # If we do not have a path, we need to use Save As.
    #        return self.file_saveas()

    #    text = self.editor.toHtml() if splitext(self.path) in HTML_EXTENSIONS else self.editor.toPlainText()

    #    try:
    #        with open(self.path, 'w') as f:
    #            f.write(text)

    #    except Exception as e:
    #        self.dialog_critical(str(e))

    #def file_saveas(self):
    #    path, _ = QFileDialog.getSaveFileName(self, "Save file", "", "HTML documents (*.html);Text documents (*.txt);All files (*.*)")

    #    if not path:
    #        # If dialog is cancelled, will return ''
    #        return

    #    text = self.editor.toHtml() if splitext(path) in HTML_EXTENSIONS else self.editor.toPlainText()

    #    try:
    #        with open(path, 'w') as f:
    #            f.write(text)

    #    except Exception as e:
    #        self.dialog_critical(str(e))

    #    else:
    #        self.path = path
    #        self.update_title()

    def file_print(self):
      dlg = QPrintDialog()
      if dlg.exec_():
        self.editor.print_(dlg.printer())

    def update_title(self):
      self.setWindowTitle("%s - Redteam Notebook" % (os.path.basename(self.path) if self.path else "Untitled"))

    def edit_toggle_wrap(self):
      self.editor.setLineWrapMode( 1 if self.editor.lineWrapMode() == 0 else 0 )

    def import_nmap(self):
      msg = QMessageBox()
      idx = self.treeView.selectedIndexes()[0]
      if not idx:
        msg.setIcon(QMessageBox.Warning)
        msg.setText("Please select a node before importing.")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
        return

      ## grab our id for later
      parentid = idx.data(ROLE_NODE_UUID)

      ## open a dialog to select our file
      dialog = QFileDialog()
      filter = 'nmap xml file (*.xml)'
      filename = dialog.getOpenFileName(None, 'Import NMap XML', '', filter)[0]

      ## If we cancelled the dialog, just return
      if not filename:
        return

      ## make sure the filename is valid
      if not os.path.exists(filename):
        msg.setIcon(QMessageBox.Critical)
        msg.setText("Unable to open file!")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
        return

      ## lock updates
      self.save_doc = False
      self.updating = True

      ## read xml file
      nmap_report = NmapParser.parse_fromfile(filename)

      ## load results into tree
      for host in nmap_report.hosts:
        if not host.is_up():
          continue
        hostid = None
        icon = 'question.png'
        ## generate the host label
        if host.hostnames:
          label = f'{host.address} ({host.hostnames[0]})'
        else:
          label = f'{host.address}'

        ## search for an OS icon
        for c in host.os_class_probabilities():
          if c.osfamily in OS_ICONS:
            icon = OS_ICONS[c.osfamily]
            break

        ## add our node
        hostid = self.add_node(name=label, parentid=parentid, icon=icon)
        if not hostid: continue

        for service in host.services:
          ## make sure we put services in the correct node
          ### find our protocol node
          proto_node = None
          rootNode = self.itemFromUUID(hostid)
          for item in self.iterItems(rootNode):
            if item.data(Qt.DisplayRole) == service.protocol:
              proto_node = item

          if not proto_node:
            ### add a node if we couldn't find one
            uuid = self.add_node(name=service.protocol, parentid=rootNode.data(ROLE_NODE_UUID))
          else:
            ### use the node we found
            uuid = proto_node.data(ROLE_NODE_UUID)

          ## set our node icon
          if service.state == 'closed':
            icon = 'stat_red.png'
          elif service.state == 'filtered':
            icon = 'stat_yellow.png'
          else:
            icon = 'stat_green.png'
          ## add port to protocol node
          portid = self.add_node(name=f'{service.port} {service.protocol} [{service.state}]', parentid=uuid, icon=icon)

      self.updating = False

def init_sql(sql_path):
  print ('[Info] Setting up sql...')
  ## create our tables
  db_engine = sqlalchemy.create_engine(f'sqlite:///{NOTEBOOK_PATH}/catalog.sqlite', convert_unicode=True, echo=True)
  #try:
  #  catalog.NodeGraph.__table__.create(bind=db_engine, checkfirst=True)
  #  catalog.Note.__table__.create(bind=db_engine, checkfirst=True)
  #except:
  #  raise

  ## apparently, sqlalchemy does not yet support ON CASCADE REPLACE, so we need to pass
  ## some raw SQL to create our schema

  db = db_engine.connect()

  sql = """CREATE TABLE IF NOT EXISTS node_graph (
  nodeid TEXT,
  parentid TEXT,
  basename TEXT,
  icon TEXT,
  mtime FLOAT,
  UNIQUE(nodeid)
);"""
  result = db.execute(sql)

  sql = """CREATE TABLE IF NOT EXISTS notes (
  nodeid TEXT,
  content TEXT,
  mtime FLOAT,
  UNIQUE(nodeid) ON CONFLICT REPLACE,
  CONSTRAINT fk_nodeid
    FOREIGN KEY (nodeid)
    REFERENCES node_graph(nodeid)
    ON DELETE CASCADE
);"""
  result = db.execute(sql)

def set_session():
  global Session
  db_engine = sqlalchemy.create_engine(f'sqlite:///{NOTEBOOK_PATH}/catalog.sqlite', convert_unicode=True)
  Session = sqlalchemy.orm.sessionmaker(bind=db_engine)

def init_notebook():
  ## create the default notebook if it doesn't exist
  if not os.path.exists(NOTEBOOK_PATH):
    os.mkdir(NOTEBOOK_PATH)
    if not os.path.exists(NOTEBOOK_PATH):
      print('[Err] Unable to create default notebook.')
      sys.exit(1)
  if not os.path.exists(NOTEBOOK_PATH+'/images'):
    os.mkdir(NOTEBOOK_PATH+'/images')
  if not os.path.exists(NOTEBOOK_PATH+'/catalog.sqlite'):
    init_sql(NOTEBOOK_PATH)
  if not Session:
    set_session()
  ## make sure our cwd is the path of the notebook
  os.chdir(NOTEBOOK_PATH)

def save_settings():
  with open(SETTINGS, 'w') as fp:
    json.dump(settings, fp)

if __name__ == '__main__':
  if not os.path.exists(SETTINGS):
    save_settings()
  else:
    with open(SETTINGS) as fp:
      settings = json.load(fp)
      NOTEBOOK_PATH = settings['last_open_notebook']

  ## get our configs
  init_notebook()
  
  app = QApplication(sys.argv)
  app.setApplicationName("Redteam Notebook")

  window = MainWindow()
  app.exec_()
