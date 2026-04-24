from abc import ABC, abstractmethod
from typing import List, Union, Dict

import pandas as pd

from openai import OpenAI


import utils.sentences as sentences
from utils.gemini import convert_messages_format
from utils.text import clean_mojibake

from classes.data_point import Player, Country, Person, PressingTeam
from classes.data_source import PersonStat

import json

from settings import USE_GEMINI, USE_LM_STUDIO

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

import streamlit as st



class Description(ABC):
    gpt_examples_base = "data/gpt_examples"
    describe_base = "data/describe"

    @property
    @abstractmethod
    def gpt_examples_path(self) -> str:
        """
        Path to excel files containing examples of user and assistant messages for the GPT to learn from.
        """

    @property
    @abstractmethod
    def describe_paths(self) -> Union[str, List[str]]:
        """
        List of paths to excel files containing questions and answers for the GPT to learn from.
        """

    def __init__(self):
        self.synthesized_text = self.synthesize_text()
        self.messages = self.setup_messages()

    def synthesize_text(self) -> str:
        """
        Return a data description that will be used to prompt GPT.

        Returns:
        str
        """

    def get_prompt_messages(self) -> List[Dict[str, str]]:
        """
        Return the prompt that the GPT will see before self.synthesized_text.

        Returns:
        List of dicts with keys "role" and "content".
        """

    def get_intro_messages(self) -> List[Dict[str, str]]:
        """
        Constant introduction messages for the assistant.

        Returns:
        List of dicts with keys "role" and "content".
        """
        intro = [
            {
                "role": "system",
                "content": (
                    "You are a data analysis bot. "
                    "You provide succinct and to the point explanations about data using data. "
                    "You use the information given to you from the data and answers "
                    "to earlier user/assistant pairs to give summaries of players."
                ),
            },
        ]
        if len(self.describe_paths) > 0:
            intro += [
                {
                    "role": "user",
                    "content": "First, could you answer some questions about the data for me?",
                },
                {"role": "assistant", "content": "Sure!"},
            ]

        return intro

    def get_messages_from_excel(
        self,
        paths: Union[str, List[str]],
    ) -> List[Dict[str, str]]:
        """
        Turn an excel file containing user and assistant columns with str values into a list of dicts.

        Arguments:
        paths: str or list of str
            Path to the excel file containing the user and assistant columns.

        Returns:
        List of dicts with keys "role" and "content".

        """

        # Handle list and str paths arg
        if isinstance(paths, str):
            paths = [paths]
        elif len(paths) == 0:
            return []

        # Concatenate dfs read from paths
        def _read(p):
            return pd.read_csv(p) if p.endswith(".csv") else pd.read_excel(p)

        df = _read(paths[0])
        for path in paths[1:]:
            df = pd.concat([df, _read(path)])

        if df.empty:
            return []

        # Convert to list of dicts
        messages = []
        for _, row in df.iterrows():
            messages.append({"role": "user", "content": row["user"]})
            messages.append({"role": "assistant", "content": row["assistant"]})

        return messages

    def setup_messages(self) -> List[Dict[str, str]]:
        messages = self.get_intro_messages()
        try:
            paths = self.describe_paths
            messages += self.get_messages_from_excel(paths)
        except (
            FileNotFoundError
        ) as e:  
            print(e)
        messages += self.get_prompt_messages()

        messages = [
            message for message in messages if isinstance(message["content"], str)
        ]

        try:
            messages += self.get_messages_from_excel(
                paths=self.gpt_examples_path,
            )
        except (
            FileNotFoundError
        ) as e:  
            print(e)

        messages += [
            {
                "role": "user",
                "content": f"Now do the same thing with the following: ```{self.synthesized_text}```",
            }
        ]
        messages = [
            message for message in messages if isinstance(message.get("content"), str)
        ]
        for message in messages:
            message["content"] = clean_mojibake(message["content"])
        return messages

    def stream_gpt(self, temperature=1, reasoning_effort=None, stream=False):
        """
        Run the GPT model on the messages and stream the output.

        Arguments:
        temperature: optional float
            The temperature of the GPT model.

        Yields:
            str
        """

        st.session_state["description_transcript"] = self.messages

        if USE_GEMINI:
            import google.generativeai as genai

            converted_msgs = convert_messages_format(self.messages)

            # # save converted messages to json
            # with open("data/wvs/msgs_0.json", "w") as f:
            #     json.dump(converted_msgs, f)

            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel(
                model_name=GEMINI_CHAT_MODEL,
                system_instruction=converted_msgs["system_instruction"],
            )
            chat = model.start_chat(history=converted_msgs["history"])
            response = chat.send_message(content=converted_msgs["content"])

            answer = clean_mojibake(response.text)
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
                        messages=self.messages,
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
                    messages=self.messages,
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
                        input=self.messages,
                        reasoning={"effort": reasoning_effort},
                        stream=True,
                    )
                elif GPT_SUPPORTS_TEMPERATURE:
                    response_stream = client.responses.create(
                        model=GPT_CHAT_MODEL,
                        input=self.messages,
                        temperature=temperature,
                        stream=True,
                    )
                else:
                    response_stream = client.responses.create(
                        model=GPT_CHAT_MODEL,
                        input=self.messages,
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
                        input=self.messages,
                        reasoning={"effort": reasoning_effort},
                    )
                elif GPT_SUPPORTS_TEMPERATURE:
                    response = client.responses.create(
                        model=GPT_CHAT_MODEL,
                        input=self.messages,
                        temperature=temperature,
                    )
                else:
                    response = client.responses.create(
                        model=GPT_CHAT_MODEL,
                        input=self.messages,
                    )

                answer = clean_mojibake(response.output_text)

        return answer


