import streamlit as st
from openai import OpenAI
from itertools import groupby
from types import GeneratorType
import pandas as pd
import json

from settings import USE_GEMINI, USE_LM_STUDIO, MAX_QUESTIONS_PER_SESSION

if USE_GEMINI:
    from settings import GEMINI_API_KEY, GEMINI_CHAT_MODEL
elif USE_LM_STUDIO:
    from settings import LM_STUDIO_API_KEY, LM_STUDIO_CHAT_MODEL, LM_STUDIO_API_BASE
else:
    from settings import (
        GPT_BASE,
        GPT_KEY,
        GPT_CHAT_MODEL,
        GPT_SUPPORTS_REASONING,
        GPT_AVAILABLE_REASONING_EFFORTS,
        GPT_SUPPORTS_TEMPERATURE,
    )

from classes.description import (
    PlayerDescription,
    CountryDescription,
    PersonDescription,
    PressingDescription,
)
from classes.embeddings import (
    PlayerEmbeddings,
    CountryEmbeddings,
    PersonEmbeddings,
    PressingEmbeddings,
)

from classes.visual import Visual, DistributionPlot, DistributionPlotPersonality

import utils.sentences as sentences
from utils.gemini import gemini_chat, gemini_tool_chat
from utils.text import clean_mojibake


