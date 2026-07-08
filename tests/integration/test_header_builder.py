from app.integration.header_builder import (
    HeaderBuilder,
    HeaderContext,
)


def test_build_basic_header():
    builder = HeaderBuilder()

    headers = builder.build(
        HeaderContext(
            api_id="au10001",
            authorization="Bearer token"
        )
    )

    assert headers["api-id"] == "au10001"
    assert headers["authorization"] == "Bearer token"
    assert headers["Content-Type"] == "application/json;charset=UTF-8"
    assert headers["cont-yn"] == "N"