class PlayerDescription(Description):
    output_token_limit = 150

    @property
    def gpt_examples_path(self):
        return f"{self.gpt_examples_base}/Forward.xlsx"

    @property
    def describe_paths(self):
        return [f"{self.describe_base}/Forward.xlsx"]

    def __init__(self, player: Player):
        self.player = player
        super().__init__()

    def get_intro_messages(self) -> List[Dict[str, str]]:
        """
        Constant introduction messages for the assistant.

        Returns:
        List of dicts with keys "role" and "content".
        """
        intro = [
            {
                "role": "system",
                "content": (
                    "You are a UK-based football scout. "
                    "You provide succinct and to the point explanations about football players using data. "
                    "You use the information given to you from the data and answers "
                    "to earlier user/assistant pairs to give summaries of players."
                ),
            },
            {
                "role": "user",
                "content": "Do you refer to the game you are an expert in as soccer or football?",
            },
            {
                "role": "assistant",
                "content": (
                    "I refer to the game as football. "
                    "When I say football, I don't mean American football, I mean what Americans call soccer. "
                    "But I always talk about football, as people do in the United Kingdom."
                ),
            },
        ]
        if len(self.describe_paths) > 0:
            intro += [
                {
                    "role": "user",
                    "content": "First, could you answer some questions about football for me?",
                },
                {"role": "assistant", "content": "Sure!"},
            ]

        return intro

    def synthesize_text(self):

        player = self.player
        metrics = self.player.relevant_metrics
        description = f"Here is a statistical description of {player.name}, who played for {player.minutes_played} minutes as a {player.position}. \n\n "

        subject_p, object_p, possessive_p = sentences.pronouns(player.gender)

        for metric in metrics:

            description += f"{subject_p.capitalize()} was "
            description += sentences.describe_level(player.ser_metrics[metric + "_Z"])
            description += " in " + sentences.write_out_metric(metric)
            description += " compared to other players in the same playing position. "

        # st.write(description)

        return description

    def get_prompt_messages(self):
        prompt = (
            f"Please use the statistical description enclosed with ``` to give a concise, 4 sentence summary of the player's playing style, strengths and weaknesses. "
            f"The first sentence should use varied language to give an overview of the player. "
            "The second sentence should describe the player's specific strengths based on the metrics. "
            "The third sentence should describe aspects in which the player is average and/or weak based on the statistics. "
            "Finally, summarise exactly how the player compares to others in the same position. "
        )
        return [{"role": "user", "content": prompt}]


