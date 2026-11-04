"""Check hidden-data ancestry through intermediate products."""
import unittest
from tcsexam.product_graph import validate_graph


class ProductGraph(unittest.TestCase):
    def test_public_runtime_cannot_inherit_hidden_data_through_tools(self):
        rows = [{'id': 'hidden', 'type': 'data', 'data_split': 'hidden'},
                {'id': 'tools', 'dependencies': ['hidden']},
                {'id': 'dev', 'runtime_role': 'development',
                 'build': {'image_args': {'BASE': 'tools'}}}]
        with self.assertRaisesRegex(ValueError, 'depends on hidden data'):
            validate_graph({'images': rows})
        rows[-1]['runtime_role'] = 'verifier'
        self.assertTrue(validate_graph({'images': rows})['dependencies_acyclic'])

    def test_missing_dependency_and_cycle_have_explicit_errors(self):
        rows = [{'id': 'a', 'dependencies': ['b']}]
        with self.assertRaisesRegex(ValueError, 'Unknown product'):
            validate_graph({'images': rows})
        rows.append({'id': 'b', 'dependencies': ['a']})
        with self.assertRaisesRegex(ValueError, 'dependency cycle'):
            validate_graph({'images': rows})

    def test_filtering_a_hidden_parent_does_not_establish_public_construction(self):
        with self.assertRaisesRegex(ValueError, 'depends on hidden data'):
            validate_graph({'images': [
                {'id': 'hidden', 'type': 'data', 'purpose': 'hidden_judging'},
                {'id': 'public', 'runtime_role': 'public_backend',
                 'build': {'kind': 'public_image', 'source_product': 'hidden'}}]})
