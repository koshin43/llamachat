from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.llms.base import LLM
from typing import Any, List, Optional
import re
import requests
import os

LLM_ENDPOINT = os.getenv("LLM_ENDPOINT")

def predict(prompt):
    inference_request = {

    "inputs": [

        {

          "name": "question",

          "shape": [1,],

          "datatype": "BYTES",

          "data": ["[INST]\n"+prompt+"\n[\INST]\n"],

          "parameters": {

              "content_type": "np"

          }

        },

    ]

}


    response = requests.post(LLM_ENDPOINT, json=inference_request, verify=False)
    res = response.json()
    output = res["outputs"][0]["data"][0].split("[\INST]\n")[1]
    return output

class CustomLLM(LLM):
    #n: int

    @property
    def _llm_type(self) -> str:
        return "custom"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        if stop is not None:
            raise ValueError("stop kwargs are not permitted.")
        prompt = re.sub(r'([ \t]+)', ' ', prompt)
        a = predict(prompt)
        return a