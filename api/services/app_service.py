import json
import logging
from datetime import UTC, datetime
from typing import Optional, cast

from flask_login import current_user
from flask_sqlalchemy.pagination import Pagination

from configs import dify_config
from constants.model_template import default_app_templates
from core.agent.entities import AgentToolEntity
from core.errors.error import LLMBadRequestError, ProviderTokenNotInitError
from core.model_manager import ModelManager
from core.model_runtime.entities.model_entities import ModelPropertyKey, ModelType
from core.model_runtime.model_providers.__base.large_language_model import LargeLanguageModel
from core.tools.tool_manager import ToolManager
from core.tools.utils.configuration import ToolParameterConfigurationManager
from events.app_event import app_was_created
from extensions.ext_database import db
from models.account import Account, TenantAccountRole
from models.model import App, AppMode, AppModelConfig, AppPermission, AppPermissionEnum, Site
from models.tools import ApiToolProvider
from services.enterprise.enterprise_service import EnterpriseService
from services.errors.account import NoPermissionError
from services.feature_service import FeatureService
from services.file_service import FileService
from services.tag_service import TagService
from tasks.remove_app_and_related_data_task import remove_app_and_related_data_task


class AppService:
    def get_paginate_apps(self, user_id: str, tenant_id: str, args: dict) -> Pagination | None:
        """
        Get app list with pagination
        :param user_id: user id
        :param tenant_id: tenant id
        :param args: request args
        :return:
        """

        user = current_user
        filters = [App.tenant_id == tenant_id, App.is_universal == False]
        create_by_me = args.get("is_created_by_me", False)

        # get permitted app ids
        app_permission = (
            db.session.query(AppPermission).filter_by(account_id=user.id, tenant_id=tenant_id).all()
        )
        permitted_app_ids = {dp.app_id for dp in app_permission} if app_permission else None

        if user.current_role != TenantAccountRole.OWNER:
            if permitted_app_ids:
                # show all datasets that the user has permission to access
                filters.append(db.or_(
                    App.permission == AppPermissionEnum.ALL_TEAM,
                    db.and_(
                        App.permission == AppPermissionEnum.ONLY_ME, App.created_by == user_id
                    ),
                    db.and_(
                        App.permission == AppPermissionEnum.PARTIAL_TEAM,
                        App.id.in_(permitted_app_ids),
                    ),
                ))
            else:
                filters.append(db.or_(
                    App.permission == AppPermissionEnum.ALL_TEAM,
                    db.and_(
                        App.permission == AppPermissionEnum.ONLY_ME, App.created_by == user_id
                    ),
                ))

        if args["mode"] == "workflow":
            filters.append(App.mode == AppMode.WORKFLOW.value)
        elif args["mode"] == "completion":
            filters.append(App.mode == AppMode.COMPLETION.value)
        elif args["mode"] == "chat":
            filters.append(App.mode == AppMode.CHAT.value)
        elif args["mode"] == "advanced-chat":
            filters.append(App.mode == AppMode.ADVANCED_CHAT.value)
        elif args["mode"] == "agent-chat":
            filters.append(App.mode == AppMode.AGENT_CHAT.value)
        elif args["mode"] == "channel":
            filters.append(App.mode == AppMode.CHANNEL.value)
        if create_by_me:
            filters.append(App.created_by == user_id)
        if args.get("name"):
            name = args["name"][:30]
            filters.append(App.name.ilike(f"%{name}%"))
        if args.get("tag_ids"):
            target_ids = TagService.get_target_ids_by_tag_ids("app", tenant_id, args["tag_ids"])
            if target_ids:
                filters.append(App.id.in_(target_ids))
            else:
                return None

        app_models = db.paginate(
            db.select(App).where(*filters).order_by(App.created_at.desc()),
            page=args["page"],
            per_page=args["limit"],
            error_out=False,
        )

        return app_models

    def create_app(self, tenant_id: str, args: dict, account: Account) -> App:
        """
        Create app
        :param tenant_id: tenant id
        :param args: request args
        :param account: Account instance
        """
        app_mode = AppMode.value_of(args["mode"])
        app_template = default_app_templates[app_mode]

        # get model config
        default_model_config = app_template.get("model_config")
        default_model_config = default_model_config.copy() if default_model_config else None
        if default_model_config and "model" in default_model_config:
            # get model provider
            model_manager = ModelManager()

            # get default model instance
            try:
                model_instance = model_manager.get_default_model_instance(
                    tenant_id=account.current_tenant_id or "", model_type=ModelType.LLM
                )
            except (ProviderTokenNotInitError, LLMBadRequestError):
                model_instance = None
            except Exception as e:
                logging.exception(f"Get default model instance failed, tenant_id: {tenant_id}")
                model_instance = None

            if model_instance:
                if (
                    model_instance.model == default_model_config["model"]["name"]
                    and model_instance.provider == default_model_config["model"]["provider"]
                ):
                    default_model_dict = default_model_config["model"]
                else:
                    llm_model = cast(LargeLanguageModel, model_instance.model_type_instance)
                    model_schema = llm_model.get_model_schema(model_instance.model, model_instance.credentials)
                    if model_schema is None:
                        raise ValueError(f"model schema not found for model {model_instance.model}")

                    default_model_dict = {
                        "provider": model_instance.provider,
                        "name": model_instance.model,
                        "mode": model_schema.model_properties.get(ModelPropertyKey.MODE),
                        "completion_params": {},
                    }
            else:
                provider, model = model_manager.get_default_provider_model_name(
                    tenant_id=account.current_tenant_id or "", model_type=ModelType.LLM
                )
                default_model_config["model"]["provider"] = provider
                default_model_config["model"]["name"] = model
                default_model_dict = default_model_config["model"]

            default_model_config["model"] = json.dumps(default_model_dict)

        app = App(**app_template["app"])
        app.name = args["name"]
        app.description = args.get("description", "")
        app.mode = args["mode"]
        icon = args.get("icon")
        if not icon:
            app.icon_type = "image"
            default_icon = FileService.get_app_default_icon()
            app.icon = default_icon.id
            # app.icon_background = args["icon_background"]
        else:
            app.icon_type = args.get("icon_type", "emoji")
            app.icon = args["icon"]
            app.icon_background = args["icon_background"]
        app.tenant_id = tenant_id
        app.api_rph = args.get("api_rph", 0)
        app.api_rpm = args.get("api_rpm", 0)
        app.created_by = account.id
        app.updated_by = account.id
        app.permission = AppPermissionEnum.ONLY_ME

        db.session.add(app)
        db.session.flush()

        if default_model_config:
            app_model_config = AppModelConfig(**default_model_config)
            app_model_config.app_id = app.id
            app_model_config.created_by = account.id
            app_model_config.updated_by = account.id
            db.session.add(app_model_config)
            db.session.flush()

            app.app_model_config_id = app_model_config.id

        db.session.commit()

        app_was_created.send(app, account=account)

        if FeatureService.get_system_features().webapp_auth.enabled:
            # update web app setting as private
            EnterpriseService.WebAppAuth.update_app_access_mode(app.id, "private")

        return app

    def get_app(self, app: App) -> App:
        """
        Get App
        """
        # get original app model config
        if app.mode == AppMode.AGENT_CHAT.value or app.is_agent:
            model_config = app.app_model_config
            agent_mode = model_config.agent_mode_dict
            # decrypt agent tool parameters if it's secret-input
            for tool in agent_mode.get("tools") or []:
                if not isinstance(tool, dict) or len(tool.keys()) <= 3:
                    continue
                agent_tool_entity = AgentToolEntity(**tool)
                # get tool
                try:
                    tool_runtime = ToolManager.get_agent_tool_runtime(
                        tenant_id=current_user.current_tenant_id,
                        app_id=app.id,
                        agent_tool=agent_tool_entity,
                    )
                    manager = ToolParameterConfigurationManager(
                        tenant_id=current_user.current_tenant_id,
                        tool_runtime=tool_runtime,
                        provider_name=agent_tool_entity.provider_id,
                        provider_type=agent_tool_entity.provider_type,
                        identity_id=f"AGENT.{app.id}",
                    )

                    # get decrypted parameters
                    if agent_tool_entity.tool_parameters:
                        parameters = manager.decrypt_tool_parameters(agent_tool_entity.tool_parameters or {})
                        masked_parameter = manager.mask_tool_parameters(parameters or {})
                    else:
                        masked_parameter = {}

                    # override tool parameters
                    tool["tool_parameters"] = masked_parameter
                except Exception as e:
                    pass

            # override agent mode
            model_config.agent_mode = json.dumps(agent_mode)

            class ModifiedApp(App):
                """
                Modified App class
                """

                def __init__(self, app):
                    self.__dict__.update(app.__dict__)

                @property
                def app_model_config(self):
                    return model_config

            app = ModifiedApp(app)

        return app

    def update_app(self, app: App, args: dict) -> App:
        """
        Update app
        :param app: App instance
        :param args: request args
        :return: App instance
        """
        app.name = args.get("name")
        app.description = args.get("description", "")
        app.icon_type = args.get("icon_type", "emoji")
        app.icon = args.get("icon")
        app.icon_background = args.get("icon_background")
        app.use_icon_as_answer_icon = args.get("use_icon_as_answer_icon", False)
        app.updated_by = current_user.id
        app.updated_at = datetime.now(UTC).replace(tzinfo=None)
        permission = args.get("permission")
        if permission:
            app.permission = permission
        db.session.commit()

        return app

    def update_app_name(self, app: App, name: str) -> App:
        """
        Update app name
        :param app: App instance
        :param name: new name
        :return: App instance
        """
        app.name = name
        app.updated_by = current_user.id
        app.updated_at = datetime.now(UTC).replace(tzinfo=None)
        db.session.commit()

        return app

    def update_app_icon(self, app: App, icon: str, icon_background: str) -> App:
        """
        Update app icon
        :param app: App instance
        :param icon: new icon
        :param icon_background: new icon_background
        :return: App instance
        """
        app.icon = icon
        app.icon_background = icon_background
        app.updated_by = current_user.id
        app.updated_at = datetime.now(UTC).replace(tzinfo=None)
        db.session.commit()

        return app

    def update_app_site_status(self, app: App, enable_site: bool) -> App:
        """
        Update app site status
        :param app: App instance
        :param enable_site: enable site status
        :return: App instance
        """
        if enable_site == app.enable_site:
            return app

        app.enable_site = enable_site
        app.updated_by = current_user.id
        app.updated_at = datetime.now(UTC).replace(tzinfo=None)
        db.session.commit()

        return app

    def update_app_api_status(self, app: App, enable_api: bool) -> App:
        """
        Update app api status
        :param app: App instance
        :param enable_api: enable api status
        :return: App instance
        """
        if enable_api == app.enable_api:
            return app

        app.enable_api = enable_api
        app.updated_by = current_user.id
        app.updated_at = datetime.now(UTC).replace(tzinfo=None)
        db.session.commit()

        return app

    def delete_app(self, app: App) -> None:
        """
        Delete app
        :param app: App instance
        """
        db.session.delete(app)
        db.session.commit()

        # clean up web app settings
        if FeatureService.get_system_features().webapp_auth.enabled:
            EnterpriseService.WebAppAuth.cleanup_webapp(app.id)

        # Trigger asynchronous deletion of app and related data
        remove_app_and_related_data_task.delay(tenant_id=app.tenant_id, app_id=app.id)

    def get_app_meta(self, app_model: App) -> dict:
        """
        Get app meta info
        :param app_model: app model
        :return:
        """
        app_mode = AppMode.value_of(app_model.mode)

        meta: dict = {"tool_icons": {}}

        if app_mode in {AppMode.ADVANCED_CHAT, AppMode.WORKFLOW}:
            workflow = app_model.workflow
            if workflow is None:
                return meta

            graph = workflow.graph_dict
            nodes = graph.get("nodes", [])
            tools = []
            for node in nodes:
                if node.get("data", {}).get("type") == "tool":
                    node_data = node.get("data", {})
                    tools.append(
                        {
                            "provider_type": node_data.get("provider_type"),
                            "provider_id": node_data.get("provider_id"),
                            "tool_name": node_data.get("tool_name"),
                            "tool_parameters": {},
                        }
                    )
        else:
            app_model_config: Optional[AppModelConfig] = app_model.app_model_config

            if not app_model_config:
                return meta

            agent_config = app_model_config.agent_mode_dict

            # get all tools
            tools = agent_config.get("tools", [])

        url_prefix = dify_config.CONSOLE_API_URL + "/console/api/workspaces/current/tool-provider/builtin/"

        for tool in tools:
            keys = list(tool.keys())
            if len(keys) >= 4:
                # current tool standard
                provider_type = tool.get("provider_type", "")
                provider_id = tool.get("provider_id", "")
                tool_name = tool.get("tool_name", "")
                if provider_type == "builtin":
                    meta["tool_icons"][tool_name] = url_prefix + provider_id + "/icon"
                elif provider_type == "api":
                    try:
                        provider: Optional[ApiToolProvider] = (
                            db.session.query(ApiToolProvider).filter(ApiToolProvider.id == provider_id).first()
                        )
                        if provider is None:
                            raise ValueError(f"provider not found for tool {tool_name}")
                        meta["tool_icons"][tool_name] = json.loads(provider.icon)
                    except:
                        meta["tool_icons"][tool_name] = {"background": "#252525", "content": "\ud83d\ude01"}

        return meta

    @staticmethod
    def get_app_code_by_id(app_id: str) -> str:
        """
        Get app code by app id
        :param app_id: app id
        :return: app code
        """
        site = db.session.query(Site).filter(Site.app_id == app_id).first()
        if not site:
            raise ValueError(f"App with id {app_id} not found")
        return str(site.code)

    @staticmethod
    def get_app_by_id(app_id) -> Optional[App]:
        dataset: Optional[App] = db.session.query(App).filter_by(id=app_id).first()
        return dataset

    @staticmethod
    def check_app_permission(app, user):
        if app.tenant_id != user.current_tenant_id:
            logging.debug(f"User {user.id} does not have permission to access app {app.id}")
            raise NoPermissionError("You do not have permission to access this app.")
        if user.current_role != TenantAccountRole.OWNER:
            if app.permission == AppPermissionEnum.ONLY_ME and app.created_by != user.id:
                logging.debug(f"User {user.id} does not have permission to access app {app.id}")
                raise NoPermissionError("You do not have permission to access this app.")
            if app.permission == AppPermissionEnum.PARTIAL_TEAM:
                # For partial team permission, user needs explicit permission or be the creator
                if app.created_by != user.id:
                    user_permission = (
                        db.session.query(AppPermission).filter_by(app_id=app.id, account_id=user.id).first()
                    )
                    if not user_permission:
                        logging.debug(f"User {user.id} does not have permission to access app {app.id}")
                        raise NoPermissionError("You do not have permission to access this app.")

    @staticmethod
    def check_app_operator_permission(user: Optional[Account] = None, app: Optional[App] = None):
        if not app:
            raise ValueError("App not found")

        if not user:
            raise ValueError("User not found")

        if user.current_role != TenantAccountRole.OWNER:
            if app.permission == AppPermissionEnum.ONLY_ME:
                if app.created_by != user.id:
                    raise NoPermissionError("You do not have permission to access this app.")

            elif app.permission == AppPermissionEnum.PARTIAL_TEAM:
                if not any(
                    dp.app_id == app.id
                    for dp in db.session.query(AppPermission).filter_by(account_id=user.id).all()
                ):
                    raise NoPermissionError("You do not have permission to access this app.")


