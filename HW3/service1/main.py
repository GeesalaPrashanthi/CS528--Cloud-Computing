import json
import logging

import functions_framework
from flask import Response
from google.cloud import storage
from google.cloud import pubsub_v1


PROJECT_ID = "enduring-trees-508117-p7"
BUCKET_NAME = "cs528-hw2-pgeesala"
TOPIC_NAME = "forbidden-requests"

FORBIDDEN_COUNTRIES = {
    "north korea",
    "iran",
    "cuba",
    "myanmar",
    "iraq",
    "libya",
    "sudan",
    "zimbabwe",
    "syria"
}


@functions_framework.http
def file_service(request):

    # Unsupported methods
    if request.method not in ["GET", "POST"]:
        message = f"HTTP method {request.method} is not implemented"

        print(message)

        logging.error(json.dumps({
            "message": message,
            "status": 501,
            "method": request.method
        }))

        return Response(message, status=501)

    # Get filename
    if request.method == "GET":
        filename = request.path.lstrip("/")
    else:
        data = request.get_json(silent=True) or {}
        filename = data.get("file")

    if not filename:
        return Response("File name not provided", status=400)

    # Check X-country header
    country = request.headers.get("X-country", "").strip()

    if country.lower() in FORBIDDEN_COUNTRIES:

        message = f"Permission denied: requests from {country} are forbidden"

        print(message)

        logging.error(json.dumps({
            "message": message,
            "status": 400,
            "country": country,
            "file": filename
        }))

        # Send message to Pub/Sub
        publisher = pubsub_v1.PublisherClient()

        topic_path = publisher.topic_path(
            PROJECT_ID,
            TOPIC_NAME
        )

        data = {
            "country": country,
            "file": filename
        }

        publisher.publish(
            topic_path,
            json.dumps(data).encode("utf-8")
        )

        return Response(message, status=400)

    # Access bucket file
    object_name = f"pages/{filename}"

    storage_client = storage.Client()

    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(object_name)

    if not blob.exists():
        message = f"File not found: {filename}"

        print(message)

        logging.error(json.dumps({
            "message": message,
            "status": 404,
            "file": filename
        }))

        return Response(message, status=404)

    contents = blob.download_as_text()

    return Response(
        contents,
        status=200,
        mimetype="text/html"
    )