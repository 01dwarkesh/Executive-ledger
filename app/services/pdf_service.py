from jinja2 import Environment, BaseLoader
from weasyprint import HTML


TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{font-family:Arial,sans-serif;font-size:13px;color:#111;padding:48px}
  .header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:40px}
  .brand{font-size:22px;font-weight:700;color:#185FA5}
  .brand-sub{font-size:11px;color:#6b7280;margin-top:3px}
  .qmeta{text-align:right}
  .qnum{font-size:20px;font-weight:700}
  .qver{font-size:12px;color:#6b7280;margin-top:2px}
  .badge{display:inline-block;margin-top:6px;padding:3px 12px;border-radius:20px;font-size:11px;font-weight:600;background:#dbeafe;color:#1e40af}
  .section{margin-bottom:28px}
  .sec-title{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#9ca3af;padding-bottom:6px;border-bottom:1px solid #f3f4f6;margin-bottom:12px}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:10px 24px}
  .fl{font-size:10px;color:#9ca3af;margin-bottom:2px}
  .fv{font-size:13px;color:#111}
  table{width:100%;border-collapse:collapse}
  th{background:#f9fafb;padding:9px 12px;font-size:10px;text-transform:uppercase;letter-spacing:.05em;color:#6b7280;text-align:left;border-bottom:2px solid #e5e7eb}
  td{padding:11px 12px;border-bottom:1px solid #f3f4f6;vertical-align:middle}
  tr:last-child td{border-bottom:none}
  .img-cell img{width:72px;height:54px;object-fit:contain;border:1px solid #e5e7eb;border-radius:4px}
  .img-cell .no-img{width:72px;height:54px;background:#f9fafb;border:1px solid #e5e7eb;border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:9px;color:#9ca3af}
  .num{text-align:right}
  .totals{display:flex;justify-content:flex-end;margin-top:16px}
  .totals table{width:260px}
  .totals td{padding:5px 10px;border:none;font-size:13px}
  .totals .lbl{color:#6b7280}
  .totals .grand{font-size:16px;font-weight:700;border-top:2px solid #111;padding-top:8px}
  .notes-box{background:#f9fafb;border:1px solid #e5e7eb;border-radius:6px;padding:14px;font-size:13px;line-height:1.6;white-space:pre-wrap}
  .footer{margin-top:48px;text-align:center;font-size:10px;color:#9ca3af;border-top:1px solid #e5e7eb;padding-top:14px}
  .row-num{color:#9ca3af;font-size:11px}
  .pname{font-weight:600;font-size:13px}
  .pdesc{font-size:11px;color:#6b7280;margin-top:2px}
</style>
</head>
<body>

<div class="header">
  <div>
    <div class="brand">Executive Ledger</div>
    <div class="brand-sub">Internal Quoting Tool</div>
  </div>
  <div class="qmeta">
    <div class="qnum">{{ quote.quote_number }}</div>
    <div class="qver">Version {{ quote.version }}</div>
    <div class="badge">{{ quote.status }}</div>
  </div>
</div>

<div class="section">
  <div class="sec-title">Client Information</div>
  <div class="grid2">
    <div><div class="fl">Company</div><div class="fv">{{ quote.client.company_name }}</div></div>
    <div><div class="fl">Contact</div><div class="fv">{{ quote.client.contact_name }}</div></div>
    <div><div class="fl">Email</div><div class="fv">{{ quote.client.email }}</div></div>
    <div><div class="fl">Phone</div><div class="fv">{{ quote.client.phone or "—" }}</div></div>
  </div>
</div>

<div class="section">
  <div class="sec-title">Quote Details</div>
  <div class="grid2">
    <div><div class="fl">Quote Number</div><div class="fv">{{ quote.quote_number }}</div></div>
    <div><div class="fl">Issue Date</div><div class="fv">{{ quote.created_at.strftime('%b %d, %Y') }}</div></div>
    <div><div class="fl">Valid Until</div><div class="fv">{{ quote.validity_date.strftime('%b %d, %Y') if quote.validity_date else "—" }}</div></div>
    <div><div class="fl">Currency</div><div class="fv">{{ quote.currency }}</div></div>
  </div>
</div>

<div class="section">
  <div class="sec-title">Line Items</div>
  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>Product</th>
        <th>Preview</th>
        <th>Size / Cap.</th>
        <th>Color</th>
        <th>Lead Time</th>
        <th class="num">Qty</th>
        <th class="num">Unit Price</th>
        <th class="num">Discount</th>
        <th class="num">Amount</th>
      </tr>
    </thead>
    <tbody>
      {% for item in quote.items %}
      <tr>
        <td class="row-num">{{ "%02d"|format(loop.index) }}</td>
        <td>
          <div class="pname">{{ item.product_name }}</div>
          {% if item.description %}<div class="pdesc">{{ item.description }}</div>{% endif %}
        </td>
        <td class="img-cell">
          {% if item.mockup_url %}
            <img src="{{ item.mockup_url }}" />
          {% else %}
            <div class="no-img">No preview</div>
          {% endif %}
        </td>
        <td>{{ item.size_capacity or "—" }}</td>
        <td>{{ item.color or "—" }}</td>
        <td>{{ item.lead_time or "—" }}</td>
        <td class="num">{{ item.quantity }}</td>
        <td class="num">{{ quote.currency }} {{ "%.2f"|format(item.unit_price) }}</td>
        <td class="num">{{ item.discount_pct }}%</td>
        <td class="num" style="font-weight:600">{{ quote.currency }} {{ "%.2f"|format(item.final_price or 0) }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>

  <div class="totals">
    <table>
      <tr><td class="lbl">Subtotal</td><td class="num">{{ quote.currency }} {{ "%.2f"|format(subtotal) }}</td></tr>
      <tr><td class="lbl">Tax ({{ quote.tax_pct }}%)</td><td class="num">{{ quote.currency }} {{ "%.2f"|format(tax) }}</td></tr>
      {% if quote.adjustment != 0 %}
      <tr><td class="lbl">Adjustment</td><td class="num">{{ quote.currency }} {{ "%.2f"|format(quote.adjustment) }}</td></tr>
      {% endif %}
      <tr class="grand"><td><strong>Grand Total Due</strong></td><td class="num"><strong>{{ quote.currency }} {{ "%.2f"|format(grand_total) }}</strong></td></tr>
    </table>
  </div>
</div>

{% if quote.notes %}
<div class="section">
  <div class="sec-title">Notes</div>
  <div class="notes-box">{{ quote.notes }}</div>
</div>
{% endif %}

{% if quote.terms %}
<div class="section">
  <div class="sec-title">Terms &amp; Conditions</div>
  <div class="notes-box">{{ quote.terms }}</div>
</div>
{% endif %}

<div class="footer">
  Executive Ledger &nbsp;|&nbsp; {{ quote.quote_number }} v{{ quote.version }} &nbsp;|&nbsp; Generated {{ quote.created_at.strftime('%Y-%m-%d') }}
</div>
</body>
</html>
"""


def generate_pdf(quote) -> bytes:
    subtotal = sum(item.final_price or 0 for item in quote.items)
    tax = round(subtotal * (quote.tax_pct / 100), 2)
    grand_total = round(subtotal + tax + (quote.adjustment or 0), 2)

    env = Environment(loader=BaseLoader())
    html_str = env.from_string(TEMPLATE).render(
        quote=quote,
        subtotal=subtotal,
        tax=tax,
        grand_total=grand_total,
    )
    return HTML(string=html_str).write_pdf()