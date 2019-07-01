#!/usr/bin/python3
# execute as www-data

import time
import subprocess
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import cv2
from faced import FaceDetector
from faced.utils import annotate_image

cwd = os.path.dirname(os.path.abspath(__file__))
watched_folder = '' # Please specify folder location


class MyHandler(FileSystemEventHandler):
    # anonymize pictures, whenever there is a new picture in the wachtched folder
    def on_created(self, event):
        print(f'event type: {event.event_type}  path : {event.src_path}')

        try:
            # the "on_created" event is called by a partially upload file
            # cut excess filename after '.png'
            #/var/nextcloud_data/c4p/files/camera_footage/Ko-retina.png.ocTransferId1983807786.part
            filetype = '.png'
            path_to_file = event.src_path.split(filetype, 1)[0]
            print("path to file", path_to_file)

            face_detector = FaceDetector()

            # Threshold for image analysis
            thresh = None

            print("reading image")
            img = cv2.imread(path_to_file + filetype)
            rgb_img = cv2.cvtColor(img.copy(), cv2.COLOR_BGR2RGB)

            if thresh:
                bboxes = face_detector.predict(rgb_img, thresh)
            else:
                bboxes = face_detector.predict(rgb_img)

            if not bboxes == []:
                print("bboxes containing face", bboxes)

                print("creating anonymous picture")
                ann_img = annotate_image(img, bboxes)

                print("overwrite original with anonymized version")
                cv2.imwrite(path_to_file + '_anonymous' + filetype, ann_img)

                print("refreshing owncloud")
                subprocess.call(cwd + "/refresh_nextcloud.sh", shell=True)
            else:
                print("no face found")

        except:
            print("Anonymizing failed")


if __name__ == "__main__":
    event_handler = MyHandler()
    observer = Observer()
    observer.schedule(event_handler, path=watched_folder, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
