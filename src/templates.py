class PromptTemplate:
    """
    Handles formatting for different LLM model families.
    """
    PHI = "phi"
    LLAMA = "llama"
    CHATML = "chatml"

    TEMPLATES = {
        PHI: "Instruct: {prompt}\nOutput:",
        LLAMA: "<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n",
        CHATML: "<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"
    }

    @staticmethod
    def format(prompt, model_type=PHI):
        template = PromptTemplate.TEMPLATES.get(model_type, PromptTemplate.TEMPLATES[PromptTemplate.PHI])
        return template.format(prompt=prompt)
