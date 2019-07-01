#!/usr/bin/python3
# execute as www-data

import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import cv2
from faced import FaceDetector
from faced.utils import annotate_image

watched_folder = '' # Please specify folder location


class MyHandler(FileSystemEventHandler):
    # anonymize pictures, whenever there is a new picture in the wachtched folder
    def on_created(self, event):
        print(f'event type: {event.event_type}  path : {event.src_path}')

        # the "on_created" event is called by a partially upload file
        # cut excess filename after '.png'
        #/var/nextcloud_data/c4p/files/camera_footage/Ko-retina.png.ocTransferId1983807786.part
        seperator = '.png'
        path_to_file = event.src_path.split(seperator, 1)[0] + seperator

        face_detector = FaceDetector()

        # Threshold for image analysis
        thresh = None

        img = cv2.imread(path_to_file)
        rgb_img = cv2.cvtColor(img.copy(), cv2.COLOR_BGR2RGB)

        if thresh:
            bboxes = face_detector.predict(rgb_img, thresh)
        else:
            bboxes = face_detector.predict(rgb_img)
        ann_img = annotate_image(img, bboxes)
        # overwrite original with anonymized version
        cv2.imwrite(event.src_path, ann_img)


if __name__ == "__main__":
    event_handler = MyHandler()
    observer = Observer()
    observer.schedule(event_handler, path=watched_folder, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
