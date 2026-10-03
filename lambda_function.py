
import boto3
import json
import io
import os
import uuid
import base64
import urllib.parse
import logging

from PIL import Image, ImageOps
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")

SOURCE_BUCKET = "serverless-image-resizer-source-2026"
DESTINATION_BUCKET = "serverless-image-resizer-destination-2026"

SIZES = {
    "small": (400, 400),
    "medium": (800, 800),
    "large": (1200, 1200)
}

ALLOWED_TYPES = {
    "image/jpeg": (".jpg", "JPEG"),
    "image/png": (".png", "PNG"),
    "image/webp": (".webp", "WEBP")
}

EXTENSION_FORMATS = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".webp": "WEBP"
}

FORMAT_DETAILS = {
    "JPEG": ("image/jpeg", ".jpg"),
    "PNG": ("image/png", ".png"),
    "WEBP": ("image/webp", ".webp")
}


def api_response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS"
        },
        "body": json.dumps(body)
    }


def handle_api(event):
    request_context = event.get("requestContext") or {}
    http_info = request_context.get("http") or {}

    method = (
        http_info.get("method")
        or event.get("httpMethod")
        or ""
    ).upper()

    route = event.get("routeKey", "")
    path = event.get("rawPath") or event.get("path") or ""

    logger.info(
        "API request: method=%s path=%s route=%s",
        method, path, route
    )

    if method == "OPTIONS":
        return api_response(200, {"message": "OK"})

    # POST /upload
    if method == "POST" and (
        route == "POST /upload" or path.endswith("/upload")
    ):
        raw_body = event.get("body") or ""

        try:
            if event.get("isBase64Encoded", False):
                raw_body = base64.b64decode(raw_body).decode("utf-8")

            data = json.loads(raw_body or "{}")

        except (ValueError, TypeError, UnicodeDecodeError):
            return api_response(400, {
                "error": "Invalid JSON. Send filename and contentType."
            })

        filename = os.path.basename(str(data.get("filename", "")))
        content_type = data.get("contentType", "")

        if not filename or content_type not in ALLOWED_TYPES:
            return api_response(400, {
                "error": (
                    "Provide a filename and contentType: "
                    "image/jpeg, image/png, or image/webp."
                )
            })

        extension = os.path.splitext(filename)[1].lower()

        expected_type = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp"
        }.get(extension)

        if expected_type != content_type:
            return api_response(400, {
                "error": "Filename extension and contentType do not match."
            })

        key = f"uploads/{uuid.uuid4().hex}{extension}"

        try:
            upload_url = s3.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": SOURCE_BUCKET,
                    "Key": key,
                    "ContentType": content_type
                },
                ExpiresIn=300
            )

            return api_response(200, {
                "key": key,
                "uploadUrl": upload_url,
                "contentType": content_type
            })

        except Exception:
            logger.exception("Could not create presigned upload URL")
            return api_response(500, {
                "error": "Could not create upload URL. Check IAM permissions."
            })

    # GET /results?key=uploads/filename.png
    if method == "GET" and (
        route == "GET /results" or path.endswith("/results")
    ):
        params = event.get("queryStringParameters") or {}
        key = params.get("key", "")

        if (
            not key.startswith("uploads/")
            or ".." in key
            or key.endswith("/")
        ):
            return api_response(400, {
                "error": "Provide a valid key beginning with uploads/."
            })

        # Output keys must match resize_s3_image().
        filename = os.path.basename(key)
        results = {}

        for size_name in SIZES:
            output_key = f"resized/{size_name}/{filename}"

            try:
                s3.head_object(
                    Bucket=DESTINATION_BUCKET,
                    Key=output_key
                )

                download_url = s3.generate_presigned_url(
                    "get_object",
                    Params={
                        "Bucket": DESTINATION_BUCKET,
                        "Key": output_key
                    },
                    ExpiresIn=3600
                )

                results[size_name] = {
                    "ready": True,
                    "key": output_key,
                    "url": download_url
                }

            except ClientError as exc:
                error_code = exc.response.get(
                    "Error", {}
                ).get("Code", "")

                if error_code in ("404", "NoSuchKey", "NotFound"):
                    results[size_name] = {"ready": False}
                else:
                    logger.exception(
                        "Error checking output object %s", output_key
                    )
                    return api_response(500, {
                        "error": "Could not check destination bucket permissions."
                    })

        complete = all(
            item.get("ready", False)
            for item in results.values()
        )

        return api_response(200, {
            "key": key,
            "results": results,
            "complete": complete
        })

    return api_response(404, {
        "error": "Route not found",
        "path": path,
        "method": method
    })


