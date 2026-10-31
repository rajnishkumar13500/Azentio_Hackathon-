import os
from PIL import Image, ImageDraw, ImageFont

DOC_DIR = "/Users/meherchand/.gemini/antigravity/scratch/claims-ingestion/sample_data/documents"
os.makedirs(DOC_DIR, exist_ok=True)

def generate_invoice_image():
    img_path = os.path.join(DOC_DIR, "hospital_bill.png")
    # Create white canvas
    img = Image.new("RGB", (800, 1000), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Simple clean rendering
    draw.text((50, 40), "CITY CARE HOSPITAL & RESEARCH CENTRE", fill=(0, 0, 0))
    draw.text((50, 70), "123 Medical Enclave, Health City, Bangalore", fill=(50, 50, 50))
    draw.line([(50, 100), (750, 100)], fill=(0, 0, 0), width=2)

    draw.text((50, 130), "INPATIENT FINAL TAX INVOICE", fill=(0, 0, 0))
    draw.text((50, 170), "Invoice No: INV-DOC-8088", fill=(0, 0, 0))
    draw.text((50, 200), "Date: 2024-03-18", fill=(0, 0, 0))
    draw.text((450, 170), "Claim No: CLM-1001", fill=(0, 0, 0))
    draw.text((450, 200), "Patient: Aarav Sharma", fill=(0, 0, 0))

    draw.line([(50, 240), (750, 240)], fill=(100, 100, 100), width=1)
    draw.text((50, 260), "Description", fill=(0, 0, 0))
    draw.text((400, 260), "Qty", fill=(0, 0, 0))
    draw.text((500, 260), "Rate", fill=(0, 0, 0))
    draw.text((650, 260), "Amount", fill=(0, 0, 0))
    draw.line([(50, 290), (750, 290)], fill=(100, 100, 100), width=1)

    items = [
        ("ICU Charges 2 Days", "2", "10000.00", "20000.00"),
        ("Diagnostic Laboratory Profile", "1", "5000.00", "5000.00"),
        ("Surgical Procedure Assistance", "1", "20000.00", "20000.00"),
    ]

    y = 310
    for desc, qty, rate, amt in items:
        draw.text((50, y), desc, fill=(0, 0, 0))
        draw.text((410, y), qty, fill=(0, 0, 0))
        draw.text((500, y), rate, fill=(0, 0, 0))
        draw.text((650, y), amt, fill=(0, 0, 0))
        y += 40

    draw.line([(50, y + 20), (750, y + 20)], fill=(0, 0, 0), width=2)
    draw.text((450, y + 40), "Total Amount: 45000.00", fill=(0, 0, 0))
    draw.text((50, y + 90), "Authorized Signatory: Dr. S. Rao, MD", fill=(50, 50, 50))

    img.save(img_path)
    print(f"Generated sample image at: {img_path}")

    # Also save as PDF
    pdf_path = os.path.join(DOC_DIR, "hospital_bill.pdf")
    img.save(pdf_path, "PDF", resolution=100.0)
    print(f"Generated sample PDF at: {pdf_path}")

if __name__ == "__main__":
    generate_invoice_image()