class Chat:
    function_names = []

    def __init__(self, chat_state_hash, state="empty"):

        if (
            "chat_state_hash" not in st.session_state
            or chat_state_hash != st.session_state.chat_state_hash
        ):
            # st.write("Initializing chat")
            st.session_state.chat_state_hash = chat_state_hash
            st.session_state.messages_to_display = []
            st.session_state.chat_state = state
        if isinstance(self, PlayerChat):
            self.name = self.player.name
        elif isinstance(self, PersonChat):
            self.name = self.person.name
        elif isinstance(self, PressingChat):
            self.name = self.team.name
        else:
            pass

        # Set session states as attributes for easier access
        self.messages_to_display = st.session_state.messages_to_display
        self.state = st.session_state.chat_state

    def instruction_messages(self):
        """
        Sets up the instructions to the agent. Should be overridden by subclasses.
        """
        return []

    def add_message(self, content, role="assistant", user_only=True, visible=True):
        """
        Used by app.py to start off the conversation with plots and descriptions.
        """
        if isinstance(content, str):
            content = clean_mojibake(content)
        elif isinstance(content, GeneratorType):
            content = (clean_mojibake(chunk) for chunk in content)
        elif isinstance(content, list):
            content = [clean_mojibake(x) for x in content]
        message = {"role": role, "content": content}
        self.messages_to_display.append(message)

    # def get_input(self):
    #     """
    #     Get input from streamlit."""

    #     if x := st.chat_input(
    #         placeholder=f"What else would you like to know about {self.player.name}?"
    #     ):
    #         if len(x) > 500:
    #             st.error(
    #                 f"Your message is too long ({len(x)} characters). Please keep it under 500 characters."
    #             )

    #         self.handle_input(x)

    def handle_input(self, input, reasoning_effort=None, temperature=1, stream=False):
        """
        The main function that calls the GPT-4 API and processes the response.
        """

        # Get the instruction messages.
        messages = self.instruction_messages()

        # Add a copy of the user messages. This is to give the assistant some context.
        messages = messages + self.messages_to_display.copy()

        # Get relevant information from the user input and then generate a response.
        # This is not added to messages_to_display as it is not a message from the assistant.
        get_relevant_info = self.get_relevant_info(input)
        get_relevant_info = clean_mojibake(get_relevant_info)

        # Now add the user input to the messages. Don't add system information and system messages to messages_to_display.
        self.messages_to_display.append({"role": "user", "content": input})

        messages.append(
            {
                "role": "user",
                "content": f"Here is the relevant information to answer the users query: {get_relevant_info}\n\n```User: {input}```",
            }
        )

        # Remove all items in messages where content is not a string
        messages = [
            message for message in messages if isinstance(message["content"], str)
        ]
        for message in messages:
            message["content"] = clean_mojibake(message["content"])

        # Show the messages in an expander
        st.expander("Chat transcript", expanded=False).write(messages)

        # Check if use gemini is set to true
        if USE_GEMINI:
            answer = gemini_chat(
                messages,
                GEMINI_API_KEY,
                GEMINI_CHAT_MODEL,
                temperature=temperature,
                stream=stream,
            )
            if stream:
                answer = (clean_mojibake(chunk) for chunk in answer)
            else:
                answer = clean_mojibake(answer)
        elif USE_LM_STUDIO:
            client = OpenAI(api_key=LM_STUDIO_API_KEY, base_url=LM_STUDIO_API_BASE)
            if stream:
                # Collect chunks eagerly so the generator over the list is
                # near-instantaneous — preventing Streamlit re-runs from
                # hitting the same generator while it is still executing.
                chunks = [
                    clean_mojibake(chunk.choices[0].delta.content)
                    for chunk in client.chat.completions.create(
                        model=LM_STUDIO_CHAT_MODEL,
                        messages=messages,
                        temperature=temperature,
                        stream=True,
                    )
                    if chunk.choices and chunk.choices[0].delta.content
                ]

                def streamed_chunks():
                    yield from chunks

                answer = streamed_chunks()
            else:
                response = client.chat.completions.create(
                    model=LM_STUDIO_CHAT_MODEL,
                    messages=messages,
                    temperature=temperature,
                )
                answer = clean_mojibake(response.choices[0].message.content)
        else:
            client = OpenAI(api_key=GPT_KEY, base_url=GPT_BASE)
            if stream:
                if GPT_SUPPORTS_REASONING:
                    reasoning_effort = reasoning_effort if reasoning_effort in GPT_AVAILABLE_REASONING_EFFORTS else GPT_AVAILABLE_REASONING_EFFORTS[0]
                    response_stream = client.responses.create(
                        model=GPT_CHAT_MODEL,
                        input=messages,
                        reasoning={"effort": reasoning_effort},
                        stream=True,
                    )
                elif GPT_SUPPORTS_TEMPERATURE:
                    response_stream = client.responses.create(
                        model=GPT_CHAT_MODEL,
                        input=messages,
                        temperature=temperature,
                        stream=True,
                    )
                else:
                    response_stream = client.responses.create(
                        model=GPT_CHAT_MODEL,
                        input=messages,
                        stream=True,
                    )

                def streamed_chunks():
                    for event in response_stream:
                        if event.type == "response.output_text.delta":
                            yield clean_mojibake(event.delta)

                answer = streamed_chunks()
            else:
                if GPT_SUPPORTS_REASONING:
                    reasoning_effort = reasoning_effort if reasoning_effort in GPT_AVAILABLE_REASONING_EFFORTS else GPT_AVAILABLE_REASONING_EFFORTS[0]
                    response = client.responses.create(
                        model=GPT_CHAT_MODEL,
                        input=messages,
                        reasoning={"effort": reasoning_effort},
                    )
                elif GPT_SUPPORTS_TEMPERATURE:
                    response = client.responses.create(
                        model=GPT_CHAT_MODEL,
                        input=messages,
                        temperature=temperature,
                    )
                else:
                    response = client.responses.create(
                        model=GPT_CHAT_MODEL,
                        input=messages,
                    )

                answer = clean_mojibake(response.output_text)
        message = {"role": "assistant", "content": answer}

        # Add the returned value to the messages.
        self.messages_to_display.append(message)

    def allow_question(self):
        """
        Enforces MAX_QUESTIONS_PER_SESSION so a public deployment cannot exhaust the API quota.
        """
        if not MAX_QUESTIONS_PER_SESSION:
            return True
        asked = st.session_state.get("questions_asked", 0)
        if asked >= MAX_QUESTIONS_PER_SESSION:
            st.warning(
                f"This demo allows {MAX_QUESTIONS_PER_SESSION} questions per session "
                "to stay within its API quota. Thanks for trying it out!"
            )
            return False
        st.session_state.questions_asked = asked + 1
        return True

    def _run_tool(self, name, args):
        """
        Executes a tool picked by the model. Overridden by subclasses that define tools.
        """
        return f"Unknown tool: {name}"

    def handle_input_gemini_tools(self, input, temperature=1, stream=False):
        """
        Gemini function-calling path, mirroring the OpenAI path in the subclasses.
        """
        messages = self.instruction_messages()
        messages = messages + self.messages_to_display.copy()
        messages = [m for m in messages if isinstance(m["content"], str)]
        messages.append({"role": "user", "content": f"```User: {input}```"})

        self.messages_to_display.append({"role": "user", "content": input})

        answer, transcript = gemini_tool_chat(
            messages,
            self.tools,
            self._run_tool,
            GEMINI_API_KEY,
            GEMINI_CHAT_MODEL,
            temperature=temperature,
            stream=stream,
        )
        st.expander("Chat transcript", expanded=False).write(transcript)

        if isinstance(answer, str):
            answer = clean_mojibake(answer)
        self.messages_to_display.append({"role": "assistant", "content": answer})

    def display_content(self, content):
        """
        Displays the content of a message in streamlit. Handles plots, strings, and StreamingMessages.
        """
        if isinstance(content, str):
            st.write(clean_mojibake(content))

        # Visual
        elif isinstance(content, Visual):
            content.show()

        else:
            # So we do this in case
            try:
                content.show()
            except:
                try:
                    st.write(content.get_string())
                except:
                    raise ValueError(
                        f"Message content of type {type(content)} not supported."
                    )

    def display_messages(self):
        """
        Displays visible messages in streamlit. Messages are grouped by role.
        If message content is a Visual, it is displayed in a st.columns((1, 2, 1))[1].
        If the message is a list of strings/Visuals of length n, they are displayed in n columns.
        If a message is a generator, it is displayed with st.write_stream
        Special case: If there are N Visuals in one message, followed by N messages/StreamingMessages in the next, they are paired up into the same N columns.
        """
        # Group by role so user name and avatar is only displayed once

        # st.write(self.messages_to_display)

        for key, group in groupby(self.messages_to_display, lambda x: x["role"]):
            group = list(group)

            if key == "assistant":
                avatar = "data/ressources/img/twelve_chat_logo.svg"
            else:
                try:
                    avatar = st.session_state.user_info["picture"]
                except:
                    avatar = None

            message_block = st.chat_message(name=key, avatar=avatar)
            with message_block:
                for message in group:
                    content = message["content"]
                    if isinstance(content, GeneratorType):
                        final_text = st.write_stream(content)
                        message["content"] = final_text
                    else:
                        self.display_content(content)

    def save_state(self):
        """
        Saves the conversation to session state.
        """
        st.session_state.messages_to_display = self.messages_to_display
        st.session_state.chat_state = self.state


