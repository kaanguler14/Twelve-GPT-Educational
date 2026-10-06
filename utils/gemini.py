"""
Utilities for more easily convert OpenAI API calls to Gemini API calls.
"""

from google.api_core.exceptions import ResourceExhausted

QUOTA_MESSAGE = (
    "The AI model's usage limit has been reached for now, so I can't answer "
    "at the moment. Please try again later."
)


def convert_messages_format(messages):
    new_messages = []
    system_prompt = None
    if len(messages) > 0 and messages[0]["role"] == "system":
        # If the first message is a system message, store it and return it.
        # Gemini requires the system prompt to be passed in separately.
        system_prompt = messages[0]["content"]
        messages = messages[1:]
    for message in messages:
        role = "model" if message["role"] == "assistant" else "user"
        new_message = {
            "role": role,
            "parts": message["content"],
        }
        new_messages.append(new_message)

    user_query = ""
    if new_messages[-1]["role"] == "user":
        user_query = new_messages.pop()
    return {"system_instruction": system_prompt, "history": new_messages, "content": user_query}


def gemini_chat(messages, api_key, model_name, temperature=1, stream=False):
    """
    Send OpenAI-style messages to Gemini.

    Returns the answer as a string, or (when stream=True) a generator over
    text chunks, matching what the OpenAI / LM Studio branches return.
    """
    try:
        import google.generativeai as genai

        converted_msgs = convert_messages_format(messages)

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=converted_msgs["system_instruction"],
            generation_config={"temperature": temperature},
        )
        chat = model.start_chat(history=converted_msgs["history"])
        response = chat.send_message(content=converted_msgs["content"], stream=stream)

        if not stream:
            return response.text

        return _eager_stream(response)
    except ResourceExhausted:
        return _single_chunk(QUOTA_MESSAGE) if stream else QUOTA_MESSAGE


def _single_chunk(text):
    def streamed_chunks():
        yield text

    return streamed_chunks()


def _eager_stream(response):
    # Collect chunks eagerly so the generator over the list is
    # near-instantaneous — preventing Streamlit re-runs from
    # hitting the same generator while it is still executing.
    chunks = [chunk.text for chunk in response if chunk.parts]

    def streamed_chunks():
        yield from chunks

    return streamed_chunks()


def convert_tools(tools):
    """Convert OpenAI Responses-style tool definitions to a Gemini Tool dict."""
    declarations = []
    for tool in tools:
        declaration = {"name": tool["name"], "description": tool["description"]}
        parameters = tool.get("parameters") or {}
        # Gemini rejects OBJECT schemas with no properties, so omit them entirely.
        if parameters.get("properties"):
            declaration["parameters"] = {
                k: v for k, v in parameters.items() if not (k == "required" and not v)
            }
        declarations.append(declaration)
    return {"function_declarations": declarations}


def gemini_tool_chat(
    messages, tools, run_tool, api_key, model_name, temperature=1, stream=False
):
    """
    Two-pass function calling with Gemini, mirroring the OpenAI Responses flow.

    Call 1 lets the model pick at most one tool (or answer directly).
    If a tool is picked, run_tool(name, args) produces its output and
    call 2 writes the final answer with tool calling disabled.

    Returns (answer, transcript): answer is a string, or a generator of text
    chunks when stream=True and a tool was called; transcript is a list of
    dicts for display in the chat transcript expander.
    """
    import google.generativeai as genai

    converted_msgs = convert_messages_format(messages)
    contents = converted_msgs["history"] + [converted_msgs["content"]]
    transcript = [
        {"role": m["role"], "content": m["content"]}
        for m in messages
        if isinstance(m, dict)
    ]

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=converted_msgs["system_instruction"],
            tools=[convert_tools(tools)],
            generation_config={"temperature": temperature},
        )

        # Call 1: model picks a tool if relevant, or answers directly if not.
        r1 = model.generate_content(
            contents, tool_config={"function_calling_config": {"mode": "AUTO"}}
        )
        model_content = r1.candidates[0].content
        fc = next(
            (part.function_call for part in model_content.parts if part.function_call.name),
            None,
        )

        if fc is None:
            return r1.text, transcript

        args = dict(fc.args) if fc.args else {}
        result = run_tool(fc.name, args)
        transcript += [
            {"tool_call": fc.name, "arguments": args},
            {"tool_result": result or "(empty)"},
        ]

        # Call 2: final answer, no more tools.
        function_response = genai.protos.Content(
            role="user",
            parts=[
                genai.protos.Part(
                    function_response=genai.protos.FunctionResponse(
                        name=fc.name, response={"result": result}
                    )
                )
            ],
        )
        r2 = model.generate_content(
            contents + [model_content, function_response],
            tool_config={"function_calling_config": {"mode": "NONE"}},
            stream=stream,
        )

        if not stream:
            return r2.text, transcript

        return _eager_stream(r2), transcript
    except ResourceExhausted:
        return QUOTA_MESSAGE, transcript
