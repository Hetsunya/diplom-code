"""Integration-style tests for `transcribe_and_emit_text_analysis`."""

from __future__ import annotations

import json
import unittest
from unittest.mock import AsyncMock, Mock, patch

from gateway_config import ModuleCfg

from modules.text.transcription import transcribe_and_emit_text_analysis


class TestTranscribeAndEmit(unittest.IsolatedAsyncioTestCase):
    async def test_circuit_error_does_not_send(self) -> None:
        ws = AsyncMock()
        msg = {
            "session_id": 7,
            "participant_id": "u1",
            "timestamp": "2026-01-01T00:00:00Z",
            "payload": {"chunk_base64": "QQ=="},
        }
        mod = ModuleCfg(
            enabled=True,
            model="asr-v1",
            params={"speech_service_url": "http://127.0.0.1:9"},
        )
        with patch("modules.text.transcription.transcribe_audio_chunk") as tr:
            tr.return_value = {"_error": "circuit_open", "_circuit_open": True}
            await transcribe_and_emit_text_analysis(msg=msg, ws=ws, text_mod=mod, trace_id="trace-1")
        ws.send.assert_not_called()

    async def test_whisper_shape_emits_text_analysis(self) -> None:
        ws = AsyncMock()
        msg = {
            "session_id": 7,
            "participant_id": "u1",
            "timestamp": "2026-01-01T00:00:00Z",
            "payload": {"chunk_base64": "QQ=="},
        }
        mod = ModuleCfg(
            enabled=True,
            model="whisper-v1",
            params={"speech_service_url": "http://127.0.0.1:8090"},
        )
        with patch("modules.text.transcription.transcribe_audio_chunk") as tr:
            tr.return_value = {"text": "hello", "language": "en", "text_features": {}}
            with patch("modules.text.transcription.get_feature_store") as gfs:
                gfs.return_value.push = Mock()
                await transcribe_and_emit_text_analysis(msg=msg, ws=ws, text_mod=mod, trace_id="tid-2")
        ws.send.assert_called_once()
        raw = ws.send.call_args[0][0]
        body = json.loads(raw)
        self.assertEqual(body["type"], "text_analysis")
        pl = body["payload"]
        self.assertEqual(pl["module"], "text")
        self.assertEqual(pl["version"], "whisper-v1")
        self.assertEqual(pl["stage"], "partial")
        self.assertEqual(pl["trace_id"], "tid-2")
        self.assertEqual(pl["transcript_partial"], "hello")
        self.assertIn("sentiment", pl["text_features"])

    async def test_empty_transcript_skips_send(self) -> None:
        ws = AsyncMock()
        msg = {
            "session_id": 1,
            "participant_id": "u1",
            "timestamp": "2026-01-01T00:00:00Z",
            "payload": {},
        }
        mod = ModuleCfg(enabled=True, model="x", params={"speech_service_url": "http://localhost:1"})
        with patch("modules.text.transcription.transcribe_audio_chunk") as tr:
            tr.return_value = {
                "transcript_partial": "",
                "transcript_final": None,
                "language": "ru",
                "text_features": {},
            }
            await transcribe_and_emit_text_analysis(msg=msg, ws=ws, text_mod=mod, trace_id="t3")
        ws.send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
