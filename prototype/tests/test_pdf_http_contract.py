"""HTTP contract smoke for private in-memory PDF download route, synthetic only."""
import contextlib
import io
import http.client
import json
import threading
import unittest
from unittest.mock import patch

from kundali_prototype import server

class PDFHTTPContract(unittest.TestCase):
    def setUp(self):
        self.app=server.PrototypeServer(0,"/not-needed-for-mocked-route",{})
        self.thread=threading.Thread(target=self.app.serve_forever,daemon=True)
        self.thread.start()
        self.host="127.0.0.1:%d"%self.app.server_address[1]

    def tearDown(self):
        self.app.shutdown()
        self.app.server_close()
        self.thread.join(timeout=5)

    def request(self,path,body=b'{}',content_type='application/json',origin=None):
        c=http.client.HTTPConnection('127.0.0.1',self.app.server_address[1],timeout=4)
        h={"Host":self.host,"Content-Type":content_type,"Content-Length":str(len(body))}
        if origin is not None:h['Origin']=origin
        c.request("POST",path,body,h)
        r=c.getresponse()
        status,headers,data=r.status,dict(r.getheaders()),r.read()
        c.close()
        return status,headers,data

    def test_pdf_attachment_headers_and_body(self):
        with patch.object(server,"handle_report",return_value=(200,b'%PDF-1.7 synthetic-only')):
            status,h,body=self.request('/api/report',origin='http://'+self.host)
        self.assertEqual(status,200)
        self.assertEqual(h["Content-Type"],"application/pdf")
        self.assertIn("attachment",h["Content-Disposition"])
        self.assertEqual(h["Cache-Control"],"no-store")
        self.assertEqual(body,b'%PDF-1.7 synthetic-only')

    def test_pdf_refusal_uses_existing_json_contract(self):
        refusal={"error":{"code":"PLACE_UNKNOWN","message":"choose a birthplace","category":"place"}}
        with patch.object(server,"handle_report",return_value=(422,refusal)):
            status,h,body=self.request('/api/report')
        self.assertEqual(status,422)
        self.assertEqual(json.loads(body),refusal)
        self.assertIn('application/json',h['Content-Type'])

    def test_cross_origin_refused_before_compute(self):
        with patch.object(server,"handle_report") as handler:
            status,_,_=self.request('/api/report',origin='https://evil.example')
            handler.assert_not_called()
        self.assertEqual(status,403)

    def test_bad_type_refused_before_compute(self):
        with patch.object(server,"handle_report") as handler:
            status,_,_=self.request('/api/report',content_type='text/plain')
            handler.assert_not_called()
        self.assertEqual(status,415)

    def test_pdf_render_exception_fixed_public_error(self):
        captured=io.StringIO()
        with patch.object(server,"handle_report",side_effect=ValueError("birth_date 1990-05-15 should not leak")):
            with contextlib.redirect_stderr(captured):
                status,_,body=self.request('/api/report')
        self.assertEqual(status,503)
        self.assertNotIn(b'1990-05-15',body)
        self.assertNotIn('1990-05-15',captured.getvalue())
        self.assertIn('"type": "ValueError"',captured.getvalue())
        self.assertEqual(json.loads(body)['error']['code'],'REPORT_UNAVAILABLE')

    def test_busy_render_rejected_without_invoking_generator(self):
        locked=server._PDF_RENDER_SLOT.acquire(blocking=False)
        self.assertTrue(locked)
        try:
            with patch.object(server,"handle_report") as generator:
                status,headers,body=self.request('/api/report')
                generator.assert_not_called()
            self.assertEqual(status,429)
            self.assertEqual(json.loads(body)['error']['code'],'REPORT_BUSY')
            self.assertEqual(headers['Cache-Control'],'no-store')
        finally:
            server._PDF_RENDER_SLOT.release()

    def test_oversized_generated_pdf_is_refused(self):
        from report.phase1 import generate_report
        with patch.object(server,"handle_chart",return_value=(200,{'input':{},'chart':{}})):
            with patch.object(generate_report,"generate",return_value=b'%PDF-'+b'x'*(server.MAX_PDF_BYTES+1)):
                with self.assertRaises(RuntimeError):
                    server.handle_report(b'{}',{},'/synthetic-only')

if __name__=='__main__':
    unittest.main()
