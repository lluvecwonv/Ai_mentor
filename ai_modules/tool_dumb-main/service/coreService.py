from util.llmClient import LlmClient


class coreService():

    def __init__(self):
        self.llmClient = LlmClient()
        
        
    def execute(self, query: str):

        system_prompt = """
            [Guideline]
            - You are an AI chatbot that answers simple questions from users.
            - Your responses should always be concise and clear, informative.
            - Your responses must always be in **Korean**, no matter what language the user uses to ask the question.
        """

        return self.llmClient.call_llm(system_prompt, query)