class PlayerChat(Chat):
    tools = [
        {
            "type": "function",
            "name": "get_player_summary",
            "description": "Returns a data-driven statistical summary of the selected player.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
        {
            "type": "function",
            "name": "search_football_knowledge",
            "description": "Searches a knowledge base for information relevant to a question about data analytics in football, especially about forwards.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The question or topic to search for.",
                    }
                },
                "required": ["query"],
            },
        },
    ]

    def __init__(self, chat_state_hash, player, players, state="empty"):
        self.embeddings = PlayerEmbeddings()
        self.player = player
        self.players = players
        super().__init__(chat_state_hash, state=state)

    def _get_player_summary(self):
        return PlayerDescription(self.player).synthesize_text()

    def _search_knowledge(self, query):
        results = self.embeddings.search(query, top_n=5)
        return "\n".join(results["assistant"].to_list())

    def _run_tool(self, name, args):
        if name == "get_player_summary":
            return self._get_player_summary()
        return self._search_knowledge(args["query"])

    def get_input(self):
        """
        Get input from streamlit."""

        if x := st.chat_input(
            placeholder=f"What else would you like to know about {self.player.name}?"
        ):
            if len(x) > 500:
                st.error(
                    f"Your message is too long ({len(x)} characters). Please keep it under 500 characters."
                )

            if self.allow_question():
                self.handle_input(x, stream=True)

    def instruction_messages(self):
        """
        Instruction for the agent.
        """
        if USE_LM_STUDIO:
            first_messages = [
            {"role": "system", "content": "You are a UK-based football scout."},
            {
                "role": "user",
                "content": (
                    "After these messages you will be interacting with a user of a football scouting platform. "
                    f"The user has selected the player {self.player.name}, and the conversation will be about them. "
                    "You will receive relevant information to answer a user's questions and then be asked to provide a response. "
                    "All user messages will be prefixed with 'User:' and enclosed with ```. "
                    "When responding to the user, speak directly to them. "
                    "Use the information provided before the query  to provide 2 sentence answers."
                    " Do not deviate from this information or provide additional information that is not in the text returned by the functions."
                ),
            },
        ]
            return first_messages
        else:
            return [
                {
                    "role": "system",
                    "content": (
                        "You are a UK-based football scout. "
                        f"The user has selected the player {self.player.name}, and the conversation will be about them. "
                        "You will receive relevant information to answer a user's questions and then be asked to provide a response. "
                        "Choose the tool that best fits the user's query to respond."
                        "- If the user is asking for information about the player, use the get_player_summary function. "  
                        "- If the user is asking for general football knowledge, use the search_football_knowledge function. "
                        "- If none of the tools are relevant to the user's query, respond directly to the user that the question is outside your scope. "
                        "- If the user asks about a different player, respond that you can only answer questions about the selected player and if they want information about a different player, they need to select that player first on the sidebar."
                        "All user messages will be prefixed with 'User:' and enclosed with ```. "
                        "When responding to the user, speak directly to them. "
                        "Use the information provided before the query to provide 2 sentence answers."
                        "Do not deviate from this information or provide additional information that is not in the text returned by the functions."
                    ),
                }
            ]

    def handle_input(self, input, reasoning_effort=None, temperature=1, stream=False):
        if USE_LM_STUDIO:
            super().handle_input(input, reasoning_effort=reasoning_effort, temperature=temperature, stream=stream)
            return
        if USE_GEMINI:
            self.handle_input_gemini_tools(input, temperature=temperature, stream=stream)
            return
        # OpenAI function-calling path
        messages = self.instruction_messages()
        messages = messages + self.messages_to_display.copy()
        messages = [m for m in messages if isinstance(m["content"], str)]
        messages.append({"role": "user", "content": f"```User: {input}```"})

        self.messages_to_display.append({"role": "user", "content": input})

        client = OpenAI(api_key=GPT_KEY, base_url=GPT_BASE)

        # Call 1: model picks a tool if relevant, or answers directly if not
        r1 = client.responses.create(
            model=GPT_CHAT_MODEL,
            input=messages,
            tools=self.tools,
            tool_choice="auto",
        )
        fc = next((item for item in r1.output if item.type == "function_call"), None)

        if fc is None:
            # Model decided no tool was needed — use its response directly
            st.expander("Chat transcript", expanded=False).write(
                [{"role": m.get("role"), "content": m.get("content", "")} for m in messages if isinstance(m, dict)]
            )
            self.messages_to_display.append({"role": "assistant", "content": r1.output_text})
            return

        result = self._run_tool(fc.name, json.loads(fc.arguments) if fc.arguments else {})

        # Call 2: final answer, no more tools
        tool_inputs = list(messages) + list(r1.output) + [
            {"type": "function_call_output", "call_id": fc.call_id, "output": result}
        ]

        formatted = []
        for item in tool_inputs:
            if isinstance(item, dict):
                if item.get("type") == "function_call_output":
                    formatted.append({"tool_result": item["output"] or "(empty)", "call_id": item["call_id"]})
                else:
                    formatted.append({"role": item.get("role"), "content": item.get("content", "")})
            elif hasattr(item, "type"):
                if item.type == "function_call":
                    formatted.append({"tool_call": item.name, "arguments": json.loads(item.arguments)})
                # reasoning items are skipped
        st.expander("Chat transcript", expanded=False).write(formatted)
       
        if stream:
            if GPT_SUPPORTS_REASONING:
                reasoning_effort = reasoning_effort if reasoning_effort in GPT_AVAILABLE_REASONING_EFFORTS else GPT_AVAILABLE_REASONING_EFFORTS[0]
                response_stream = client.responses.create(
                    model=GPT_CHAT_MODEL,
                    input=tool_inputs,
                    tool_choice="none",
                    tools=self.tools,
                    reasoning={"effort": reasoning_effort},
                    stream=True,
                )
            elif GPT_SUPPORTS_TEMPERATURE:
                response_stream = client.responses.create(
                    model=GPT_CHAT_MODEL,
                    input=tool_inputs,
                    tool_choice="none",
                    tools=self.tools,
                    temperature=temperature,
                    stream=True,
                )
            else:
                response_stream = client.responses.create(
                    model=GPT_CHAT_MODEL,
                    input=tool_inputs,
                    tool_choice="none",
                    tools=self.tools,
                    stream=True,
                )

            def streamed_chunks():
                for event in response_stream:
                    if event.type == "response.output_text.delta":
                        yield event.delta

            answer = streamed_chunks()
        else:
            if GPT_SUPPORTS_REASONING:
                reasoning_effort = reasoning_effort if reasoning_effort in GPT_AVAILABLE_REASONING_EFFORTS else GPT_AVAILABLE_REASONING_EFFORTS[0]
                response = client.responses.create(
                    model=GPT_CHAT_MODEL,
                    input=tool_inputs,
                    tool_choice="none",
                    tools=self.tools,
                    reasoning={"effort": reasoning_effort},
                )
            elif GPT_SUPPORTS_TEMPERATURE:
                response = client.responses.create(
                    model=GPT_CHAT_MODEL,
                    input=tool_inputs,
                    tool_choice="none",
                    tools=self.tools,
                    temperature=temperature,
                )
            else:
                response = client.responses.create(
                    model=GPT_CHAT_MODEL,
                    input=tool_inputs,
                    tool_choice="none",
                    tools=self.tools,
                )
            answer = response.output_text

        self.messages_to_display.append({"role": "assistant", "content": answer})

    def get_relevant_info(self, query):
        # Used by the LM Studio path via super().handle_input

        # If there is no query then use the last message from the user
        if query == "":
            query = self.visible_messages[-1]["content"]

        ret_val = "Here is a description of the player in terms of data: \n\n"
        description = PlayerDescription(self.player)
        ret_val += description.synthesize_text()

        # This finds some relevant information
        results = self.embeddings.search(query, top_n=5)
        ret_val += "\n\nHere is a description of some relevant information for answering the question:  \n"
        ret_val += "\n".join(results["assistant"].to_list())

        ret_val += f"\n\nIf none of this information is relevent to the users's query then use the information below to remind the user about the chat functionality: \n"
        ret_val += "This chat can answer questions about a player's statistics and what they mean for how they play football."
        ret_val += "The user can select the player they are interested in using the menu to the left."

        return ret_val


