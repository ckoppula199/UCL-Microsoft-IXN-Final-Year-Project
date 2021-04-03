import cv2, time, pandas, imutils
from imutils.video import VideoStream
from datetime import datetime
import json
from SendToHub import iothub_client_init, send_to_hub

def get_video_feed(video_path):
    """
    Method to determine whther or not to use a live camera feed or a pre-recorded video feed.

    @param video_path: The provided path to the video to use.
    @return: The VideoCapture object that uses the correct type of video feed.
    """

    if video_path is None:
        # 0 returns video from first camera on machine.
        # If multiple cameras on machine change this value as needed.
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

    @return: The longitude, latitude, reference frame reset and object size values to be used
    when carrying out the motion detection and sending signals back to Azure.
    """

    with open('config.json', 'r') as config_file:
        config = json.load(config_file)

    reference_frame_reset = config["reference_frame_reset"]
    object_size = config["object_size"]
    Longitude = config["Longitude"]
    Latitude = config["Latitude"]
    return Longitude, Latitude, reference_frame_reset, object_size 

def show_frames(frame, grey, thresh_frame, delta_frame, text):
    """
    Method to display the different stages of image processing on screen.

    @param frame: The original frame captured from the video feed.
    @param grey: The greyscaled and denoised version of the original frame.
    @param thresh_frame: The frame that highlights clearly the moving objects.
    @param: delta_frame: The frame showing the difference between the current frame and the reference frame.
    @param text: Text to be put on the frame.
    """

    # adds text overlay of current status and time
    cv2.putText(frame, "Status: {}".format(text), (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
    cv2.putText(frame, datetime.now().strftime("%A %d %B %Y %I:%M:%S%p"), (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0 , 255), 1)

    # displays images
    cv2.imshow("Grey", grey)
    cv2.imshow("Threshold", thresh_frame)
    cv2.imshow("Delta", delta_frame)
    cv2.imshow("Normal", frame)

def create_times_csv(df, times):
    """
    Creates a dataframe and then a CSV file of all the times objects entered then exited the frame.

    @param df: empty dataframe with the correct format.
    @param times: list of times object entered and exited the frame.
    """

    # creates a csv file of all the times when motion was detected and for how long.
    if len(times) % 2 != 0:
        times = times[:-1]
    for i in range(0, len(times), 2):
        df = df.append({"Start": times[i], "End": times[i+1]}, ignore_index=True)
    df.to_csv("Times.csv")

def preprocess_frame(frame):
    """
    Method that converts the original frame to greyscale then applies a guassian blur to denoise it.
    Also resizes the original frame.

    @param frame: The original clean frame from the video feed.
    @return: The resized frame and the greyed denoised frame.
    """

    frame = imutils.resize(frame, width=500)
    grey=cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) # converts image to a grey version for more accuracy later on
    grey=cv2.GaussianBlur(grey, (21, 21,), 0) # smooths edges and reduces noise in calculations
    return frame, grey

def identify_differences(reference_frame, grey):
    """
    Method to identify differences between the current frame and the reference frame and to check
    if any objects of sufficient size have been detected.

    @param reference_frame: The reference frane against which current frames are being compared to
    to check for differences.
    @param grey: The greyscaled and denoised version of the original frame.
    @return: The frame with the differences between the reference frame and the current frame and the frame that highlights moving objects.
    """

    # calculates difference between reference_frame and current fram and stores as an image
    delta_frame=cv2.absdiff(reference_frame, grey)

    # makes any pixel with a difference larger than a threshold white, else black
    thresh_frame=cv2.threshold(delta_frame, 25, 255, cv2.THRESH_BINARY)[1] #adjust second argument to change the difference required for a pixel to be classed as moving
    thresh_frame=cv2.dilate(thresh_frame, None,iterations=2)

    return delta_frame, thresh_frame

def update_status(status_list, times, status, client, Longitude, Latitude):
    """
    Method that keeps track of if there is an object currently being detected or not.

    @param status_list: List with status of the last 2 frames. 0 if object is being detected, 1 if nothing is being detected.
    @param times: List keeping track of what times objects enter and exit the frame.
    @param status: The status of the current frame.
    @param client: The Azure IoT hub client used to send messages to IoT hub.
    @param Longitude: The simulated longitude.
    @param Latitude: The simulated latitude.
    """

    #saves space as we only need the last 2 values to check a change in status
    status_list.append(status)
    status_list = status_list[-2:]

    if status_list[-1] == 1 and status_list[-2] == 0: #object has been detected
        times.append(datetime.now())
        send_to_hub(client, Longitude, Latitude) # send message to Azure IoT hub
    if status_list[-1] == 0 and status_list[-2] == 1: #object is no longer being detected
        times.append(datetime.now())

def motion_trap(video_path=None):
    """
    This method acts partly as a control method. It executes the other required methods in the correct order and when needed.
    Consists of a while loop that continously runs until the q button is pressed. Constantly checks to see if there is motion.
    If motion is detected a message is sent to Azure IoT hub.

    @param video_path: The provided path to the video to use.
    """
    video = get_video_feed(video_path)
    Longitude, Latitude, reference_frame_reset, object_size = read_json_parameters()
    reference_frame = None
    frame_count = 0
    status_list = [None, None]
    times = []
    df=pandas.DataFrame(columns=["Start", "End"])
    client = iothub_client_init()


    while True:

        # captures boolean and numpy array from camera
        check, frame = video.read()
        text = "No Movement Detected"
        status = 0
        
        if frame is None:
            break

        frame, grey = preprocess_frame(frame)

        #checks to see if we need to assign the reference frame a value
        if reference_frame is None or frame_count == reference_frame_reset:
            reference_frame = grey
            frame_count = 0
            continue

        frame_count += 1
        delta_frame, thresh_frame = identify_differences(reference_frame, grey)

        # finds contours of distinct objects in the frame
        cnts,_=cv2.findContours(thresh_frame.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # if object has area greater than object_size pxls then it is highlighted
        for contour in cnts:
            if cv2.contourArea(contour) < object_size: # change value based on size of object trying to detect
                continue
            status = 1

            # draw bounding box around area where motion is occuring
            (x, y, w, h) = cv2.boundingRect(contour)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
            text = "Motion Detected"

        update_status(status_list, times, status, client, Longitude, Latitude)
        show_frames(frame, grey, thresh_frame, delta_frame, text)

        # if q is pressed then loop is exited
        key = cv2.waitKey(2)
        if key == ord('q'):
            if status == 1:
                times.append(datetime.now())
            break

    create_times_csv(df, times)
    video.release()
    cv2.destroyAllWindows()
