import argparse
from pathlib import Path

from google.cloud import storage


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upload images to GCS for use with RubinTV"
    )
    parser.add_argument("files", type=str, nargs="+", help="Files to upload")
    parser.add_argument(
        "--bucket",
        type=str,
        default="rubintv_data",
        help="Bucket to upload to",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--image", action="store_true", help="Upload files from imExam"
    )
    group.add_argument(
        "--spec", action="store_true", help="Upload files from specExam"
    )
    args = parser.parse_args()

    client = storage.Client()
    bucket = client.get_bucket(args.bucket)
    if args.image:
        prefix = "summit_imexam"
    elif args.spec:
        prefix = "summit_specexam"
    else:
        raise RuntimeError("Somehow neither --image nor --spec was passed")

    for f in args.files:
        path = Path(f)
        blob = bucket.blob("/".join([prefix, path.name]))
        blob.upload_from_filename(f)


if __name__ == "__main__":
    main()
