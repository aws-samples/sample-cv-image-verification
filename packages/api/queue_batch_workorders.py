import json
import asyncio
import mimetypes
import time
from typing import List
import uuid
import boto3

from routers.methods.collection_utils import collection_to_dynamodb_item,collections_table
from routers.methods.create_verification_job import create_verification_job
from schemas.requests_responses import CreateVerificationJobRequest
from schemas.datamodel import Collection, CollectionFile, Item

from constants import STORAGE_BUCKET_NAME

from routers.methods.item_utils import get_items_by_name


s3 = boto3.client("s3")


def fetch_items_by_name(item_names: list[str]) -> list[Item]:
    items: List[Item] = []
    for item_name in item_names:
        item = get_items_by_name(item_name)

        if item is None or len(item) == 0:
            raise Exception(f"Item with name '{item_name}' not found")

        items += item

    return items


def get_collection_files(collection_id: str) -> list[CollectionFile]:
    new_dupes = 0
    prefix = f"collection-batch/{collection_id}/"

    try:
        response = s3.list_objects_v2(Bucket=STORAGE_BUCKET_NAME, Prefix=prefix)

        s3_files = []
        s3_keys = []
        e_tags = {}

        if "Contents" in response:
            for obj in response["Contents"]:
                s3_keys.append(obj.get("Key"))

        for key in s3_keys:
            head_response = s3.head_object(Bucket=STORAGE_BUCKET_NAME, Key=key)
            file_size = head_response.get("ContentLength")
            content_type = head_response.get("ContentType")
            content_type, _ = mimetypes.guess_type(key)
            if not content_type:
                content_type = "application/octet-stream"

            e_tag = head_response.get("ETag")

            if e_tag in e_tags:
                new_dupes += 1
                continue

            e_tags[e_tag] = True

            file_id = str(uuid.uuid4())

            collection_file = CollectionFile(
                id=file_id,
                s3_key=key,
                size=file_size,
                created_at=int(time.time()),
                filename=key.split("/")[-1],
                content_type=content_type,
            )

            s3_files.append(collection_file)

        return s3_files

    except Exception:
        return []


async def process_collections(collections: dict[str, str]):
    # Create the workorders
    for wo in collections:
        collection_id = wo
        items = collections[wo].split(",")

        current_time = int(time.time())

        fetched_items= fetch_items_by_name(items)
        s3_files = get_collection_files(collection_id)

        collection = Collection(
            id=collection_id,
            created_at=current_time,
            updated_at=current_time,
            description=collection_id,
            files=s3_files,
            items=fetched_items,
            address=None,
        )

        item_data = collection_to_dynamodb_item(collection)
        collections_table.put_item(Item=item_data)

    # Create the verification Jobs
    for wo in collections:
        request = CreateVerificationJobRequest(collection_id=wo)
        await create_verification_job(request)


def handler(event, context):
    payload = event

    if isinstance(event, str):
        payload = json.loads(event)
    elif "body" in event and isinstance(event["body"], str):
        payload = json.loads(event["body"])

    loop = asyncio.get_event_loop()
    loop.run_until_complete(process_collections(payload))


