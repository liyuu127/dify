from flask_restful import Resource, inputs, marshal_with, reqparse
from werkzeug.exceptions import NotFound

from controllers.console.wraps import (
    account_initialization_required,
    setup_required,
)
from extensions.ext_database import db
from fields.conversation_fields import conversation_with_summary_pagination_fields
from libs.infinite_scroll_pagination import InfiniteScrollPagination
from libs.login import login_required
from models.model import EndUser
from services.conversation_service import ConversationService
from services.errors.conversation import LastConversationNotExistsError

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

        end_users = db.session.query(EndUser).filter(EndUser.session_id == args["session_id"]).all()
        if not end_users:
            return InfiniteScrollPagination(data=[], limit=args["limit"], has_more=False), 200

        try:
            return ConversationService.pagination_by_end_user(
                end_users=end_users,
                keyword=args["keyword"],
                page=args["page"],
                limit=args["limit"],
                sort_by=args["sort_by"],
            ), 200
        except LastConversationNotExistsError:
            raise NotFound("Last Conversation Not Exists.")
