

import openai
from typing import Optional

def rewrite_query(query: str, history: Optional[list] = None) -> str:
    """
    사용자의 질문과 대화 기록을 바탕으로, 검색에 더 용이하도록
    명확하고 표준화된 질문으로 재구성합니다.
    """
    history_str = "\n".join([f"  - {msg['role']}: {msg['content']}" for msg in history]) if history else "  - 이전 대화 없음"
    system_prompt = f"""
    # Mission
    Your mission is to rewrite the user's question into a concise and standardized query optimal for semantic search, based on the conversation history.
    
    # Rules
    1.  **Conciseness**: Remove fillers and focus on core keywords.
    2.  **Standardization**: Convert colloquialisms to standard terms (e.g., '얼마야?' -> '금리', '돼?' -> '조건', '필요해?' -> '필요서류').
    3.  **Contextualization**: If a specific product was discussed in the history, you MUST incorporate it into the rewritten query.
    
    # Examples
    - User Input: '직장 안 다니는데 신용대출 가능?'
    - Rewritten Query: '무직자 신용대출 조건'
    
    - User Input: '그거 이자는 어떻게 돼?'
    - Conversation History:
      - user: 우리 네이버 스마트스토어 대출 알려줘
      - assistant: 네, 우리 네이버 스마트스토어 대출에 대해 안내해 드릴게요.
    - Rewritten Query: '우리 네이버 스마트스토어 대출 금리'

    # Conversation History
    {history_str}
    """

    user_prompt = f"""
    # User Input
    - {query}
    # Rewritten Query
    """

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini", # gpt-3.5-turbo 보다 이 작업에 더 적합할 수 있습니다.
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0,
            max_tokens=100
        )
        rewritten_query = response.choices[0].message.content.strip()
        print(f"원래 질문: '{query}' -> 재구성된 질문: '{rewritten_query}'")
        return rewritten_query
    except Exception as e:
        print(f"질문 재구성 중 오류 발생: {e}")
        return query