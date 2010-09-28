import os
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import utube

class NewDlg (QDialog):
	
	def __init__ (self, parent=None):
		super (NewDlg, self).__init__(parent)
		self.parent = parent
		
		icon = lambda name: QIcon(os.path.dirname(__file__)+'/icons/'+name)
		
		urlLabel = QLabel ('URL:')
		self.urlEdit = QLineEdit()
		
		savetoLabel = QLabel ('Save to:')
		self.savetoEdit = QLineEdit ( os.getcwd() )
		browseButton = QToolButton ()
		browseButton.setIcon ( icon('document-open.png') )
		
		self.startDownload = QCheckBox('Start download immediately')
		self.startDownload.setChecked (True)
		
		buttonBox = QDialogButtonBox ( QDialogButtonBox.Ok | QDialogButtonBox.Cancel )
		
		grid = QGridLayout()
		grid.addWidget (urlLabel, 0, 0)
		grid.addWidget (self.urlEdit, 0, 1, 1, 2)
		grid.addWidget (savetoLabel, 1, 0)
		grid.addWidget (self.savetoEdit, 1, 1)
		grid.addWidget (browseButton, 1, 2)
		grid.addWidget (self.startDownload, 2, 0, 1, 3)
		grid.addWidget (buttonBox, 3, 0, 1, 3)
		self.setLayout (grid)
		self.setWindowTitle ('New Download')
		#self.resize (self.size().height(), 444)
		
		self.connect (browseButton, SIGNAL('clicked()'), self.browse)
		self.connect (buttonBox, SIGNAL('accepted()'), self.check_accept)
		self.connect (buttonBox, SIGNAL('rejected()'), self, SLOT('reject()'))

	def browse (self):
		self.savetoEdit.setText ( QFileDialog.getExistingDirectory(self) )
	
	def check_accept (self):
		url = str(self.urlEdit.text()).strip()
		if ( utube.valid(url) ):
			self.vid_id = utube.get_video_id (url).decode('utf-8')
			cnt = self.parent.table.topLevelItemCount()
			for i in range (cnt):
				curr = self.parent.table.topLevelItem (i)
				if curr.vid_id == self.vid_id:
					QMessageBox.critical (self, 'Already there', 'This video is already in the list.')
					return
			self.accept()
		else:
			QMessageBox.critical (self, 'Invalid URL', 'Invalid URL:\n'+url)
