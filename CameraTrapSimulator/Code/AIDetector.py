import cv2, time
from imutils.video import VideoStream
from SendToHub import iothub_client_init, send_to_hub
import tensorflow.keras as keras
import numpy as np
import json

def get_video_feed(video_path):
    """
    Method to determine whther or not to use a live camera feed or a pre-recorded video feed.

    @param video_path: The provided path to the video to use.
    @return: The VideoCapture object that uses the correct type of video feed.
    """

    if video_path is None:
        video = cv2.VideoCapture(0)
        time.sleep(2.0)
        return video 
    else:
        video = cv2.VideoCapture(video_path)
        time.sleep(2.0)
        return video

def read_json_parameters():
    """
    Method that reads the required parameters from the config file.

    @return: The longitude, latitude and model run rate to use when using the AI model 
    and sending data to Azure IoT hub.
    """

    with open('config.json', 'r') as config_file:
        config = json.load(config_file)

    model_check_rate = config["model_check_rate"]
    Longitude = config["Longitude"]
    Latitude = config["Latitude"]
    return Longitude, Latitude, model_check_rate

def send_message(prediction, encodings, client, Longitude, Latitude):
    """
    Method to determine which animal was being predicted and sends a message to Azure IoT hub
    if the animal detected was an elephant.

    @param prediction: List of confidence values for each class.
    @param encodings: Mapping between prediction indicies and animals.
    @param client: The Azure IoT hub client used to send messages to IoT hub.
    @param Longitude: The simulated longitude.
    @param Latitude: The simulated latitude.
    """
    label = np.argmax(prediction)
    animal = encodings[label]
    if animal == 'elephant':
        send_to_hub(client, Longitude, Latitude, animal) # send message to Azure IoT hub
    return


def AI_trap(model_path, video_path=None):
    """
    This method partly acts as a control method, executing other methods in the correct order and when needed.
    Runs a frame per given time interval against the given ML model to check for the desired animal. Sends a message
    to IoT hub if the animal is detected.

    @param video_path: The provided path to the video to use.
    """
    video = get_video_feed(video_path)
    Longitude, Latitude, model_check_rate = read_json_parameters()
    frame_count = 0
    status_list = [None, None] # list needs 2 initial items
    client = iothub_client_init()
    encodings = {0: 'dog', 1: 'horse', 2: 'elephant', 3: 'butterfly', 4: 'chicken', 5: 'cat', 6: 'cow', 7: 'sheep', 8: 'spider', 9: 'squirrel'}


    model = keras.models.load_model(model_path)

    while True:

        frame_count += 1
        # captures boolean and numpy array from camera
        check, frame = video.read()

        if frame_count == model_check_rate:
            frame_count = 0
            # Below line can be changed if the input to the CNN is anything other than 256x256
            data = np.ndarray(shape=(1, 256, 256, 3), dtype=np.float32)
            image_array = cv2.resize(frame, dsize=(256, 256), interpolation=cv2.INTER_CUBIC)
            cv2.imshow("Image seen by ML model", image_array)

            # Normalize the image
            normalized_image_array = (image_array.astype(np.float32) / 255.0)

            # Load the image into the array
            data[0] = normalized_image_array

            # run the inference
            prediction = model.predict(data)
            send_message(prediction, encodings, client, Longitude, Latitude)

        cv2.imshow("Normal Frame", frame)

        # if q is pressed then program is exited
        key = cv2.waitKey(2)
        if key == ord('q'):
            break

    video.release()
    cv2.destroyAllWindows()
