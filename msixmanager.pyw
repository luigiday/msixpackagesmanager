import sys
import time
from time import sleep
import subprocess
import tkinter as tk
from tkinter import messagebox
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QEventLoop, QObject
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QListWidget, QPushButton, QLineEdit, QMessageBox, QListWidgetItem, QProgressDialog

class Splash(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("MSIX Package Manager")
        self.geometry("400x200")
        self.label = tk.Label(self, text="Launching MSIX Package Manager...", padx=10, pady=10)
        self.label.pack(expand=True)
        self.after(2000, self.destroy)


    

class WorkerThread(QThread):
    finished = pyqtSignal(list)

    def __init__(self, func):
        super().__init__()
        self.func = func

    def run(self):
        result = self.func()
        if result is not None:  # Check if result is not None
            self.finished.emit(result)

class UninstallThread(QThread):
    finished_uninstall = pyqtSignal()

    def __init__(self, func):
        super().__init__()
        self.func = func

    def run(self):
        self.func()
        self.finished_uninstall.emit()

class MSIXManager(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.progress_dialog = None
        self.uninstall_thread = None

    def init_ui(self):
        self.setWindowTitle("MSIX Package Manager")
        self.setGeometry(100, 100, 1000, 600)

        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Search for packages...")
        self.package_list = QListWidget(self)
        self.refresh_button = QPushButton("Refresh List", self)
        self.uninstall_button = QPushButton("Uninstall Selected Package", self)

        layout = QVBoxLayout()
        layout.addWidget(self.search_input)
        layout.addWidget(self.package_list)
        layout.addWidget(self.refresh_button)
        layout.addWidget(self.uninstall_button)
        self.setLayout(layout)

        self.refresh_button.clicked.connect(self.refresh_package_list)
        self.uninstall_button.clicked.connect(self.uninstall_selected_package)
        self.search_input.textChanged.connect(self.filter_package_list)

        self.refresh_package_list()

    def refresh_package_list(self):
        self.progress_dialog = QProgressDialog("Refreshing Package List...", "", 0, 0, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setWindowTitle("Please Wait")
        self.progress_dialog.setCancelButton(None)
        self.progress_dialog.show()

        self.worker_thread = WorkerThread(self.get_msix_packages)
        self.worker_thread.finished.connect(self.on_refresh_finished)
        self.worker_thread.start()

        loop = QEventLoop()
        self.worker_thread.finished.connect(loop.quit)
        loop.exec_()

    def get_msix_packages(self):
        time.sleep(3)  # Simulate a delay (remove this in your actual code)
        try:
            result = subprocess.check_output(['powershell', 'Get-AppxPackage']).decode('utf-8')
            packages = [line.split('\t')[0] for line in result.splitlines()[3:]]
            return packages
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error getting MSIX packages: {str(e)}")
            return []

    def on_refresh_finished(self, result):
        if self.progress_dialog is not None:
            self.progress_dialog.close()  # Close the progress dialog
        self.progress_dialog = None
        self.package_list.clear()
        if result:  # Check if result is not empty
            msix_packages = result
            self.package_list.addItems(msix_packages)

    def uninstall_selected_package(self):
        selected_item = self.package_list.currentItem()
        if selected_item:
            package_name = selected_item.text()
            try:
                # Check if the selected package line contains "PackageFullName"
                if "PackageFullName" not in package_name:
                    QMessageBox.warning(self, "Warning", "Please select the 'PackageFullName' line.")
                    return

                # Remove the "PackageFullName" part from the package name
                package_name = package_name.split(" : ")[-1]

                # Show a confirmation dialog before uninstalling
                confirmation = QMessageBox.question(self, "Confirmation",
                                                    f"Do you want to uninstall package: {package_name}?",
                                                    QMessageBox.Yes | QMessageBox.No)
                if confirmation == QMessageBox.Yes:
                    self.progress_dialog = QProgressDialog("Uninstalling Package...", "", 0, 0, self)
                    self.progress_dialog.setWindowModality(Qt.WindowModal)
                    self.progress_dialog.setWindowTitle("Please Wait")
                    self.progress_dialog.setCancelButton(None)
                    self.progress_dialog.show()

                    self.uninstall_thread = UninstallThread(lambda: self.uninstall_package(package_name))
                    self.uninstall_thread.finished_uninstall.connect(self.on_uninstall_finished)
                    self.uninstall_thread.start()

                else:
                    QMessageBox.information(self, "Information", "Package not uninstalled.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error uninstalling package: {str(e)}")
        else:
            QMessageBox.warning(self, "Warning", "No package selected for uninstall.")

    def uninstall_package(self, package_name):
        try:
            subprocess.run(['powershell', 'Remove-AppxPackage', f'"{package_name}"', '-Confirm:$false'])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error uninstalling package: {str(e)}")

    def on_uninstall_finished(self):
        if self.progress_dialog is not None:
            self.progress_dialog.close()  # Close the progress dialog
        self.progress_dialog = None
        self.refresh_package_list()
        QMessageBox.information(self, "Success", "Package has been uninstalled.")

    def filter_package_list(self):
        search_text = self.search_input.text().strip().lower()  # Convert to lowercase for case-insensitive search
        for index in range(self.package_list.count()):
            item = self.package_list.item(index)
            if search_text in item.text().lower():
                item.setHidden(False)
            else:
                item.setHidden(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)  # Create the QApplication object

    if messagebox.askyesno("Pre-launch warning - MSIX Package Manager by colin524", "WARNING !\nThis program is just a graphical frontend for PowerShell Remove-Package commands, wich means it can uninstall any package PowerShell can, including potentially important ones.\n\nDo you wish to proceed ?\n\n(The creator is not responsible for system breakages using this software, don't continue if you don't know what you are doing)", icon=messagebox.WARNING):
        messagebox.showwarning("Warning", "This tool is OLD and might no longer work properly, you should probably not use it as it is also unmaintained")
    else:
        sys.exit()
    
    root = tk.Tk()
    root.withdraw()  # Hide the root window

    splash = Splash(root)
    root.update()  # Update the splash screen to display it

    

    window = MSIXManager()
    window.show()

    splash.destroy()  # Close the splash screen when the main window is shown

    sys.exit(app.exec_())  # Run the QApplication event loop
