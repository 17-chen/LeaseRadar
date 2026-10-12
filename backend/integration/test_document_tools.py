"""Real Poppler integration using a synthetic byte fixture; no source-network data."""
from app.document_worker import extract

def synthetic_pdf():
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 400 300] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    content=b'BT /F1 16 Tf 20 250 Td (Synthetic rental evidence 120000) Tj ET'
    objects.append(b'<< /Length '+str(len(content)).encode()+b' >>\nstream\n'+content+b'\nendstream')
    output=bytearray(b'%PDF-1.4\n');offsets=[0]
    for i,obj in enumerate(objects,1):offsets.append(len(output));output.extend(str(i).encode()+b' 0 obj\n'+obj+b'\nendobj\n')
    xref=len(output);output.extend(b'xref\n0 6\n0000000000 65535 f \n')
    for offset in offsets[1:]:output.extend(f'{offset:010d} 00000 n \n'.encode())
    output.extend(f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
    return bytes(output)

def test_real_pdf_text_preserves_page_and_evidence():
    result=extract(synthetic_pdf(),'pdf')
    assert len(result)==1 and result[0]['page']==1 and result[0]['method']=='pdf_text'
    assert 'Synthetic rental evidence 120000' in result[0]['text']