class PressingChat(Chat):
    tools = [
        {
            "type": "function",
            "name": "get_team_pressing_summary",
            "description": (
                "Returns a data-grounded summary of the selected team's pressing style, "
                "strengths and weaknesses. Use when the user asks about how the selected "
                "team presses, their identity, or what they are good or bad at."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
        {
            "type": "function",
            "name": "search_pressing_knowledge",
            "description": (
                "Searches a curated Q&A corpus for tactical pressing concepts and metric "
                "definitions. Use for general questions about pressing terminology "
                "(e.g. 'what is PPDA', 'what is a pressing chain') rather than questions "
                "about a specific team."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The pressing concept or term to look up.",
                    },
                },
                "required": ["query"],
            },
        },
        {
            "type": "function",
            "name": "compare_team_pressing",
            "description": (
                "Compares the selected team to another named Premier League team across "
                "all pressing metrics. Use when the user names a specific rival team for "
                "head-to-head comparison."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "other_team": {
                        "type": "string",
                        "description": "The rival team name to compare against.",
                    },
                },
                "required": ["other_team"],
            },
        },
        {
            "type": "function",
            "name": "get_league_rankings",
            "description": (
                "Returns the selected team's rank (out of 20) across all pressing metrics. "
                "Use when the user asks where the team stands in the league, about their "
                "ranking, or whether they are top/bottom in something."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
        {
            "type": "function",
            "name": "get_season_pressing_trend",
            "description": (
                "Renders a chart of the selected team's pressing performance match-by-match "
                "across the season. Use when the user asks how the press evolved over the "
                "season, week-by-week, across the campaign, or whether the press got "
                "better or worse over time."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {
                        "type": "string",
                        "description": (
                            "Optional pressing proxy metric to plot. All metrics are "
                            "restricted to chains starting in the opposition half "
                            "(high-press lens). If omitted, plots a composite press "
                            "strength score (the mean of the five metrics' z-scores). "
                            "Allowed values: chains, regains, "
                            "regain_rate, chain_length_avg, lead_to_shot_count."
                        ),
                    },
                },
                "required": [],
            },
        },
        {
            "type": "function",
            "name": "get_intra_match_pressing",
            "description": (
                "Renders a chart of how the selected team's pressing intensity evolved "
                "within a single match using 5-minute buckets. Use when the user asks "
                "about pressing change during a match, first-half vs second-half "
                "intensity, fatigue effects, or 'show me match X'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "match_id": {
                        "type": "integer",
                        "description": "Optional match id. If omitted, uses the team's most recent match.",
                    },
                },
                "required": [],
            },
        },
    ]

    def __init__(self, chat_state_hash, team, pressing, state="empty"):
        self.embeddings = PressingEmbeddings()
        self.team = team
        self.pressing = pressing
        super().__init__(chat_state_hash, state=state)

    def get_input(self):
        if x := st.chat_input(
            placeholder=f"What else would you like to know about {self.team.name}'s pressing?"
        ):
            if len(x) > 500:
                st.error(
                    f"Your message is too long ({len(x)} characters). Please keep it under 500 characters."
                )
                return

            if self.allow_question():
                self.handle_input(x, temperature=0.3, stream=True)

    def instruction_messages(self):
        if USE_LM_STUDIO:
            # LM Studio falls back to the get_relevant_info() path,
            # so they need a self-contained instruction in the legacy shape.
            return [
                {
                    "role": "system",
                    "content": (
                        "You are a tactical data analyst embedded in a Premier League "
                        "coaching staff. Your language is direct and action-oriented. "
                        "You write in British English and refer to the sport as football."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "After these messages you will be interacting with a user of a football "
                        "analytics platform. "
                        f"The user has selected the team {self.team.name}, and the conversation "
                        "will be about their pressing. "
                        "You will receive relevant information to answer a user's questions and "
                        "then be asked to provide a response. "
                        "All user messages will be prefixed with 'User:' and enclosed with ```. "
                        "When responding to the user, speak directly to them. "
                        "Use the information provided before the query to provide 2 sentence answers. "
                        "Do not deviate from this information or provide additional information "
                        "that is not in the text returned by the functions."
                    ),
                },
            ]
        return [
            {
                "role": "system",
                "content": (
                    "You are a tactical data analyst embedded in a Premier League coaching staff. "
                    "You write in British English, refer to the sport as football, and speak "
                    "directly to the coach in a concise, action-oriented voice. "
                    f"The user has selected the team {self.team.name}; all tools are scoped to "
                    "this team. "
                    "Pick exactly one tool per user message based on the question type: "
                    "use get_team_pressing_summary for the selected team's style, strengths or "
                    "weaknesses; "
                    "use search_pressing_knowledge for tactical concept definitions or metric "
                    "explanations; "
                    "use compare_team_pressing when the user names a specific rival team; "
                    "use get_league_rankings when the user asks about league position or rank; "
                    "use get_season_pressing_trend when the user asks how the press evolved across "
                    "the season, week-by-week, or wants a season-long chart; "
                    "use get_intra_match_pressing when the user asks how pressing changed within a "
                    "single match, about fatigue, halves, or wants a match-level chart. "
                    "If the user asks about a different team than the selected one, do not call "
                    f"any tool — remind them they need to switch the team from the sidebar "
                    f"(currently {self.team.name}). "
                    "If the question is off-topic (other sports, politics, anything not about "
                    "Premier League pressing), do not call any tool — politely decline and "
                    "refocus on pressing analysis. "
                    "Once a tool returns, write a concise 2-3 sentence answer grounded only in "
                    "the data the tool returned. Do not invent metrics or numbers."
                ),
            }
        ]

    def _get_team_summary(self):
        return PressingDescription(self.team).synthesize_text()

    def _search_knowledge(self, query):
        if self.embeddings.df_dict is None or self.embeddings.df_dict.empty:
            return "Knowledge corpus is empty."
        results = self.embeddings.search(query, top_n=3)
        if results.empty:
            return "No relevant entries found in the pressing knowledge corpus."
        return "\n\n".join(results["assistant"].astype(str).to_list())

    def _compare_team(self, other_team):
        from rapidfuzz import process, fuzz

        team_names = self.pressing.df["Team"].astype(str).tolist()
        match = process.extractOne(
            other_team, team_names, scorer=fuzz.WRatio, score_cutoff=60
        )
        if match is None:
            return (
                f"No team matching '{other_team}' was found in the league dataset. "
                f"Available teams: {', '.join(team_names)}."
            )
        matched_name = match[0]
        if matched_name == self.team.name:
            return (
                f"The user named '{other_team}', which resolves to the currently selected "
                f"team ({self.team.name}). No comparison to perform."
            )

        df = self.pressing.df
        self_row = df[df["Team"] == self.team.name].iloc[0]
        other_row = df[df["Team"] == matched_name].iloc[0]

        labels = PressingDescription.METRIC_LABELS
        metrics = self.team.relevant_metrics

        # The direction column stops the model reading a higher raw value as
        # better on metrics where lower is better (e.g. Press Break Rate).
        header = (
            f"{'metric':<48}| {'direction':<17}| {self.team.name:<14}| "
            f"{matched_name:<14}| better"
        )
        lines = [header, "-" * len(header)]
        for m in metrics:
            direction = (
                "lower is better"
                if m in self.pressing.negative_metrics
                else "higher is better"
            )
            self_raw = float(self_row[m])
            other_raw = float(other_row[m])
            self_z = float(self_row[m + "_Z"])
            other_z = float(other_row[m + "_Z"])
            # _Z values are already sign-flipped for negative metrics, so higher = better.
            if abs(self_z - other_z) < 0.05:
                better = "≈ even"
            elif self_z > other_z:
                better = self.team.name
            else:
                better = matched_name
            label = labels.get(m, m)
            lines.append(
                f"{label:<48}| {direction:<17}| {self_raw:<14.3f}| "
                f"{other_raw:<14.3f}| {better}"
            )
        return "\n".join(lines)

    def _get_rankings(self):
        df = self.pressing.df
        team_row = df[df["Team"] == self.team.name].iloc[0]
        labels = PressingDescription.METRIC_LABELS
        total = len(df)
        lines = [f"Rankings for {self.team.name} (out of {total} teams):"]
        for m in self.team.relevant_metrics:
            if m + "_Ranks" not in df.columns:
                continue
            # Competition ranking ("1224"): tied teams share the best position.
            ascending = m in self.pressing.negative_metrics
            rank = int(df[m].rank(method="min", ascending=ascending)[team_row.name])
            tied = (df[m] == team_row[m]).sum() > 1
            label = labels.get(m, m)
            lines.append(f"- {label}: {rank} / {total}{' (joint)' if tied else ''}")
        return "\n".join(lines)

    def _get_season_trend(self, metric=None):
        from classes.pressing_timeseries import PressingTimeSeries, METRIC_DEFS
        from classes.visual import PressingTimeSeriesPlot

        ts = PressingTimeSeries()
        try:
            df = ts.season_trend(self.team.name, metric=metric)
        except ValueError as e:
            return str(e)
        if df.empty:
            return f"No season pressing data found for {self.team.name}."

        if metric is None:
            metric_label = "Composite Press Strength (mean z-score)"
        else:
            metric_label = METRIC_DEFS[metric][0]

        plot = PressingTimeSeriesPlot()
        plot.add_season_line(df, self.team.name, metric_label)
        self.add_message(plot)

        best_idx = df["value_z"].idxmax()
        worst_idx = df["value_z"].idxmin()
        best = df.loc[best_idx]
        worst = df.loc[worst_idx]
        scheduled = ts.scheduled_match_count(self.team.name)
        missing = scheduled - len(df)
        missing_note = (
            f" ({missing} of {scheduled} matches missing from the event dataset)"
            if missing > 0
            else ""
        )
        return (
            f"{self.team.name} season pressing trend ({metric_label}):\n"
            f"- Matches plotted: {len(df)}{missing_note}\n"
            f"- Strongest pressing performance: vs {best['opponent']} on "
            f"{best['date'].strftime('%Y-%m-%d')} (value={best['value']:.2f}, z={best['value_z']:+.2f})\n"
            f"- Weakest pressing performance: vs {worst['opponent']} on "
            f"{worst['date'].strftime('%Y-%m-%d')} (value={worst['value']:.2f}, z={worst['value_z']:+.2f})\n"
            f"- Season mean: {df['value'].mean():.2f}, std: {df['value'].std():.2f}"
        )

    def _get_intra_match(self, match_id=None):
        from classes.pressing_timeseries import PressingTimeSeries
        from classes.visual import PressingTimeSeriesPlot

        ts = PressingTimeSeries()
        if match_id is None:
            match_id = ts.latest_match_id(self.team.name)
            if match_id is None:
                return f"No matches found for {self.team.name}."

        df = ts.intra_match(self.team.name, match_id=match_id)
        match_label = ts.match_label(self.team.name, match_id)

        if df.empty:
            return f"No pressing data found for {self.team.name} in {match_label}."

        plot = PressingTimeSeriesPlot()
        plot.add_intra_match_line(df, self.team.name, match_label, "Pressing chains per 5 min")
        self.add_message(plot)

        first_half, second_half = ts.half_split(self.team.name, match_id)
        peak_value = int(df["value"].max())
        peak_buckets = df.loc[df["value"] == peak_value, "bucket"].astype(int)
        peak_windows = ", ".join(f"minute {b}–{b + 5}" for b in peak_buckets)
        each = " each" if len(peak_buckets) > 1 else ""
        return (
            f"{self.team.name} intra-match pressing ({match_label}):\n"
            f"- Total pressing chains: {int(df['value'].sum())}\n"
            f"- First half (incl. stoppage time): {first_half} chains\n"
            f"- Second half (incl. stoppage time): {second_half} chains\n"
            f"- Peak window(s): {peak_windows} with {peak_value} chains{each}"
        )

    def _run_tool(self, name, args):
        if name == "get_team_pressing_summary":
            return self._get_team_summary()
        if name == "search_pressing_knowledge":
            return self._search_knowledge(args["query"])
        if name == "compare_team_pressing":
            return self._compare_team(args["other_team"])
        if name == "get_league_rankings":
            return self._get_rankings()
        if name == "get_season_pressing_trend":
            return self._get_season_trend(metric=args.get("metric"))
        if name == "get_intra_match_pressing":
            match_id = args.get("match_id")
            # Gemini returns all numbers as floats.
            return self._get_intra_match(
                match_id=int(match_id) if match_id is not None else None
            )
        return f"Unknown tool: {name}"

    def handle_input(self, input, reasoning_effort=None, temperature=0.3, stream=False):
        if USE_LM_STUDIO:
            super().handle_input(
                input,
                reasoning_effort=reasoning_effort,
                temperature=temperature,
                stream=stream,
            )
            return
        if USE_GEMINI:
            self.handle_input_gemini_tools(input, temperature=temperature, stream=stream)
            return

        # OpenAI function-calling path (mirrors PlayerChat.handle_input).
        messages = self.instruction_messages()
        messages = messages + self.messages_to_display.copy()
        messages = [m for m in messages if isinstance(m["content"], str)]
        messages.append({"role": "user", "content": f"```User: {input}```"})

        self.messages_to_display.append({"role": "user", "content": input})

        client = OpenAI(api_key=GPT_KEY, base_url=GPT_BASE)

        # Call 1: routing pass — model picks one tool, or none.
        r1 = client.responses.create(
            model=GPT_CHAT_MODEL,
            input=messages,
            tools=self.tools,
            tool_choice="auto",
        )
        fc = next((item for item in r1.output if item.type == "function_call"), None)

        if fc is None:
            # No tool fired — model declined or chose to answer directly.
            st.expander("Chat transcript", expanded=False).write(
                [
                    {"role": m.get("role"), "content": m.get("content", "")}
                    for m in messages
                    if isinstance(m, dict)
                ]
            )
            self.messages_to_display.append(
                {"role": "assistant", "content": r1.output_text}
            )
            return

        result = self._run_tool(fc.name, json.loads(fc.arguments) if fc.arguments else {})

        # Call 2: answer pass — model writes the final reply, no more tools.
        tool_inputs = (
            list(messages)
            + list(r1.output)
            + [
                {
                    "type": "function_call_output",
                    "call_id": fc.call_id,
                    "output": result,
                }
            ]
        )

        formatted = []
        for item in tool_inputs:
            if isinstance(item, dict):
                if item.get("type") == "function_call_output":
                    formatted.append(
                        {
                            "tool_result": item["output"] or "(empty)",
                            "call_id": item["call_id"],
                        }
                    )
                else:
                    formatted.append(
                        {"role": item.get("role"), "content": item.get("content", "")}
                    )
            elif hasattr(item, "type"):
                if item.type == "function_call":
                    formatted.append(
                        {"tool_call": item.name, "arguments": json.loads(item.arguments)}
                    )
        st.expander("Chat transcript", expanded=False).write(formatted)

        if stream:
            if GPT_SUPPORTS_REASONING:
                reasoning_effort = (
                    reasoning_effort
                    if reasoning_effort in GPT_AVAILABLE_REASONING_EFFORTS
                    else GPT_AVAILABLE_REASONING_EFFORTS[0]
                )
                response_stream = client.responses.create(
                    model=GPT_CHAT_MODEL,
                    input=tool_inputs,
                    tool_choice="none",
                    tools=self.tools,
                    reasoning={"effort": reasoning_effort},
                    stream=True,
                )
            elif GPT_SUPPORTS_TEMPERATURE:
                response_stream = client.responses.create(
                    model=GPT_CHAT_MODEL,
                    input=tool_inputs,
                    tool_choice="none",
                    tools=self.tools,
                    temperature=temperature,
                    stream=True,
                )
            else:
                response_stream = client.responses.create(
                    model=GPT_CHAT_MODEL,
                    input=tool_inputs,
                    tool_choice="none",
                    tools=self.tools,
                    stream=True,
                )

            def streamed_chunks():
                for event in response_stream:
                    if event.type == "response.output_text.delta":
                        yield event.delta

            answer = streamed_chunks()
        else:
            if GPT_SUPPORTS_REASONING:
                reasoning_effort = (
                    reasoning_effort
                    if reasoning_effort in GPT_AVAILABLE_REASONING_EFFORTS
                    else GPT_AVAILABLE_REASONING_EFFORTS[0]
                )
                response = client.responses.create(
                    model=GPT_CHAT_MODEL,
                    input=tool_inputs,
                    tool_choice="none",
                    tools=self.tools,
                    reasoning={"effort": reasoning_effort},
                )
            elif GPT_SUPPORTS_TEMPERATURE:
                response = client.responses.create(
                    model=GPT_CHAT_MODEL,
                    input=tool_inputs,
                    tool_choice="none",
                    tools=self.tools,
                    temperature=temperature,
                )
            else:
                response = client.responses.create(
                    model=GPT_CHAT_MODEL,
                    input=tool_inputs,
                    tool_choice="none",
                    tools=self.tools,
                )
            answer = response.output_text

        self.messages_to_display.append({"role": "assistant", "content": answer})

    def get_relevant_info(self, query):
        # Used only by the LM Studio fallback path via super().handle_input.
        ret_val = "Here is a description of the team in terms of pressing data: \n\n"
        if not hasattr(self, "_cached_synth_text"):
            self._cached_synth_text = PressingDescription(self.team).synthesized_text
        ret_val += self._cached_synth_text
        if self.embeddings.df_dict is not None and not self.embeddings.df_dict.empty:
            results = self.embeddings.search(query, top_n=5)
            if not results.empty:
                ret_val += (
                    "\n\nHere is some relevant information for answering the question: \n"
                )
                ret_val += "\n".join(results["assistant"].astype(str).to_list())
        ret_val += (
            "\n\nIf none of this information is relevant to the user's query, remind them that this chat "
            "is about team pressing statistics versus the league. The user can select another team from the menu on the left."
        )
        return ret_val


