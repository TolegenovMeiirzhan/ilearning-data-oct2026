import io
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import get_data_path
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether
from xml.sax.saxutils import escape


def create_report(report):
    font = Path(get_data_path()) / 'fonts' / 'ttf' / 'DejaVuSans.ttf'
    pdfmetrics.registerFont(TTFont('ReportSans', str(font)))
    styles = getSampleStyleSheet()
    for name in ['Normal', 'Title', 'Heading1', 'Heading2']:
        styles[name].fontName = 'ReportSans'
    styles.add(ParagraphStyle('SmallReport', fontName='ReportSans', fontSize=8, leading=11))
    stream = io.BytesIO()
    document = SimpleDocTemplate(stream, pagesize=(21 * cm, 29.7 * cm), rightMargin=1.6 * cm, leftMargin=1.6 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    story = [Paragraph('Mine production report', styles['Title'])]
    story.append(Paragraph(f"{report['dates'][0]} to {report['dates'][-1]}", styles['Normal']))
    story.append(Spacer(1, 0.3 * cm))
    parameters = report['parameters']
    configuration = f"IQR factor: {parameters['iqr']}; z-score threshold: {parameters['z']}; previous observations: {parameters['window']}; moving gap: {parameters['moving_percent']}%; Grubbs alpha: {parameters['alpha']}; polynomial degree: {parameters['degree']}."
    story.append(Paragraph(escape(configuration), styles['SmallReport']))
    for index, series in enumerate(report['series']):
        if index:
            story.append(PageBreak())
        story.append(Paragraph(escape(series['name']), styles['Heading1']))
        rows = [['Metric', 'Value'], ['Observations', str(series['count'])]]
        rows += [[key.replace('_', ' ').title(), f'{series[key]:,.2f}'] for key in ['total', 'mean', 'standard_deviation', 'median', 'iqr']]
        table = Table(rows, colWidths=[9 * cm, 8 * cm], hAlign='LEFT')
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'ReportSans'), ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#254A60')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F1F5F8')]),
            ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
        ]))
        story.append(table)
        figure, axis = plt.subplots(figsize=(8.5, 3.2))
        axis.plot(report['dates'], series['values'], color='#315681', linewidth=1.4, label='Output')
        if series['trend'] is not None:
            axis.plot(report['dates'], series['trend'], color='#B47829', linestyle='--', label='Polynomial trend')
        if series['anomalies']:
            positions = [item['index'] for item in series['anomalies']]
            axis.scatter(positions, [series['values'][position] for position in positions], color='#B83240', s=15, label='Outlier')
        step = max(1, len(report['dates']) // 6)
        axis.set_xticks(list(range(0, len(report['dates']), step)))
        axis.set_xticklabels(report['dates'][::step], rotation=25, ha='right')
        axis.set_ylabel('Tonnes / day')
        axis.grid(alpha=0.2)
        axis.legend(fontsize=8)
        figure.tight_layout()
        image_stream = io.BytesIO()
        figure.savefig(image_stream, format='png', dpi=150)
        plt.close(figure)
        image_stream.seek(0)
        story.append(Image(image_stream, width=17.5 * cm, height=6.6 * cm))
        story.append(Paragraph(f"Detected anomalous observations: {len(series['anomalies'])}", styles['Heading2']))
        if not series['anomalies']:
            story.append(Paragraph('No observations exceeded the selected thresholds.', styles['Normal']))
        for anomaly in series['anomalies']:
            story.append(KeepTogether([
                Paragraph(escape(f"{anomaly['date']}: {anomaly['kind']}"), styles['Heading2']),
                Paragraph(escape(f"Output: {anomaly['value']:,.2f} tonnes. Tests: {', '.join(anomaly['tests'])}."), styles['Normal']),
            ]))
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph(escape(report['notes']['moving_average']), styles['SmallReport']))
        story.append(Paragraph(escape(report['notes']['grubbs']), styles['SmallReport']))
    def footer(canvas, doc):
        canvas.setFont('ReportSans', 8)
        canvas.setFillColor(colors.HexColor('#667788'))
        canvas.drawString(1.6 * cm, 0.8 * cm, 'Weyland-Yutani | Generated analytics')
        canvas.drawRightString(19.4 * cm, 0.8 * cm, str(doc.page))
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return stream.getvalue()
