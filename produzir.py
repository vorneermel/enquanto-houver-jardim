from pathlib import Path
import re, json, html, zipfile, uuid, posixpath
from xml.etree import ElementTree as ET
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader, PdfWriter

ROOT = Path(__file__).resolve().parent
TMP = ROOT / 'tmp'
TMP.mkdir(exist_ok=True)
TITLE = 'Enquanto Houver Jardim'
W, H = 432, 648
text = (ROOT / 'manuscrito.md').read_text(encoding='utf-8')
parts = re.split(r'^## ', text, flags=re.M)[1:]
chapters = []
for i, part in enumerate(parts, 1):
    heading, body = part.split('\n', 1)
    paragraphs = [p.strip() for p in body.strip().split('\n\n') if p.strip()]
    chapters.append((heading, paragraphs))
    target = ROOT / 'capitulos' / f'{i:02d}.md'
    target.parent.mkdir(exist_ok=True)
    target.write_text('# ' + heading + '\n\n' + '\n\n'.join(paragraphs) + '\n', encoding='utf-8')
assert len(chapters) == 6
back = (ROOT / 'contracapa.md').read_text(encoding='utf-8').split('\n\n')[1:]
for name, filename in [('Georgia','georgia.ttf'),('GeorgiaBold','georgiab.ttf'),('GeorgiaItalic','georgiai.ttf')]:
    pdfmetrics.registerFont(TTFont(name, 'C:/Windows/Fonts/' + filename))
pdfmetrics.registerFontFamily('Georgia',normal='Georgia',bold='GeorgiaBold',italic='GeorgiaItalic',boldItalic='GeorgiaBold')
styles = {
    'body': ParagraphStyle('body', fontName='Georgia',fontSize=11.2,leading=16.3,alignment=TA_JUSTIFY,firstLineIndent=16,spaceAfter=4,allowWidows=0,allowOrphans=0),
    'opening': ParagraphStyle('opening', fontName='Georgia',fontSize=11.2,leading=16.3,alignment=TA_JUSTIFY,spaceAfter=4,allowWidows=0,allowOrphans=0),
    'label': ParagraphStyle('label',fontName='Georgia',fontSize=10,leading=15,alignment=TA_CENTER,textColor=HexColor('#6c705d'),spaceAfter=16),
    'chapter': ParagraphStyle('chapter',fontName='GeorgiaBold',fontSize=22,leading=28,alignment=TA_CENTER,spaceAfter=28),
    'title': ParagraphStyle('title',fontName='Georgia',fontSize=35,leading=43,alignment=TA_CENTER,textColor=HexColor('#233e34'),spaceAfter=30),
    'toc': ParagraphStyle('toc',fontName='Georgia',fontSize=12,leading=20,spaceAfter=14),
    'back': ParagraphStyle('back',fontName='Georgia',fontSize=12.5,leading=19.5,textColor=HexColor('#f1eadb'),spaceAfter=16),
    'quote': ParagraphStyle('quote',fontName='GeorgiaItalic',fontSize=15,leading=22,textColor=HexColor('#d8c69c'),spaceBefore=12),
}
def esc(s): return html.escape(s,quote=False)
class BookDoc(SimpleDocTemplate):
    chapter_pages = {}
    def afterFlowable(self, flowable):
        if hasattr(flowable, 'chapter_id'):
            key = flowable.chapter_id
            self.chapter_pages[key] = self.page
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(flowable.getPlainText(),key,0,False)

def footer(c, doc):
    if doc.page > 2:
        c.setFont('Georgia',8)
        c.setFillColor(HexColor('#6c705d'))
        c.drawCentredString(W/2,24,str(doc.page-2))

story = [Spacer(1,130),Paragraph(TITLE,styles['title']),Paragraph('ROMANCE',styles['label']),PageBreak(),Paragraph('Sumário',styles['chapter']),Spacer(1,15)]
for i,(heading,_) in enumerate(chapters,1):
    story.append(Paragraph(esc(heading),styles['toc']))
story.append(PageBreak())
for i,(heading,paragraphs) in enumerate(chapters,1):
    number, name = heading.split(' — ',1)
    story += [Spacer(1,25),Paragraph(esc(number.upper()),styles['label'])]
    h = Paragraph(esc(name),styles['chapter']); h.chapter_id = f'ch{i}'
    story.append(h)
    for j,p in enumerate(paragraphs):
        if p == 'FIM':
            story.extend([Spacer(1,22),Paragraph('FIM',styles['label'])])
        else:
            story.append(Paragraph(esc(p),styles['opening' if j==0 or p.startswith('—') else 'body']))
    if i < len(chapters): story.append(PageBreak())
doc = BookDoc(str(TMP/'miolo.pdf'),pagesize=(W,H),leftMargin=47,rightMargin=47,topMargin=44,bottomMargin=44,title=TITLE,author='',pageCompression=1)
doc.build(story,onFirstPage=footer,onLaterPages=footer)

