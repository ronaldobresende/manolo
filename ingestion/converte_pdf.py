# Instale caso não tenha: pip install reportlab
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

def gerar_pdf_nativo():
    pdf_filename = "relatorio_fonoaudiologico_bernardo.pdf"
    doc = SimpleDocTemplate(
        pdf_filename, 
        pagesize=letter,
        rightMargin=40, leftMargin=40,
        topMargin=40, bottomMargin=40
    )
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'TitleStyle', parent=styles['Heading1'],
        fontName='Helvetica-Bold', fontSize=14, leading=18,
        alignment=TA_CENTER, spaceAfter=12
    )
    
    h2_style = ParagraphStyle(
        'H2Style', parent=styles['Heading2'],
        fontName='Helvetica-Bold', fontSize=11, leading=15,
        spaceBefore=10, spaceAfter=4
    )
    
    body_style = ParagraphStyle(
        'BodyStyle', parent=styles['Normal'],
        fontName='Helvetica', fontSize=9, leading=13,
        alignment=TA_JUSTIFY, spaceAfter=5
    )
    
    bullet_style = ParagraphStyle(
        'BulletStyle', parent=styles['Normal'],
        fontName='Helvetica', fontSize=9, leading=13,
        leftIndent=15, spaceAfter=3
    )

    # Cabeçalho
    story.append(Paragraph("INSTITUTO NINHO — ACOLHER PARA CRESCER", title_style))
    story.append(Paragraph("RELATÓRIO FONOAUDIOLÓGICO", title_style))
    story.append(Paragraph("Mogi das Cruzes, 19 de setembro de 2025", body_style))
    story.append(Spacer(1, 8))
    
    # Identificação
    story.append(Paragraph("<b>Nome:</b> Bernardo Suzuki Andrade Resende", body_style))
    story.append(Paragraph("<b>Responsável:</b> Ronaldo Barbosa Resende", body_style))
    story.append(Paragraph("<b>D.N:</b> 14/12/2023", body_style))
    story.append(Paragraph("<b>Hipótese Diagnóstica Fonoaudiológica (HDF):</b> Transtorno de Linguagem expressiva e receptiva.", body_style))
    story.append(Paragraph("<b>Encaminhamento:</b> Dra Erika", body_style))
    story.append(Paragraph("<b>Queixa:</b> \"Meu filho ainda não fala.\" (sic-mãe e pai).", body_style))
    story.append(Spacer(1, 8))
    
    # Anamnese
    story.append(Paragraph("Anamnese", h2_style))
    story.append(Paragraph("Foi realizado anamnese no dia 22/08/2025, durante a anamnese os pais relatam que a gravidez foi de alto risco devido a idade da mãe na gestação. Bernardo Suzuki nasceu com 38 semanas, 3.730kg de parto cesariana. Foi relatado que o mesmo dorme bem e com facilidade, foi amamentado até os 8 meses.", body_style))
    story.append(Paragraph("Responsáveis relatam que na maternidade foi realizado o teste da orelhinha (normal), teste da linguinha (alterado), foi realizado frenectomia. Quanto ao desenvolvimento psicomotor Bernardo começou a engatinhar por volta dos 7 meses, andar com 1A2M, balbuciar aos 5 meses.", body_style))
    story.append(Paragraph("Mãe e pai relatam que o meio de comunicação de Bernardo é puxando a mão ou aponta o que deseja e que não possui convivência com crianças, somente adultos.", body_style))
    story.append(Spacer(1, 8))
    
    # Achados Avaliativos
    story.append(Paragraph("Achados Avaliativos", h2_style))
    story.append(Paragraph("Foi utilizado protocolo PROC para realização da avaliação do sistema pragmático por meio de observação comportamental PROC (Zorzi e Hage, 2004), este protocolo observa as habilidades comunicativas da criança, que verificam a participação e o grau de desenvolvimento durante as suas trocas comunicativas. Sendo visto as seguintes:", body_style))
    
    story.append(Paragraph("• <b>Inicia a conversação/interação:</b> presente raramente, sem a presença de troca de turno (espera o final da solicitação verbal para dar resposta ao interlocutor) não participa da atividade ativamente. Paciente não apresenta resposta ao interlocutor.", bullet_style))
    story.append(Paragraph("• <b>Funções comunicativas:</b>", bullet_style))
    story.append(Paragraph("  1. O paciente não apresenta a função interativa (dar oi/tchau);", bullet_style))
    story.append(Paragraph("  2. Demonstra de forma as funções: não realiza solicitação instrumental de modo verbal e gestual (solicitação de objetos/dar objetos);", bullet_style))
    story.append(Paragraph("  3. Não realiza nomeação (nomeação espontânea de objetos);", bullet_style))
    story.append(Paragraph("  4. Apresenta frequentemente protesto (interrupção de uma ação indesejada);", bullet_style))
    story.append(Paragraph("  5. Não realiza informativa (comentários e informações espontâneas na interação);", bullet_style))
    story.append(Paragraph("  6. Não possui heurística (solicitação de informação ou permissão);", bullet_style))
    story.append(Paragraph("  7. Não realiza narrativa (presença de turnos narrativos).", bullet_style))
    
    story.append(Paragraph("• <b>Meios comunicativos:</b> a criança utiliza gestos não simbólicos elementares (pegar na mão e levar, puxar, cutucar). Utiliza vocalização não articuladas e articuladas com entonação da língua (jargão), sendo que o paciente possui nível de contextualização da linguagem na situação imediata e concreta.", body_style))
    story.append(Paragraph("• <b>Compreensão verbal:</b> responde assistematicamente.", body_style))
    story.append(Paragraph("• <b>Aspectos cognitivos:</b> observo que Bernardo atua sobre os objetos de forma repetitiva ou estereotipada (põe tudo na boca, joga), explora os objetos por meio de poucas ações.", body_style))
    story.append(Paragraph("• <b>Nível de desenvolvimento do simbolismo:</b> Bernardo não apresenta condutas simbólicas, somente sensório-motoras, faz uso convencional dos objetos.", body_style))
    story.append(Spacer(1, 8))
    
    # Evidências
    story.append(Paragraph("Desta Forma Evidencia-se:", h2_style))
    story.append(Paragraph("• <b>Características gerais das habilidades comunicativas:</b> Comunicação intencional com funções primárias, restrita em participação dialógica por meios não verbais e não simbólicos.", bullet_style))
    story.append(Paragraph("• <b>Características gerais da compreensão da linguagem oral:</b> Não demonstra compreensão da linguagem oral.", bullet_style))
    story.append(Paragraph("• <b>Características gerais de imitação sonora:</b> Não realizou.", bullet_style))
    story.append(Paragraph("• <b>Características gerais da imitação gestual:</b> Não realizou.", bullet_style))
    story.append(Paragraph("• <b>Características gerais do desenvolvimento cognitivo:</b> Sensório motor - fases avançadas.", bullet_style))
    story.append(Spacer(1, 8))
    
    # Planejamento
    story.append(Paragraph("Planejamento Terapêutico e Metas", h2_style))
    story.append(Paragraph("As sessões de terapia fonoaudiológica terão como meta melhorar a linguagem expressiva e receptiva de Bernardo, trabalhando assim:", body_style))
    story.append(Paragraph("- Aprimorar a pragmática.", bullet_style))
    story.append(Paragraph("- Maturidade do brincar simbólico.", bullet_style))
    story.append(Paragraph("- Melhora da linguagem receptiva (Trabalhando verbos de ação. Exemplo: pegar, chutar, jogar).", bullet_style))
    story.append(Paragraph("- Ampliação da linguagem receptiva e expressiva (Trabalhando partes do corpo humano para que reconheça e faça nomeação. Exemplo: pé, mão, barriga).", bullet_style))
    story.append(Paragraph("- Trabalho com onomatopeias para favorecer a imitação verbal, emissão dos sons bilabiais (som da vaca 'muuu', som do pintinho 'piuu-piuu').", bullet_style))
    story.append(Paragraph("- Produção de monossílabos e dissílabos: ai, da, aju para ajuda, pé, esse, mão, mais.", bullet_style))
    story.append(Spacer(1, 8))
    
    # Recomendações
    story.append(Paragraph("Recomendações e Condutas", h2_style))
    story.append(Paragraph("Recomenda-se intervenção fonoaudiológica 2x na semana para a melhora da linguagem receptiva/expressiva pois o vocabulário está aquém do esperado para idade cronológica.", body_style))
    story.append(Paragraph("Ressalto a necessidade da avaliação psicológica, avaliação neuropediátrica devido aos aspectos cognitivos e motores do desenvolvimento infantil.", body_style))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("<b>Pamella P.S Costa</b><br/>CRFa 2-12556-5 SP<br/>Fonoaudióloga", body_style))
    
    doc.build(story)

if __name__ == '__main__':
    gerar_pdf_nativo()