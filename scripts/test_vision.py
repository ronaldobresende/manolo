import os
import sys
import base64
import argparse
import json
from datetime import datetime

# Adiciona o diretório raiz ao path para podermos importar 'core'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.clients import get_openai_client
from core.schemas import LLMChecklistResponse
from core.config import settings

def encode_image(image_path: str) -> str:
    """Lê a imagem local e converte para base64"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def test_vision(image_path: str, contexto_texto: str = ""):
    if not os.path.exists(image_path):
        print(f"Erro: Arquivo não encontrado em {image_path}")
        return
        
    print(f"\nCarregando imagem: {image_path}")
    base64_image = encode_image(image_path)
    
    # Prepara o prompt (mesmo usado no agent.py)
    data_hoje = datetime.now().strftime("%Y-%m-%d")
    hora_atual = datetime.now().strftime("%H:%M")
    
    prompt_extracao = f"""Você é um extrator de dados de rotina infantil.
Analise a imagem enviada (e o texto se houver) para extrair as informações para o checklist diário da criança (Bernardo).
A data de hoje é {data_hoje} e o horário atual é {hora_atual}.

REGRAS DE VISÃO E CONTEXTO:
1. FOTO IRRELEVANTE: Se a foto não tiver NENHUMA relação com rotina infantil (ex: paisagens, memes, planilhas), retorne `contem_dados = false`.
2. MÚLTIPLAS CRIANÇAS: Se houver várias crianças na foto com comidas ou ações diferentes e não for possível identificar quem é o foco, retorne `data_ambigua = true` para que o bot peça esclarecimento.
3. ALIMENTOS (TRADUÇÃO): Mapeie comidas para o Português do Brasil de forma culturalmente correta. Não use termos estrangeiros como "dumplings" ou "noodles", prefira "pastel/guioza" ou "macarrão".
4. DEDUÇÃO SEGURA: Tente deduzir os campos de rotina visualmente (ex: se for um prato de comida, descreva os alimentos). Não invente informações que não estão claras na foto.
5. DATAS: Sempre que a data não for EXPLÍCITA, retorne data_referencia_iso = null (assumiremos hoje)."""

    client = get_openai_client()
    
    # Vamos usar o modelo padrão que, no nosso novo design SOTA, 
    # deve ser o gpt-4o (que suporta imagem e structured outputs)
    modelo = getattr(settings, 'LLM_MODEL_DEFAULT', "gpt-4o")
    
    print(f"\nEnviando para o LLM ({modelo} - Vision + Structured Outputs)...")
    try:
        # A API Vision funciona passando o tipo 'image_url' no array de conteúdo
        content = [{"type": "text", "text": prompt_extracao}]
        
        if contexto_texto:
            content.append({"type": "text", "text": f"Texto enviado junto com a foto: {contexto_texto}"})
            
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}",
                "detail": "high"
            }
        })

        # Utilizando Structured Outputs (beta.chat.completions.parse)
        response = client.beta.chat.completions.parse(
            model=modelo, 
            response_format=LLMChecklistResponse,
            messages=[
                {"role": "user", "content": content}
            ],
            temperature=0,
        )
        
        resultado = response.choices[0].message.parsed
        
        print("\n" + "="*50)
        print("RESULTADO EXTRAÍDO (JSON Pydantic)")
        print("="*50)
        print(resultado.model_dump_json(indent=2))
        print("="*50)
        
    except Exception as e:
        print(f"\nErro ao chamar a API: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Testar extração de checklist via Imagem (Vision)")
    parser.add_argument("image_path", help="Caminho relativo ou absoluto da imagem")
    parser.add_argument("--texto", "-t", default="", help="Contexto em texto (como se fosse a legenda da foto no WhatsApp)")
    
    args = parser.parse_args()
    test_vision(args.image_path, args.texto)
