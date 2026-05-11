import os
import traceback

# If user set GEMINI_API_KEY in .env, propagate it to GOOGLE_API_KEY which
# the google client library also checks for (avoids needing ADC).
if os.environ.get('GEMINI_API_KEY') and not os.environ.get('GOOGLE_API_KEY'):
    os.environ['GOOGLE_API_KEY'] = os.environ['GEMINI_API_KEY']

try:
    import google.generativeai as genai
except Exception as e:
    print('IMPORT_ERROR', type(e).__name__, e)
    raise

api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
if not api_key:
    print('NO_API_KEY: set GEMINI_API_KEY or GOOGLE_API_KEY in the environment')
else:
    genai.configure(api_key=api_key)

models = [
    'gemini-2.0-flash',
    'models/gemini-3.1-flash-lite',
    'models/gemini-3-flash',
    'models/gemini-2.5-flash'
]

for m in models:
    try:
        resp = genai.GenerativeModel(m).generate_content(
            'Responde solo: OK', generation_config={'max_output_tokens': 5}
        )
        text = getattr(resp, 'text', None)
        if not text and hasattr(resp, 'candidates'):
            # older client shapes
            text = ' '.join(getattr(c, 'content', '') for c in resp.candidates)
        print(m, '=> OK:', (text or str(resp))[:400])
    except Exception as e:
        print(m, '=> ERROR:', type(e).__name__, e)
        traceback.print_exc()
