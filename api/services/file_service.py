import datetime
import hashlib
import os
import uuid
from pathlib import Path
from typing import Any, Literal, Union

from flask_login import current_user
from werkzeug.exceptions import NotFound

from configs import dify_config
from constants import (
    AUDIO_EXTENSIONS,
    DOCUMENT_EXTENSIONS,
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
)
from constants.common import DEFAULT_AGENT_ICORN_PATH, DEFAULT_AGENT_ICORN_USED_BY
from core.file import helpers as file_helpers
from core.rag.extractor.extract_processor import ExtractProcessor
from extensions.ext_database import db
from extensions.ext_storage import storage
from models.account import Account
from models.enums import CreatorUserRole
from models.model import EndUser, UploadFile

from .errors.file import FileTooLargeError, UnsupportedFileTypeError

PREVIEW_WORDS_LIMIT = 3000

import requests
import ssl
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
from urllib3.exceptions import InsecureRequestWarning

# 禁用不安全请求的警告
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class LegacyHTTPAdapter(HTTPAdapter):
    """支持不安全TLS重新协商并禁用主机名验证的HTTP适配器"""

    def init_poolmanager(self, connections, maxsize, block=False):
        context = ssl.create_default_context()
        # 允许不安全的重新协商
        context.options |= 0x4  # OP_LEGACY_SERVER_CONNECT

        # 关键修复：禁用主机名验证
        context.check_hostname = False

        # 降低安全级别以支持旧版TLS
        context.set_ciphers('DEFAULT@SECLEVEL=1')

        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_context=context,
            assert_hostname=False  # 禁用主机名验证
        )


