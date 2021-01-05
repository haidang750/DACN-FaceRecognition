from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tensorflow as tf
from scipy import misc
import cv2
import matplotlib.pyplot as plt
import numpy as np
import argparse
import facenet
import detect_face
import os
from os.path import join as pjoin
import sys
import time
import copy
import math
import pickle
from sklearn.svm import SVC
from sklearn.externals import joblib
from joblib import Parallel, delayed
import tkinter
import time
from tkinter import *
from PIL import ImageTk, Image

 # display popup (form) when login by face succeeds
def createWindow():
    window = Tk()
    window.title("Face Login Authentication")
    canvas = Canvas(window,width=512,height=329)
    canvas.grid(row=2, column=3)
    img = ImageTk.PhotoImage(Image.open("background1.gif"))  # PIL solution
    canvas.create_image(0, 0, anchor=NW, image=img)
    label = Label(window, text="LOGIN SUCCESSFUL", fg="red", font=("Arial", 24))
    label.place(x=90, y=130)
    window.mainloop()
def createWindow1():
    window = Tk()
    window.title("Face Login Authentication")
    canvas = Canvas(window,width=512,height=329)
    canvas.grid(row=2, column=3)
    img = ImageTk.PhotoImage(Image.open("background1.gif"))  # PIL solution
    canvas.create_image(0, 0, anchor=NW, image=img)
    label = Label(window, text="LOGIN UNSUCCESSFUL", fg="red", font=("Arial", 24))
    label.place(x=90, y=130)
    window.mainloop()