c = canvas.Canvas(str(TMP/'capa.pdf'),pagesize=(W,H))
c.setTitle(TITLE)
c.drawImage(str(ROOT/'capa.png'),0,0,width=W,height=H)
c.showPage(); c.save()
c = canvas.Canvas(str(TMP/'contracapa.pdf'),pagesize=(W,H))
c.setFillColor(HexColor('#173c31'));c.rect(0,0,W,H,fill=1,stroke=0)
c.setStrokeColor(HexColor('#b8ac80'));c.setLineWidth(.7);c.rect(28,28,W-56,H-56,fill=0,stroke=1)
c.setFillColor(HexColor('#f1eadb'));c.setFont('Georgia',22)
c.drawCentredString(W/2,H-72,TITLE)
c.setStrokeColor(HexColor('#b8ac80'));c.line(160,H-93,272,H-93)
y = H-125
for i,p in enumerate(back):
    style = styles['quote'] if p.startswith('“') else styles['back']
    para = Paragraph(esc(p),style)
    _,ph = para.wrap(W-100,H)
    assert y-ph > 38, 'Contracapa excedeu a pagina'
    para.drawOn(c,50,y-ph)
    y -= ph + style.spaceAfter + style.spaceBefore
c.showPage();c.save()
writer = PdfWriter()
for name in ['capa','miolo','contracapa']:
    writer.append(str(TMP/f'{name}.pdf'),import_outline=False)
for i,(heading,_) in enumerate(chapters,1): writer.add_outline_item(heading,doc.chapter_pages[f'ch{i}'])
writer.add_metadata({'/Title':TITLE,'/Subject':'Romance curto em seis capítulos','/Creator':'Preparação editorial com IA'})
with (ROOT/'Enquanto Houver Jardim.pdf').open('wb') as f:writer.write(f)

CSS = '''body{font-family:serif;line-height:1.5;margin:5%;}h1,h2{text-align:center;font-weight:normal;line-height:1.25;}h1{margin:1.5em 0;}p{text-indent:1.2em;margin:0 0 .35em;}p.first,p.dialogue{text-indent:0;}nav ol{padding-left:1.4em;}nav li{margin:.6em 0;}.cover{margin:0;padding:0;text-align:center;}.cover img{max-width:100%;height:auto;}.label{text-align:center;text-indent:0;letter-spacing:.08em;margin:2em 0;}.end{text-align:center;text-indent:0;margin:2em 0;}'''
def xhtml(title, body):
    return f'''<?xml version="1.0" encoding="utf-8"?><!DOCTYPE html><html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="pt-BR" xml:lang="pt-BR"><head><title>{esc(title)}</title><link rel="stylesheet" type="text/css" href="style.css"/></head><body>{body}</body></html>'''
files = {'OEBPS/style.css': CSS,'OEBPS/cover.xhtml':xhtml(TITLE,'<section class="cover" epub:type="cover"><img src="cover.png" alt="Augusto e Helena de mãos dadas no jardim; título Enquanto Houver Jardim"/></section>'),'OEBPS/title.xhtml':xhtml(TITLE,f'<section epub:type="titlepage"><h1>{TITLE}</h1><p class="label">ROMANCE</p></section>')}
tocitems=[]
for i,(heading,paragraphs) in enumerate(chapters,1):
    elements=[]
    for j,p in enumerate(paragraphs):
        cl = 'end' if p=='FIM' else 'dialogue' if p.startswith('—') else 'first' if j==0 else ''
        elements.append(f'<p class="{cl}">{esc(p)}</p>')
    files[f'OEBPS/ch{i}.xhtml']=xhtml(heading,f'<section epub:type="chapter" id="ch{i}"><h1>{esc(heading)}</h1>'+''.join(elements)+'</section>')
    tocitems.append(f'<li><a href="ch{i}.xhtml">{esc(heading)}</a></li>')