class WVSChat(Chat):
    def __init__(
        self,
        chat_state_hash,
        country,
        countries,
        description_dict,
        thresholds_dict,
        state="empty",
    ):
        # TODO:
        self.embeddings = CountryEmbeddings()
        self.country = country
        self.countries = countries
        self.description_dict = description_dict
        self.thresholds_dict = thresholds_dict
        super().__init__(chat_state_hash, state=state)

    def get_input(self):
        """
        Get input from streamlit."""

        if x := st.chat_input(
            placeholder=f"What else would you like to know about {self.country.name}?"
        ):
            if len(x) > 500:
                st.error(
                    f"Your message is too long ({len(x)} characters). Please keep it under 500 characters."
                )

            if self.allow_question():
                self.handle_input(x, stream=True)

    def instruction_messages(self):
        """
        Instruction for the agent.
        """
        # TODO: Update first_messages
        first_messages = [
            {"role": "system", "content": "You are a researcher."},
            {
                "role": "user",
                "content": (
                    "After these messages you will be interacting with a user of a data analysis platform. "
                    f"The user has selected the country {self.country.name}, and the conversation will be about different core value measured in the World Value Survey study. "
                    # "You will receive relevant information to answer a user's questions and then be asked to provide a response. "
                    "All user messages will be prefixed with 'User:' and enclosed with ```. "
                    "When responding to the user, speak directly to them. "
                    "Use the information provided before the query to provide 2 sentence answers."
                    " Do not deviate from this information or provide additional information that is not in the text returned by the functions."
                ),
            },
        ]
        return first_messages

    def get_relevant_info(self, query):

        # If there is no query then use the last message from the user
        if query == "":
            query = self.visible_messages[-1]["content"]

        ret_val = "Here is a description of the country in terms of data: \n\n"
        description = CountryDescription(
            self.country, self.description_dict, self.thresholds_dict
        )
        ret_val += description.synthesize_text()

        # This finds some relevant information
        results = self.embeddings.search(query, top_n=5)
        ret_val += "\n\nHere is a description of some relevant information for answering the question:  \n"
        ret_val += "\n".join(results["assistant"].to_list())

        ret_val += f"\n\nIf none of this information is relevant to the users's query then use the information below to remind the user about the chat functionality: \n"
        ret_val += "This chat can answer questions about a country's core values."
        ret_val += "The user can select the country they are interested in using the menu to the left."

        return ret_val


