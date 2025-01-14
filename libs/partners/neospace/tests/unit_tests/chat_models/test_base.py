"""Test NeoSpace Chat API wrapper."""

import json
from typing import Any, List, Type, Union
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import (
    AIMessage,
    FunctionMessage,
    HumanMessage,
    InvalidToolCall,
    SystemMessage,
    ToolCall,
    ToolMessage,
)
from langchain_core.pydantic_v1 import BaseModel

from langchain_neospace import ChatNeoSpace
from langchain_neospace.chat_models.base import (
    _convert_dict_to_message,
    _convert_message_to_dict,
    _format_message_content,
)


def test_neospace_model_param() -> None:
    llm = ChatNeoSpace(model="foo")
    assert llm.model_name == "foo"
    llm = ChatNeoSpace(model_name="foo")  # type: ignore[call-arg]
    assert llm.model_name == "foo"


def test_function_message_dict_to_function_message() -> None:
    content = json.dumps({"result": "Example #1"})
    name = "test_function"
    result = _convert_dict_to_message(
        {"role": "function", "name": name, "content": content}
    )
    assert isinstance(result, FunctionMessage)
    assert result.name == name
    assert result.content == content


def test__convert_dict_to_message_human() -> None:
    message = {"role": "user", "content": "foo"}
    result = _convert_dict_to_message(message)
    expected_output = HumanMessage(content="foo")
    assert result == expected_output
    assert _convert_message_to_dict(expected_output) == message


def test__convert_dict_to_message_human_with_name() -> None:
    message = {"role": "user", "content": "foo", "name": "test"}
    result = _convert_dict_to_message(message)
    expected_output = HumanMessage(content="foo", name="test")
    assert result == expected_output
    assert _convert_message_to_dict(expected_output) == message


def test__convert_dict_to_message_ai() -> None:
    message = {"role": "assistant", "content": "foo"}
    result = _convert_dict_to_message(message)
    expected_output = AIMessage(content="foo")
    assert result == expected_output
    assert _convert_message_to_dict(expected_output) == message


def test__convert_dict_to_message_ai_with_name() -> None:
    message = {"role": "assistant", "content": "foo", "name": "test"}
    result = _convert_dict_to_message(message)
    expected_output = AIMessage(content="foo", name="test")
    assert result == expected_output
    assert _convert_message_to_dict(expected_output) == message


def test__convert_dict_to_message_system() -> None:
    message = {"role": "system", "content": "foo"}
    result = _convert_dict_to_message(message)
    expected_output = SystemMessage(content="foo")
    assert result == expected_output
    assert _convert_message_to_dict(expected_output) == message


def test__convert_dict_to_message_system_with_name() -> None:
    message = {"role": "system", "content": "foo", "name": "test"}
    result = _convert_dict_to_message(message)
    expected_output = SystemMessage(content="foo", name="test")
    assert result == expected_output
    assert _convert_message_to_dict(expected_output) == message


def test__convert_dict_to_message_tool() -> None:
    message = {"role": "tool", "content": "foo", "tool_call_id": "bar"}
    result = _convert_dict_to_message(message)
    expected_output = ToolMessage(content="foo", tool_call_id="bar")
    assert result == expected_output
    assert _convert_message_to_dict(expected_output) == message


