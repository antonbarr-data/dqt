"""Apache Airflow provider for dqt."""

PROVIDER_PACKAGE_NAME = "airflow-providers-dqt"
PROVIDER_PACKAGE_VERSION = "0.7.2"


def get_provider_info() -> dict:
    return {
        "package-name": PROVIDER_PACKAGE_NAME,
        "name": "dqt",
        "description": "dqt data quality operators and sensors",
        "versions": [PROVIDER_PACKAGE_VERSION],
    }


from dqt_airflow.operators import DqtCheckOperator, DqtSuiteOperator  # noqa: E402

__all__ = ["DqtCheckOperator", "DqtSuiteOperator", "get_provider_info"]