class PressingDescription(Description):
    output_token_limit = 250

    CONTEXT_CSV = "data/pressing/pressing_league_table.csv"
    BLOCK_PCT_COLUMN = "Block %"

    METRIC_LABELS = {
        "chains_pm": "Pressing Chains Per Match",
        "recovery_opp_half_pm": "Regains In Opp. Half Per Match",
        "force_long_ball_pm": "Opp. Long Balls Forced Per Match",
        "press_break_rate_opp_half": "Press Break Rate In Opp. Half",
        "lead_to_goal_after_broken_pm": "Opp. Goals After Broken Press Per Match",
        "pass_accuracy_under_pressure": "Opp. Pass Accuracy Under Pressure",
        "line_breaking_pass_rate_under_pressure": "Opp. Line-Breaking Pass Rate Under Pressure",
        "ppda": "PPDA",
    }

    # Direct consequence statements: metric -> level -> what happens on the pitch.
    # Removes all ambiguity about metric direction.
    METRIC_CONSEQUENCES = {
        "chains_pm": {
            "outstanding": "The team starts pressing sequences in the opposition half far more than any other side.",
            "excellent": "The team starts pressing sequences in the opposition half significantly more often than most.",
            "good": "The team starts pressing sequences in the opposition half more often than average.",
            "average": "The team starts pressing sequences in the opposition half at a typical rate.",
            "below average": "The team starts pressing sequences in the opposition half less often than most.",
            "poor": "The team rarely starts pressing sequences in the opposition half.",
        },
        "recovery_opp_half_pm": {
            "outstanding": "The team wins the ball back in the opposition half far more than any other side.",
            "excellent": "The team wins the ball back in the opposition half significantly more often than most.",
            "good": "The team wins the ball back in the opposition half more often than average.",
            "average": "The team wins the ball back in the opposition half at a typical rate.",
            "below average": "The team wins the ball back in the opposition half less often than most.",
            "poor": "The team rarely wins the ball back in the opposition half.",
        },
        "force_long_ball_pm": {
            "outstanding": "The press forces opponents into long balls far more than any other side.",
            "excellent": "The press forces opponents into long balls significantly more often than most.",
            "good": "The press forces opponents into long balls more often than average.",
            "average": "The press forces opponents into long balls at a typical rate.",
            "below average": "The press forces opponents into long balls less often than most.",
            "poor": "The press rarely forces opponents into long balls.",
        },
        "press_break_rate_opp_half": {
            "outstanding": "Opponents almost never escape the press in the opposition half.",
            "excellent": "Opponents rarely escape the press in the opposition half.",
            "good": "Opponents escape the press in the opposition half less often than against most teams.",
            "average": "Opponents escape the press in the opposition half at a typical rate.",
            "below average": "Opponents escape the press in the opposition half more often than against most teams.",
            "poor": "Opponents escape the press in the opposition half frequently — the press is easily broken.",
        },
        "lead_to_goal_after_broken_pm": {
            "outstanding": "When the press is broken, opponents almost never score — the rest-defence absorbs danger completely.",
            "excellent": "When the press is broken, opponents rarely score — the rest-defence contains the damage well.",
            "good": "When the press is broken, opponents score less often than against most teams.",
            "average": "When the press is broken, opponents score at a typical rate.",
            "below average": "When the press is broken, opponents score more often than against most teams.",
            "poor": "When the press is broken, opponents frequently score — the rest-defence is exposed.",
        },
        "pass_accuracy_under_pressure": {
            "outstanding": "Opponents struggle badly to complete passes under this team's pressure — passing accuracy collapses.",
            "excellent": "Opponents complete far fewer passes under this team's pressure — passing accuracy drops sharply.",
            "good": "Opponents find it harder to complete passes under this team's pressure than against most sides.",
            "average": "Opponents complete passes under this team's pressure at a typical rate.",
            "below average": "Opponents still complete passes fairly comfortably under this team's pressure.",
            "poor": "Opponents pass comfortably under this team's pressure — the press does little to disrupt passing accuracy.",
        },
        "line_breaking_pass_rate_under_pressure": {
            "outstanding": "Opponents almost never play through the defensive lines under this team's pressure.",
            "excellent": "Opponents rarely play through the defensive lines under this team's pressure — the pressing structure holds its shape.",
            "good": "Opponents break through the defensive lines under this team's pressure less often than against most sides.",
            "average": "Opponents break through the defensive lines under this team's pressure at a typical rate.",
            "below average": "Opponents break through the defensive lines under this team's pressure more often than against most sides.",
            "poor": "Opponents play through the defensive lines comfortably under this team's pressure.",
        },
        "ppda": {
            "outstanding": "The team steps in extremely early, allowing opponents almost no passes before a defensive action.",
            "excellent": "The team steps in early, allowing opponents very few passes before a defensive action.",
            "good": "The team steps in to break opponent sequences quicker than most.",
            "average": "The team allows a typical number of opponent passes before stepping in with a defensive action.",
            "below average": "The team is slow to step in, allowing opponents more passes before a defensive action than most.",
            "poor": "The team is very slow to step in — opponents circulate freely before any defensive action arrives.",
        },
    }

    @property
    def gpt_examples_path(self):
        return f"{self.gpt_examples_base}/Pressing_analyst.csv"

    @property
    def describe_paths(self):
        return [f"{self.describe_base}/Pressing_analyst.csv"]

    def __init__(self, team: PressingTeam):
        self.team = team
        super().__init__()

    def get_intro_messages(self) -> List[Dict[str, str]]:
        intro = [
            {
                "role": "system",
                "content": (
                    "You are a tactical data analyst embedded in a Premier League coaching staff. "
                    "You write concise pressing briefings for the head coach. "
                    "Your language is direct and action-oriented — you focus on what the data means tactically. "
                    "You write in British English and refer to the sport as football."
                ),
            },
            {
                "role": "user",
                "content": "Do you refer to the game as soccer or football?",
            },
            {
                "role": "assistant",
                "content": (
                    "I refer to the game as football. "
                    "I write for coaches, not commentators."
                ),
            },
        ]
        if len(self.describe_paths) > 0:
            intro += [
                {
                    "role": "user",
                    "content": "First, could you answer some questions about pressing metrics for me?",
                },
                {"role": "assistant", "content": "Sure!"},
            ]

        return intro

    PROFILE_METRICS = ("ppda", "chains_pm", "recovery_opp_half_pm")
    COST_METRIC = "lead_to_goal_after_broken_pm"

    def _block_context(self):
        team = self.team
        try:
            df_context = pd.read_csv(self.CONTEXT_CSV)
        except FileNotFoundError:
            return "", ""
        col = self.BLOCK_PCT_COLUMN
        if col not in df_context.columns:
            return "", ""
        team_row = df_context[df_context["Team"] == team.name]
        if team_row.empty:
            return "", ""
        pct = float(team_row[col].iloc[0])
        all_pcts = df_context[col]
        if all_pcts.std() == 0:
            return "", ""
        z = (pct - all_pcts.mean()) / all_pcts.std()
        if z >= 0.5:
            return "high", (
                f"{team.name} defend in a high or medium block for the great majority "
                "of their out-of-possession time, more than most teams in the league."
            )
        if z <= -0.5:
            return "deep", (
                f"{team.name} sit deeper than most, spending relatively little of "
                "their out-of-possession time in a high or medium block."
            )
        return "balanced", (
            f"{team.name} split their out-of-possession time between high/medium and "
            "low blocks at a typical rate for the league."
        )

    def _opening_sentence(self, ppda_z, chains_z, block_state):
        team_name = self.team.name
        if block_state == "high" and chains_z < -0.5:
            return (
                f"{team_name} defend high but press selectively, "
                "preferring controlled engagements over constant front-foot pressure."
            )
        if ppda_z > 1.0:
            return f"{team_name} press with aggressive intent from the front."
        if ppda_z < -1.0 and block_state == "deep":
            return (
                f"{team_name} defend from a deeper starting point and wait before engaging, "
                "giving opponents time on the ball."
            )
        if ppda_z < -1.0:
            return (
                f"{team_name} defend with a patient, passive approach, "
                "conceding space before engaging."
            )
        return f"{team_name} adopt a balanced approach to pressing."

    def _metric_z(self, metric):
        try:
            return float(self.team.ser_metrics.get(metric + "_Z", 0.0))
        except (TypeError, ValueError):
            return 0.0

    def _top_sentences(self, findings, limit=3):
        findings = sorted(findings, key=lambda item: item[0], reverse=True)
        return [sentence for _, sentence in findings[:limit]]

    def _profile_support_sentence(self, chains_z, recovery_z):
        if chains_z > 0.5 and recovery_z > 0.5:
            return (
                "They start plenty of high pressing sequences and regularly turn them "
                "into regains in the opposition half."
            )
        if chains_z > 0.5 and recovery_z < -0.5:
            return (
                "They step forward to press high often, but that volume does not turn "
                "into enough regains in advanced areas."
            )
        if chains_z < -0.5 and recovery_z > 0.5:
            return (
                "They do not press high constantly, yet when they do step forward they "
                "still recover the ball well in advanced areas."
            )
        if chains_z < -0.5 and recovery_z < -0.5:
            return (
                "They do not press high often, and the ball is rarely being won back "
                "in the opposition half."
            )
        if chains_z > 0.5:
            return (
                "They create plenty of high pressing moments, even if the regain return "
                "is closer to average."
            )
        if recovery_z > 0.5:
            return (
                "They recover the ball high more often than most, even without "
                "sustaining constant high pressure."
            )
        if chains_z < -0.5:
            return "The overall pressing volume is selective rather than constant."
        if recovery_z < -0.5:
            return "The press is not producing enough regains in the opposition half."
        return "The overall pressing volume and regain output sit close to the league norm."

    def _profile_cost_sentence(self, chains_z, recovery_z, block_state):
        if chains_z < -0.5 and recovery_z < -0.5:
            return (
                "That keeps the press from generating much territorial pressure "
                "higher up the pitch."
            )
        if chains_z < -0.5 and block_state == "high":
            return (
                "That profile limits how much territory they win through the press, "
                "even from an aggressive starting position."
            )
        if chains_z < -0.5:
            return (
                "That profile limits how much territorial pressure they create through "
                "the press."
            )
        if recovery_z < -0.5:
            return "That means the press is not generating enough territorial payoff after it engages."
        return ""

    def synthesize_text(self) -> str:
        team = self.team
        metrics = team.relevant_metrics

        ppda_z = self._metric_z("ppda")
        chains_z = self._metric_z("chains_pm")
        recovery_z = self._metric_z("recovery_opp_half_pm")
        reward_findings = []
        weakness_findings = []
        cost_findings = []

        for metric in metrics:
            z_key = metric + "_Z"
            if z_key not in team.ser_metrics.index:
                continue
            z = float(team.ser_metrics[z_key])
            level = sentences.describe_level(z)
            sentence = self.METRIC_CONSEQUENCES.get(metric, {}).get(level, "")
            if not sentence:
                continue

            if metric in self.PROFILE_METRICS:
                continue
            if metric == self.COST_METRIC:
                if z > 0.5:
                    reward_findings.append((abs(z), sentence))
                elif z < -0.5:
                    cost_findings.append((abs(z), sentence))
            elif z > 0.5:
                reward_findings.append((abs(z), sentence))
            elif z < -0.5:
                weakness_findings.append((abs(z), sentence))

        reward_sentences = self._top_sentences(reward_findings)
        weakness_sentences = self._top_sentences(weakness_findings)
        cost_sentences = self._top_sentences(cost_findings, limit=2)

        block_state, block_sentence = self._block_context()
        profile_sentences = [
            self._opening_sentence(ppda_z, chains_z, block_state),
            self._profile_support_sentence(chains_z, recovery_z),
        ]
        if block_sentence:
            profile_sentences.append(block_sentence)

        if reward_sentences:
            reward = (
                "The reward comes from what happens once they engage. "
                + " ".join(reward_sentences)
            )
        else:
            reward = (
                "Beyond the basic profile, the press offers only modest additional "
                "disruption once it engages."
            )

        risk_parts = []
        profile_cost_sentence = self._profile_cost_sentence(
            chains_z, recovery_z, block_state
        )
        if profile_cost_sentence:
            risk_parts.append(profile_cost_sentence)
        if weakness_sentences:
            risk_parts.append(
                "Once the first action is bypassed or softened, the press loses bite. "
                + " ".join(weakness_sentences)
            )
        if cost_sentences:
            risk_parts.append(
                "The bigger danger sits behind the press. "
                + " ".join(cost_sentences)
            )
        if risk_parts:
            risk = " ".join(risk_parts)
        else:
            risk = (
                "The risk profile is relatively clean: opponents are not exposing "
                "the structure regularly when the press breaks."
            )

        r = len(reward_findings)
        w = len(weakness_findings)
        c = len(cost_findings)
        p = 1 if profile_cost_sentence else 0

        if r > 0 and w == 0 and c == 0 and p == 0:
            closing = (
                "Overall, this is a front-foot pressing approach that combines pressure, "
                "disruption, and security."
            )
        elif r > 0 and p > 0 and w == 0 and c == 0:
            closing = (
                "Overall, this is a selective press: it works when triggered, but it is "
                "not built to dominate matches through constant territorial pressure."
            )
        elif r == 0 and w == 0 and c == 0 and p == 0:
            closing = (
                "Overall, this is a pressing approach that sits close to league average "
                "throughout."
            )
        elif r == 0 and (w > 0 or c > 0 or p > 0):
            closing = (
                "Overall, this pressing approach carries more risk than reward."
            )
        elif c > 0 and r > 0:
            closing = (
                "Overall, this is a press that can create problems when intact, "
                "but becomes costly when bypassed."
            )
        elif r > 0 and (w > 0 or p > 0):
            closing = (
                "Overall, this press can disrupt opponents, but the payoff comes with "
                "clear limits elsewhere in the profile."
            )
        else:
            closing = (
                "Overall, this is a measured pressing approach with rewards and risks "
                "in proportion."
            )

        profile = " ".join(profile_sentences)
        return (
            f"Pressing profile for {team.name}, benchmarked against the rest of the league.\n\n"
            f"{profile}\n\n{reward}\n\n{risk}\n\n{closing}"
        )

    def get_prompt_messages(self):
        return [
            {
                "role": "user",
                "content": (
                    "Rewrite the pressing briefing enclosed with ``` as a coach "
                    "would deliver it to their staff, as a single continuous "
                    "paragraph with no line breaks or blank lines. "
                    "Keep the total length under 120 words. Avoid repeating the "
                    "same observation. "
                    "Preserve all factual content and do not add any claim not "
                    "already in the text. "
                    "Use connectives — 'and', 'while', 'however', 'meanwhile', "
                    "'yet', 'although' — so the paragraph reads as a single "
                    "analytical thought rather than a list of separate sentences. "
                    "Do not add metric names, percentages, ranks, or level labels "
                    "(outstanding, excellent, good, average, below average, poor). "
                    "Do not invent consequences not supported by the text "
                    "(e.g. rapid restarts, transition speed, possession recycling). "
                    "Write as a tactical analyst briefing coaching staff in British English. "
                    "Output a single paragraph only — no headings, no bullet points, "
                    "no newline characters between sentences."
                ),
            },
            {
                "role": "assistant",
                "content": "Sure, please provide the pressing profile.",
            },
        ]