class FileService:
    @staticmethod
    def upload_file(
        *,
        filename: str,
        content: bytes,
        mimetype: str,
        user: Union[Account, EndUser, Any],
        source: Literal["datasets"] | None = None,
        source_url: str = "",
    ) -> UploadFile:
        # get file extension
        extension = os.path.splitext(filename)[1].lstrip(".").lower()

        # check if filename contains invalid characters
        if any(c in filename for c in ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]):
            raise ValueError("Filename contains invalid characters")

        if len(filename) > 200:
            filename = filename.split(".")[0][:200] + "." + extension

        if source == "datasets" and extension not in DOCUMENT_EXTENSIONS:
            raise UnsupportedFileTypeError()

        # get file size
        file_size = len(content)

        # check if the file size is exceeded
        if not FileService.is_file_size_within_limit(extension=extension, file_size=file_size):
            raise FileTooLargeError

        # generate file key
        file_uuid = str(uuid.uuid4())

        if isinstance(user, Account):
            current_tenant_id = user.current_tenant_id
        else:
            # end_user
            current_tenant_id = user.tenant_id

        file_key = "upload_files/" + (current_tenant_id or "") + "/" + file_uuid + "." + extension

        # save file to storage
        storage.save(file_key, content)

        # save file to db
        upload_file = UploadFile(
            tenant_id=current_tenant_id or "",
            storage_type=dify_config.STORAGE_TYPE,
            key=file_key,
            name=filename,
            size=file_size,
            extension=extension,
            mime_type=mimetype,
            created_by_role=(CreatorUserRole.ACCOUNT if isinstance(user, Account) else CreatorUserRole.END_USER),
            created_by=user.id,
            created_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
            used=False,
            hash=hashlib.sha3_256(content).hexdigest(),
            source_url=source_url,
        )

        db.session.add(upload_file)
        db.session.commit()

        if not upload_file.source_url:
            upload_file.source_url = file_helpers.get_signed_file_url(upload_file_id=upload_file.id)
            db.session.add(upload_file)
            db.session.commit()

        return upload_file

    @staticmethod
    def is_file_size_within_limit(*, extension: str, file_size: int) -> bool:
        if extension in IMAGE_EXTENSIONS:
            file_size_limit = dify_config.UPLOAD_IMAGE_FILE_SIZE_LIMIT * 1024 * 1024
        elif extension in VIDEO_EXTENSIONS:
            file_size_limit = dify_config.UPLOAD_VIDEO_FILE_SIZE_LIMIT * 1024 * 1024
        elif extension in AUDIO_EXTENSIONS:
            file_size_limit = dify_config.UPLOAD_AUDIO_FILE_SIZE_LIMIT * 1024 * 1024
        else:
            file_size_limit = dify_config.UPLOAD_FILE_SIZE_LIMIT * 1024 * 1024

        return file_size <= file_size_limit

    @staticmethod
    def upload_text(text: str, text_name: str) -> UploadFile:
        if len(text_name) > 200:
            text_name = text_name[:200]
        # user uuid as file name
        file_uuid = str(uuid.uuid4())
        file_key = "upload_files/" + current_user.current_tenant_id + "/" + file_uuid + ".txt"

        # save file to storage
        storage.save(file_key, text.encode("utf-8"))

        # save file to db
        upload_file = UploadFile(
            tenant_id=current_user.current_tenant_id,
            storage_type=dify_config.STORAGE_TYPE,
            key=file_key,
            name=text_name,
            size=len(text),
            extension="txt",
            mime_type="text/plain",
            created_by=current_user.id,
            created_by_role=CreatorUserRole.ACCOUNT,
            created_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
            used=True,
            used_by=current_user.id,
            used_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
        )

        db.session.add(upload_file)
        db.session.commit()

        return upload_file

    @staticmethod
    def get_file_preview(file_id: str):
        upload_file = db.session.query(UploadFile).filter(UploadFile.id == file_id).first()

        if not upload_file:
            raise NotFound("File not found")

        # extract text from file
        extension = upload_file.extension
        if extension.lower() not in DOCUMENT_EXTENSIONS:
            raise UnsupportedFileTypeError()

        text = ExtractProcessor.load_from_upload_file(upload_file, return_text=True)
        text = text[0:PREVIEW_WORDS_LIMIT] if text else ""

        return text

    @staticmethod
    def get_image_preview(file_id: str, timestamp: str, nonce: str, sign: str):
        result = file_helpers.verify_image_signature(
            upload_file_id=file_id, timestamp=timestamp, nonce=nonce, sign=sign
        )
        if not result:
            raise NotFound("File not found or signature is invalid")

        upload_file = db.session.query(UploadFile).filter(UploadFile.id == file_id).first()

        if not upload_file:
            raise NotFound("File not found or signature is invalid")

        # extract text from file
        extension = upload_file.extension
        if extension.lower() not in IMAGE_EXTENSIONS:
            raise UnsupportedFileTypeError()

        generator = storage.load(upload_file.key, stream=True)

        return generator, upload_file.mime_type

    @staticmethod
    def post_analysis_file(filename: str, content: bytes, mimetype: str):
        api_url = dify_config.DOCUMENT_RECOGNITION_URL

        # 创建支持旧版TLS的会话
        session = requests.Session()
        session.mount('https://', LegacyHTTPAdapter())

        try:
            files = {
                'file_bytes': (filename, content, mimetype)
            }

            data = {
                'not_save_img_link': 'true',
                'use_llm': 'false'
            }

            print("【多模态文档识别】发送 POST 请求")
            # 注意：verify=False 仍然需要，但真正的禁用逻辑在适配器中
            response = session.post(api_url, files=files, data=data, timeout=30, verify=False)
            response.raise_for_status()

            json = response.json()
            print("【多模态文档识别】接口响应：")
            print(f"【多模态文档识别】状态码：{response.status_code}")
            print(f"【多模态文档识别】响应内容：{json}")
            return json

        except requests.exceptions.RequestException as e:
            print(f"【锡商行】请求失败：{e}")
        finally:
            session.close()

    @staticmethod
    def replace_extension(filename: str) -> str:
        """将任意扩展名替换为.md"""
        # 查找最后一个点的位置（即扩展名的起始位置）
        last_dot_index = filename.rfind('.')

        if last_dot_index != -1:
            # 如果找到点，截取点之前的部分并添加.md
            return filename[:last_dot_index] + '.md'
        else:
            # 如果没有扩展名，直接添加.md
            return filename + '.md'

    @staticmethod
    def analysis_file(file_id: str):
        file = db.session.query(UploadFile).filter(UploadFile.id == file_id).first()

        if not file:
            raise NotFound("File not found or signature is invalid")

        # TODO 调用三方接口解析文件

        generator = storage.load_once(file.key)

        json = FileService.post_analysis_file(filename=file.name, content=generator, mimetype=file.mime_type)

        text = json["data"]["text"]

        text_bytes = text.encode(encoding="utf-8")

        return FileService.upload_file(
            filename=FileService.replace_extension(file.name),
            content=text_bytes,
            mimetype='text/markdown',
            user=current_user
        )

    @staticmethod
    def get_file_generator_by_file_id(file_id: str, timestamp: str, nonce: str, sign: str):
        result = file_helpers.verify_file_signature(upload_file_id=file_id, timestamp=timestamp, nonce=nonce, sign=sign)
        if not result:
            raise NotFound("File not found or signature is invalid")

        upload_file = db.session.query(UploadFile).filter(UploadFile.id == file_id).first()

        if not upload_file:
            raise NotFound("File not found or signature is invalid")

        generator = storage.load(upload_file.key, stream=True)

        return generator, upload_file

    @staticmethod
    def get_public_image_preview(file_id: str):
        upload_file = db.session.query(UploadFile).filter(UploadFile.id == file_id).first()

        if not upload_file:
            raise NotFound("File not found or signature is invalid")

        # extract text from file
        extension = upload_file.extension
        if extension.lower() not in IMAGE_EXTENSIONS:
            raise UnsupportedFileTypeError()

        generator = storage.load(upload_file.key)

        return generator, upload_file.mime_type

    @staticmethod
    def get_app_default_icon():
        upload_file = db.session.query(UploadFile).filter(UploadFile.used_by == DEFAULT_AGENT_ICORN_USED_BY).first()
        if not upload_file:
            if not Path(DEFAULT_AGENT_ICORN_PATH).exists():
                raise FileNotFoundError(f"文件 {DEFAULT_AGENT_ICORN_PATH} 不存在")
            filename = Path(DEFAULT_AGENT_ICORN_PATH).name
            with open(DEFAULT_AGENT_ICORN_PATH, "rb") as f:
                content = f.read()
            # 获取 MIME 类型（可以根据扩展名推断）
            extension = filename.split('.')[-1].lower()
            mimetype = f"image/{extension}" if extension in IMAGE_EXTENSIONS else "application/octet-stream"
            # get file size
            file_size = len(content)

            # check if the file size is exceeded
            if not FileService.is_file_size_within_limit(extension=extension, file_size=file_size):
                raise FileTooLargeError

            # generate file key
            file_uuid = str(uuid.uuid4())
            current_tenant_id = current_user.current_tenant_id

            file_key = "upload_files/" + (current_tenant_id or "") + "/" + file_uuid + "." + extension

            # save file to storage
            storage.save(file_key, content)

            # save file to db
            upload_file = UploadFile(
                tenant_id=current_tenant_id or "",
                storage_type=dify_config.STORAGE_TYPE,
                key=file_key,
                name=filename,
                size=file_size,
                extension=extension,
                mime_type=mimetype,
                created_by_role=CreatorUserRole.ACCOUNT,
                created_by=current_user.id,
                created_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
                used=False,
                used_by=DEFAULT_AGENT_ICORN_USED_BY,
                used_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
                hash=hashlib.sha3_256(content).hexdigest(),
                source_url="",
            )

            db.session.add(upload_file)
            db.session.commit()

            if not upload_file.source_url:
                upload_file.source_url = file_helpers.get_signed_file_url(upload_file_id=upload_file.id)
                db.session.add(upload_file)
                db.session.commit()

            return upload_file

        return upload_file