print('Creating networks and loading parameters')
with tf.Graph().as_default():
    gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=0.6)
    sess = tf.Session(config=tf.ConfigProto(gpu_options=gpu_options, log_device_placement=False))
    with sess.as_default():
        pnet, rnet, onet = detect_face.create_mtcnn(sess, 'data')

        minsize = 20  # minimum size of face
        threshold = [0.6, 0.7, 0.7]  # three steps's threshold
        factor = 0.709  # scale factor
        margin = 44
        frame_interval = 3
        batch_size = 1000
        image_size = 182
        input_image_size = 160

        HumanNames = ['DinhHan','HaiDang','VoHieu']    #train human name

        print('Loading feature extraction model')
        modeldir = 'data/20180402-114759/20180402-114759.pb'
        facenet.load_model(modeldir)

        images_placeholder = tf.get_default_graph().get_tensor_by_name("input:0")
        embeddings = tf.get_default_graph().get_tensor_by_name("embeddings:0")
        phase_train_placeholder = tf.get_default_graph().get_tensor_by_name("phase_train:0")
        embedding_size = embeddings.get_shape()[1]

        classifier_filename = 'my_classifier.pkl'
        classifier_filename_exp = os.path.expanduser(classifier_filename)
        with open(classifier_filename_exp, 'rb') as infile:
            (model, class_names) = pickle.load(infile)
            print('load classifier file-> %s' % classifier_filename_exp)

        video_capture = cv2.VideoCapture(0)
        c = 0

        print('Start Recognition!')
        prevTime = 0
        prevTime1 = time.time()
        prevTime2 = time.time()
        timeException1 = 0
        timeException2 = 0
        while True:
            ret, frame = video_capture.read()

            frame = cv2.resize(frame, (0,0), fx=0.75, fy=0.75)    #resize frame (optional)
            curTime = time.time()
            curTime1 = time.time()
            timeF = frame_interval

            if (c % timeF == 0):
                find_results = []

                if frame.ndim == 2:
                    frame = facenet.to_rgb(frame)
                frame = frame[:, :, 0:3]
                bounding_boxes, _ = detect_face.detect_face(frame, minsize, pnet, rnet, onet, threshold, factor)
                nrof_faces = bounding_boxes.shape[0]
                print('Detected_FaceNum: %d' % nrof_faces)

                if nrof_faces > 0:
                    det = bounding_boxes[:, 0:4]
                    img_size = np.asarray(frame.shape)[0:2]

                    # cropped = []
                    # scaled = []
                    # scaled_reshape = []
                    bb = np.zeros((nrof_faces,4), dtype=np.int32)

                    for i in range(nrof_faces):
                        emb_array = np.zeros((1, embedding_size))

                        bb[i][0] = det[i][0]
                        bb[i][1] = det[i][1]
                        bb[i][2] = det[i][2]
                        bb[i][3] = det[i][3]

                        # inner exception
                        if bb[i][0] <= 0 or bb[i][1] <= 0 or bb[i][2] >= len(frame[0]) or bb[i][3] >= len(frame):
                            print('face is inner of range!')
                            continue

                        cropped = (frame[bb[i][1]:bb[i][3], bb[i][0]:bb[i][2], :])
                        # print("{0} {1} {2} {3}".format(bb[i][0], bb[i][1], bb[i][2], bb[i][3]))
                        cropped = facenet.flip(cropped, False)
                        scaled = (misc.imresize(cropped, (image_size, image_size), interp='bilinear'))
                        scaled = cv2.resize(scaled, (input_image_size, input_image_size),
                                            interpolation=cv2.INTER_CUBIC)
                        scaled = facenet.prewhiten(scaled)
                        scaled_reshape = (scaled.reshape(-1, input_image_size, input_image_size, 3))
                        feed_dict = {images_placeholder: scaled_reshape, phase_train_placeholder: False}

                        emb_array[0, :] = sess.run(embeddings, feed_dict=feed_dict)
                        predictions = model.predict_proba(emb_array)

                        best_class_indices = np.argmax(predictions, axis=1)
                        best_class_probabilities = predictions[np.arange(len(best_class_indices)), best_class_indices]
                        cv2.rectangle(frame, (bb[i][0], bb[i][1]), (bb[i][2], bb[i][3]), (0, 255, 0), 2)    #boxing face

                        #plot result idx under box
                        text_x = bb[i][0]
                        text_y = bb[i][3] + 20
                        # print('result: ', best_class_indices[0])

                        result_names = class_names[best_class_indices[0] + 1]
                        result_names1 = result_names
                        print("Person : %s" % result_names)
                        if(result_names1 == 'zUnknown'):
                            cv2.putText(frame, result_names1, (text_x, text_y), cv2.FONT_HERSHEY_COMPLEX_SMALL,
                                        1, (0, 0, 255), thickness=1, lineType=2)
                        else:
                            temp = round(best_class_probabilities[0] * 100, 2)
                            result_names = result_names + ":" + str(temp) + "%"
                            cv2.putText(frame, result_names, (text_x, text_y), cv2.FONT_HERSHEY_COMPLEX_SMALL,
                                        1, (0, 0, 255), thickness=1, lineType=2)
                        # check face to login
                        if (result_names1 == "nhaidang"):
                            prevTime2 = time.time()
                            sec1 = curTime1 - prevTime1
                            timeException1 = timeException1 + sec1
                            prevTime1 = curTime1
                            if(timeException1 > 1.75):
                                print("LOGIN SUCCESSFUL")
                                createWindow()
                                timeException1 = 0
                        else:
                            curTime2 = time.time()
                            sec2 = curTime2 - prevTime2
                            timeException2 = timeException2 + sec2
                            prevTime2 = curTime2
                            if(timeException2 > 3.5):
                                print("LOGIN UNSUCCESSFUL")
                                createWindow1()
                                timeException2 = 0
                else:
                    print('Unable to align')
            sec = curTime - prevTime
            prevTime = curTime
            fps = 1 / (sec)
            str1 = 'FPS: %2.3f' % fps
            text_fps_x = len(frame[0]) - 150
            text_fps_y = 20
            cv2.putText(frame, str1, (text_fps_x, text_fps_y),
                        cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (0, 0, 0), thickness=1, lineType=2)
            # c+=1
            cv2.imshow('Video', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        video_capture.release()
        # #video writer
        # out.release()
        cv2.destroyAllWindows()