def resize_s3_image(event):
    for record in event.get("Records", []):
        if record.get("eventSource") != "aws:s3":
            logger.warning("Skipping non-S3 event record")
            continue

        source_bucket = record["s3"]["bucket"]["name"]

        object_key = urllib.parse.unquote_plus(
            record["s3"]["object"]["key"]
        )

        if source_bucket != SOURCE_BUCKET:
            logger.warning("Unexpected source bucket: %s", source_bucket)
            continue

        if not object_key.startswith("uploads/"):
            logger.info("Skipping object outside uploads/: %s", object_key)
            continue

        logger.info("Processing s3://%s/%s", source_bucket, object_key)

        response = s3.get_object(
            Bucket=source_bucket,
            Key=object_key
        )

        image_data = response["Body"].read()

        # First open the original image and capture its format.
        with Image.open(io.BytesIO(image_data)) as original:
            original.load()

            # IMPORTANT:
            # exif_transpose() may return a new image with format=None.
            # Capture the format BEFORE applying EXIF orientation.
            original_format = (original.format or "").upper()

            # Fallback to the uploaded file extension.
            if original_format not in FORMAT_DETAILS:
                extension = os.path.splitext(object_key)[1].lower()
                original_format = EXTENSION_FORMATS.get(extension, "")

            if original_format not in FORMAT_DETAILS:
                raise ValueError(
                    f"Unsupported image format: {original_format!r}; "
                    f"uploaded key: {object_key}"
                )

            oriented = ImageOps.exif_transpose(original)

            logger.info(
                "Image format: %s; dimensions: %s x %s",
                original_format,
                oriented.width,
                oriented.height
            )

            content_type, extension = FORMAT_DETAILS[original_format]
            filename = os.path.splitext(
                os.path.basename(object_key)
            )[0]

            for size_name, dimensions in SIZES.items():
                resized = oriented.copy()
                resized.thumbnail(dimensions)

                # JPEG does not support transparency.
                if original_format == "JPEG":
                    if resized.mode not in ("RGB", "L"):
                        resized = resized.convert("RGB")

                buffer = io.BytesIO()
                resized.save(buffer, format=original_format)
                buffer.seek(0)

                # Example: resized/small/abc123.png
                output_key = (
                    f"resized/{size_name}/"
                    f"{filename}{extension}"
                )

                s3.put_object(
                    Bucket=DESTINATION_BUCKET,
                    Key=output_key,
                    Body=buffer.getvalue(),
                    ContentType=content_type
                )

                logger.info(
                    "Created %s (%s x %s)",
                    output_key,
                    resized.width,
                    resized.height
                )

    return {
        "statusCode": 200,
        "body": "Image resizing completed"
    }


def lambda_handler(event, context):
    logger.info("Received event")

    try:
        # S3-triggered invocation
        if event.get("Records"):
            return resize_s3_image(event)

        # API Gateway invocation
        return handle_api(event)

    except Exception:
        logger.exception("Unhandled Lambda error")

        # Raise the error for S3 events so the failure is visible in logs.
        if event.get("Records"):
            raise

        return api_response(500, {
            "error": "Internal server error. Check Lambda CloudWatch logs."
        })