if __name__ == "__main__":
    approved_demo_orders: dict[str, str] = {
        # "WOR200903248556": "FD-01-01-02",
        # "WOR200907494373": "FD-01-01-02",
        "WOR200909934293": "FD-01-01-02",
        # "WOR200910168973": "CW-06-01-04,CW-06-02-04,FD-01-01-02,FD-01-02-05",
        # "WOR200910802444": "FD-01-02-05,FD-01-01-02",
        # "WOR200913611808": "FD-01-01-02,FD-01-02-05",
        # "WOR200913673044": "FD-01-02-05,FD-01-01-02",
        # "WOR200917139956": "CW-06-01-04,FD-01-01-02,CW-06-02-04",
        # "WOR200917557168": "FD-01-01-02,FD-01-02-05",
        # "WOR200918836168": "FD-01-01-02,CW-06-01-04,CW-06-02-04",
        # "WOR200919122393": "FD-01-01-02,FD-01-02-05",
        # "WOR200919515286": "FD-01-02-05,FD-01-01-02",
        # "WOR200919683344": "FD-01-02-05,FD-01-01-02",
        # "WOR200919887473": "FD-01-01-02",
        # "WOR200919990718": "FD-01-01-02,FD-01-02-05",
        # "WOR200920018318": "FD-01-02-05,FD-01-01-02",
        # "WOR200920238986": "FD-01-01-02",
        # "WOR200921133186": "FD-01-02-05,FD-01-01-02",
        # "WOR200921454518": "FD-01-01-02,FD-01-02-05",
        # "WOR200921674244": "FD-01-01-02",
        # "WOR200921676308": "FD-01-01-02,CW-06-02-04,CW-06-01-04",
        # "WOR200921870138": "FD-01-01-02",
        # "WOR200922336486": "FD-01-01-02",
        # "WOR200922503708": "FD-01-01-02",
        # "WOR200922596173": "FD-01-02-05,FD-01-01-02",
        # "WOR200922661273": "FD-01-02-05,FD-01-01-02",
        # "WOR200922710886": "FD-01-02-05,FD-01-01-02",
        # "WOR200922717444": "CW-06-02-04,FD-01-01-02,CW-06-01-04",
        # "WOR200922734144": "FD-01-01-02,FD-01-02-05",
        # "WOR200922807808": "FD-01-01-02,CW-06-01-04,CW-06-02-04",
        # "WOR200922909568": "FD-01-01-02,FD-01-02-05",
        # "WOR200922916568": "FD-01-01-02,FD-01-02-05",
        # "WOR200923099238": "FD-01-01-02",
        # "WOR200923102644": "FD-01-01-02",
        # "WOR200923526193": "FD-01-01-02",
        # "WOR200923979208": "FD-01-01-02",
        # "WOR200924155021": "FD-01-01-02",
        # "WOR200924389773": "FD-01-01-02,FD-01-02-05",
        # "WOR200924457608": "CW-06-01-04,CW-06-02-04,FD-01-01-02,FD-01-02-05",
        # "WOR200925515118": "FD-01-01-02,CW-06-01-04,CW-06-02-04",
        # "WOR200925634321": "FD-01-01-02",
        # "WOR200925851956": "FD-01-01-02",
        # "WOR200925940373": "FD-01-01-02,CW-06-01-04,CW-06-02-04",
        # "WOR200926268956": "FD-01-01-02",
        # "WOR200926636973": "FD-01-02-05,FD-01-01-02",
        # "WOR200926825286": "FD-01-01-02",
        # "WOR200927106093": "FD-01-01-02,FD-01-02-05",
        # "WOR200927730721": "FD-01-01-02",
        # "WOR200928002086": "CW-06-02-04,FD-01-01-02,CW-06-01-04",
        # "WOR200928154268": "FD-01-02-05,FD-01-01-02",
    }

    rejected_demo_orders = {
        "WOR200910964886": "FD-01-01-02",
        "WOR200918048021": "FD-01-01-02",
        "WOR200920499838": "FD-01-01-02",
        "WOR200921473486": "FD-01-01-02",
        "WOR200921797456": "FD-01-01-02",
        "WOR200922445973": "FD-01-01-02",
        "WOR200922575608": "FD-01-01-02",
        "WOR200922945008": "FD-01-01-02",
        "WOR200924247956": "FD-01-01-02",
        "WOR200924371808": "FD-01-01-02",
        "WOR200925166256": "FD-01-01-02",
        "WOR200925624093": "FD-01-01-02",
        "WOR200925737156": "FD-01-01-02",
        "WOR200926770744": "FD-01-01-02",
        "WOR200926884293": "FD-01-01-02",
        "WOR200927301721": "FD-01-01-02",
        "WOR200927860921": "FD-01-01-02",
        "WOR200928053044": "FD-01-01-02",
        "WOR200929995208": "FD-01-01-02",
        "WOR200931090644": "FD-01-01-02",
    }

    handler(approved_demo_orders, {})
    # handler(rejected_demo_orders, {})
