"""
Test: İki farklı konu sırayla sorulduğunda ikinci cevabın konusu ikinci prompt olsun.

Doğrular:
1. Her run() çağrısında connector.call()'a giden user= parametresi o çağrının prompt'u.
2. İkinci run("Auth tasarla") ile çağrıldığında LLM'e giden ana mesaj "Auth tasarla" olur;
   context (session/knowledge) sadece system prompt'a eklenir, user mesajı değişmez.
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.agent_runtime import AgentRuntime
from core.llm_connector import LLMResponse


def _mock_connector_call(model, system, user, **kwargs):
    """LLM'e giden system ve user'ı kaydedip sahte cevap döndür."""
    return LLMResponse(
        text=f"[MOCK] user_prompt_was: {user[:80]}...",
        model=model,
        provider="openai",
        prompt_tokens=len(system) + len(user),
        completion_tokens=50,
        total_tokens=len(system) + len(user) + 50,
        duration_ms=100.0,
    )


def test_second_run_receives_second_prompt_as_user_message():
    """
    Simülasyon: Önce 'Todo API' sonra 'Auth sistemi' sorulduğunda,
    ikinci çağrıda connector.call()'a giden user= ikinci prompt olmalı.
    Closer kullanıyoruz (memory_enabled=False) ki DB/embedding tetiklenmesin.
    """
    runtime = AgentRuntime()
    call_args_list = []

    def capture_call(model, system, user, **kwargs):
        call_args_list.append({"user": user})
        return _mock_connector_call(model=model, system=system, user=user, **kwargs)

    fake_log = MagicMock()
    fake_log.name = "test.json"
    with patch.object(runtime.connector, "call", side_effect=capture_call):
        with patch("core.agent_runtime.write_json", return_value=fake_log):
            runtime.run(
                agent="closer",
                prompt="Todo uygulaması için REST API tasarla.",
                session_id="test-session-1",
                mock_mode=False,
            )
            runtime.run(
                agent="closer",
                prompt="JWT ile kimlik doğrulama sistemi tasarla.",
                session_id="test-session-1",
                mock_mode=False,
            )

    assert len(call_args_list) >= 2
    assert call_args_list[0]["user"] == "Todo uygulaması için REST API tasarla."
    assert call_args_list[1]["user"] == "JWT ile kimlik doğrulama sistemi tasarla."


def test_second_run_user_message_is_not_first_prompt():
    """İkinci run'da user= birinci prompt ile karışmamalı (closer, memory yok)."""
    runtime = AgentRuntime()
    call_users = []

    def capture_user(model, system, user, **kwargs):
        call_users.append(user)
        return _mock_connector_call(model=model, system=system, user=user, **kwargs)

    fake_log = MagicMock()
    fake_log.name = "x.json"
    with patch.object(runtime.connector, "call", side_effect=capture_user):
        with patch("core.agent_runtime.write_json", return_value=fake_log):
            runtime.run(agent="closer", prompt="Birinci konu: cache stratejisi tasarla.", session_id="s1", mock_mode=False)
            runtime.run(agent="closer", prompt="İkinci konu: rate limiter tasarla.", session_id="s1", mock_mode=False)

    assert call_users[1] == "İkinci konu: rate limiter tasarla."
    assert call_users[1] != "Birinci konu: cache stratejisi tasarla."
