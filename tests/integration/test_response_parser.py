from app.integration.response_parser import ResponseParser

def test_parse_success():
    p=ResponseParser()
    r=p.parse({"return_code":0,"return_msg":"OK","token":"abc"})
    assert r.success
    assert r.data["token"]=="abc"
