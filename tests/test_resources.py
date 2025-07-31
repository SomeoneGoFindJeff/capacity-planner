# tests/test_resources.py
def test_add_resource_and_list(client):
    resp = client.post('/resources', data={'name': 'Alice'})
    assert resp.status_code == 302

    resp = client.get('/resources')
    assert b"Alice" in resp.data
