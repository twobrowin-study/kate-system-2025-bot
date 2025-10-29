import asyncio
from io import BytesIO

from loguru import logger
from minio import Minio, S3Error
from urllib3 import BaseHTTPResponse

from src.config import settings


class NoContentBytesError(Exception):
    """Нет контента"""


class MinIOClient:
    """
    Обёртка для удобного асинхронного взаимодействия с MINIO
    """

    def __init__(self, host: str, secure: bool, access_key: str, secret_key: str) -> None:  # noqa: FBT001
        self.host = host
        self._client = Minio(self.host, access_key=access_key, secret_key=secret_key, secure=secure)
        self._semaphore = asyncio.Semaphore(50)

    async def download(self, bucket: str, filename: str) -> tuple[BytesIO, str]:
        """Асинхронная загрузка файла из бакета"""
        logger.debug(f"Downloading {filename} from MinIO bucket {bucket}")

        def _get_object() -> BaseHTTPResponse:
            return self._client.get_object(bucket, filename)

        try:
            response = await asyncio.get_event_loop().run_in_executor(None, _get_object)
            logger.debug(f"Done downloading {filename} from MinIO bucket {bucket}")
            file_bytes = BytesIO(response.read())
            content_type = response.getheader("content-type")
        except S3Error as e:
            if e.code == "NoSuchKey":
                logger.debug(f"File {filename} not found in MinIO bucket {bucket}")
                file_bytes = None
                content_type = None
            else:
                raise
        else:
            response.close()
            response.release_conn()

        if not content_type:
            content_type = "application/octet-stream"

        if not file_bytes:
            raise NoContentBytesError(f"No content bytes for bucket {bucket} and file {filename}")

        return file_bytes, content_type


minio = MinIOClient(
    settings.minio_host,
    settings.minio_secure,
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key.get_secret_value(),
)
