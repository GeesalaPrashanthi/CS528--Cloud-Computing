import json
from datetime import datetime, timezone

from google.cloud import pubsub_v1
from google.cloud import storage


PROJECT_ID = "enduring-trees-508117-p7"
SUBSCRIPTION_NAME = "forbidden-requests-sub"

BUCKET_NAME = "cs528-hw2-pgeesala"
LOG_OBJECT = "forbidden_requests/forbidden_requests.log"


subscriber = pubsub_v1.SubscriberClient()
storage_client = storage.Client()

subscription_path = subscriber.subscription_path(
    PROJECT_ID,
    SUBSCRIPTION_NAME
)


def append_to_gcs(log_message):
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(LOG_OBJECT)

    if blob.exists():
        existing = blob.download_as_text()
    else:
        existing = ""

    blob.upload_from_string(
        existing + log_message + "\n"
    )


def callback(message):
    try:
        data = json.loads(
            message.data.decode("utf-8")
        )

        timestamp = datetime.now(
            timezone.utc
        ).isoformat()

        log_message = (
            f"{timestamp} | "
            f"FORBIDDEN REQUEST | "
            f"country={data.get('country')} | "
            f"file={data.get('file')}"
        )

        print(log_message)

        append_to_gcs(log_message)

        message.ack()

    except Exception as exc:
        print(f"Error processing message: {exc}")
        message.nack()


print(
    f"Listening on {subscription_path}..."
)

streaming_pull_future = subscriber.subscribe(
    subscription_path,
    callback=callback
)

try:
    streaming_pull_future.result()

except KeyboardInterrupt:
    streaming_pull_future.cancel()
