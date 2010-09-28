#!/usr/bin/env python

import os
import sys
import time
import urllib2
from PyQt4.QtCore import *
from PyQt4.QtGui import *

import utube

__author__ = "Viranch Mehta"
__author_email__ = "viranch.mehta@gmail.com"
__version__ = '0.9'

class Item (QTreeWidgetItem):

	def __init__ (self, ref_url, target_dir, vid_id, parent, columns):
		super (Item, self).__init__(parent, columns)
		self.parent = parent
		self.ref_url = ref_url
		self.target = target_dir
		self.vid_id = vid_id
		
		self.title = 'This video'
		self.length = 0
		self.pbar = QProgressBar()
		self.downloader = QThread()
		self.downloader.run = self.download
		self.stop_download = False
		self.t = QThread()
		self.t.run = self.extract_info
		self.t.start()

	def extract_info (self):
		self.setText (1, 'Extracting info')
		info = utube.get_video_info(self.ref_url)
		if info == None:
			self.t.emit (SIGNAL('error()'))
			self.setText (1, 'Error')
			self.stop_download = True
			return
		self.url = info['url']
		self.uploader = info['uploader']
		if info['title']!='':
			self.title = info['title']
			self.stitle = info['stitle']
		else:
			self.stitle = self.text(0)
		self.ext = info['ext']
		self.format = info['format']
		self.thumbnail = info['thumbnail']
		self.description = info['description']
		self.player_url = info['player_url']
		
		self.setText (0, self.title)
		self.setText (4, self.ext+' ('+str(self.format)+')')
		self.target = self.target+os.sep+self.stitle+'.'+self.ext
		self.setText (5, self.target)
		self.setText (1, '')
		self.getSize()

	def getSize (self):
		req = urllib2.Request(self.url, None, utube.std_headers)
		f = urllib2.urlopen ( req )
		self.length = int( f.info()['Content-length'] )
		f.close()
		if self.length > 1024*1024:
			self.setText ( 3, str(round(self.length/1024.0/1024.0, 2))+' MB' )
		elif self.length > 1024:
			self.setText ( 3, str(round(self.length/1024.0, 2))+' KB' )
		else:
			self.setText ( 3, str(self.length)+' B' )
		self.pbar.setRange (0, self.length)
		if os.path.isfile (self.target):
			self.downloader.emit ( SIGNAL('doneSize(int)'), os.path.getsize(self.target) )

	def download (self):
		if self.stop_download:
			return
		self.setText (1, 'Downloading')
		done_size = 0
		req = urllib2.Request(self.url, None, utube.std_headers)
		open_mode = 'wb'
		if os.path.isfile (self.target):
			done_size = os.path.getsize (self.target)
			req.add_header ('Range', 'bytes=%d-' % done_size)
			open_mode = 'ab'
		self.downloader.emit (SIGNAL('doneSize(int)'), done_size)
		if done_size>=self.length:
			self.setText (1, 'Complete')
			return
		
		vid = open ( self.target, open_mode )
		f = urllib2.urlopen ( req )
		while done_size<self.length and not self.stop_download:
			s = f.read (1024*5)
			vid.write (s)
			done_size += len(s)
			self.downloader.emit (SIGNAL('doneSize(int)'), done_size)
		f.close()
		vid.close()
		if self.stop_download:
			self.setText (1, 'Paused')
		else:
			self.setText (1, 'Complete')

