async def run(state, *, code):
    openai = _lazy_import('openai')
    response = await state['__llm'].complete(
        prompt=state['__prompt'],
        max_tokens=150
    )
    summary, contextual_insights = response['choices'][0]['text'].strip().split('\n', 1)
    return {'summary': summary.strip(), 'contextual_insights': contextual_insights.strip()}