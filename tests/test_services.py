"""Unit tests for portal.services."""

import pytest
import services  # imported directly from portal/ via conftest.py sys.path


class TestServiceRegistry:
    def test_keys_are_unique(self):
        keys = [service.key for service in services.SERVICES]
        assert len(keys) == len(set(keys))

    def test_each_service_has_exactly_one_link_target(self):
        for service in services.SERVICES:
            assert (service.endpoint is None) != (service.url is None), service.key

    def test_get_returns_service_by_key(self):
        assert services.get("jupyterlab").label == "JupyterLab"

    def test_get_unknown_key_raises(self):
        with pytest.raises(KeyError):
            services.get("not-a-service")


class TestParseDisabledServices:
    def test_empty_list_disables_nothing(self):
        assert services.parse_disabled_services([]) == frozenset()

    def test_known_keys_are_accepted(self):
        assert services.parse_disabled_services(["jupyterlab", "reana"]) == frozenset(
            {"jupyterlab", "reana"}
        )

    def test_all_registered_keys_are_accepted(self):
        keys = [service.key for service in services.SERVICES]
        assert services.parse_disabled_services(keys) == frozenset(keys)

    def test_unknown_key_raises(self):
        with pytest.raises(ValueError, match="jupyter"):
            services.parse_disabled_services(["jupyter"])

    @pytest.mark.parametrize("value", ["jupyterlab", None, {"jupyterlab": True}, [1]])
    def test_non_list_of_strings_raises(self, value):
        # A bare string must be rejected: `"jupyter" in "jupyterlab"` is a
        # substring match, so an un-JSON env var would silently misbehave.
        with pytest.raises(ValueError, match="list of service keys"):
            services.parse_disabled_services(value)