class MainWindow(QMainWindow):

	def __init__ ( self, parent=None ):
		super (MainWindow, self).__init__(parent)

		icon = lambda name: QIcon (os.path.dirname(__file__)+'/icons/'+name)

		self.toolbar = self.addToolBar ('Toolbar')
		self.status = self.statusBar()
		self.status.showMessage ('Ready')

		self.table = QTreeWidget()
		headerItem = self.table.headerItem()
		headerItem.setIcon (0, QIcon(icon('applications-multimedia.png')))
		headerItem.setText (0, 'Title')
		#headerItem.setIcon (1, QIcon(icon('flag-green.png')))
		headerItem.setText (1, 'Status')
		#headerItem.setIcon (2, QIcon(icon('flag-red.png')))
		headerItem.setText (2, 'Downloaded')
		#headerItem.setIcon (3, QIcon(icon('edit-copy.png')))
		headerItem.setText (3, 'Size')
		#headerItem.setIcon (4, QIcon(icon('edit-copy.png')))
		headerItem.setText (4, 'Format')
		#headerItem.setIcon (5, QIcon(icon('flag-green.png')))
		headerItem.setText (5, 'Location')
		self.table.setRootIsDecorated (False)

		addAction = self.createAction ('Add', self.add, QKeySequence.New, 'Add...', icon('document-new.png'))
		rmAction = self.createAction ('Remove', self.remove, QKeySequence.Delete, 'Remove', icon('edit-delete.png'))
		clearAction = self.createAction ('Clear', self.clear, 'Shift+Del', 'Clear', icon('edit-clear-list.png'))
		startAction = self.createAction ('Start/Resume', self.download, QKeySequence.Save, 'Start/Resume Download', icon('media-playback-start.png'))
		pauseAction = self.createAction ('Pause', self.pause, None, 'Pause Download', icon('media-playback-pause.png'))
		aboutAction = self.createAction ('About', self.about, None, 'About', icon('help-about.png'))
		quitAction = self.createAction ('Quit', self.quit, 'Ctrl+Q', 'Quit', icon('application-exit.png'))
		
		self.toolbar.addAction ( addAction )
		self.toolbar.addAction ( rmAction )
		self.toolbar.addAction ( clearAction )
		self.toolbar.addSeparator()
		self.toolbar.addAction ( startAction )
		self.toolbar.addAction ( pauseAction )
		self.toolbar.addSeparator()
		self.toolbar.addAction ( aboutAction )
		self.toolbar.addAction ( quitAction )
		
		self.tray = QSystemTrayIcon()
		self.tray.setIcon ( icon('tool-animator.png') )
		self.tray.setVisible (True)
		self.trayMenu = QMenu()
		toggleAction = self.createAction ('Show/Hide', self.toggleWindow)
		self.trayMenu.addAction (toggleAction)
		self.trayMenu.addSeparator()
		self.trayMenu.addAction (quitAction)

		self.setCentralWidget (self.table)
		self.setWindowTitle ('WeTube')
		self.setWindowIcon ( QIcon(icon('acroread.png')) )
		
		self.connect ( self.tray, SIGNAL('activated(QSystemTrayIcon::ActivationReason)'), self.toggleWindow )

	def add (self):
		import new
		dlg = new.NewDlg(self)
		if dlg.exec_():
			url = str(dlg.urlEdit.text()).strip()
			new_item = Item (url, str(dlg.savetoEdit.text()), dlg.vid_id, self.table, ['video_'+str(dlg.vid_id), '', '', '', '', ''])
			self.table.addTopLevelItem ( new_item )
			self.table.setItemWidget ( new_item, 2, new_item.pbar )
			self.status.showMessage ('Video added.', 5000)
			self.connect (new_item.t, SIGNAL('error()'), self.trouble)
			self.connect (new_item.downloader, SIGNAL('doneSize(int)'), new_item.pbar.setValue)
			if dlg.startDownload.isChecked():
				if new_item.t.isRunning():
					self.connect (new_item.t, SIGNAL('finished()'), new_item.downloader.start)
				elif not new_item.stop_download:
					new_item.downloader.start()

	def remove (self):
		if self.table.topLevelItemCount() == 0:
			self.status.showMessage ('Nothing to remove!', 5000)
			return None
		curr = self.table.currentItem()
		if curr is None:
			self.status.showMessage ('No video selected!', 5000)
			return
		if curr.downloader.isRunning():
			curr.stop_download = True
			curr.downloader.wait()
		if curr.t.isRunning():
			curr.t.terminate()
			curr.t.wait()
		self.table.takeTopLevelItem ( self.table.indexOfTopLevelItem(curr) )
		self.status.showMessage ('Removed', 5000)

	def clear (self):
		cnt = self.table.topLevelItemCount()
		if cnt==0:
			self.status.showMessage ('List already clear!', 5000)
			return None
		for i in range (0, cnt):
			curr = self.table.topLevelItem (i)
			if curr.downloader.isRunning():
				curr.stop_download = True
				curr.downloader.wait()
			if curr.t.isRunning():
				curr.t.terminate()
				curr.t.wait()
		self.table.clear()
		self.status.showMessage ('List cleared', 5000)

	def download (self):
		curr = self.table.currentItem()
		if curr is None:
			return
		if curr.t.isRunning():
			self.connect (curr.t, SIGNAL('finished()'), curr.downloader.start)
		elif not curr.downloader.isRunning():
			curr.downloader.start()
	
	def pause (self):
		curr = self.table.currentItem()
		if curr is None:
			return
		if curr.downloader.isRunning():
			curr.stop_download = True
			curr.downloader.wait()
			curr.stop_download = False

	def trouble (self):
		QMessageBox.critical (self, 'Error', utube._err[0])

	def about (self):
		return

	def closeEvent(self, event):
		if self.isVisible():
			self.hide()
		event.ignore()

	def toggleWindow (self, reason):
		if reason == QSystemTrayIcon.Trigger:
			self.hide() if self.isVisible() else self.show()

	def quit (self):
		qApp.quit()

	def createAction (self, text, slot=None, shortcut=None, tip=None, icon=None, checkable=False, signal='triggered()'):
		action = QAction (text, self)
		if icon is not None:
			action.setIcon (icon)
		if shortcut is not None:
			action.setShortcut (shortcut)
		if tip is not None:
			action.setToolTip (tip)
			action.setStatusTip (tip)
		if slot is not None:
			self.connect (action, SIGNAL(signal), slot)
		action.setCheckable (checkable)
		return action

if __name__=='__main__':
	app = QApplication (sys.argv)
	window = MainWindow()
	window.showMaximized()
	app.exec_()
