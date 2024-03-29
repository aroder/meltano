import pytest
import os
import shutil
import yaml
import logging
import datetime
from pathlib import Path

import meltano.core.bundle
from meltano.core.project import Project
from meltano.core.behavior.canonical import Canonical
from meltano.core.project_init_service import ProjectInitService
from meltano.core.project_add_service import ProjectAddService
from meltano.core.plugin_install_service import PluginInstallService
from meltano.core.plugin_discovery_service import PluginDiscoveryService
from meltano.core.plugin.settings_service import PluginSettingsService
from meltano.core.plugin_invoker import invoker_factory
from meltano.core.config_service import ConfigService
from meltano.core.schedule_service import ScheduleService
from meltano.core.compiler.project_compiler import ProjectCompiler
from meltano.core.plugin import PluginRef, PluginType, PluginInstall
from meltano.core.plugin.factory import plugin_factory
from meltano.core.elt_context import ELTContextBuilder
from meltano.core.logging.job_logging_service import JobLoggingService


PROJECT_NAME = "a_meltano_project"


@pytest.fixture(scope="class")
def discovery():
    with meltano.core.bundle.find("discovery.yml").open() as base:
        discovery = yaml.safe_load(base)

    discovery[PluginType.EXTRACTORS].append(
        {
            "name": "tap-mock",
            "namespace": "tap_mock",
            "pip_url": "tap-mock",
            "capabilities": ["discover", "catalog", "state"],
            "settings": [
                {"name": "test", "value": "mock"},
                {"name": "start_date"},
                {"name": "protected", "protected": True},
                {"name": "secure", "kind": "password"},
                {"name": "hidden", "kind": "hidden", "value": 42},
                {"name": "boolean", "kind": "boolean", "value": False},
            ],
        }
    )

    discovery[PluginType.LOADERS].append(
        {"name": "target-mock", "namespace": "target_mock", "pip_url": "target-mock"}
    )

    discovery[PluginType.TRANSFORMS].append(
        {
            "name": "tap-mock-transform",
            "namespace": "tap_mock",
            "pip_url": "tap-mock-transform",
        }
    )

    discovery[PluginType.MODELS].append(
        {
            "name": "model-gitlab",
            "namespace": "tap_gitlab",
            "pip_url": "git+https://gitlab.com/meltano/model-gitlab.git",
        }
    )

    discovery[PluginType.DASHBOARDS].append(
        {
            "name": "dashboard-google-analytics",
            "namespace": "tap_google_analytics",
            "pip_url": "git+https://gitlab.com/meltano/dashboard-google-analytics.git",
        }
    )

    discovery[PluginType.ORCHESTRATORS].append(
        {
            "name": "orchestrator-mock",
            "namespace": "pytest",
            "pip_url": "orchestrator-mock",
        }
    )

    discovery[PluginType.TRANSFORMERS].append(
        {
            "name": "transformer-mock",
            "namespace": "transformer_mock",
            "pip_url": "transformer-mock",
        }
    )

    return discovery


@pytest.fixture(scope="class")
def plugin_discovery_service(project, discovery, config_service):
    return PluginDiscoveryService(
        project, discovery=discovery, config_service=config_service
    )


@pytest.fixture(scope="class")
def project_compiler(project):
    return ProjectCompiler(project)


@pytest.fixture(scope="class")
def project_init_service():
    return ProjectInitService(PROJECT_NAME)


@pytest.fixture(scope="class")
def plugin_install_service(project, config_service):
    return PluginInstallService(project, config_service=config_service)


@pytest.fixture(scope="class")
def project_add_service(project, config_service, plugin_discovery_service):
    return ProjectAddService(
        project,
        config_service=config_service,
        plugin_discovery_service=plugin_discovery_service,
    )


@pytest.fixture(scope="class")
def plugin_settings_service(project, config_service, plugin_discovery_service):
    return PluginSettingsService(
        project,
        config_service=config_service,
        plugin_discovery_service=plugin_discovery_service,
    )


@pytest.fixture(scope="class")
def plugin_invoker_factory(project, plugin_settings_service, plugin_discovery_service):
    def _factory(plugin, **kwargs):
        return invoker_factory(
            project,
            plugin,
            plugin_settings_service=plugin_settings_service,
            plugin_discovery_service=plugin_discovery_service,
            **kwargs,
        )

    return _factory


@pytest.fixture(scope="class")
def add_model(project, plugin_install_service, project_add_service):
    MODELS = [
        "model-carbon-intensity",
        "model-gitflix",
        "model-salesforce",
        "model-gitlab",
    ]

    for model in MODELS:
        plugin = project_add_service.add(PluginType.MODELS, model)
        plugin_install_service.install_plugin(plugin)

    yield

    # clean-up
    with project.meltano_update() as meltano:
        meltano["plugins"]["models"] = [
            model_def
            for model_def in meltano["plugins"]["models"]
            if model_def["name"] not in MODELS
        ]

    for model in MODELS:
        shutil.rmtree(project.model_dir(model))


@pytest.fixture(scope="class")
def config_service(project):
    return ConfigService(project)


@pytest.fixture(scope="class")
def tap(config_service):
    tap = PluginInstall(PluginType.EXTRACTORS, "tap-mock", "tap-mock")
    return config_service.add_to_file(tap)


@pytest.fixture(scope="class")
def target(config_service):
    target = PluginInstall(PluginType.LOADERS, "target-mock", "target-mock")
    return config_service.add_to_file(target)


@pytest.fixture(scope="class")
def dbt(config_service):
    dbt = PluginInstall(PluginType.TRANSFORMERS, "dbt", "dbt")
    return config_service.add_to_file(dbt)


@pytest.fixture(scope="class")
def schedule_service(project, plugin_settings_service):
    return ScheduleService(project, plugin_settings_service=plugin_settings_service)


@pytest.fixture(scope="class")
def schedule(project, tap, target, schedule_service):
    return schedule_service.add(
        None,
        "schedule-mock",
        extractor=tap.name,
        loader=target.name,
        transform="skip",
        interval="@once",
        start_date=datetime.datetime.now(),
    )


@pytest.fixture(scope="class")
def elt_context_builder(
    project, config_service, plugin_settings_service, plugin_discovery_service
):
    return ELTContextBuilder(
        project,
        config_service=config_service,
        plugin_settings_service=plugin_settings_service,
        plugin_discovery_service=plugin_discovery_service,
    )


@pytest.fixture(scope="class")
def job_logging_service(project):
    return JobLoggingService(project)


@pytest.fixture(scope="class")
def project(test_dir, project_init_service):
    project = project_init_service.init(create_system_database=False)
    logging.debug(f"Created new project at {project.root}")

    # empty out the `plugins`
    with project.meltano_update() as meltano:
        meltano.plugins = Canonical()

    # cd into the new project root
    os.chdir(project.root)

    yield project

    # clean-up
    Project._default = None
    os.chdir(test_dir)
    shutil.rmtree(project.root)
    logging.debug(f"Cleaned project at {project.root}")
