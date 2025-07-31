# tests/test_sprints.py
def test_home_redirects(client):
    resp = client.get('/')
    assert resp.status_code == 302
    assert '/sprints' in resp.headers['Location']

def test_add_and_list_sprint(client):
    # initially no sprints
    resp = client.get('/sprints')
    assert b"No sprints" in resp.data or resp.status_code == 200

    # add one
    resp = client.post('/sprints', data={'name': 'Test Sprint'})
    assert resp.status_code == 302

    # now list shows it
    resp = client.get('/sprints')
    assert b"Test Sprint" in resp.data
