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
watched_folder = '/var/nextcloud_data/c4p/files/camera_footage/raw_footage/' # Please specify folder location
anonymous_folder = '/var/nextcloud_data/c4p/files/camera_footage/anonymous_footage/' # Please specify folder location

# Threshold for image analysis
thresh = None




class MyHandler(FileSystemEventHandler):
    # anonymize pictures, whenever there is a new picture in the wachtched folder
    def on_created(self, event):
        print(f'event type: {event.event_type}  path : {event.src_path}')
        time.sleep(1)

        try:
            # the "on_created" event is called by a partially upload file
            # cut excess filename after '.png'
            #/var/nextcloud_data/c4p/files/camera_footage/Ko-retina.png.ocTransferId1983807786.part
            # /camera_footage/camera_1/raw_footage
            # /camera_footage/camera_1/anonymized_footage

            # todo : anonymizing more than 1 face
            # todo : put face over face

            sucessful_anonymization = False


            filetype = find_filetype(event.src_path)
            path_to_file = event.src_path.split(filetype, 1)[0] + filetype
            print("path to file", path_to_file)

            camera_folder = get_camera_folder(path_to_file)
            print("camera_id", camera_folder)

            picture_id = get_picture_id(path_to_file, camera_folder, filetype)
            print("picture_id", picture_id)

            an_path = get_path_for_anonymous_pic(anonymous_folder, camera_folder, picture_id, filetype)

            face_detector = FaceDetector()



            print("reading image")
            img = cv2.imread(path_to_file)
            rgb_img = cv2.cvtColor(img.copy(), cv2.COLOR_BGR2RGB)

            if thresh:
                bboxes = face_detector.predict(rgb_img, thresh)
            else:
                bboxes = face_detector.predict(rgb_img)

            # anonymize
            if not bboxes == []:
                try:
                    print("bboxes containing face", bboxes)

                    print("creating anonymous picture")
                    ann_img = annotate_image(img, bboxes)

                    print("write anonymized version to anonymous folder")
                    cv2.imwrite(an_path)

                    sucessful_anonymization = True

                except:
                    print("writing anonymized version failed")
                    sucessful_anonymization = False


                # delete original if sucessfully anonymized
                if sucessful_anonymization:
                    if os.path.exists(path_to_file):
                        os.remove(path_to_file)
                    else:
                        print("Tried deleting, but the file does not exist", path_to_file)

            # no faces found, picture is already anonymous
            else:
                print("no face found")
                if os.path.exists(path_to_file):
                    os.rename(path_to_file, an_path)

            print("refreshing owncloud")
            subprocess.call(cwd + "/refresh_nextcloud.sh", shell=True)

        except Exception as e:
            print(e)
            print("Anonymizing failed")


# iterates over potential filetypes and returns the filetype if matched
def find_filetype(file_path):
    filetypes = ['.png', '.PNG', '.jpg', '.JPG', '.jpeg', '.JPEG']

    for filetype in filetypes:
        if filetype in file_path:
            return filetype

    return None

# filters the camera_id from filepath
def get_camera_folder(file_path):
    for camera_id in range(1, 5):
        if 'camera_' + str(camera_id) in file_path:
            return 'camera_' + str(camera_id)

    return None


# substract all information but the picture_id from path_to_file
def get_picture_id(path_to_file, camera_id, filetype):
    picture_id = path_to_file
    for substring in [path_to_file, camera_id, filetype]:
        picture_id.replace(substring, '')

    return picture_id


def get_path_for_anonymous_pic(anonymous_folder, camera_id, picture_id, filetype):
    return anonymous_folder + '/' + camera_id + '/' + picture_id + filetype


if __name__ == "__main__":
    print("File watching started")
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