class PersonChat(Chat):
    def __init__(self, chat_state_hash, person, persons, state="empty"):
        self.embeddings = PersonEmbeddings()
        self.person = person
        self.persons = persons
        super().__init__(chat_state_hash, state=state)

    def instruction_messages(self):
        """
        Instruction for the agent.
        """
        first_messages = [
            {"role": "system", "content": "You are a recruiter."},
            {
                "role": "user",
                "content": (
                    "After these messages you will be interacting with a user of personality test platform. "
                    f"The user has selected the person {self.person.name}, and the conversation will be about them. "
                    "You will receive relevant information to answer a user's questions and then be asked to provide a response. "
                    "All user messages will be prefixed with 'User:' and enclosed with ```. "
                    "When responding to the user, speak directly to them. "
                    "Use the information provided before the query  to provide 2 sentence answers."
                    " Do not deviate from this information or provide additional information that is not in the text returned by the functions."
                ),
            },
        ]
        return first_messages

    def get_relevant_info(self, query):

        # If there is no query then use the last message from the user
        if query == "":
            query = self.visible_messages[-1]["content"]

        ret_val = "Here is a description of the person in terms of data: \n\n"
        description = PersonDescription(self.person)
        ret_val += description.synthesize_text()

        # This finds some relevant information
        results = self.embeddings.search(query, top_n=5)
        ret_val += "\n\nHere is a description of some relevant information for answering the question:  \n"
        ret_val += "\n".join(results["assistant"].to_list())

        ret_val += f"\n\nIf none of this information is relevent to the users's query then use the information below to remind the user about the chat functionality: \n"
        ret_val += "This chat can answer questions about person's statistics and what they mean about their personality."
        ret_val += "The user can select the persons they are interested in using the menu to the left."

        return ret_val

    def get_input(self):
        """
        Get input from streamlit."""

        if x := st.chat_input(
            placeholder=f"What else would you like to know about {self.person.name}?"
        ):
            if len(x) > 500:
                st.error(
                    f"Your message is too long ({len(x)} characters). Please keep it under 500 characters."
                )

            if self.allow_question():
                self.handle_input(x, stream=True)
