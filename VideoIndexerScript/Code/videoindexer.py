import requests
import os
import io
import json
import time

from azure.storage.blob import (
    ContentSettings,
    BlobBlock,
    BlockListType,
    BlockBlobService
)


# Load details from config file
with open('config.json', 'r') as config_file:
        config = json.load(config_file)

storage_account_name = config["storage_account_name"]
storage_account_key = config["storage_account_key"]
storage_container_name = config["storage_container_name"]

video_indexer_account_id = config["video_indexer_account_id"]
video_indexer_api_key = config["video_indexer_api_key"]
video_indexer_api_region = config["video_indexer_api_region"]

file_name = config["file_name"]

confidence_threshold = config["confidence_threshold"]

print('Blob Storage: Account: {}, Container: {}.'.format(storage_account_name,storage_container_name))

# Get File content from blob
block_blob_service = BlockBlobService(account_name=storage_account_name, account_key=storage_account_key)
audio_blob = block_blob_service.get_blob_to_bytes(storage_container_name, file_name)
audio_file = io.BytesIO(audio_blob.content).read()

print('Blob Storage: Blob {} loaded.'.format(file_name))

# Authorize against Video Indexer API
auth_uri = 'https://api.videoindexer.ai/auth/{}/Accounts/{}/AccessToken'.format(video_indexer_api_region,video_indexer_account_id)
auth_params = {'allowEdit':'true'}
auth_header = {'Ocp-Apim-Subscription-Key': video_indexer_api_key}
auth_token = requests.get(auth_uri,headers=auth_header,params=auth_params).text.replace('"','')

print('Video Indexer API: Authorization Complete.')
print('Video Indexer API: Uploading file: ',file_name)

# Upload Video to Video Indexer API
upload_uri = 'https://api.videoindexer.ai/{}/Accounts/{}/Videos'.format(video_indexer_api_region,video_indexer_account_id)
upload_header = {'Content-Type': 'multipart/form-data'}
upload_params = {
    'name':file_name,
    'accessToken':auth_token,
    'streamingPreset':'Default',
    'fileName':file_name,
    'description': '#testfile',
    'privacy': 'Private',
    'indexingPreset': 'Default',
    'sendSuccessEmail': 'False'}

files= {'file': (file_name, audio_file)}
r = requests.post(upload_uri,params=upload_params, files=files)
response_body = r.json()

print('Video Indexer API: Upload Completed.')
print('Video Indexer API: File Id: {}.'.format(response_body.get('id')))
video_id = response_body.get('id')

# Check if video is done processing
video_index_uri = 'https://api.videoindexer.ai/{}/Accounts/{}/Videos/{}/Index'.format(video_indexer_api_region, video_indexer_account_id, video_id)
video_index_params = {
    'accessToken': auth_token,
    'reTranslate': 'False',
    'includeStreamingUrls': 'True'
}
r = requests.get(video_index_uri, params=video_index_params)
response_body = r.json()

while response_body.get('state') != 'Processed':
    time.sleep(10)
    r = requests.get(video_index_uri, params=video_index_params)
    response_body = r.json()
    print(response_body.get('state'))

print("Done")

output_response = []
item_index = 1
for item in response_body.get('videos')[0]['insights']['labels']:
    reformatted_item = {}
    instances = []
    reformatted_item['id'] = item_index
    reformatted_item['label'] = item['name']
    for instance in item['instances']:
        reformatted_instance = {}
        if instance['confidence'] > confidence_threshold:
            reformatted_instance['confidence'] = instance['confidence']
            reformatted_instance['start'] = instance['start']
            reformatted_instance['end'] = instance['end']
            instances.append(reformatted_instance)
    if len(instances) > 0:
        item_index += 1
        reformatted_item['instances'] = instances
        output_response.append(reformatted_item)

#Print response given by the script
print(json.dumps(output_response, indent=4))