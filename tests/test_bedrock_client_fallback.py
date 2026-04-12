import unittest

from src.core.llm.llm_client import BedrockClient


class _DummyResponse:
    def __init__(self, content: str):
        self.content = content


class _FailingChatModel:
    def invoke(self, messages):
        raise RuntimeError("Provider us model does not support chat.")


class _SuccessChatModel:
    def invoke(self, messages):
        return _DummyResponse("ok-from-fallback")


class _CredentialErrorChatModel:
    def invoke(self, messages):
        raise RuntimeError(
            "An error occurred (UnrecognizedClientException) when calling the InvokeModel operation: "
            "The security token included in the request is invalid."
        )


class _NoFallbackBedrockClient(BedrockClient):
    def __init__(self):
        self.config = type(
            "BedrockConfig",
            (),
            {
                "region": "us-east-1",
                "model_id": "us.anthropic.claude-opus-4-5-20251101-v1:0",
                "access_key": "",
                "secret_key": "",
            },
        )()
        self._model = None
        self._fallback_model = None

    def get_model(self):
        return _FailingChatModel()

    def _get_fallback_model(self):
        return None

    def _convert_messages(self, messages):
        return messages


class _FallbackBedrockClient(_NoFallbackBedrockClient):
    def _get_fallback_model(self):
        return _SuccessChatModel()


class _CredentialErrorBedrockClient(_NoFallbackBedrockClient):
    def get_model(self):
        return _CredentialErrorChatModel()


class BedrockClientFallbackTest(unittest.TestCase):
    def test_raise_when_no_fallback_model(self):
        client = _NoFallbackBedrockClient()
        with self.assertRaises(RuntimeError):
            client.chat([{"role": "user", "content": "hello"}])

    def test_retry_with_fallback_model(self):
        client = _FallbackBedrockClient()
        response = client.chat([{"role": "user", "content": "hello"}])
        self.assertEqual(response, "ok-from-fallback")
    
    def test_raise_clear_error_for_invalid_aws_token(self):
        client = _CredentialErrorBedrockClient()
        with self.assertRaises(RuntimeError) as ctx:
            client.chat([{"role": "user", "content": "hello"}])
        self.assertIn("AWS凭证无效", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
