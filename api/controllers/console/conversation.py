from flask_restful import reqparse
from flask_restful.inputs import int_range

from services.conversation_service import ConversationService
from flask_restful import Resource, marshal_with
from sqlalchemy.orm import Session

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

PREVIEW_WORDS_LIMIT = 3000


class ConversationListApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    @marshal_with(upload_config_fields)
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("last_id", type=uuid_value, location="args")
        parser.add_argument("limit", type=int_range(1, 100), required=False, default=20, location="args")
        parser.add_argument(
            "sort_by",
            type=str,
            choices=["created_at", "-created_at", "updated_at", "-updated_at"],
            required=False,
            default="-updated_at",
            location="args",
        )
        args = parser.parse_args()

        pinned = None
        if "pinned" in args and args["pinned"] is not None:
            pinned = args["pinned"] == "true"

        end_user = db.session.query(EndUser).filter(EndUser.session_id == args["session_id"]).first()
        if not end_user:
            raise BadRequest("Session ID does not exist.")

        try:
            with Session(db.engine) as session:
                return ConversationService.pagination_by_end_user(
                    session=session,
                    end_user_id=end_user.id,
                    last_id=args["last_id"],
                    limit=args["limit"],
                    pinned=pinned,
                    sort_by=args["sort_by"],
                ), 200
        except LastConversationNotExistsError:
            raise NotFound("Last Conversation Not Exists.")
