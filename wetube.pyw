#!/usr/bin/env python

import os
import sys
import urllib2
import item
from PyQt4.QtCore import *
from PyQt4.QtGui import *

import utube

__author__ = "Viranch Mehta"
__author_email__ = "viranch.mehta@gmail.com"
__version__ = '0.9'

icon = lambda name: QIcon (os.path.dirname(__file__)+'/icons/'+name)

class MainWindow(QMainWindow):

	def __init__ ( self, parent=None ):
		super (MainWindow, self).__init__(parent)

		self.running_startAll = False

		self.toolbar = self.addToolBar ('Toolbar')
		self.status = self.statusBar()
		self.status.showMessage ('Ready')

		self.table = QTreeWidget()
		self.table.setHeaderLabels ( ['Title', 'Status', 'Downloaded', 'Size', 'Format', 'Location'] )
		#headerItem = self.tabel.headerItem()
		#headerItem.setIcon (0, icon('applications-multimedia.png'))
		#headerItem.setIcon (1, icon('flag-green.png'))
		#headerItem.setIcon (2, icon('flag-red.png'))
		#headerItem.setIcon (3, icon('edit-copy.png'))
		#headerItem.setIcon (4, icon('edit-copy.png'))
		#headerItem.setIcon (5, icon('flag-green.png'))
		self.table.setRootIsDecorated (False)

		addAction = self.createAction ('Add', self.add, QKeySequence.New, 'Add...', icon('document-new.png'))
		rmAction = self.createAction ('Remove', self.remove, QKeySequence.Delete, 'Remove', icon('edit-delete.png'))
		clearAction = self.createAction ('Clear', self.clear, 'Shift+Del', 'Clear', icon('edit-clear-list.png'))
		startAction = self.createAction ('Start/Resume', self.download, None, 'Start/Resume Download', icon('media-playback-start.png'))
		pauseAction = self.createAction ('Pause', self.pause, None, 'Pause Download', icon('media-playback-pause.png'))
		startAllAction = self.createAction ('Start All', self.startAll, None, 'Start/Resume all downloads', icon('media-playback-start.png'))
		suspendAction = self.createAction ('Suspend Downloads', self.suspend, None, 'Suspend all downloads', icon('media-playback-start.png'))
		configAction = self.createAction ('Settings', self.configure, None, 'Configure WeTube', icon('configure.png'))
		aboutAction = self.createAction ('About', self.about, None, 'About', icon('help-about.png'))
		quitAction = self.createAction ('Quit', self.quit, 'Ctrl+Q', 'Quit', icon('application-exit.png'))
		
		self.toolbar.addAction ( addAction )
		self.toolbar.addAction ( rmAction )
		self.toolbar.addAction ( clearAction )
		self.toolbar.addSeparator()
		self.toolbar.addAction ( startAction )
		self.toolbar.addAction ( pauseAction )
		self.toolbar.addSeparator()
		self.toolbar.addAction ( startAllAction )
		self.toolbar.addAction ( suspendAction )
		self.toolbar.addSeparator()
		self.toolbar.addAction ( configAction )
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
		self.tray.setContextMenu (self.trayMenu)

		self.setCentralWidget (self.table)
		self.setWindowTitle ('WeTube')
		self.setWindowIcon ( QIcon(icon('acroread.png')) )
		
		self.connect ( self.tray, SIGNAL('activated(QSystemTrayIcon::ActivationReason)'), self.toggleWindow )
		self.connect ( self.table, SIGNAL('itemChanged(QTreeWidgetItem*,int)'), self.updateUi )

	def updateUi (self, item, col):
		if col==1:
			if item.text (col) == 'Downloading':
				item.setIcon (0, icon('download.png'))
			elif item.text(col) == '' or item.text(col) == 'Paused':
				item.setIcon (0, icon('empty.png'))
			elif item.text (col) == 'Complete':
				item.setIcon (0, icon('task-complete.png'))
			elif item.text (col) == 'Queued':
				item.setIcon (0, icon('download-later.png'))
			else:
				print item.text(col)

	def loadPrefs (self):
		settings = QSettings ('WeTube', 'WeTube')
		cnt = settings.value('count').toInt()[0]
		self.maxSimulDlds = settings.value('msd').toInt()[0]
		self.download_dir = str ( settings.value('download_dir').toString() )
		for i in range(cnt):
			settings.beginGroup('vid'+str(i))
			
			ref_url = str ( settings.value('ref_url').toString() )
			target_dir = str ( settings.value ('target_dir').toString() )
			title = str ( settings.value ('title').toString() )
			length = str ( settings.value ('length').toString() )
			format = str ( settings.value ('format').toString() )
			target = str ( settings.value ('target').toString() )

			curr = item.Item (self, ref_url, target_dir, [title, '', '', length, format, target])
			
			bytes = settings.value('bytes').toInt()[0]
			pbar = settings.value('pbar').toInt()[0]
			curr.pbar.setRange (0, bytes)
			if pbar < bytes:
				if not os.path.isfile (target): pbar = -1
				else: pbar = os.path.getsize (target)
			curr.set_state ( pbar )
			settings.endGroup()
			self.updateUi (curr, 1)
			self.add (curr)

	def check_filename (self, target, index):
		tgt = target
		ctr = 1
		while True:
			ctr += 1
			found = False
			for i in range ( self.table.topLevelItemCount() ):
				if i==index:
					continue
				curr = self.table.topLevelItem(i)
				if curr.text(5) == tgt:
					tgt = target[:-4]+'_'+str(ctr)+target[-4:]
					found = True
					break
			if not found:
				break
		return tgt

	def add (self, new_item=None, startDownload=False):
		if new_item == None:
			import new
			dlg = new.NewDlg(self)
			if dlg.exec_():
				ref_url = str(dlg.urlEdit.text()).strip()
				target_dir = str(dlg.savetoEdit.text())
				new_item = item.Item (self, ref_url, target_dir, ['', '', '', '', '', ''])
				self.add (new_item, dlg.startDownload.isChecked())
		else:
			pos = self.table.topLevelItemCount()
			for i in range ( pos ):
				curr = self.table.topLevelItem(i)
				if curr.pbar.value() >= curr.pbar.maximum():
					pos = i
					break
			self.table.insertTopLevelItem ( pos, new_item )
			new_item.index = pos
			self.table.setItemWidget ( new_item, 2, new_item.pbar )
			self.status.showMessage ('Video added.', 5000)
			self.connect (new_item.t, SIGNAL('error()'), self.trouble)
			self.connect (new_item.downloader, SIGNAL('doneSize(int)'), new_item.set_state)
			self.connect (new_item.downloader, SIGNAL('done()'), self.startAll)
			if new_item.pbar.value() < new_item.pbar.maximum():
				new_item.t.start()
			if startDownload:
				if new_item.t.isRunning():
					new_item.startDownload = True
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
			curr.startDownload = True
			curr.explicit = True
			print 'getting info thread running'
		elif not curr.downloader.isRunning():
			curr.downloader.start()
			curr.explicit = True
			print 'download should start'
	
	def pause (self):
		curr = self.table.currentItem()
		if curr is None:
			return
		if curr.downloader.isRunning():
			curr.stop_download = True

	def startAll (self):
		if not self.running_startAll:
			self.running_startAll = True
		else: return
		i = 0
		if self.maxSimulDlds==0:
			i_max = self.table.topLevelItemCount()
		else:
			i_max = self.maxSimulDlds
		for ctr in range ( self.table.topLevelItemCount() ):
			curr = self.table.topLevelItem (ctr)
			if curr.pbar.value() < curr.pbar.maximum() and not curr.explicit:
				if i<i_max:
					if curr.t.isRunning():
						curr.startDownload = i<i_max
					elif not curr.downloader.isRunning():
						curr.downloader.start()
					i += 1
				else:
					if curr.t.isRunning():
						curr.startDownload = False
					elif curr.downloader.isRunning():
						curr.stop_download = True
					curr.setText (1, 'Queued')
		self.running_startAll = False

	def suspend (self):
		for i in range ( self.table.topLevelItemCount() ):
			curr = self.table.topLevelItem(i)
			if curr.t.isRunning():
				curr.startDownload = False
			elif curr.downloader.isRunning():
				curr.stop_download = True
	"""
#				stopped.append (curr)
#		cnt = 0
#		while cnt<len(stopped):
#			for curr in stopped:
#				if not curr.downloader.isRunning():
#					cnt += 1
#					curr.stop_download = False
	"""
	def trouble (self):
		QMessageBox.critical (self, 'Error', utube._err[0])

	def configure (self):
		import settings
		dlg = settings.SettingsDlg(self)
		if dlg.exec_():
			if self.maxSimulDlds != dlg.msdSpin.value():
				self.maxSimulDlds = dlg.msdSpin.value()
				self.startAll()
			self.download_dir = str ( dlg.downdirEdit.text() )

	def about (self):
		return

	def closeEvent(self, event):
		if self.isVisible():
			self.hide()
		event.ignore()

	def toggleWindow (self, reason=QSystemTrayIcon.Trigger):
		if reason == QSystemTrayIcon.Trigger:
			self.hide() if self.isVisible() else self.show()

	def quit (self):
		self.hide()
		settings = QSettings ('WeTube', 'WeTube')
		settings.clear()
		cnt = self.table.topLevelItemCount()
		settings.setValue ('count', cnt)
		settings.setValue ('msd', self.maxSimulDlds)
		settings.setValue ('download_dir', self.download_dir)
		for i in range (cnt):
			curr = self.table.topLevelItem (i)
			if curr.t.isRunning():
				curr.t.terminate()
			if curr.downloader.isRunning():
				curr.stop_download = True
				if not curr.downloader.wait(10*1000): #wait for 10 seconds = 10*1000 milli seconds
					curr.downloader.terminate()
			settings.beginGroup ('vid'+str(i))
			settings.setValue ('ref_url', curr.ref_url)
			settings.setValue ('target_dir', curr.target_dir)
			settings.setValue ('bytes', curr.pbar.maximum())
			settings.setValue ('pbar', curr.pbar.value())
			settings.setValue ('title', curr.text(0))
			settings.setValue ('length', curr.text(3))
			settings.setValue ('format', curr.text(4))
			settings.setValue ('target', curr.text(5))
			settings.endGroup()
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
	window.loadPrefs()
	window.showMaximized()
	if len(QSettings('WeTube','WeTube').allKeys())==0:
		window.configure()
	app.exec_()