def test__convert_dict_to_message_tool_call() -> None:
    raw_tool_call = {
        "id": "call_wm0JY6CdwOMZ4eTxHWUThDNz",
        "function": {
            "arguments": '{"name": "Sally", "hair_color": "green"}',
            "name": "GenerateUsername",
        },
        "type": "function",
    }
    message = {"role": "assistant", "content": None, "tool_calls": [raw_tool_call]}
    result = _convert_dict_to_message(message)
    expected_output = AIMessage(
        content="",
        additional_kwargs={"tool_calls": [raw_tool_call]},
        tool_calls=[
            ToolCall(
                name="GenerateUsername",
                args={"name": "Sally", "hair_color": "green"},
                id="call_wm0JY6CdwOMZ4eTxHWUThDNz",
                type="tool_call",
            )
        ],
    )
    assert result == expected_output
    assert _convert_message_to_dict(expected_output) == message

    # Test malformed tool call
    raw_tool_calls: list = [
        {
            "id": "call_wm0JY6CdwOMZ4eTxHWUThDNz",
            "function": {"arguments": "oops", "name": "GenerateUsername"},
            "type": "function",
        },
        {
            "id": "call_abc123",
            "function": {
                "arguments": '{"name": "Sally", "hair_color": "green"}',
                "name": "GenerateUsername",
            },
            "type": "function",
        },
    ]
    raw_tool_calls = list(sorted(raw_tool_calls, key=lambda x: x["id"]))
    message = {"role": "assistant", "content": None, "tool_calls": raw_tool_calls}
    result = _convert_dict_to_message(message)
    expected_output = AIMessage(
        content="",
        additional_kwargs={"tool_calls": raw_tool_calls},
        invalid_tool_calls=[
            InvalidToolCall(
                name="GenerateUsername",
                args="oops",
                id="call_wm0JY6CdwOMZ4eTxHWUThDNz",
                error="Function GenerateUsername arguments:\n\noops\n\nare not valid JSON. Received JSONDecodeError Expecting value: line 1 column 1 (char 0)",  # noqa: E501
                type="invalid_tool_call",
            )
        ],
        tool_calls=[
            ToolCall(
                name="GenerateUsername",
                args={"name": "Sally", "hair_color": "green"},
                id="call_abc123",
                type="tool_call",
            )
        ],
    )
    assert result == expected_output
    reverted_message_dict = _convert_message_to_dict(expected_output)
    reverted_message_dict["tool_calls"] = list(
        sorted(reverted_message_dict["tool_calls"], key=lambda x: x["id"])
    )
    assert reverted_message_dict == message


@pytest.fixture
def mock_completion() -> dict:
    return {
        "id": "chatcmpl-7fcZavknQda3SQ",
        "object": "chat.completion",
        "created": 1689989000,
        "model": "neo-3.5-turbo-0613",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Bar Baz", "name": "Erick"},
                "finish_reason": "stop",
            }
        ],
    }


@pytest.fixture
def mock_client(mock_completion: dict) -> MagicMock:
    rtn = MagicMock()

    mock_create = MagicMock()

    mock_resp = MagicMock()
    mock_resp.headers = {"content-type": "application/json"}
    mock_resp.parse.return_value = mock_completion
    mock_create.return_value = mock_resp

    rtn.with_raw_response.create = mock_create
    rtn.create.return_value = mock_completion
    return rtn


@pytest.fixture
def mock_async_client(mock_completion: dict) -> AsyncMock:
    rtn = AsyncMock()

    mock_create = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.parse.return_value = mock_completion
    mock_create.return_value = mock_resp

    rtn.with_raw_response.create = mock_create
    rtn.create.return_value = mock_completion
    return rtn


def test_neospace_invoke(mock_client: MagicMock) -> None:
    llm = ChatNeoSpace()

    with patch.object(llm, "client", mock_client):
        res = llm.invoke("bar")
        assert res.content == "Bar Baz"

        # headers are not in response_metadata if include_response_headers not set
        assert "headers" not in res.response_metadata
    assert mock_client.create.called


async def test_neospace_ainvoke(mock_async_client: AsyncMock) -> None:
    llm = ChatNeoSpace()

    with patch.object(llm, "async_client", mock_async_client):
        res = await llm.ainvoke("bar")
        assert res.content == "Bar Baz"

        # headers are not in response_metadata if include_response_headers not set
        assert "headers" not in res.response_metadata
    assert mock_async_client.create.called


@pytest.mark.parametrize(
    "model",
    [
        "neo-3.5-turbo",
        "neo-4",
        "neo-3.5-0125",
        "neo-4-0125-preview",
        "neo-4-turbo-preview",
        "neo-4-vision-preview",
    ],
)
def test__get_encoding_model(model: str) -> None:
    ChatNeoSpace(model=model)._get_encoding_model()
    return


