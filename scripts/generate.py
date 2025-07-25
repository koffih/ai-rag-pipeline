from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

model_name = 'TheBloke/Mistral-7B-Instruct-v0.1-GPTQ'
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name, device_map='auto')

prompt = "Explique-moi simplement la différence entre une IA générative et une IA classique."

inputs = tokenizer(prompt, return_tensors='pt').to(model.device)
with torch.no_grad():
    outputs = model.generate(**inputs, max_new_tokens=200, do_sample=True, temperature=0.7)

print(tokenizer.decode(outputs[0], skip_special_tokens=True))
