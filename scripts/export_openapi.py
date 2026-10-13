import json
import sys

from delphi_code.http_api.app import create_app
from delphi_code.http_api.settings import ApiSettings
from delphi_code.services.application import DelphiCode

TOKEN_UNUSED_BY_THE_SCHEMA = "schema-export"


def schema_without_release_version() -> dict:
    schema = create_app(DelphiCode.from_environment(), ApiSettings(TOKEN_UNUSED_BY_THE_SCHEMA)).openapi()
    # The committed schema would otherwise change with every version bump.
    schema["info"].pop("version")
    return schema


def main():
    json.dump(schema_without_release_version(), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