class CountryDescription(Description):
    output_token_limit = 150

    @property
    def gpt_examples_path(self):
        return f"{self.gpt_examples_base}/WVS_examples.xlsx"

    @property
    def describe_paths(self):
        return [f"{self.describe_base}/WVS_qualities.xlsx"]

    def __init__(self, country: Country, description_dict, thresholds_dict):
        self.country = country
        self.description_dict = description_dict
        self.thresholds_dict = thresholds_dict

        # read data/wvs/intermediate_data/relevant_questions.json
        with open("data/wvs/intermediate_data/relevant_questions.json", "r") as f:
            self.relevant_questions = json.load(f)

        super().__init__()

    def get_intro_messages(self) -> List[Dict[str, str]]:
        """
        Constant introduction messages for the assistant.

        Returns:
        List of dicts with keys "role" and "content".
        """
        intro = [
            {
                "role": "system",
                "content": (
                    "You are a data analyst and a social scientist. "
                    "You provide succinct and to the point explanations about countries using social factors derived from the World Value Survey. "
                    "You use the information given to you to answer questions about how countries score in various social factors that attempt to measure the social values held by the population of a country."
                ),
            },
        ]
        if len(self.describe_paths) > 0:
            intro += [
                {
                    "role": "user",
                    "content": "First, could you answer some questions about the World Value Survey for me?",
                },
                {"role": "assistant", "content": "Sure!"},
            ]

        return intro

    def synthesize_text(self):

        description = f"Here is a statistical description of the societal values of {self.country.name.capitalize()}."

        # subject_p, object_p, possessive_p = sentences.pronouns(country.gender)

        for metric in self.country.relevant_metrics:

            description += f"\n\nAccording to the WVS, {self.country.name.capitalize()} was found to "
            description += sentences.describe_level(
                self.country.ser_metrics[metric + "_Z"],
                thresholds=self.thresholds_dict[metric],
                words=self.description_dict[metric],
            )
            description += " compared to other countries in the same wave. "

            if metric in self.country.drill_down_metrics:

                if self.country.ser_metrics[metric + "_Z"] > 0:
                    index = 1
                else:
                    index = 0

                question, value = self.country.drill_down_metrics[metric]
                question, value = question[index], value[index]
                description += "In response to the question '"
                description += self.relevant_questions[metric][question][0]
                description += "', on average participants "
                description += self.relevant_questions[metric][question][1]
                description += " '"
                description += self.relevant_questions[metric][question][2][str(value)]
                description += "' "
                description += self.relevant_questions[metric][question][3]
                description += ". "

        # st.write(description)

        return description

    def get_prompt_messages(self):
        prompt = (
            f"Please use the statistical description enclosed with ``` to give a concise, 2 short paragraph summary of the social values held by population of the country. "
            f"The first paragraph should focus on any factors or values for which the country is above or bellow average. If the country is neither above nor below average in any values, mention that. "
            f"The remaining paragraph should mention any specific values or factors that are neither high nor low compared to the average. "
        )
        return [{"role": "user", "content": prompt}]


