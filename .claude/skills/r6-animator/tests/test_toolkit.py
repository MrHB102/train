"""Behavioral/CLI regressions for original-authorship rules and practical utilities."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import db,r6,qa,mcp_server,install,video_reference

class ToolkitTests(unittest.TestCase):
    def test_database_cannot_expose_motion(self):
        for rec in db.db()['anims'].values():
            self.assertFalse(set(rec)&{'keys','raw','ext'})
        for mode in ('keys','raw'):
            with self.assertRaises(ValueError):db.show('manji.yuji',mode)
            out=mcp_server.handle({'id':1,'method':'tools/call','params':{'name':'r6_show','arguments':{'id':'manji.yuji','mode':mode}}})
            self.assertTrue(out['isError'])
        with self.assertRaises(ValueError):mcp_server.t_preview({'id':'manji.yuji'})

    def test_legacy_sanitization_and_ingest(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);database=base/'anims.json';index=base/'index.json'
            database.write_text(json.dumps({'schema':1,'anims':{'old':{'name':'old','keys':[[1,{}]],'raw':[123],'ext':{'raw':[456]},'m':{'hold_pct':0.4}}}}))
            with patch.object(db,'P_DB',str(database)),patch.object(db,'P_IX',str(index)),patch.object(db,'DATA',td),patch.object(db,'_cache',{}):
                self.assertEqual(db.get('old')['m']['hold_pct'],0.4)
                self.assertNotIn('raw',db.get('old'));db.save()
                r6.new('diagnostic',30);r6.key(0,ra=[0]);r6.key(12,ra=[8]);r6.key(30,ra=[0])
                clip=base/'own.json';r6.dump(str(clip));db.add_clip(str(clip),'mine')
                xml=base/'own.rbxmx';r6.export(str(xml));db.ingest(str(xml),'own')
                saved=json.loads(database.read_text())
                self.assertEqual(saved['schema'],2)
                self.assertTrue(all(not set(x)&{'keys','raw','ext'} for x in saved['anims'].values()))

    def test_support_is_not_assumed(self):
        r6.new('support',30);r6.key(0,hrp=[0]);r6.key(30,hrp=[0])
        self.assertEqual(qa.assess(r6.cur())['plants_status'],'not-assessed')
        plan={'duration_s':1,'grounded':[[0,1]],'plants':[{'bone':'rl','start_s':0,'end_s':1,'tolerance':0.01}]}
        self.assertTrue(qa.assess(r6.cur(),plan)['passed'])
        r6.key(30,hrp=[0,0,0,1])
        out=qa.assess(r6.cur(),plan)
        self.assertFalse(out['passed']);self.assertTrue(any(f['check']=='plant' for f in out['findings']))

    def test_inbetween_floor_and_loop_velocity(self):
        r6.new('floor',30);r6.key(0,hrp=[0,0,0,0,0]);r6.key(15,hrp=[0,0,0,0,-1]);r6.key(30,hrp=[0])
        out=qa.assess(r6.cur(),{'grounded':[[0,1]]})
        self.assertFalse(out['passed']);self.assertLess(out['ground'][0]['min_y'],-0.9)
        r6.new('seam',30,True,'lin');r6.key(0,ra=[0]);r6.key(6,ra=[30]);r6.key(30,ra=[0])
        out=qa.assess(r6.cur())
        self.assertFalse(out['passed']);self.assertEqual(out['loop']['metrics']['pose_deg'],0)
        self.assertGreater(out['loop']['metrics']['velocity_deg_s'],100)

    def test_invalid_channels_and_nan_mcp(self):
        d={'fps':30,'keys':[[0,{'ra':[float('nan')]},'lin']]}
        with self.assertRaises(ValueError):qa.validate_source(d)
        with self.assertRaises(ValueError):r6.new('bad',0)
        out=mcp_server.handle({'id':1,'method':'tools/call','params':{'name':'r6_export','arguments':{'table':'f ra\n0 nan\n1 0'}}})
        self.assertTrue(out['isError'])

    def test_dump_preserves_subtle_motion(self):
        r6.new('subtle',30);r6.key(0,ra=[0.001234,0,0,0,0.0000012]);r6.key(30,ra=[0])
        d=json.loads(r6.dump())
        self.assertEqual(d['keys'][0][1]['ra'][0],0.001234)
        self.assertEqual(d['keys'][0][1]['ra'][4],0.0000012)

    def test_mcp_schemas_and_state_restore(self):
        tools=mcp_server.handle({'id':1,'method':'tools/list'})['tools'];by={x['name']:x for x in tools}
        self.assertEqual(by['r6_show']['inputSchema']['properties']['mode']['enum'],['brief'])
        self.assertIn('table',by['r6_preview']['inputSchema']['required'])
        self.assertIn('r6_video_reference',by);self.assertIn('r6_qa',by)
        r6.new('keep',30);r6.key(0,ra=[5]);saved=copy.deepcopy(r6.cur())
        mcp_server.t_qa({'table':'f ra\n0 0\n30 5','fps':30})
        self.assertEqual(r6.cur(),saved)

    def test_install_preserves_existing(self):
        with tempfile.TemporaryDirectory() as td:
            project=Path(td)
            for client,folder in [('claude','.claude'),('codex','.agents')]:
                result=install.copy_skill(client,'project',td)
                target=project/folder/'skills/r6-animator'
                self.assertEqual(Path(result['path']),target);self.assertTrue((target/'SKILL.md').is_file())
                (target/'custom.txt').write_text('keep me')
                with self.assertRaises(ValueError):install.copy_skill(client,'project',td)
                result=install.copy_skill(client,'project',td,replace=True)
                self.assertEqual((Path(result['backup'])/'custom.txt').read_text(),'keep me')

    def test_rig_name_and_action_slot_are_respected(self):
        from types import SimpleNamespace as NS
        class Objects(list):
            def get(self, name): return next((o for o in self if o.name==name),None)
        rig=NS(name='actual',type='ARMATURE',data=NS(bones={b:None for b in r6._NEED}))
        mock_bpy=NS(data=NS(objects=Objects([rig])),context=NS(view_layer=NS(objects=NS(active=None))))
        with patch.object(r6,'_bpy',return_value=mock_bpy),patch.dict(sys.modules,{'mathutils':NS(Vector=None,Matrix=None)}):
            with self.assertRaisesRegex(RuntimeError,'named R6'):r6.use('missing')
        mock_bpy.data.objects=Objects([])
        with patch.object(r6,'_bpy',return_value=mock_bpy),patch.dict(sys.modules,{'mathutils':NS(Vector=None,Matrix=None)}):
            with self.assertRaisesRegex(RuntimeError,'no armature'):r6.use()
        action=NS(is_action_layered=True,layers=[NS(strips=[NS(channelbags=[NS(slot_handle=1,fcurves=['one']),NS(slot_handle=2,fcurves=['two'])])])])
        self.assertEqual(r6._fcs(action,NS(handle=2)),['two'])

    def test_docs_links_and_no_choreography(self):
        import re
        text=(ROOT/'SKILL.md').read_text()
        for link in re.findall(r'\]\((references/[^)]+)\)',text):self.assertTrue((ROOT/link).is_file(),link)
        self.assertLess(len(text.split()),2000)
        self.assertFalse((ROOT/'scripts/fight').exists())
        self.assertFalse((ROOT/'examples').exists())
        self.assertNotIn('paste-ready', (ROOT/'scripts/mcp_server.py').read_text())

    def test_media_preparation_and_evidence_status(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);media=root/'moving.mp4'
            video_reference.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=size=320x240:rate=24:duration=2','-c:v','libx264','-pix_fmt','yuv420p','-y',media])
            out=video_reference.prepare(str(media),root/'ref',0.25,1,4)
            self.assertEqual(out['status'],'prepared-not-analyzed');self.assertFalse(out['visual_inspection_performed'])
            self.assertEqual(len(out['frames']),4);self.assertEqual(out['interval_source_s'],[0.25,1.25])
            self.assertTrue(Path(out['contact_sheet']).is_file());self.assertTrue(Path(out['proxy']).is_file())
            self.assertAlmostEqual(video_reference.probe(out['proxy'])['duration_s'],1,delta=0.1)
            from PIL import Image,ImageChops
            with Image.open(out['frames'][0]['path']) as a,Image.open(out['frames'][-1]['path']) as b:
                self.assertIsNotNone(ImageChops.difference(a.crop((0,30,a.width,a.height)),b.crop((0,30,b.width,b.height))).getbbox())
            with self.assertRaises(ValueError):video_reference.prepare(str(media),root/'ref',0,1,4)
            with self.assertRaises(ValueError):video_reference.prepare(str(media),root/'bad',0,1,4,[1.5])
            with self.assertRaises(ValueError):video_reference.prepare(str(media),root/'bad2',float('nan'),1,4)

    def test_video_url_uses_arglist_and_no_auto_cookies(self):
        with tempfile.TemporaryDirectory() as td:
            captured=[]
            def fake_run(args,timeout=90):
                captured.extend(args);(Path(td)/'download/source.mp4').write_bytes(b'fixture');return ''
            with patch.object(video_reference.shutil,'which',return_value='/bin/yt-dlp'),patch.object(video_reference,'run',side_effect=fake_run):
                video_reference.acquire('https://example.com/video?x=$(touch%20bad)',Path(td))
            self.assertIn('--ignore-config',captured);self.assertIn('--no-playlist',captured)
            self.assertNotIn('--cookies-from-browser',captured)
            self.assertEqual(captured[-2],'--');self.assertTrue(captured[-1].startswith('https://'))

if __name__=='__main__':unittest.main(verbosity=2)
