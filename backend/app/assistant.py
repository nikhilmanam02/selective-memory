from app.models import AnswerResult


def answer(llm, message, zone, allowed, withheld_counts, history):
    result = llm.answer(message, zone, allowed, withheld_counts, history)
    allowed_ids = {memory["id"] for memory in allowed}
    safe_ids = [memory_id for memory_id in result.used_memory_ids if memory_id in allowed_ids]
    return AnswerResult(text=result.text, used_memory_ids=safe_ids)