files['OEBPS/back.xhtml']=xhtml('Sobre a história','<section><h1>Sobre a história</h1>'+''.join(f'<p>{esc(p)}</p>' for p in back)+'</section>')
files['OEBPS/nav.xhtml']=xhtml('Sumário','<nav epub:type="toc" id="toc"><h1>Sumário</h1><ol>'+''.join(tocitems)+'</ol></nav><nav epub:type="landmarks" hidden="hidden"><ol><li><a epub:type="bodymatter" href="ch1.xhtml">Início da história</a></li></ol></nav>')
bookid='urn:uuid:'+str(uuid.uuid5(uuid.NAMESPACE_URL,'EnquantoHouverJardim-2026-10-08'))
ncxpoints=''.join(f'<navPoint id="nav{i}" playOrder="{i}"><navLabel><text>{esc(h)}</text></navLabel><content src="ch{i}.xhtml"/></navPoint>' for i,(h,_) in enumerate(chapters,1))
files['OEBPS/toc.ncx']=f'''<?xml version="1.0" encoding="utf-8"?><ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1"><head><meta name="dtb:uid" content="{bookid}"/></head><docTitle><text>{TITLE}</text></docTitle><navMap>{ncxpoints}</navMap></ncx>'''
manifest='''<item id="cover-image" href="cover.png" media-type="image/png" properties="cover-image"/><item id="cover" href="cover.xhtml" media-type="application/xhtml+xml"/><item id="title" href="title.xhtml" media-type="application/xhtml+xml"/><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/><item id="css" href="style.css" media-type="text/css"/><item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/><item id="back" href="back.xhtml" media-type="application/xhtml+xml"/>'''+''.join(f'<item id="ch{i}" href="ch{i}.xhtml" media-type="application/xhtml+xml"/>' for i in range(1,7))
spine='<itemref idref="cover" linear="no"/><itemref idref="title"/><itemref idref="nav"/>'+''.join(f'<itemref idref="ch{i}"/>' for i in range(1,7))+'<itemref idref="back"/>'
files['OEBPS/content.opf']=f'''<?xml version="1.0" encoding="utf-8"?><package xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid" version="3.0" xml:lang="pt-BR"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="bookid">{bookid}</dc:identifier><dc:title>{TITLE}</dc:title><dc:language>pt-BR</dc:language><dc:description>Romance curto em seis capítulos sobre Augusto e Helena, em Porto Alegre.</dc:description><meta property="dcterms:modified">2026-10-09T00:00:00Z</meta><meta name="cover" content="cover-image"/></metadata><manifest>{manifest}</manifest><spine toc="ncx">{spine}</spine></package>'''
files['META-INF/container.xml']='''<?xml version="1.0" encoding="utf-8"?><container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>'''
with zipfile.ZipFile(ROOT/'Enquanto Houver Jardim.epub','w') as z:
    z.writestr('mimetype','application/epub+zip',compress_type=zipfile.ZIP_STORED)
    for name,content in files.items(): z.writestr(name,content.encode('utf-8'),compress_type=zipfile.ZIP_DEFLATED)
    z.write(ROOT/'capa.png','OEBPS/cover.png',compress_type=zipfile.ZIP_DEFLATED)

# Integridade textual: mesmos parágrafos e mesma ordem, sem depender de contagens apenas.
with zipfile.ZipFile(ROOT/'Enquanto Houver Jardim.epub') as z:
    assert z.testzip() is None
    assert z.infolist()[0].filename=='mimetype' and z.infolist()[0].compress_type==0
    for name in z.namelist():
        if name.endswith(('.xml','.xhtml','.opf','.ncx')): ET.fromstring(z.read(name))
    for i,(_,paragraphs) in enumerate(chapters,1):
        tree=ET.fromstring(z.read(f'OEBPS/ch{i}.xhtml'))
        actual=[''.join(p.itertext()) for p in tree.findall('.//{http://www.w3.org/1999/xhtml}p')]
        assert actual==paragraphs, f'Divergencia no capitulo {i}'
    for name in z.namelist():
        if name.endswith('.xhtml'):
            tree=ET.fromstring(z.read(name))
            for el in tree.iter():
                for attr in ('href','src'):
                    ref=el.get(attr)
                    if ref and not ref.startswith(('http:', 'https:', '#')):
                        target=posixpath.normpath(posixpath.join(posixpath.dirname(name),ref.split('#')[0]))
                        assert target in z.namelist(), target
reader=PdfReader(ROOT/'Enquanto Houver Jardim.pdf')
pdftext='\n'.join(re.sub(r'^\s*\d+\s*\n','',p.extract_text() or '') for p in reader.pages)
normalize=lambda s:re.sub(r'\s+','',s)
all_normal=normalize(pdftext)
for i,(heading,paragraphs) in enumerate(chapters,1):
    # Título se divide visualmente em rótulo e nome no PDF.
    for p in paragraphs:
        assert normalize(p) in all_normal, f'Paragrafo ausente do PDF no capitulo {i}: {p[:70]}'
words=len(re.findall(r'\b\w+\b','\n'.join('\n'.join(p) for _,p in chapters)))
report={'titulo':TITLE,'capitulos':6,'palavras_da_narrativa':words,'minutos_a_235_palavras_por_minuto':round(words/235,1),'faixa_a_200_250_palavras_por_minuto':[round(words/250,1),round(words/200,1)],'paginas_pdf':len(reader.pages),'aberturas_pdf_paginas_fisicas':[doc.chapter_pages[f'ch{i}']+1 for i in range(1,7)],'epub_zip_xml_links_paragrafos':'PASSOU','pdf_todos_paragrafos_presentes':'PASSOU','epubcheck':'NAO EXECUTADO','kindle_previewer':'NAO EXECUTADO','autoria':'Nao informada; omitida','backup_publico':'PENDENTE: GitHub CLI informa credencial invalida'}
(ROOT/'validacao.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
