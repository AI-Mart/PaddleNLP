# Copyright (c) 2022 PaddlePaddle Authors. All Rights Reserved.
# Copyright 2021 deepset GmbH. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import logging
import pandas as pd
from json import JSONDecodeError
from pathlib import Path
import streamlit as st
from annotated_text import annotation
from markdown import markdown

sys.path.append('ui')
from utils import pipelines_is_ready, semantic_search, send_feedback, upload_doc, pipelines_version, get_backlink

# Adjust to a question that you would like users to see in the search bar when they load the UI:
DEFAULT_QUESTION_AT_STARTUP = os.getenv("DEFAULT_QUESTION_AT_STARTUP",
                                        "燃气热水器哪个牌子好?")
DEFAULT_ANSWER_AT_STARTUP = os.getenv("DEFAULT_ANSWER_AT_STARTUP", "北京")

# Sliders
DEFAULT_DOCS_FROM_RETRIEVER = int(os.getenv("DEFAULT_DOCS_FROM_RETRIEVER",
                                            "30"))
DEFAULT_NUMBER_OF_ANSWERS = int(os.getenv("DEFAULT_NUMBER_OF_ANSWERS", "3"))

# Whether the file upload should be enabled or not
DISABLE_FILE_UPLOAD = bool(os.getenv("DISABLE_FILE_UPLOAD"))


def set_state_if_absent(key, value):
    if key not in st.session_state:
        st.session_state[key] = value


def main():

    st.set_page_config(
        page_title="pipelines 语义检索",
        page_icon=
        "https://github.com/PaddlePaddle/Paddle/blob/develop/doc/imgs/logo.png")

    # Persistent state
    set_state_if_absent("question", DEFAULT_QUESTION_AT_STARTUP)
    set_state_if_absent("results", None)
    set_state_if_absent("raw_json", None)
    set_state_if_absent("random_question_requested", False)

    # Small callback to reset the interface in case the text of the question changes
    def reset_results(*args):
        st.session_state.answer = None
        st.session_state.results = None
        st.session_state.raw_json = None

        # Title

    st.write("# PaddleNLP语义检索")
    #st.markdown(
    #    """
    #    基于开源最强 **ERNIE 3.0** 预训练模型和 DuReader 数据集搭建的语义检索系统
    #
    #    您可以输入 query 进行语义检索，例如:
    #    1. 燃气热水器哪些品牌比较好？
    #    2. 亚马逊河流的介绍
    #   """,
    #    unsafe_allow_html=True,
    #)

    # Sidebar
    st.sidebar.header("选项")
    top_k_reader = st.sidebar.slider(
        "最大的答案的数量",
        min_value=1,
        max_value=30,
        value=DEFAULT_NUMBER_OF_ANSWERS,
        step=1,
        on_change=reset_results,
    )
    top_k_retriever = st.sidebar.slider(
        "最大检索数量",
        min_value=1,
        max_value=100,
        value=DEFAULT_DOCS_FROM_RETRIEVER,
        step=1,
        on_change=reset_results,
    )

    if not DISABLE_FILE_UPLOAD:
        st.sidebar.write("## 文件上传:")
        data_files = st.sidebar.file_uploader(
            "",
            type=["pdf", "txt", "docx", "png"],
            help="文件上传",
            accept_multiple_files=True)
        for data_file in data_files:
            # Upload file
            if data_file:
                raw_json = upload_doc(data_file)
                st.sidebar.write(str(data_file.name) + " &nbsp;&nbsp; ✅ ")
    hs_version = ""
    try:
        hs_version = f" <small>(v{pipelines_version()})</small>"
    except Exception:
        pass

    # Search bar
    question = st.text_input("",
                             value=st.session_state.question,
                             max_chars=100,
                             on_change=reset_results)
    col1, col2 = st.columns(2)
    col1.markdown("<style>.stButton button {width:100%;}</style>",
                  unsafe_allow_html=True)
    col2.markdown("<style>.stButton button {width:100%;}</style>",
                  unsafe_allow_html=True)

    # Run button
    run_pressed = col1.button("运行")

    # Get next random question from the CSV
    if col2.button("随机生成"):
        reset_results()
        new_row = df.sample(1)
        while (
                new_row["Question Text"].values[0] == st.session_state.question
        ):  # Avoid picking the same question twice (the change is not visible on the UI)
            new_row = df.sample(1)
        st.session_state.question = new_row["Question Text"].values[0]
        st.session_state.random_question_requested = True
        # Re-runs the script setting the random question as the textbox value
        # Unfortunately necessary as the Random Question button is _below_ the textbox
        st.experimental_rerun()

    st.session_state.random_question_requested = False

    run_query = (run_pressed or question != st.session_state.question
                 ) and not st.session_state.random_question_requested

    # st.write(question)
    # Check the connection
    with st.spinner("⌛️ &nbsp;&nbsp; pipelines is starting..."):
        if not pipelines_is_ready():
            st.error("🚫 &nbsp;&nbsp; Connection Error. Is pipelines running?")
            run_query = False
            reset_results()

    # Get results for query
    if run_query and question:
        reset_results()
        st.session_state.question = question

        with st.spinner(
                "🧠 &nbsp;&nbsp; Performing neural search on documents... \n "
                "Do you want to optimize speed or accuracy? \n"):
            try:
                st.session_state.results, st.session_state.raw_json = semantic_search(
                    question,
                    top_k_reader=top_k_reader,
                    top_k_retriever=top_k_retriever)
            except JSONDecodeError as je:
                st.error(
                    "👓 &nbsp;&nbsp; An error occurred reading the results. Is the document store working?"
                )
                return
            except Exception as e:
                logging.exception(e)
                if "The server is busy processing requests" in str(
                        e) or "503" in str(e):
                    st.error(
                        "🧑‍🌾 &nbsp;&nbsp; All our workers are busy! Try again later."
                    )
                else:
                    st.error(
                        "🐞 &nbsp;&nbsp; An error occurred during the request.")
                return

    if st.session_state.results:

        st.write("## 返回结果:")

        for count, result in enumerate(st.session_state.results):
            context = result["context"]
            st.write(
                #markdown(context[:start_idx] + str(annotation(answer, "ANSWER", "#8ef")) + context[end_idx:]),
                markdown(context),
                unsafe_allow_html=True,
            )
            st.write("**Relevance:** ", result["relevance"])

            st.write("___")


main()
