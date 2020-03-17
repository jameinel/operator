#!/usr/bin/python3
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

import unittest

from ops.charm import (
    CharmBase,
)
from ops.framework import (
    Object,
)
from ops.model import (
    ModelError,
    RelationNotFoundError,
)
from ops.testing import Harness


class TestTestingHarness(unittest.TestCase):

    def test_add_relation(self):
        # language=YAML
        harness = Harness('''
            name: test-app
            requires:
                db:
                    interface: pgsql
            ''')
        rel_id = harness.add_relation('db', 'postgresql')
        self.assertIsInstance(rel_id, int)
        backend = harness._backend
        self.assertEqual([rel_id], backend.relation_ids('db'))
        self.assertEqual([], backend.relation_list(rel_id))

    def test_add_relation_and_unit(self):
        # language=YAML
        harness = Harness('''
            name: test-app
            requires:
                db:
                    interface: pgsql
            ''')
        remote_unit = 'postgresql/0'
        rel_id = harness.add_relation('db', 'postgresql', remote_app_data={'app': 'data'})
        self.assertIsInstance(rel_id, int)
        harness.add_relation_unit(rel_id, remote_unit, remote_unit_data={'foo': 'bar'})
        backend = harness._backend
        self.assertEqual([rel_id], backend.relation_ids('db'))
        self.assertEqual([remote_unit], backend.relation_list(rel_id))
        self.assertEqual({'foo': 'bar'}, backend.relation_get(rel_id, remote_unit, is_app=False))
        self.assertEqual({'app': 'data'}, backend.relation_get(rel_id, remote_unit, is_app=True))

    def test_read_relation_data(self):
        # language=YAML
        harness = Harness('''
            name: test-app
            requires:
                db:
                    interface: pgsql
            ''')
        rel_id = harness.add_relation('db', 'postgresql',
                                      remote_app_data={'remote': 'data'})
        self.assertEqual(harness.read_relation_data(rel_id, 'test-app'), {})
        self.assertEqual(harness.read_relation_data(rel_id, 'test-app/0'), {})
        self.assertEqual(harness.read_relation_data(rel_id, 'test-app/1'), None)
        self.assertEqual(harness.read_relation_data(rel_id, 'postgresql'), {'remote': 'data'})
        with self.assertRaises(KeyError):
            # unknown relation id
            harness.read_relation_data(99, 'postgresql')

    def test_create_harness(self):
        # language=YAML
        harness = Harness('''
            name: my-charm
            requires:
              db:
                interface: pgsql
            ''')
        charm = harness.initialize(CharmBase)
        helper = DBRelationChangedHelper(charm, "helper")
        rel_id = harness.add_relation('db', 'postgresql')
        relation = charm.model.get_relation('db', rel_id)
        app = charm.model.get_app('postgresql')
        charm.on.db_relation_changed.emit(relation, app)
        self.assertEqual(helper.changes, [(rel_id, 'postgresql')])

    def test_create_harness_twice(self):
        # language=YAML
        harness1 = Harness('''
            name: my-charm
            requires:
              db:
                interface: pgsql
            ''')
        # language=YAML
        harness2 = Harness('''
            name: my-charm
            requires:
              db:
                interface: pgsql
            ''')
        charm1 = harness1.initialize(CharmBase)
        charm2 = harness2.initialize(CharmBase)
        helper1 = DBRelationChangedHelper(charm1, "helper1")
        helper2 = DBRelationChangedHelper(charm2, "helper2")
        rel_id = harness2.add_relation('db', 'postgresql')
        harness1.enable_events(charm1)
        harness2.enable_events(charm2)
        harness2.update_relation_data(rel_id, 'postgresql', {'key': 'value'})
        # Helper2 should see the event triggered by harness2, but helper1 should see no events.
        self.assertEqual(helper1.changes, [])
        self.assertEqual(helper2.changes, [(rel_id, 'postgresql')])

    def test_update_relation_exposes_new_data(self):
        # language=YAML
        harness = Harness('''
            name: my-charm
            requires:
              db:
                interface: pgsql
            ''')
        charm = harness.initialize(CharmBase)
        harness.enable_events(charm)
        viewer = RelationChangedViewer(charm, 'db')
        rel_id = harness.add_relation('db', 'postgresql')
        harness.add_relation_unit(rel_id, 'postgresql/0', remote_unit_data={'initial': 'data'})
        self.assertEqual(viewer.changes, [{'initial': 'data'}])
        harness.update_relation_data(rel_id, 'postgresql/0', {'new': 'value'})
        self.assertEqual(viewer.changes, [{'initial': 'data'},
                                          {'initial': 'data', 'new': 'value'}])

    def test_update_relation_remove_data(self):
        # language=YAML
        harness = Harness('''
            name: my-charm
            requires:
              db:
                interface: pgsql
            ''')
        charm = harness.initialize(CharmBase)
        harness.enable_events(charm)
        viewer = RelationChangedViewer(charm, 'db')
        rel_id = harness.add_relation('db', 'postgresql')
        harness.add_relation_unit(rel_id, 'postgresql/0', remote_unit_data={'initial': 'data'})
        harness.update_relation_data(rel_id, 'postgresql/0', {'initial': ''})
        self.assertEqual(viewer.changes, [{'initial': 'data'}, {}])

    def test_update_config(self):
        # language=YAML
        harness = Harness('''
            name: my-charm
            ''')
        charm = harness.initialize(RecordingCharm)
        harness.enable_events(charm)
        harness.update_config(key_values={'a': 'foo', 'b': 2})
        self.assertEqual(charm.changes, [{'name': 'config', 'data': {'a': 'foo', 'b': 2}}])
        harness.update_config(key_values={'b': 3})
        self.assertEqual(charm.changes, [{'name': 'config', 'data': {'a': 'foo', 'b': 2}},
                                         {'name': 'config', 'data': {'a': 'foo', 'b': 3}}])
        # you can set config values to the empty string, you can use unset to actually remove items
        harness.update_config(key_values={'a': ''}, unset=set('b'))
        self.assertEqual(charm.changes, [{'name': 'config', 'data': {'a': 'foo', 'b': 2}},
                                         {'name': 'config', 'data': {'a': 'foo', 'b': 3}},
                                         {'name': 'config', 'data': {'a': ''}},
                                         ])

    def test_set_leader(self):
        # language=YAML
        harness = Harness('''
            name: my-charm
            ''')
        # No event happens here
        harness.set_leader(False)
        charm = harness.initialize(RecordingCharm)
        harness.enable_events(charm)
        self.assertFalse(charm.model.unit.is_leader())
        harness.set_leader(True)
        self.assertEqual(charm.changes, [{'name': 'leader-elected'}])
        self.assertTrue(charm.model.unit.is_leader())

    def test_relation_set_app_not_leader(self):
        # language=YAML
        harness = Harness('''
            name: test-charm
            requires:
                db:
                    interface: pgsql
            ''')
        harness.set_leader(False)
        rel_id = harness.add_relation('db', 'postgresql')
        harness.add_relation_unit(rel_id, 'postgresql/0')
        charm = harness.initialize(RecordingCharm)
        harness.enable_events(charm)
        rel = charm.model.get_relation('db')
        with self.assertRaises(ModelError):
            rel.data[charm.model.app]['foo'] = 'bar'
        # The data has not actually been changed
        self.assertEqual(harness.read_relation_data(rel_id, 'test-charm'), {})
        harness.set_leader(True)
        rel.data[charm.model.app]['foo'] = 'bar'
        self.assertEqual(harness.read_relation_data(rel_id, 'test-charm'), {'foo': 'bar'})

    def test_relation_set_deletes(self):
        # language=YAML
        harness = Harness('''
            name: test-charm
            requires:
                db:
                    interface: pgsql
            ''')
        charm = harness.initialize(CharmBase)
        harness.set_leader(False)
        rel_id = harness.add_relation('db', 'postgresql', initial_unit_data={'foo': 'bar'})
        harness.add_relation_unit(rel_id, 'postgresql/0')
        rel = charm.model.get_relation('db', rel_id)
        del rel.data[charm.model.unit]['foo']
        self.assertEqual({}, harness.read_relation_data(rel_id, 'test-charm/0'))

    def test_get_backend_calls(self):
        # language=YAML
        harness = Harness('''
            name: test-charm
            requires:
                db:
                    interface: pgsql
            ''')
        harness.enable_events(harness.initialize(CharmBase))
        # No calls to the backend yet
        self.assertEqual([], harness.get_backend_calls())
        rel_id = harness.add_relation('db', 'postgresql', initial_unit_data={'foo': 'bar'})
        self.assertEqual([], harness.get_backend_calls())
        # add_relation_unit resets the relation_list, and causes the Model to read
        # it to fire `relation_changed`
        harness.add_relation_unit(rel_id, 'postgresql/0')
        self.assertEqual([
            ('relation_ids', 'db'),
            ('relation_list', rel_id),
        ], harness.get_backend_calls())
        # If we check again, they are still there, but now we reset it
        self.assertEqual([
            ('relation_ids', 'db'),
            ('relation_list', rel_id),
        ], harness.get_backend_calls(reset=True))
        # And the calls are gone
        self.assertEqual([], harness.get_backend_calls())