def test_neospace_invoke_name(mock_client: MagicMock) -> None:
    llm = ChatNeoSpace()

    with patch.object(llm, "client", mock_client):
        messages = [HumanMessage(content="Foo", name="Katie")]
        res = llm.invoke(messages)
        call_args, call_kwargs = mock_client.create.call_args
        assert len(call_args) == 0  # no positional args
        call_messages = call_kwargs["messages"]
        assert len(call_messages) == 1
        assert call_messages[0]["role"] == "user"
        assert call_messages[0]["content"] == "Foo"
        assert call_messages[0]["name"] == "Katie"

        # check return type has name
        assert res.content == "Bar Baz"
        assert res.name == "Erick"


def test_custom_token_counting() -> None:
    def token_encoder(text: str) -> List[int]:
        return [1, 2, 3]

    llm = ChatNeoSpace(custom_get_token_ids=token_encoder)
    assert llm.get_token_ids("foo") == [1, 2, 3]


def test_format_message_content() -> None:
    content: Any = "hello"
    assert content == _format_message_content(content)

    content = None
    assert content == _format_message_content(content)

    content = []
    assert content == _format_message_content(content)

    content = [
        {"type": "text", "text": "What is in this image?"},
        {"type": "image_url", "image_url": {"url": "url.com"}},
    ]
    assert content == _format_message_content(content)

    content = [
        {"type": "text", "text": "hello"},
        {
            "type": "tool_use",
            "id": "toolu_01A09q90qw90lq917835lq9",
            "name": "get_weather",
            "input": {"location": "San Francisco, CA", "unit": "celsius"},
        },
    ]
    assert [{"type": "text", "text": "hello"}] == _format_message_content(content)


class GenerateUsername(BaseModel):
    "Get a username based on someone's name and hair color."

    name: str
    hair_color: str


class MakeASandwich(BaseModel):
    "Make a sandwich given a list of ingredients."

    bread_type: str
    cheese_type: str
    condiments: List[str]
    vegetables: List[str]


@pytest.mark.parametrize(
    "tool_choice",
    [
        "any",
        "none",
        "auto",
        "required",
        "GenerateUsername",
        {"type": "function", "function": {"name": "MakeASandwich"}},
        False,
        None,
    ],
)
def test_bind_tools_tool_choice(tool_choice: Any) -> None:
    """Test passing in manually construct tool call message."""
    llm = ChatNeoSpace(model="better_KD_loss_03_lora_full", temperature=0)
    llm.bind_tools(tools=[GenerateUsername, MakeASandwich], tool_choice=tool_choice)


@pytest.mark.parametrize("schema", [GenerateUsername, GenerateUsername.schema()])
def test_with_structured_output(schema: Union[Type[BaseModel], dict]) -> None:
    """Test passing in manually construct tool call message."""
    llm = ChatNeoSpace(model="better_KD_loss_03_lora_full", temperature=0)
    llm.with_structured_output(schema)


def test_get_num_tokens_from_messages() -> None:
    llm = ChatNeoSpace(model="better_KD_loss_03_lora_full")
    messages = [
        SystemMessage("you're a good assistant"),
        HumanMessage("how are you"),
        HumanMessage(
            [
                {"type": "text", "text": "what's in this image"},
                {"type": "image_url", "image_url": {"url": "https://foobar.com"}},
                {
                    "type": "image_url",
                    "image_url": {"url": "https://foobar.com", "detail": "low"},
                },
            ]
        ),
        AIMessage("a nice bird"),
        AIMessage(
            "",
            tool_calls=[
                ToolCall(id="foo", name="bar", args={"arg1": "arg1"}, type="tool_call")
            ],
        ),
        AIMessage(
            "",
            additional_kwargs={
                "function_call": json.dumps({"arguments": "old", "name": "fun"})
            },
        ),
        AIMessage(
            "text",
            tool_calls=[
                ToolCall(id="foo", name="bar", args={"arg1": "arg1"}, type="tool_call")
            ],
        ),
        ToolMessage("foobar", tool_call_id="foo"),
    ]
    expected = 170
    actual = llm.get_num_tokens_from_messages(messages)
    assert expected == actual
