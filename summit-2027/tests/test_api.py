"""Security and release-boundary checks without production credentials."""
import importlib.util
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch
spec = importlib.util.spec_from_file_location('api', Path(__file__).parents[1]/'api'/'app.py')
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)
class Request(api.handler):
    def __init__(self, action, data=None, headers=None):
        self.path='/api/app?action='+action
        raw=json.dumps(data).encode() if data is not None else b''
        self.rfile=io.BytesIO(raw)
        self.headers={'Content-Type':'application/json','Content-Length':str(len(raw)),'Host':'localhost',**(headers or {})}
        self.client_address=('127.0.0.1',1234)
    def respond(self, status, body, cookie=None):
        self.result=(status,body,cookie)
class Boundaries(unittest.TestCase):
    def call(self,action,data=None,headers=None):
        req=Request(action,data,headers);req.dispatch(data is not None);return req.result
    def test_demo_is_explicit(self):
        with patch.object(api,'LIVE',False):
            self.assertEqual(self.call('status')[1]['mode'],'demo')
            self.assertEqual(self.call('upload',{'image':'x'})[0],503)
    def test_private_shared_endpoints_require_session(self):
        with patch.object(api,'LIVE',True):
            for action,data in [('shared',None),('upload',{}),('drink',{}),('delete-photo',{})]:
                self.assertEqual(self.call(action,data)[0],401)
    def test_cross_origin_mutation_rejected(self):
        self.assertEqual(self.call('login',{'code':'x'},{'Origin':'https://another.example'})[0],403)
    def test_login_signs_cookie_and_tampering_fails(self):
        with patch.multiple(api,LIVE=True,EVENT_CODE='test-code',SESSION_SECRET='test-secret'),patch.object(api,'remote',return_value=True):
            self.assertEqual(self.call('login',{'code':'wrong'})[0],401)
            status,body,cookie=self.call('login',{'code':'test-code'})
            self.assertEqual(status,200)
            self.assertIn('HttpOnly',cookie)
            self.assertTrue(self.call('status',headers={'Cookie':cookie})[1]['authenticated'])
            self.assertFalse(self.call('status',headers={'Cookie':cookie.replace('gp27_session=','gp27_session=broken')})[1]['authenticated'])
    def test_locked_video_url_never_reaches_client(self):
        class Content:
            def read_text(self):
                return json.dumps({'videos':[{'team_id':1,'title':'Team 01','url':'https://example.com/secret.mp4','release_at':'2099-01-01T00:00:00Z'},{'team_id':2,'title':'Team 02','url':'https://example.com/open.mp4','release_at':'2020-01-01T00:00:00Z'}]})
        def remote(path,*args):
            return [] if path.startswith('/rest/v1/photos') else {'coffee':0,'beer':0,'wine':0}
        with patch.object(api,'LIVE',True),patch.object(Request,'session',return_value='owner'),patch.object(api,'CONTENT',Content()),patch.object(api,'remote',side_effect=remote):
            status,body,_=self.call('shared')
            self.assertEqual(status,200)
            self.assertNotIn('url',body['videos'][0])
            self.assertEqual(body['videos'][1]['url'],'https://example.com/open.mp4')
    def test_cannot_delete_someone_elses_photo(self):
        with patch.object(api,'LIVE',True),patch.object(Request,'session',return_value='owner'),patch.object(api,'remote',return_value=[]) as remote:
            self.assertEqual(self.call('delete-photo',{'id':'test'})[0],404)
            self.assertIn('owner_id=eq.owner',remote.call_args[0][0])
    def test_no_service_error_details_exposed(self):
        with patch.object(api,'LIVE',True),patch.object(Request,'session',return_value='owner'),patch.object(api,'remote',side_effect=RuntimeError('secret-value')):
            status,body,_=self.call('shared')
            self.assertEqual(status,502)
            self.assertNotIn('secret-value',json.dumps(body))
    def test_missing_sheet_does_not_claim_live_data(self):
        with patch.dict(api.os.environ,{'GOOGLE_SHEET_CSV_URL':''}):
            self.assertEqual(self.call('agenda')[1],{'connected':False,'rows':[]})
if __name__=='__main__':unittest.main()
