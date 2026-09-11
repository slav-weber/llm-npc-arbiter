"""The knowledge graph is an optional layer: a broken graph file must not break retrieval.

Pinned against knowledge/graph.py with temporary files only; the committed graph is only read.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from knowledge import graph    # noqa: E402


class GraphDegradation(unittest.TestCase):
    """Optional layers degrade to a no-op."""

    def setUp(self):
        graph.reload()
        self.addCleanup(graph.reload)
        with open(graph.GRAPH, "rb") as f:
            self.committed = f.read()
        adj = json.loads(self.committed.decode("utf-8"))["adj"]
        self.entity = next(name for name, nbrs in sorted(adj.items()) if nbrs)

    def _expand(self, path: str) -> list:
        """Every expansion the module offers for one entity, with the graph read from `path`."""
        with mock.patch.object(graph, "GRAPH", path):
            graph.reload()
            try:
                return [graph.neighbors(self.entity), graph.neighbors_of([self.entity]),
                        graph.related_facts([self.entity])]
            finally:
                graph.reload()

    def test_a_corrupt_or_half_written_graph_file_degrades_to_a_no_op(self):
        """A graph file that is missing, empty, cut off mid-write or not text expands to nothing.

        Real behaviour [CODE]: `_graph` loads the file under a broad except and falls back to an empty
        graph; the module reads its path from the `GRAPH` attribute at call time and drops its cache on
        `reload`, which is the hook used here. The query that the committed graph expands must come
        back empty, and not raise, from each broken file: an interrupted rebuild must not take
        retrieval down with it.
        """
        self.assertTrue(all(self._expand(graph.GRAPH)), "the committed graph must expand the query")
        broken = {"missing": None,
                  "empty": b"",
                  "half-written": self.committed[: len(self.committed) // 2],
                  "not text": b"\xff\xfe\x00\x81 not a graph"}
        with tempfile.TemporaryDirectory() as tmp:
            for label, data in broken.items():
                path = os.path.join(tmp, label.replace(" ", "-") + ".json")
                if data is not None:
                    with open(path, "wb") as f:
                        f.write(data)
                with self.subTest(file=label):
                    self.assertEqual(self._expand(path), [[], [], []])

    def test_a_graph_file_of_the_wrong_shape_degrades_to_a_no_op(self):
        """A readable file that is not a graph (null, a list, a dict without the node and adjacency
        maps) expands to nothing and does not raise either: the loader checks the shape instead of
        assuming it."""
        wrong = {"null": b"null", "a list": b"[1, 2, 3]", "no adjacency": b'{"nodes": {}}',
                 "adjacency not a map": b'{"nodes": {}, "adj": []}'}
        with tempfile.TemporaryDirectory() as tmp:
            for label, data in wrong.items():
                path = os.path.join(tmp, label.replace(" ", "-") + ".json")
                with open(path, "wb") as f:
                    f.write(data)
                with self.subTest(file=label):
                    self.assertEqual(self._expand(path), [[], [], []])


if __name__ == "__main__":
    unittest.main()