class Test_TestingModelBackend(unittest.TestCase):

    def test_relation_ids_unknown_relation(self):
        harness = Harness('''
            name: test-charm
            provides:
              db:
                interface: mydb
            ''')
        backend = harness._backend
        # With no relations added, we just get an empty list for the interface
        self.assertEqual(backend.relation_ids('db'), [])
        # But an unknown interface raises a ModelError
        with self.assertRaises(ModelError):
            backend.relation_ids('unknown')

    def test_relation_get_unknown_relation_id(self):
        # language=YAML
        harness = Harness('''
            name: test-charm
            ''')
        backend = harness._backend
        with self.assertRaises(RelationNotFoundError):
            backend.relation_get(1234, 'unit/0', False)

    def test_relation_list_unknown_relation_id(self):
        # language=YAML
        harness = Harness('''
            name: test-charm
            ''')
        backend = harness._backend
        with self.assertRaises(RelationNotFoundError):
            backend.relation_list(1234)


class DBRelationChangedHelper(Object):
    def __init__(self, parent, key):
        super().__init__(parent, key)
        self.changes = []
        parent.framework.observe(parent.on.db_relation_changed, self.on_relation_changed)

    def on_relation_changed(self, event):
        if event.unit is not None:
            self.changes.append((event.relation.id, event.unit.name))
        else:
            self.changes.append((event.relation.id, event.app.name))


class RelationChangedViewer(Object):
    """Track relation_changed events and saves the data seen in the relation bucket."""

    def __init__(self, charm, relation_name):
        super().__init__(charm, relation_name)
        self.changes = []
        charm.framework.observe(charm.on[relation_name].relation_changed, self.on_relation_changed)

    def on_relation_changed(self, event):
        if event.unit is not None:
            data = event.relation.data[event.unit]
        else:
            data = event.relation.data[event.app]
        self.changes.append(dict(data))


class RecordingCharm(CharmBase):
    """Record the events that we see, and any associated data."""

    def __init__(self, framework, charm_name):
        super().__init__(framework, charm_name)
        self.changes = []
        self.framework.observe(self.on.config_changed, self.on_config_changed)
        self.framework.observe(self.on.leader_elected, self.on_leader_elected)

    def on_config_changed(self, _):
        self.changes.append(dict(name='config', data=dict(self.framework.model.config)))

    def on_leader_elected(self, _):
        self.changes.append(dict(name='leader-elected'))


if __name__ == "__main__":
    unittest.main()
