---
layout: post
title:  "Machine Learning Models Light as a Feather"
description: How to train a text classification model with Scikit-Learn and deploy it for prediction with ONNX.
---
**Have you ever faced the challenge to create a fast, lightweight and powerfull API out of your machine learning model? In this case you've probably cursed the bloatware introduced by all the machine learning dependencies from the training environment that you also need to carry over to the production web service. This post tests an approach which should make it possible to leave most of this behind and share the blank model in a way that it can even be used across multiple programming languages.**

ONNX, the "Open Neural Network Exchange" format is an open specification for sharing machine learning models which was released into the open in December 2018 under the liberal MIT license. It is developed by big players of the software industry, amongst them Microsoft, Amazon and Facebook. Also there is growing support by hardware companies like Nvidia or AMD for hardware optimizations. The format covers both deep learning and more traditional model types. It isn't only about the representation of the models, but there is also an [open source runtime](https://onnxruntime.ai/) attached to it which can do inference in multiple programming languages. The runtime is written in plain C, maybe because there is a C compiler for nearly everything that runs on electricity. And maybe that means that one day also the ONNX runtime can run on everything from a supercomputer to an NFC banking card. For now it already has an impressive record of supported environments. Most remarkably it has support for many of the main programming languages like C++, C#, Java, Python and even partially for Javascript. 

ONNX models are typically not created directly. Only recently some support for model training was added to the ONNX runtime. The usual way is to create a model in one of the traditional machine learning frameworks and do a conversion afterwards. There are converters for CoreML, Keras, PyTorch, Scikit-Learn, XGBoost and more. 

So the initiative is promising. But can it keep its promises? In the course of this blog post I'll pick an example to see how ONNX actually performs in practice.

## Training an example model
There's a lot of image processing examples out there. But let us take a look at something simpler and maybe more typical for bread-and-butter machine learning: a text classification. The task is to read a short text and decide which language it is written in. This is solved here with a [Tf-idf](https://en.wikipedia.org/wiki/Tf%E2%80%93idf) ngram embedding and a [Naive Bayes classifier](https://en.wikipedia.org/wiki/Naive_Bayes_classifier). Both algorithms are readily available in scikit-learn.

The training data is borrowed from a [kaggle competition](https://www.kaggle.com/basilb2s/language-detection). It is a labeled list of short text fragments in 17 different languages. The distribution is of languages is relatively equal. These are some examples of the data:

Text                                                                                                                                                                | Language
--------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------
dans un pays anglophone, vous pouvez totalement l'utiliser.                                                                                                         | French
झिझक रहा है। यह एक अच्छा सवाल है। मुझे देखने दो। एक पल के लिए मुझे सोचने दो। दुबारा दोहराने के लिए पूछें। क्षमा कीजिय?                                              | Hindi
terry sen aslında o meleğe biraz benziyorsun ama ne görüyorum, nasıl o olursun ikiniz çok hoşsunuz                                                                  | Turkish
அது எப்படி நடக்கிறது?                                                                                                                                               | Tamil
Кроме того, по мнению Шекмана, проблема в том, что редакторы этих журналов являются не учёными, а издателями и их интересуют прежде всего шумиха, сенсация и фурор. | Russian

As this is just for demonstration purposes, we  dont't spend more time on data exploration but continue with creating a model. We start our machine learning task by splitting the data into a train and a test set, so that we can later measure the performance:
```python
data = pd.read_csv(data_folder / "LanguageDetection.csv", sep=",")
x = data["Text"].values
y = data["Language"].values
x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42)
```

The next step is to create a scikit-learn pipeline for the preprocessing and training. The two steps in the pipeline are the Tf-idf vectorizer and a Naive Bayes model.
```python
from sklearn.pipeline import Pipeline
from sklearn.naive_bayes import MultinomialNB
from sklearn import metrics
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer


clf_pipeline = Pipeline([
    ("tfidf", TfidfVectorizer(token_pattern=r"[\w_]{2,}", lowercase=False)),
    ("naive_bayes", MultinomialNB(alpha=.01)),
])
clf_pipeline.fit(x_train, y_train)
```

Now that we have a model, we can already test it and measure its prediction quality:
```python
pred = clf_pipeline.predict(x_test)

print(metrics.classification_report(y_test, pred))
```

Language      | precision   | recall     | f1-score   | support
--------------|-------------|------------|------------|----------
Arabic        | 1.00        | 0.98       | 0.99       | 106
Danish        | 0.99        | 0.96       | 0.97       | 73
Dutch         | 0.99        | 0.98       | 0.99       | 111
English       | 0.92        | 1.00       | 0.96       | 291
French        | 1.00        | 0.99       | 0.99       | 219
German        | 1.00        | 0.98       | 0.99       | 93
Greek         | 1.00        | 1.00       | 1.00       | 68
Hindi         | 1.00        | 1.00       | 1.00       | 10
Italian       | 1.00        | 0.99       | 0.99       | 145
Kannada       | 1.00        | 1.00       | 1.00       | 66
Malayalam     | 1.00        | 0.98       | 0.99       | 121
Portugeese    | 0.99        | 0.97       | 0.98       | 144
Russian       | 1.00        | 0.99       | 0.99       | 136
Spanish       | 0.99        | 0.97       | 0.98       | 160
Sweedish      | 0.99        | 0.98       | 0.99       | 133
Tamil         | 1.00        | 0.99       | 0.99       | 87
Turkish       | 1.00        | 0.98       | 0.99       | 105
--------------|-------------|------------|------------|----------
**accuracy**  |             |            | 0.98       | 2068
**macro avg** | 0.99        | 0.98       | 0.99       | 2068
**weighted avg**| 0.99        | 0.98       | 0.98       | 2068


The prediction results are amazingly good. It was low effort to create the model, but nevertheless the overall accuracy score is 98%. So apparently the data is good and the problem simple. In any case it looks as if the solution works reliable enough to be used in production. So let's see how we can expose the model for inference.

## Serializing the model with pickle
The easiest way to pack this model for running in a different environment is to pickle it:
```python
with (output_folder / "classifier.pickle").open("wb") as f:
    pickle.dump(clf_pipeline, f)
```

This is done often enough, but it has a couple of disadvantages. Two important ones are:
1. You can only use the model in Python again.
2. Pickle stores type names and values of the object which is pickled including all its attributes. That means to deserialize ("unpickle") the object again you need to have the original source code and the complete environment which was there when the object was stored. Otherwise, for example if the source code has changed in the meantime pickle might throw an exception like `Attribute error: 'X' object has no attribute 'y'`. Or if a dependency is missing you might get `ImportError: No module named 'X'`.

The first one is an inherent problem because pickle is language specific. The second one can be circumvented partially if the objects are stripped down to the most relevant parts before serialization. So fore example one might create a json object with all the relevant parameters and weights of the models and only store this in a file. So it is possible to read the data also in a different context if only the format of the data is known. However, this needs  careful attention and therefore won't be done in many cases.


## Converting to ONNX format
Pickling of the sklearn objects has some disadvantages and designing a custom serialization format seems inconvenient. So it would be nice if with ONNX we'd get a standard solution for this problem that can be used without a custom implementation of the (de-)serialization.



## Deploying for Production Inference

## Comparison of the Scikit-learn and Onnx models

- disk size
- memory
- prediction speed
- dependencies (GB size difference of API images)

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