class PersonDescription(Description):
    output_token_limit = 150

    @property
    def gpt_examples_path(self):
        return f"{self.gpt_examples_base}/Forward_bigfive.xlsx"

    @property
    def describe_paths(self):
        return [f"{self.describe_base}/Forward_bigfive.xlsx"]

    def __init__(self, person: Person):
        self.person = person
        super().__init__()

    def get_intro_messages(self) -> List[Dict[str, str]]:
        """
        Constant introduction messages for the assistant.

        Returns:
        List of dicts with keys "role" and "content".
        """
        intro = [
            {
                "role": "system",
                "content": (
                    "You are a recruiter. "
                    "You provide succinct and to the point explanations about a candidate using data.  "
                    "You use the information given to you from the data and answers"
                    "to earlier user/assistant pairs to give summaries of candidates."
                ),
            },
            {
                "role": "user",
                "content": "Do you refer to the candidate as a candidate or a person?",
            },
            {
                "role": "assistant",
                "content": (
                    "I refer to the candidate as a person. "
                    "When I say candidate, I mean person. "
                    "But I always talk about the candidate, as a person."
                ),
            },
        ]
        if len(self.describe_paths) > 0:
            intro += [
                {
                    "role": "user",
                    "content": "First, could you answer some questions about a candidate for me?",
                },
                {"role": "assistant", "content": "Sure!"},
            ]

        return intro

    def categorie_description(self, value):
        if value <= -2:
            return "The candidate is extremely "
        elif -2 < value <= -1:
            return "The candidate is very "
        elif -1 < value <= -0.5:
            return "The candidate is quite "
        elif -0.5 < value <= 0.5:
            return "The candidate is relatively "
        elif 0.5 < value <= 1:
            return "The candidate is quite "
        elif 1 < value <= 2:
            return "The candidate is very "
        else:
            return "The candidate is extremely "

    def all_max_indices(self, row):
        max_value = row.max()
        return list(row[row == max_value].index)

    def all_min_indices(self, row):
        min_value = row.min()
        return list(row[row == min_value].index)

    def get_description(self, person):
        # here we need the dataset to check the min and max score of the person

        person_metrics = person.ser_metrics
        person_stat = PersonStat()
        questions = person_stat.get_questions()

        name = person.name
        extraversion = person_metrics["extraversion_Z"]
        neuroticism = person_metrics["neuroticism_Z"]
        agreeableness = person_metrics["agreeableness_Z"]
        conscientiousness = person_metrics["conscientiousness_Z"]
        openness = person_metrics["openness_Z"]

        text = []

        # extraversion
        cat_0 = "solitary and reserved. "
        cat_1 = "outgoing and energetic. "

        if extraversion > 0:
            text_t = (self.categorie_description(extraversion) 
            + cat_1
            + "The candidate tends to be more social. "
                     )
            if extraversion > 1:
                index_max = person_metrics[0:10].idxmax()
                text_2 = (
                    "In particular they said that " + questions[index_max][0] + ". "
                )
                text_t += text_2
        else:
            text_t = (self.categorie_description(extraversion) 
            + cat_0
            + "The candidate tends to be less social. "
                     )
            if extraversion < -1:
                index_min = person_metrics[0:10].idxmin()
                text_2 = (
                    "In particular they said that " + questions[index_min][0] + ". "
                )
                text_t += text_2
        text.append(text_t)

        # neuroticism
        cat_0 = "resilient and confident. "
        cat_1 = "sensitive and nervous. "

        if neuroticism > 0:
            text_t = (
                self.categorie_description(neuroticism)
                + cat_1
                + "The candidate tends to feel more negative emotions and anxiety. "
            )
            if neuroticism > 1:
                index_max = person_metrics[10:20].idxmax()
                text_2 = (
                    "In particular they said that " + questions[index_max][0] + ". "
                )
                text_t += text_2

        else:
            text_t = (
                self.categorie_description(neuroticism)
                + cat_0
                + "The candidate tends to feel less negative emotions and anxiety. "
            )
            if neuroticism < -1:
                index_min = person_metrics[10:20].idxmin()
                text_2 = (
                    "In particular they said that " + questions[index_min][0] + ". "
                )
                text_t += text_2
        text.append(text_t)

        # agreeableness
        cat_0 = "critical and rational. "
        cat_1 = "friendly and compassionate. "

        if agreeableness > 0:
            text_t = (
                self.categorie_description(agreeableness)
                + cat_1
                + "The candidate tends to be more cooperative, polite, kind and friendly. "
            )
            if agreeableness > 1:
                index_max = person_metrics[20:30].idxmax()
                text_2 = (
                    "In particular they said that " + questions[index_max][0] + ". "
                )
                text_t += text_2

        else:
            text_t = (
                self.categorie_description(agreeableness)
                + cat_0
                + "The candidate tends to be less cooperative, polite, kind and friendly. "
            )
            if agreeableness < -1:
                index_min = person_metrics[20:30].idxmin()
                text_2 = (
                    "In particular they said that " + questions[index_min][0] + ". "
                )
                text_t += text_2
        text.append(text_t)

        # conscientiousness
        cat_0 = "extravagant and careless. "
        cat_1 = "efficient and organized. "

        if conscientiousness > 0:
            text_t = (
                self.categorie_description(conscientiousness)
                + cat_1
                + "The candidate tends to be more careful or diligent. "
            )
            if conscientiousness > 1:
                index_max = person_metrics[30:40].idxmax()
                text_2 = (
                    "In particular they said that " + questions[index_max][0] + ". "
                )
                text_t += text_2
        else:
            text_t = (
                self.categorie_description(conscientiousness)
                + cat_0
                + "The candidate tends to be less careful or diligent. "
            )
            if conscientiousness < -1:
                index_min = person_metrics[30:40].idxmin()
                text_2 = (
                    "In particular they said that " + questions[index_min][0] + ". "
                )
                text_t += text_2
        text.append(text_t)

        # openness
        cat_0 = "consistent and cautious. "
        cat_1 = "inventive and curious. "

        if openness > 0:
            text_t = (
                self.categorie_description(openness)
                + cat_1
                + "The candidate tends to be more open to new ideas and experiences. "
            )
            if openness > 1:
                index_max = person_metrics[40:50].idxmax()
                text_2 = (
                    "In particular they said that " + questions[index_max][0] + ". "
                )
                text_t += text_2
        else:
            text_t = (
                self.categorie_description(openness)
                + cat_0
                + "The candidate tends to be less open to new ideas and experiences. "
            )
            if openness < -1:
                index_min = person_metrics[40:50].idxmin()
                text_2 = (
                    "In particular they said that " + questions[index_min][0] + ". "
                )
                text_t += text_2
        text.append(text_t)

        text = "".join(text)
        text = text.replace(",", "")
        return text

    def synthesize_text(self):
        person = self.person
        metrics = self.person.ser_metrics
        description = self.get_description(person)

        return description

    def get_prompt_messages(self):
        prompt = (
            f"Please use the statistical description enclosed with ``` to give a concise, 4 sentence summary of the person's personality, strengths and weaknesses. "
            f"The first sentence should use varied language to give an overview of the person. "
            "The second sentence should describe the person's specific strengths based on the metrics. "
            "The third sentence should describe aspects in which the person is average and/or weak based on the statistics. "
            "Finally, summarise exactly how the person compares to others in the same position. "
        )
        return [{"role": "user", "content": prompt}]
