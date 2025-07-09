from flask_restful import reqparse

from services.conversation_service import ConversationService
from flask_restful import Resource, marshal_with, inputs

from libs.helper import uuid_value

import services
from configs import dify_config
from constants import DOCUMENT_EXTENSIONS
from controllers.common.errors import FilenameNotExistsError
from controllers.console.wraps import (
    account_initialization_required,
    cloud_edition_billing_resource_check,
    setup_required,
)
from fields.file_fields import file_fields, upload_config_fields
from libs.login import login_required
from services.file_service import FileService

from werkzeug.exceptions import BadRequest, Forbidden, NotFound, abort

from extensions.ext_database import db

from models.model import EndUser
from services.errors.conversation import ConversationNotExistsError, LastConversationNotExistsError
from fields.conversation_fields import conversation_with_summary_pagination_fields

PREVIEW_WORDS_LIMIT = 3000


class ConversationListApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    @marshal_with(conversation_with_summary_pagination_fields)
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument(
            "session_id",
            type=str,
            required=True,
            location="args"
        )
        parser.add_argument(
            "keyword",
            type=str,
            required=False,
            location="args"
        )
        parser.add_argument("page", type=inputs.int_range(1, 99999), required=False, default=1, location="args")
        parser.add_argument("limit", type=inputs.int_range(1, 100), required=False, default=20, location="args")
        parser.add_argument(
            "sort_by",
            type=str,
            choices=["created_at", "-created_at", "updated_at", "-updated_at"],
            required=False,
            default="-updated_at",
            location="args",
        )
        args = parser.parse_args()

        end_user = db.session.query(EndUser).filter(EndUser.session_id == args["session_id"]).first()
        if not end_user:
            raise BadRequest("Session ID does not exist.")

        try:
            return ConversationService.pagination_by_end_user(
                end_user_id=end_user.id,
                keyword=args["keyword"],
                page=args["page"],
                limit=args["limit"],
                sort_by=args["sort_by"],
            ), 200
        except LastConversationNotExistsError:
            raise NotFound("Last Conversation Not Exists.")
