import json
import torch
import os
import argparse
from fairseq.models.roberta import RobertaModel
from examples.roberta import social_iqa  # load the Commonsense QA task


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_path", default=None, type=str, required=True,
                        help="Path to pre-trained model")
    parser.add_argument(
            "--knowledge_layer",
            nargs='+',
            default=[-1, 0],
            help="Layers that would add kowledge embedding",
        )
    parser.add_argument(
            "--data_file",
            type=str,
            default='../data/social_iqa/test.jsonl',
            help="The data to be evaluate",
        )
    args = parser.parse_args()
    roberta = RobertaModel.from_pretrained(args.model_path, 'checkpoint_best.pt', '../data/social_iqa/', knowledge_layer=args.knowledge_layer)
    """
        - from_pretrained está en la clase RobertaModel que está en el fichero model.py. Aquí dentro se llama a otro 
          from_pretrained del fichero hub_utils.py (esto tampoco es muy importante)
        - Importante: el primer argumento es el path al modelo, el segundo el checkpoint del modelo a obtener, el 
          tercero es el path a los datos y luego van los datos de knowledge (lo de add_args).
        - Return: un objeto del tipo "RobertaHubInterface" que es una interfaz entre Roberta y Pytorch
    """

    print(roberta)
    roberta.eval()  # disable dropout
    roberta.cuda()  # use the GPU (optional)
    nsamples, ncorrect = 0, 0
    max_know_length = 45

    print(f"{'*' * 20}\n\nARGS:{'*' * 20}\n\n{args}\n\n")

    with torch.no_grad():
        """
            - Esto pone le argumento 'requires_grad' a False
        """
        with open(args.data_file) as h:
            for line in h:
                example = json.loads(line)
                scores = []
                knowledges = example["knowledges"]
                know_bin = []
                for know in knowledges:
                    bina_know = roberta.encode(know, not_a_sentence=True)
                    bina_know = bina_know[:max_know_length]
                    padding_length = max_know_length - len(bina_know)
                    bina_know = torch.cat((bina_know, torch.tensor([1] * padding_length, dtype=torch.int64)))
                    know_bin.append(bina_know)
                knowledge_bin = torch.stack(know_bin).unsqueeze(0)
                for choice in example['choices']:
                    input = roberta.encode(
                        example['context'],
                        'Q: ' + example['question'],
                        'A: ' + choice['text'],
                        no_separator=True
                    )
                    score = roberta.predict('sentence_classification_head', input, return_logits=True, knowledge = knowledge_bin)
                    # score = roberta.predict('sentence_classification_head', input, return_logits=True)
                    scores.append(score)
                pred = torch.cat(scores).argmax()
                answer = int(example['AnswerKey']) - 1
                nsamples += 1
                if pred == answer:
                    ncorrect += 1
    result = {
        'acc': ncorrect / float(nsamples)
    }
    print('Accuracy: ' + str(ncorrect / float(nsamples)))
    output_file = os.path.join(args.model_path, "eval_out.txt")
    with open(output_file, "w") as writer:
        writer.write(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

