# from databases import Database
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    MetaData,
    String,
    Table,
    create_engine,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, mapped_column, registry, sessionmaker
from sqlalchemy.sql import expression

from src.config import settings
from src.constants import DB_NAMING_CONVENTION

mapper = registry()
DATABASE_URL = str(settings)

engine = create_engine(DATABASE_URL)
metadata = MetaData(naming_convention=DB_NAMING_CONVENTION)

# database = Database(DATABASE_URL, force_rollback=settings.ENVIRONMENT.is_testing)

all_users = Table(
    "all_users",
    metadata,
    Column("user_id", UUID(as_uuid=True), primary_key=True),
    Column("email", String, nullable=False),
    Column("org_id", UUID(as_uuid=True), nullable=False),
    Column("simple_org_id", String, nullable=False),
    Column("role", String, nullable=False),
    Column("created_on", DateTime, server_default=func.now(), nullable=False),
)

organizations = Table(
    "organizations",
    metadata,
    Column("org_id", UUID(as_uuid=True), primary_key=True),
    Column("org_name", String, nullable=False),
    Column(
        "org_owner", UUID(as_uuid=True), ForeignKey(all_users.c.user_id), nullable=False
    ),
    Column("simple_org_id", String, nullable=False, unique=True),
)

# datasource table
datasource = Table(
    "datasource",
    metadata,
    Column(
        "id",
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    ),
    Column(
        "user_id",
        UUID(as_uuid=True),
        ForeignKey(all_users.c.user_id, ondelete="CASCADE"),
        nullable=False,
    ),
    Column("datasource_name_script", String, nullable=False),
    Column("datasource_name_generic", String, nullable=False),
    Column("datasource_description", String, nullable=True),
    Column("connection_details", JSONB, nullable=False),
    Column("datasource_type", String, nullable=False),
    Column("datasource_details", JSONB, nullable=False),
    Column("creation_date", DateTime, server_default=func.now(), nullable=False),
    Column("last_updated", DateTime, onupdate=func.now()),
    Column("hashed_value", String, nullable=True),
    Column(
        "execution_id",
        UUID(as_uuid=True),
        nullable=False,
        server_default="453b0274-4a6a-498f-a661-a83e3172b323",
    ),
)

# feature table
feature = Table(
    "feature",
    metadata,
    Column(
        "id",
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    ),
    Column(
        "user_id",
        UUID(as_uuid=True),
        ForeignKey(all_users.c.user_id, ondelete="CASCADE"),
        nullable=False,
    ),
    Column("datasource_ids", ARRAY(String), nullable=False),
    Column("feature_name_script", String, nullable=False),
    Column("feature_name_generic", String, nullable=False),
    Column("feature_description", String, nullable=False),
    Column("column_types", JSONB, nullable=False),
    Column("feature_dest", String, nullable=False),  # preloop
    Column("feature_cols", ARRAY(String), nullable=False),
    Column("feature_signature", JSONB, nullable=True),
    Column("id_cols", ARRAY(String), nullable=False),
    Column("target_cols", ARRAY(String), nullable=True),
    Column("creation_date", DateTime, server_default=func.now(), nullable=False),
    Column("last_updated", DateTime, onupdate=func.now()),
    Column("scheduling_expression_string", String, nullable=True),
    Column("creation_method", String, nullable=False),
    Column("script_loc", String, nullable=False),
    Column("versioning", Boolean, nullable=False),
    Column("latest_version", Integer, nullable=False),
    Column("location_string", String, nullable=True),
    Column("feature_drift_enabled", Boolean, nullable=False),
    Column(
        "execution_id",
        UUID(as_uuid=True),
        nullable=False,
        server_default="453b0274-4a6a-498f-a661-a83e3172b323",
    ),
)

feature_versions = Table(
    "feature_versions",
    metadata,
    Column(
        "id",
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    ),
    Column(
        "feature_id",
        UUID(as_uuid=True),
        ForeignKey(feature.c.id, ondelete="CASCADE"),
        nullable=False,
    ),
    Column("version", Integer, nullable=False),
    Column(
        "description",
        String,
        nullable=True,
        default="Enter a description for this version of your feature.",
    ),
)

feature_drift = Table(
    "feature_drift",
    metadata,
    Column(
        "id",
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    ),
    Column(
        "feature_id",
        UUID(as_uuid=True),
        ForeignKey(feature.c.id, ondelete="CASCADE"),
        nullable=False,
    ),
    Column("version", Integer, nullable=False),
    Column("drifts", JSONB, nullable=False),
    Column("record_date", DateTime, server_default=func.now(), nullable=False),
)

