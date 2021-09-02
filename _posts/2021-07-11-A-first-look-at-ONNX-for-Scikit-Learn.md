---
layout: post
title:  "Machine Learning Models Light as a Feather with ONNX"
description: How to train a text classification model with Scikit-Learn and deploy it for prediction with ONNX.
---
**Have you ever faced the challenge to create a fast, lightweight and powerfull API out of your machine learning model? In this case you've probably cursed the bloatware introduced by all the machine learning dependencies from the training environment that you also need to carry over to the production web service. This post shows an approach which makes it possible to leave most of this behind and share the blank model in a way that it can even be used across multiple programming languages.**


## What is ONNX?

## Training an example model

## Converting to ONNX format

## Deploying for Production Inference

## Summary



## Notes
Older attempt: (PMML)[http://dmg.org/pmml/v4-4-1/GeneralStructure.html]
- https://en.wikipedia.org/wiki/Predictive_Model_Markup_Language

(KNNF)[https://www.khronos.org/nnef/] for neural networks

Tutorials: https://github.com/onnx/tutorials

SKlearn about model serialization (also mentioning ONNX and PMML): https://scikit-learn.org/stable/modules/model_persistence.html

Netron to view model: https://github.com/lutzroeder/netron
Online at: https://netron.app/

Example with onnx + tfidf: http://onnx.ai/sklearn-onnx/auto_examples/plot_tfidfvectorizer.html

ONNX + JS MNIST example: https://microsoft.github.io/onnxruntime-web-demo/#/mnist


## Issues

### Locale setting
2021-07-16 00:08:07.123770858 [E:onnxruntime:, inference_session.cc:1340 operator()] Exception during initialization: /onnxruntime_src/onnxruntime/core/providers/cpu/nn/string_normalizer.cc:89 onnxruntime::string_normalizer::Locale::Locale(const string&)::<lambda()> Failed to construct locale with name:en_US.UTF-8:locale::facet::_S_create_c_locale name not valid:Please, install necessary language-pack-XX and configure locales

    Certain operators makes use of system locales. Installation of the English language package and configuring en_US.UTF-8 locale is required.
        For Ubuntu install language-pack-en package
        Run the following commands: locale-gen en_US.UTF-8 update-locale LANG=en_US.UTF-8
        Follow similar procedure to configure other locales on other platforms.

https://github.com/faxu/onnxruntime

### Unicode handling of TFIDF

```python
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import StringTensorType

initial_type = [('string_input', StringTensorType([None, 1]))]
onx = convert_sklearn(clf_pipeline, initial_types=initial_type)
with open("data/classifier.onnx", "wb") as f:
    f.write(onx.SerializeToString())
```

This way only languages in roman letters are correctly identified:
```
              precision    recall  f1-score   support

      Arabic       0.00      0.00      0.00       106
      Danish       0.93      0.96      0.95        73
       Dutch       0.98      0.98      0.98       111
     English       0.35      1.00      0.52       291
      French       0.96      0.98      0.97       219
      German       0.93      0.98      0.95        93
       Greek       0.00      0.00      0.00        68
       Hindi       0.00      0.00      0.00        10
     Italian       0.96      0.99      0.98       145
     Kannada       0.50      0.02      0.03        66
   Malayalam       0.00      0.00      0.00       121
  Portugeese       0.90      0.94      0.92       144
     Russian       0.29      0.04      0.07       136
     Spanish       0.96      0.96      0.96       160
    Sweedish       0.93      0.94      0.93       133
       Tamil       0.00      0.00      0.00        87
     Turkish       0.98      0.92      0.95       105

    accuracy                           0.69      2068
   macro avg       0.57      0.57      0.54      2068
weighted avg       0.63      0.69      0.62      2068
```

See pictures from Netron

The problem is the tokenization. sklearn's tfidf uses the regular expression `"(?u)\b\w\w+\b"` 
to define a word. This is a sequence of two or more unicode code points. (See https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html).
The onnx C++ runtime uses a different regular expression library and per default changes the 
expression to `[a-zA-Z0-9_]+` which is something entirely different, because it means one or more
standard roman letters, digits or underscores. http://onnx.ai/sklearn-onnx/parameterized.html#tfidfvectorizer-countvectorizer
The resulting tokens are incompatible with the vocabulary build up in tfidf by sklearn during the 
training.


## Further topics
Manipulate onnx graphs with sclblonnx: https://towardsdatascience.com/creating-editing-and-merging-onnx-pipelines-897e55e98bb0