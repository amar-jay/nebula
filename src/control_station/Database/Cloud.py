from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QWidget
from Database.users_db import FirebaseUser


class FirebaseThread(QThread):

    def __init__(self, firebase):
        super().__init__()
        self.loop = True
        self.firebase = firebase

    def run(self):
        while self.loop:
            # Fetching user data such as location, online status
            self.firebase.get_user_data()

            # Sending targets to the database
            if len(self.firebase.targets) != 0:
                self.firebase.send_targets()

            # Updating UAV data
            self.firebase.update_marker_latitude()
            self.firebase.update_marker_longitude()
            self.firebase.update_marker_compass()

            self.msleep(100)

    def stop(self):
        self.loop = False


def updateUserMenu(usermenu, firebase, id):
    if usermenu.isOnline != firebase.users[id]['online']:
        usermenu.setOnline(firebase.users[id]['online'])
    if usermenu.location_label.text()[10:] != str(firebase.users[id]['location']):
        usermenu.setLocation(firebase.users[id]['location'])


class UpdateUserMenuThread(QThread):
    updateUserMenu_signal = Signal(QWidget, FirebaseUser, int)

    def __init__(self, user_id, firebase, usermenu, parent=None):
        super().__init__()
        self.parent = parent
        self.id = user_id
        self.loop = True
        self.firebase = firebase
        self.usermenu = usermenu
        self.updateUserMenu_signal.connect(updateUserMenu)

    def run(self):
        while self.loop:
            self.updateUserMenu_signal.emit(self.usermenu, self.firebase, self.id)
            self.msleep(100)

    def stop(self):
        self.loop = False
