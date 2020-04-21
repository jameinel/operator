#!/usr/bin/env python3
# Copyright 2019 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import base64
import pickle
import sys
sys.path.append('lib')  # noqa

from ops.charm import CharmBase
from ops.framework import StoredState
from ops.main import main

import logging

logger = logging.getLogger()


class Charm(CharmBase):

    _stored = StoredState()

    def __init__(self, *args):
        super().__init__(*args)

        charm_config = os.environ.get('CHARM_CONFIG')
        if charm_config is not None:
            self._charm_config = pickle.loads(base64.b64decode(charm_config))
        else:
            self._charm_config = {}

        self._stored.set_default(
            on_install=[],
            on_start=[],
            on_config_changed=[],
            on_update_status=[],
            on_leader_settings_changed=[],
            on_db_relation_joined=[],
            on_mon_relation_changed=[],
            on_mon_relation_departed=[],
            on_ha_relation_broken=[],
            on_foo_bar_action=[],
            on_start_action=[],
            on_collect_metrics=[],
            on_log_critical_action=[],
            on_log_error_action=[],
            on_log_warning_action=[],
            on_log_info_action=[],
            on_log_debug_action=[],
            # Observed event types per invocation. A list is used to preserve the
            # order in which charm handlers have observed the events.
            observed_event_types=[],

            use_actions=False,
        )

        self.framework.observe(self.on.install, self)
        self.framework.observe(self.on.start, self)
        self.framework.observe(self.on.config_changed, self)
        self.framework.observe(self.on.update_status, self)
        self.framework.observe(self.on.leader_settings_changed, self)
        # Test relation events with endpoints from different
        # sections (provides, requires, peers) as well.
        self.framework.observe(self.on.db_relation_joined, self)
        self.framework.observe(self.on.mon_relation_changed, self)
        self.framework.observe(self.on.mon_relation_departed, self)
        self.framework.observe(self.on.ha_relation_broken, self)

        if self._charm_config.get('USE_ACTIONS'):
            self.framework.observe(self.on.start_action, self)
            self.framework.observe(self.on.foo_bar_action, self)

        self.framework.observe(self.on.collect_metrics, self)

        if self._charm_config.get('USE_LOG_ACTIONS'):
            self.framework.observe(self.on.log_critical_action, self)
            self.framework.observe(self.on.log_error_action, self)
            self.framework.observe(self.on.log_warning_action, self)
            self.framework.observe(self.on.log_info_action, self)
            self.framework.observe(self.on.log_debug_action, self)

    def on_install(self, event):
        self._stored.on_install.append(type(event))
        self._stored.observed_event_types.append(type(event))

    def on_start(self, event):
        self._stored.on_start.append(type(event))
        self._stored.observed_event_types.append(type(event))

    def on_config_changed(self, event):
        self._stored.on_config_changed.append(type(event))
        self._stored.observed_event_types.append(type(event))
        event.defer()

    def on_update_status(self, event):
        self._stored.on_update_status.append(type(event))
        self._stored.observed_event_types.append(type(event))

    def on_leader_settings_changed(self, event):
        self._stored.on_leader_settings_changed.append(type(event))
        self._stored.observed_event_types.append(type(event))

    def on_db_relation_joined(self, event):
        assert event.app is not None, 'application name cannot be None for a relation-joined event'
        self._stored.on_db_relation_joined.append(type(event))
        self._stored.observed_event_types.append(type(event))
        self._stored.db_relation_joined_data = event.snapshot()

    def on_mon_relation_changed(self, event):
        assert event.app is not None, (
            'application name cannot be None for a relation-changed event')
        if os.environ.get('JUJU_REMOTE_UNIT'):
            assert event.unit is not None, (
                'a unit name cannot be None for a relation-changed event'
                ' associated with a remote unit')
        self._stored.on_mon_relation_changed.append(type(event))
        self._stored.observed_event_types.append(type(event))
        self._stored.mon_relation_changed_data = event.snapshot()

    def on_mon_relation_departed(self, event):
        assert event.app is not None, (
            'application name cannot be None for a relation-departed event')
        self._stored.on_mon_relation_departed.append(type(event))
        self._stored.observed_event_types.append(type(event))
        self._stored.mon_relation_departed_data = event.snapshot()

    def on_ha_relation_broken(self, event):
        assert event.app is None, (
            'relation-broken events cannot have a reference to a remote application')
        assert event.unit is None, (
            'relation broken events cannot have a reference to a remote unit')
        self._stored.on_ha_relation_broken.append(type(event))
        self._stored.observed_event_types.append(type(event))
        self._stored.ha_relation_broken_data = event.snapshot()

    def on_start_action(self, event):
        assert event.handle.kind == 'start_action', (
            'event action name cannot be different from the one being handled')
        self._stored.on_start_action.append(type(event))
        self._stored.observed_event_types.append(type(event))

    def on_foo_bar_action(self, event):
        assert event.handle.kind == 'foo_bar_action', (
            'event action name cannot be different from the one being handled')
        self._stored.on_foo_bar_action.append(type(event))
        self._stored.observed_event_types.append(type(event))

    def on_collect_metrics(self, event):
        self._stored.on_collect_metrics.append(type(event))
        self._stored.observed_event_types.append(type(event))
        event.add_metrics({'foo': 42}, {'bar': 4.2})

    def on_log_critical_action(self, event):
        logger.critical('super critical')

    def on_log_error_action(self, event):
        logger.error('grave error')

    def on_log_warning_action(self, event):
        logger.warning('wise warning')

    def on_log_info_action(self, event):
        logger.info('useful info')

    def on_log_debug_action(self, event):
        logger.debug('insightful debug')


if __name__ == '__main__':
    main(Charm)
