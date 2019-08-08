#!/usr/bin/python3
# execute as www-data

import time
import datetime
import subprocess
import os
import signal
import shutil
import cv2
import csv

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from faced import FaceDetector
from faced.utils import annotate_image

cwd = os.path.dirname(os.path.abspath(__file__))
watched_folder = '/var/nextcloud_data/c4p/files/camera_footage/raw_footage/'  # Please specify folder location
anonymous_folder = '/var/nextcloud_data/c4p/files/camera_footage/anonymous_footage/'  # Please specify folder location
faces_csv = '/var/nextcloud_data/c4p/files/camera_footage/anonymous_footage/face_positions.csv'  # Please specify folder location

# Threshold for image analysis
thresh = None
counter = 0


class MyHandler(FileSystemEventHandler):
    # anonymize pictures, whenever there is a new picture in the wachtched folder
    def on_created(self, event):
        print(f'event type: {event.event_type}  path : {event.src_path}')
        # let time pass to finish upload
        time.sleep(2)
        global counter
        counter = counter + 1

         # todo : put face over face

        file_type = find_filetype(event.src_path)
        print("file_type", file_type)

        # the "on_created" event is called by a partially upload file
        # cut excess filename after '.png'
        path_to_file = event.src_path.split(file_type, 1)[0] + file_type
        print("path to file", path_to_file)

        # check if the file is already upload entirely
        tries_to_reach_file = 0
        while not os.path.exists(path_to_file):
            tries_to_reach_file = tries_to_reach_file + 1
            time.sleep(1)
            if tries_to_reach_file > 10:
                print("file does not exit")
                print(path_to_file)

                return

        camera_folder = get_camera_folder(path_to_file)

        #print("camera_id", camera_folder)

        picture_id = get_picture_id(path_to_file, camera_folder, file_type)
        #print("picture_id", picture_id)

        an_path = get_path_for_anonymous_folder(camera_folder) + '/' + picture_id + file_type
        # print("path to anonymous file", an_path)

        face_detector = FaceDetector()

        # print("reading image", path_to_file)
        img = cv2.imread(path_to_file)
        # crop picture for camera 1 to cut off unnecessary parts of the imagae
        if camera_folder == 'camera_1':
            img = crop_img(img)

        rgb_img = cv2.cvtColor(img.copy(), cv2.COLOR_BGR2RGB)

        if thresh:
            bboxes = face_detector.predict(rgb_img, thresh)
        else:
            bboxes = face_detector.predict(rgb_img)

        # anonymize picture
        if not bboxes == []:
            try:
                # TODO save bboxes per picture in csv
                print("bboxes containing face", bboxes)

                print("creating anonymous picture")
                ann_img = annotate_image(img, bboxes)

                print("write anonymized version to anonymous folder")
                cv2.imwrite(an_path, ann_img)

                successful_anonymization = True

                save_bboxes_to_csv(camera_folder, picture_id, bboxes)

            except Exception as ex:
                print(ex)
                print("Anonymizing failed")
                successful_anonymization = False

            # delete original if successfully anonymized
            if successful_anonymization:
                os.remove(path_to_file)
            # else:
            #     os.rename(path_to_file, an_path)
            #     shutil.move(path_to_file, an_path)

        # no faces found, picture is already anonymous
        else:
            print("no face found")
            if os.path.exists(path_to_file):
                os.rename(path_to_file, an_path)

        if counter == 10:
            counter = 0
            print("refreshing owncloud")
            try:
                # The os.setsid() is passed in the argument preexec_fn so
                # it's run after the fork() and before  exec() to run the shell.
                pro = subprocess.Popen(cwd + "/refresh_nextcloud.sh", stdout=subprocess.PIPE,
                                       shell=True, preexec_fn=os.setsid)
            except:
                os.killpg(os.getpgid(pro.pid), signal.SIGTERM)  # Send the signal to all the process groups


def save_bboxes_to_csv(camera_folder, picture_id, bboxes):
    an_folder = get_path_for_anonymous_folder(camera_folder)
    csv_row = [camera_folder, picture_id]

    if not os.path.exists(an_folder + '/face_positions.csv'):
        init_face_positions_csv(an_folder)

    for bbox in bboxes:
        for coordinate in bbox:
            csv_row.append(coordinate)
        with open(an_folder + '/face_positions.csv', "a", newline='') as f:
            writer = csv.writer(f, delimiter=',')
            writer.writerow(csv_row)


def init_face_positions_csv(an_folder):
    header = ['camera', 'picture', 'bbox_coord_0', 'bbox_coord_1', 'bbox_coord_2', 'bbox_coord_3']

    with open(an_folder + '/face_positions.csv', "w", newline='') as f:
        writer = csv.writer(f, delimiter=',')
        writer.writerow(header)  # write the header


def crop_img(img):
    height, width = img.shape[:2]

    return img[int(height / 1.75):height, 0:width]


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
def get_picture_id(path_to_file, camera_folder, filetype):
    picture_id = path_to_file
    for substring in [watched_folder, camera_folder, filetype, '/']:
        picture_id = substract_from_string(picture_id, substring)

    return picture_id


def substract_from_string(long_string, substring):
    return long_string.replace(substring, '')


def get_path_for_anonymous_folder(camera_folder_name):
    day = datetime.date.today()
    date = day.strftime('%m') + '_' + day.strftime('%d')
    an_directory_with_date = anonymous_folder + camera_folder_name + '/' + date

    try:
        if not os.path.exists(an_directory_with_date):
            os.makedirs(an_directory_with_date)
    except OSError:
        print('Error: Creating directory. ' + an_directory_with_date)

    return an_directory_with_date


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
