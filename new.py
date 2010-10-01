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
		self.savetoEdit = QLineEdit ( parent.download_dir )
		browseButton = QToolButton ()
		browseButton.setIcon ( icon('document-open.png') )
		
		self.startDownload = QCheckBox('Add to download queue')
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
		self.urlEdit.setText ( url.split('&')[0] )
		if ( utube.valid(url) ):
			self.vid_id = utube.get_video_id (url).decode('utf-8')
			cnt = self.parent.table.topLevelItemCount()
			for i in range (cnt):
				curr = self.parent.table.topLevelItem (i)
				if curr.vid_id == self.vid_id:
					QMessageBox.critical (self, 'Already there', curr.title+' is already in the list.')
					return
			saveTo = str(self.savetoEdit.text())
			if os.access ( saveTo, os.F_OK ):
				if os.access ( saveTo, os.W_OK ):
					self.accept()
				else:
					QMessageBox.critical (self, 'Permission Error', 'You do not have write permission on the directory.\nPlease select another directory.')
			else:
				b = QMessageBox.question (self, 'Error', saveTo+' does not exist.\nDo you want to create it?', QMessageBox.Yes|QMessageBox.No)
				if b==QMessageBox.Yes:
					try:
						os.makedirs (saveTo)
						self.accept()
					except Exception as err:
						QMessageBox.critical (self, 'Error', str(err))
		else:
			QMessageBox.critical (self, 'Invalid URL', 'Invalid URL:\n'+url)
