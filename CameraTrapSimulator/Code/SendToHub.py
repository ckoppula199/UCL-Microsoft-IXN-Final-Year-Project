import random
import time
import json
from azure.iot.device import IoTHubDeviceClient, Message

# CONNECTION_STRING = "HostName=CameraTrap.azure-devices.net;DeviceId=MyPythonDevice;SharedAccessKey=wvOeXrEhPju2uVWiIaxRWIkR3ILn1fnQgnJo/uQ9wsg="

def iothub_client_init():
    """
    Method used to create a IoT hub client and connect to IoT hub using a connection string.
    @return: The Azure IoT hub client.
    """
    # Create an IoT Hub client
    with open('config.json', 'r') as config_file:
        config = json.load(config_file)

    client = IoTHubDeviceClient.create_from_connection_string(config['connection_string'])
    return client

def send_to_hub(client, longitude, latitude, animal=None):
    """
    Method that sends the data to Azure IoT hub.

    @param client: The Azure IoT hub client.
    @param longitude: The simulated longitude.
    @param latitide: The simulated latitude.
    @param animal: The animal that was detected.
    """

    Longitude = longitude #36.2833
    Latitude = latitude #-18.8333
    Animal = ''
    geo_json_format = f'{{"type": "Feature", "geometry": {{"type": "Point", "coordinates": [{Longitude}, {Latitude}]}}}}'
    # MSG_TXT can be customised to deliver different messages containing different information to Azure IoT Hub 
    MSG_TXT = '{{GeoJSON: {geo_json_format}, Animal: {Animal}}}'

    if animal is not None:
        Animal = animal
    msg_txt_formatted = MSG_TXT.format(geo_json_format=geo_json_format, Animal=Animal)
    message = Message(msg_txt_formatted)
    message.custom_properties["Location"] = geo_json_format

    # Example of how to add a custom property to the message being sent to Azure IoT Hub.

    if Animal == 'elephant':
        message.custom_properties["elephantAlert"] = "true"
    else:
        message.custom_properties["elephantAlert"] = "false"

    # Send the message.
    print( "Sending message: {}".format(message) )
    client.send_message(message)
    print ( "Message successfully sent" )
