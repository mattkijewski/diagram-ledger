import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SKILL=ROOT/'skills/diagram-ledger'
spec=importlib.util.spec_from_file_location('revision',SKILL/'scripts/revision.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
spec=importlib.util.spec_from_file_location('migration_install',ROOT/'install.py')
i=importlib.util.module_from_spec(spec);spec.loader.exec_module(i)

SVG='''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200"><style>text {font-size:16px}</style><g data-node="a"><rect x="20" y="20" width="100" height="40"/><text x="30" y="45">Intake</text></g><g data-node="b"><rect x="220" y="20" width="100" height="40"/><text x="230" y="45">Archive</text></g><path data-edge="ab" data-from="a" data-to="b" d="M120 40 H220"/></svg>'''
DRAW='''<mxfile><diagram id="main" name="Pipeline"><mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/><mxCell id="a" value="Intake" vertex="1" parent="1" style="fillColor=white;"><mxGeometry x="20" y="20" width="100" height="40" as="geometry"/></mxCell><mxCell id="b" value="Archive" vertex="1" parent="1"><mxGeometry x="220" y="20" width="100" height="40" as="geometry"/></mxCell><mxCell id="ab" edge="1" parent="1" source="a" target="b"><mxGeometry relative="1" as="geometry"/></mxCell></root></mxGraphModel></diagram></mxfile>'''

class RevisionChecks(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
    def snap(self,text,name='source.svg'):
        p=self.root/name;p.write_text(text, encoding='utf-8');return r.snapshot(p)
    def contract(self,state,allow=None,require=None):
        return {'version':1,'baseline_sha256':state['sha256'],'allow':allow or {},'require':require or []}
    def test_rename_allowed_but_geometry_protected_both_formats(self):
        for text,key in [(SVG,'node:a'),(DRAW,'node:main/a')]:
            a=self.snap(text);c=self.contract(a,{key:['label']},[{'entity':key,'field':'label','equals':'Validated intake'}])
            b=self.snap(text.replace('Intake','Validated intake'))
            self.assertEqual(r.compare(a,b,c)['status'],'pass')
            b=self.snap(text.replace('Intake','Validated intake').replace('x="20"','x="25"'))
            result=r.compare(a,b,c);self.assertEqual(result['status'],'fail')
            self.assertTrue(any(x['field']=='geometry' and not x['allowed'] for x in result['changes']))
    def test_required_work_cannot_be_omitted(self):
        a=self.snap(SVG);c=self.contract(a,{'node:a':['label']},[{'entity':'node:a','field':'label','equals':'Updated'}])
        self.assertEqual(r.compare(a,a,c)['status'],'fail')
    def test_connections_membership_style_and_global_css_protected(self):
        for original,mutation,field in [(SVG,SVG.replace('data-to="b"','data-to="a"'),'target'),(SVG,SVG.replace('16px','14px'),'content'),(DRAW,DRAW.replace('fillColor=white','fillColor=red'),'style'),(DRAW,DRAW.replace('id="a" value="Intake" vertex="1" parent="1"','id="a" value="Intake" vertex="1" parent="b"'),'membership')]:
            a=self.snap(original);result=r.compare(a,self.snap(mutation),self.contract(a))
            self.assertEqual(result['status'],'fail');self.assertTrue(any(x['field']==field for x in result['changes']))
    def test_add_remove_and_source_hash_protection(self):
        a=self.snap(SVG);extra='<g data-node="c"><rect x="30" y="130" width="100" height="40"/></g>'
        b=self.snap(SVG.replace('</svg>',extra+'</svg>'))
        c=self.contract(a,{'node:c':['added']},[{'entity':'node:c','exists':True}])
        self.assertEqual(r.compare(a,b,c)['status'],'pass')
        with self.assertRaises(ValueError):r.compare(b,a,c)
        c=self.contract(b,{'node:c':['removed']},[{'entity':'node:c','exists':False}])
        self.assertEqual(r.compare(b,a,c)['status'],'pass')
    def test_stacking_order_changes_are_not_silent(self):
        root=r.load_xml(SVG.encode());a=self.snap(SVG);node=root[1];root.remove(node);root.append(node)
        b=self.snap(r.ET.tostring(root).decode());result=r.compare(a,b,self.contract(a))
        self.assertTrue(any(x['field']=='order' for x in result['changes']));self.assertEqual(result['status'],'fail')
    def test_invalid_contracts_rejected(self):
        a=self.snap(SVG)
        for update in [{'allow':{'node:typo':['label']}},{'allow':{'node:a':['*']}},{'allow':{'node:a':['added']}},{'require':[{'entity':'node:a','exists':'true'}]},{'requires':[]}]:
            c=self.contract(a);c.update(update)
            with self.subTest(update=update),self.assertRaises(ValueError):r.compare(a,a,c)
    def test_invalid_or_unsupported_sources_rejected(self):
        for text in [SVG.replace('data-node="b"','data-node="a"'),SVG.replace('data-to="b"','data-to="missing"'),'<svg/>','<html/>','flowchart LR\nA-->B','<!DOCTYPE svg><svg/>',DRAW.replace('id="b"','id="a"'),DRAW.replace('parent="1"','parent="a"'),'<mxfile><diagram id="a">compressed</diagram></mxfile>']:
            with self.subTest(text=text[:50]),self.assertRaises((ValueError,r.ET.ParseError)):self.snap(text)
    def test_page_ids_are_scoped_and_new_page_needs_allowance(self):
        root=r.load_xml(DRAW.encode());second=copy.deepcopy(root[0]);second.set('id','second');root.append(second)
        a=self.snap(r.ET.tostring(root).decode());self.assertIn('node:second/a',a['entities'])
        b=self.snap(r.ET.tostring(root).decode().replace('name="Pipeline"','name="Changed"',1))
        self.assertEqual(r.compare(a,b,self.contract(a))['status'],'fail')
    def test_report_binds_sources_escapes_labels_and_does_not_overwrite(self):
        p=self.root/'before.svg';p.write_text(SVG, encoding='utf-8');a=r.snapshot(p);c=self.contract(a);c['intent']='<script>bad()</script>'
        result=r.compare(a,a,c);out=self.root/'report';r.write_report(out,result,p,p,c)
        self.assertEqual(r.sha((out/'before.svg').read_bytes()),result['before_sha256'])
        self.assertNotIn('<script>',(out/'index.html').read_text(encoding='utf-8'));self.assertIn('&lt;script&gt;', (out/'index.html').read_text(encoding='utf-8'))
        with self.assertRaises(ValueError):r.write_report(out,result,p,p,c)
    def test_cli_capture_and_failed_check_exit_status(self):
        p=self.root/'before.svg';p.write_text(SVG, encoding='utf-8');script=str(SKILL/'scripts/revision.py')
        result=subprocess.run([sys.executable,script,'plan',str(p),'--out',str(self.root/'plan')],capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        after=self.root/'after.svg';after.write_text(SVG.replace('Intake','Changed'), encoding='utf-8')
        result=subprocess.run([sys.executable,script,'check',str(p),str(after),'--contract',str(self.root/'plan/contract.json'),'--out',str(self.root/'review')],capture_output=True)
        self.assertEqual(result.returncode,1,result.stderr);self.assertEqual(json.loads((self.root/'review/report.json').read_text(encoding='utf-8'))['status'],'fail')

class MigrationChecks(unittest.TestCase):
    def test_migration_keeps_customizations_and_single_discovery(self):
        with tempfile.TemporaryDirectory() as d:
            old=Path(d)/'.claude/skills/diagram-craft';old.mkdir(parents=True);(old/'SKILL.md').write_text('---\nname: diagram-craft\n---\nMy version', encoding='utf-8')
            new=old.with_name('diagram-ledger')
            with self.assertRaises(ValueError):i.install(SKILL,[new])
            i.install(SKILL,[new],dry_run=True,update=True);self.assertTrue(old.exists());self.assertFalse(new.exists())
            i.install(SKILL,[new],update=True);self.assertFalse(old.exists());self.assertTrue(new.exists())
            backup=list((old.parent.parent/'skill-backups').glob('diagram-craft-*'));self.assertEqual(len(backup),1);self.assertIn('My version',(backup[0]/'SKILL.md').read_text(encoding='utf-8'))
    def test_migration_rolls_back_after_rename_failure(self):
        with tempfile.TemporaryDirectory() as d:
            old=Path(d)/'.claude/skills/diagram-craft';old.mkdir(parents=True);(old/'SKILL.md').write_text('---\nname: diagram-craft\n---', encoding='utf-8')
            new=old.with_name('diagram-ledger');rename=Path.rename
            def fail_stage(path,target):
                if path.name.startswith('.diagram-ledger-stage'):raise OSError('disk full')
                return rename(path,target)
            with patch.object(Path,'rename',fail_stage),self.assertRaises(OSError):i.install(SKILL,[new],update=True)
            self.assertTrue(old.exists());self.assertFalse(new.exists())

class NativeOrderCheck(unittest.TestCase):
    def test_reordering_native_cells_is_a_protected_change(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'original.drawio';p.write_text(DRAW, encoding='utf-8');a=r.snapshot(p)
            root=r.load_xml(DRAW.encode());graph=root.find('./diagram/mxGraphModel/root');node=graph.find("mxCell[@id='a']");graph.remove(node);graph.append(node)
            p.write_text(r.ET.tostring(root).decode(), encoding='utf-8');b=r.snapshot(p)
            report=r.compare(a,b,{'version':1,'baseline_sha256':a['sha256'],'allow':{},'require':[]})
            self.assertEqual(report['status'],'fail');self.assertTrue(any(c['field']=='order' for c in report['changes']))

class SvgStackingContextCheck(unittest.TestCase):
    def test_moving_entities_across_untracked_background_is_detected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'before.svg';p.write_text(SVG.replace('<style>','<rect width="400" height="200" fill="white"/><style>'), encoding='utf-8');a=r.snapshot(p)
            root=r.load_xml(p.read_bytes());background=root[0];root.remove(background);root.append(background)
            p.write_text(r.ET.tostring(root).decode(), encoding='utf-8');b=r.snapshot(p)
            report=r.compare(a,b,{'version':1,'baseline_sha256':a['sha256'],'allow':{},'require':[]})
            self.assertEqual(report['status'],'fail');self.assertTrue(any(c['field']=='membership' for c in report['changes']))

class NarrowContractCheck(unittest.TestCase):
    def test_cli_outcome_gate_rejects_empty_and_unmet_requirements(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);before=root/'before.svg';after=root/'after.svg'
            before.write_text(SVG,encoding='utf-8')
            after.write_text(SVG.replace('Intake','Updated intake'),encoding='utf-8')
            contract={'version':1,'baseline_sha256':r.snapshot(before)['sha256'],
                      'allow':{'node:a':['label']},'require':[]}
            path=root/'contract.json'
            for name,requirements,expected in [
                ('empty',[],2),
                ('unmet',[{'entity':'node:a','field':'label','equals':'Wrong label'}],1),
                ('satisfied',[{'entity':'node:a','field':'label','equals':'Updated intake'}],0),
            ]:
                with self.subTest(name=name):
                    contract['require']=requirements;path.write_text(json.dumps(contract),encoding='utf-8')
                    out=root/name
                    result=subprocess.run([sys.executable,str(SKILL/'scripts/revision.py'),'check',
                        str(before),str(after),'--contract',str(path),'--out',str(out),
                        '--require-outcomes'],capture_output=True,text=True)
                    self.assertEqual(result.returncode,expected,result.stderr)
                    if name=='empty':
                        self.assertIn('nonempty require list',result.stderr)
                        self.assertFalse(out.exists())
                    else:
                        self.assertEqual(json.loads((out/'report.json').read_text())['status'],
                                         'pass' if expected==0 else 'fail')

    def test_unneeded_document_permissions_fail_even_with_correct_diagram(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'before.svg';p.write_text(SVG, encoding='utf-8');a=r.snapshot(p);p.write_text(SVG.replace('Intake','Validated intake'), encoding='utf-8');b=r.snapshot(p)
            c={'version':1,'baseline_sha256':a['sha256'],'allow':{'node:a':['label'],'document:root':['content','order']},'require':[{'entity':'node:a','field':'label','equals':'Validated intake'}]}
            report=r.compare(a,b,c);self.assertEqual(report['status'],'fail');self.assertEqual(len(report['unused_allowances']),2)
            del c['allow']['document:root'];self.assertEqual(r.compare(a,b,c)['status'],'pass')

class UnicodeReceiptCheck(unittest.TestCase):
    def test_receipt_keeps_unicode_labels_in_utf8(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);before=root/'before.svg';after=root/'after.svg'
            before.write_text(SVG,encoding='utf-8')
            after.write_text(SVG.replace('Intake','Café 東京'),encoding='utf-8')
            a=r.snapshot(before);b=r.snapshot(after)
            c={'version':1,'baseline_sha256':a['sha256'],'intent':'Renommer Café 東京','allow':{'node:a':['label']},'require':[{'entity':'node:a','field':'label','equals':'Café 東京'}]}
            report=r.compare(a,b,c);self.assertEqual(report['status'],'pass')
            r.write_report(root/'receipt',report,before,after,c)
            self.assertIn('Café 東京',(root/'receipt/index.html').read_text(encoding='utf-8'))
            self.assertEqual((root/'receipt/after.svg').read_bytes(),after.read_bytes())
