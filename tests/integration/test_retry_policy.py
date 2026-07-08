from app.integration.retry_policy import RetryPolicy
def test_defaults():
    p=RetryPolicy()
    assert p.retries==3
