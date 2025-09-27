from typing import List, Optional, Union
from pydantic import BaseModel, ConfigDict

class OpenAIChatMessage(BaseModel):
    role: str
    content: Union[str, List]

    model_config = ConfigDict(extra="allow")


class OpenAIChatCompletionForm(BaseModel):
    stream: bool = True
    model: str
    messages: List[OpenAIChatMessage]

    model_config = ConfigDict(extra="allow")


class FilterForm(BaseModel):
    body: dict
    user: Optional[dict] = None
    model_config = ConfigDict(extra="allow")