ml_model = Table(
    "ml_model",
    metadata,
    Column(
        "id",
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    ),
    Column(
        "user_id",
        UUID(as_uuid=True),
        ForeignKey(all_users.c.user_id, ondelete="CASCADE"),
        nullable=False,
    ),
    Column("ml_model_name", String, nullable=False),
    Column("ml_model_description", String, nullable=False),
    Column("ml_model_inputs", JSONB, nullable=True),
    Column("ml_prediction_type", String, nullable=True),
    Column("ml_model_details", JSONB, nullable=True),
    Column("ml_model_data_flow", JSONB, nullable=True),
    Column("versioning", Boolean, nullable=False, server_default=expression.true()),
    Column("latest_version", Integer, nullable=True),
    Column("creation_date", DateTime, server_default=func.now(), nullable=False),
    Column("last_updated", DateTime, onupdate=func.now()),
    Column("ml_object_dir", String, nullable=True),
    Column("script_dir", String, nullable=True),
    Column("status", String, nullable=False),
    Column("reason", String, nullable=True),
    Column("endpoint_url", String, nullable=True),
    Column(
        "require_api_key", Boolean, nullable=False, server_default=expression.true()
    ),
    Column("libraries", ARRAY(String), nullable=False, server_default=text("'{}'")),
    Column("schedule", String, nullable=True),
    Column("ml_model_metric_limits", JSONB, nullable=True),
    Column("latest_deployed_version", Integer, nullable=True),
    Column("predict_function_name", String, nullable=True),
    Column("env_vars", String, nullable=True),
)

