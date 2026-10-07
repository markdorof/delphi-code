import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from delphi_code.cli import arguments
from delphi_code.domain.errors import Failure
from delphi_code.infrastructure.paths import model_directory


class ModelDefaults(unittest.TestCase):
    def test_environment_overrides_default(self):
        with patch.dict(os.environ, {"DELPHI_CODE_MODEL": "/configured/model"}):
            self.assertEqual(model_directory(), Path("/configured/model"))

    def test_default_without_environment(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("delphi_code.infrastructure.paths.data_directory", return_value=Path("/local/data")),
        ):
            self.assertEqual(model_directory(), Path("/local/data/models/all-MiniLM-L6-v2"))

    def test_model_flag_is_gone(self):
        with (
            patch.object(sys, "argv", ["delphi-code", "index", "--model", "/explicit/model"]),
            self.assertRaises(Failure),
        ):
            arguments()


class ModelIdentity(unittest.TestCase):
    def test_incidental_files_do_not_change_identity(self):
        import json
        import tempfile

        from delphi_code.infrastructure.model import LocalModel

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "modules.json").write_text(
                json.dumps([{"type": "sentence_transformers.models.Normalize", "path": ""}])
            )
            (root / "model.safetensors").write_bytes(b"weights")
            before = LocalModel.inspect(root).sha256
            (root / ".DS_Store").write_bytes(b"finder")
            (root / "._model.safetensors").write_bytes(b"resource fork")
            (root / "README.md").write_text("model card")
            (root / "LICENSE").write_text("license")
            self.assertEqual(LocalModel.inspect(root).sha256, before)
            (root / "model.safetensors").write_bytes(b"changed")
            self.assertNotEqual(LocalModel.inspect(root).sha256, before)