class AppPermissionService:
    @classmethod
    def get_app_partial_member_list(cls, app_id):
        user_list_query = (
            db.session.query(
                AppPermission.account_id,
            )
            .filter(AppPermission.app_id == app_id)
            .all()
        )

        user_list = []
        for user in user_list_query:
            user_list.append(user.account_id)

        return user_list

    @classmethod
    def update_partial_member_list(cls, tenant_id, app_id, user_list):
        try:
            db.session.query(AppPermission).filter(AppPermission.app_id == app_id).delete()
            permissions = []
            for user in user_list:
                permission = AppPermission(
                    tenant_id=tenant_id,
                    app_id=app_id,
                    account_id=user["user_id"],
                )
                permissions.append(permission)

            db.session.add_all(permissions)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

    @classmethod
    def check_permission(cls, user, app, requested_permission, requested_partial_member_list):
        if not user.is_dataset_editor:
            raise NoPermissionError("User does not have permission to edit this app.")

        if user.is_dataset_operator and app.permission != requested_permission:
            raise NoPermissionError("App operators cannot change the app permissions.")

        if user.is_dataset_operator and requested_permission == "partial_members":
            if not requested_partial_member_list:
                raise ValueError("Partial member list is required when setting to partial members.")

            local_member_list = cls.get_app_partial_member_list(app.id)
            request_member_list = [user["user_id"] for user in requested_partial_member_list]
            if set(local_member_list) != set(request_member_list):
                raise ValueError("App operators cannot change the app permissions.")

    @classmethod
    def clear_partial_member_list(cls, app_id):
        try:
            db.session.query(AppPermission).filter(AppPermission.app_id == app_id).delete()
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e