ml_model_training_jobs = Table(
    "ml_model_training_jobs",
    metadata,
    Column(
        "id",
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    ),
    Column(
        "user_id",
        UUID(as_uuid=True),
        ForeignKey(all_users.c.user_id, ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "ml_model_id",
        UUID(as_uuid=True),
        ForeignKey(ml_model.c.id, ondelete="CASCADE"),
        nullable=False,
    ),
    Column("start_time", DateTime, server_default=func.now(), nullable=False),
    Column("end_time", DateTime, nullable=True),
    Column("status", String, nullable=False),
    Column("reason", String, nullable=True),
    Column("ecs_cluster_arn", String, nullable=True),
    Column("ecs_task_arn", String, nullable=True),
    Column("cloudwatch_log_group_name", String, nullable=True),
    Column("cloudwatch_log_stream_name", String, nullable=True),
)

ml_model_versions = Table(
    "ml_model_versions",
    metadata,
    Column(
        "id",
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    ),
    Column(
        "user_id",
        UUID(as_uuid=True),
        ForeignKey(all_users.c.user_id, ondelete="CASCADE"),
        nullable=False,
        server_default=text("gen_random_uuid()"),
    ),
    Column(
        "ml_model_id",
        UUID(as_uuid=True),
        ForeignKey(ml_model.c.id, ondelete="CASCADE"),
        nullable=False,
    ),
    Column("version", Integer, nullable=False),
    Column("hyper_params", JSONB, nullable=True),
    Column("ml_model_metrics", JSONB, nullable=True),
    Column("creation_date", DateTime, server_default=func.now(), nullable=False),
    Column("metric_limit_breaches", JSONB, nullable=True),
)

org_load_balancers = Table(
    "org_load_balancers",
    metadata,
    Column(
        "id",
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    ),
    Column(
        "org_id",
        UUID(as_uuid=True),
        ForeignKey(organizations.c.org_id, ondelete="CASCADE"),
        nullable=False,
    ),
    Column("load_balancer_arn", String, nullable=False),
    Column("listener_arn", String, nullable=True),
    Column("url", String, nullable=True),
    Column("creation_date", DateTime, server_default=func.now(), nullable=False),
    Column("num_target_groups", Integer, nullable=False),
    Column("route_53_record", JSONB, nullable=True),
    Column("status", String, nullable=False),
    Column("security_group_id", String, nullable=False),
)

hosted_ml_models = Table(
    "hosted_ml_models",
    metadata,
    Column(
        "id",
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    ),
    Column(
        "user_id",
        UUID(as_uuid=True),
        ForeignKey(all_users.c.user_id, ondelete="CASCADE"),
        nullable=False,
        server_default=text("gen_random_uuid()"),
    ),
    Column(
        "ml_model_id",
        UUID(as_uuid=True),
        ForeignKey(ml_model.c.id, ondelete="CASCADE"),
        nullable=False,
    ),
    Column("version", Integer, nullable=False),
    Column(
        "load_balancer_id",
        UUID(as_uuid=True),
        nullable=True,
    ),
    Column("target_group_arn", String, nullable=True),
    Column("listener_rule_arn", String, nullable=True),
    Column("ecs_cluster_name", String, nullable=True),
    Column("ecs_service_name", String, nullable=True),
    Column("creation_date", DateTime, server_default=func.now(), nullable=False),
    Column("task_security_group_id", String, nullable=True),
    Column("task_definition_arn", String, nullable=True),
    Column("status", String, nullable=False),
    Column("reason", String, nullable=True),
    Column("endpoint_url", String, nullable=True),
    Column(
        "require_api_key", Boolean, nullable=False, server_default=expression.true()
    ),
)

executions = Table(
    "executions",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column(
        "user_id",
        UUID(as_uuid=True),
        ForeignKey(all_users.c.user_id, ondelete="CASCADE"),
        nullable=False,
    ),
    Column("record_date", DateTime, server_default=func.now(), nullable=False),
    Column("status", String, nullable=False),
    Column("reason", String, nullable=True),
    Column("execution_type", String, nullable=False),
)

api_keys = Table(
    "api_keys",
    metadata,
    Column(
        "user_id",
        UUID(as_uuid=True),
        ForeignKey(all_users.c.user_id, ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "org_id",
        UUID(as_uuid=True),
        ForeignKey(organizations.c.org_id, ondelete="CASCADE"),
        nullable=False,
    ),
    Column("role", String, nullable=False),
    Column("key_id", String, nullable=False, primary_key=True),
    Column("hashed_secret", String, nullable=False),
    Column("creation_date", DateTime, server_default=func.now(), nullable=False),
    Column("visibility", String, default="external", nullable=False),
    Column("encrypted_secret", LargeBinary, nullable=True),
)

# team tables
team = Table(
    "team",
    metadata,
    Column(
        "id",
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    ),
    Column(
        "org_id",
        UUID(as_uuid=True),
        ForeignKey(organizations.c.org_id, ondelete="CASCADE"),
        nullable=False,
    ),
    Column("team_name", String, nullable=False),
    Column("team_description", String, nullable=False),
    Column(
        "team_owner",
        UUID(as_uuid=True),
        ForeignKey(all_users.c.user_id),
        nullable=False,
    ),
    Column("creation_date", DateTime, server_default=func.now(), nullable=False),
    Column("last_updated", DateTime, onupdate=func.now()),
)

team_member = Table(
    "team_member",
    metadata,
    Column(
        "id",
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    ),
    Column("team_id", UUID(as_uuid=True), ForeignKey(team.c.id), nullable=False),
    Column(
        "user_id",
        UUID(as_uuid=True),
        ForeignKey(all_users.c.user_id, ondelete="CASCADE"),
        nullable=False,
    ),
    Column("team_role", String, nullable=False),
    Column("member_from", DateTime, server_default=func.now(), nullable=False),
    Column("is_accepted", Boolean, nullable=False),
)


class AllUsers:
    pass


class Organizations:
    pass


class Datasource:
    pass


class Feature:
    pass


class FeatureVersions:
    pass


class FeatureDrift:
    pass


class MLModel:
    pass


class MLModelTrainingJobs:
    pass


class MLModelVersions:
    pass


class OrgLoadBalancers:
    pass


class HostedMLModels:
    pass


class Executions:
    pass


class ApiKeys:
    pass


class Team:
    pass


class TeamMember:
    pass


mapper.map_imperatively(AllUsers, all_users)
mapper.map_imperatively(Organizations, organizations)
mapper.map_imperatively(Datasource, datasource)
mapper.map_imperatively(Feature, feature)
mapper.map_imperatively(FeatureVersions, feature_versions)
mapper.map_imperatively(FeatureDrift, feature_drift)
mapper.map_imperatively(MLModel, ml_model)
mapper.map_imperatively(MLModelTrainingJobs, ml_model_training_jobs)
mapper.map_imperatively(MLModelVersions, ml_model_versions)
mapper.map_imperatively(OrgLoadBalancers, org_load_balancers)
mapper.map_imperatively(HostedMLModels, hosted_ml_models)
mapper.map_imperatively(Executions, executions)
mapper.map_imperatively(ApiKeys, api_keys)
mapper.map_imperatively(Team, team)
mapper.map_imperatively(TeamMember, team_member)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine, expire_on_commit=False)
