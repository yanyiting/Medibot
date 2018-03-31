# =================================
# using for initialize data sets
# =================================
# import pandas as pd
import sample.jieba as jieba
import numpy as np
import progressbar
import logging
import csv
import multiprocessing as mp
from math import floor
from contextlib import contextmanager
import pickle


class Dataset():
    # private data
    _stopwordset = ''
    _splitsymbol = ''

    _counter = 0
    _bar = progressbar.ProgressBar(maxval=100)
    _raw_data = []
    _word_data = []
    _id_data = []
    # _vec_data = []
    _data_len = 0

    _split_scope_sum = 0
    _split_scope_1 = 0
    _split_scope_2 = 0

    # public data
    train_data = []
    valid_data = []
    test_data = []

    _id2vec_lookup_list = []
    _word2id_lookup_list = []
    # path
    _userdict = ''

    def __init__(self, *, filename, splitsymbol, word2id_file, id2vec_file, user_dict,  stopword_dict, prop):
        # ray.init(redis_address="127.0.0.1:35247")
        self._splitsymbol = splitsymbol

        # 初始化停用词表
        if(stopword_dict != []):
            self.set_stopword(stopword_dict)

        # 初始化自定义词表
        if(user_dict != []):
            self._userdict = user_dict

        # 加载词向量和id查找表
        _word2id_lookup_list = self.load_obj(word2id_file)
        _id2vec_lookup_list = np.load(id2vec_file)

        # 导入数据集
        # 读取csv, 创建dataframe
        print('导入数据集')
        with open(filename, "r") as csvFile:
            reader = csv.reader(csvFile)
            self._raw_data = [{'index': reader.line_num,
                               'question': row[0], 'answer': row[1]} for row in reader]
            csvFile.close()
        self._data_len = len(self._raw_data)

        # 分词
        print('\n\n分词')
        self._word_data = self.split_word(self._raw_data, '')

        # 切分数据集
        self.split_data_set(prop, self._word_data, self._data_len)

    def split_data_set(self, prop, data, len):
        """
        分配数据集
            :param self:
            :param prop:
        """   # split data
        # split=[]
        _split_scope_sum = sum(prop)
        _split_scope_1 = prop[0]/_split_scope_sum
        _split_scope_2 = prop[1]/_split_scope_sum

        train_data_begin = 0
        train_data_end = train_data_begin+floor(_split_scope_1*len)
        valid_data_begin = train_data_end+1
        valid_data_end = valid_data_begin+floor(_split_scope_2*len)
        test_data_begin = valid_data_end+1
        test_data_end = len-1

        self.train_data = data[train_data_begin:train_data_end]
        self.test_data = data[valid_data_begin:valid_data_end]
        self.valid_data = data[test_data_begin:test_data_end]

    def split_word(self, data, log_info):
        # 设置进度条
        with self.prograssbar(len(data)):
            return list(self.pool_map(self._split_data, data))

    def _split_data(self, data):
        """
        pair question and answer into one setence vector
            :param question:
            :param answer:
            :param negative:
            :param domain:
        """
        self._counter = self._counter + 1
        self._bar.update(self._counter)
        # self._bar.update_widgets
        # split words
        try:
            # 分词
            jieba.load_userdict(self._userdict)
            seg_question = jieba.lcut(data['question'])
            seg_answer = jieba.lcut(data['answer'])

            # 去除停用词
            if (self._stopwordset != []):
                seg_question = self.movestopwords(seg_question)
                seg_answer = self.movestopwords(seg_answer)

            # word2id
            id_question = map(self._word2id_lookup_list.get, seg_question)
            id_answer = map(self._word2id_lookup_list.get, seg_answer)

            result = [data['index'], seg_question,
                      seg_answer, id_question, id_answer]
            return result
        except Exception as e:
            print(e)

    def set_stopword(self, files):
        """
        load stop words
        """
        try:
            stopwords = ''
            for item in files:
                stopwords = ''.join(stopwords + '\n' + self.readfile(item))
            stopwordslist = stopwords.split('\n')
            not_stopword = set(['', '\n'])
            self._stopwordset = set(stopwordslist)
            self._stopwordset = self._stopwordset - not_stopword
        except Exception as e:
            print(e)

    def movestopwords(self, sentence):
        '''
        remove stop words
        '''
        try:
            def is_stopwords(word):
                if (word != '\t'and'\n') and (word not in self._stopwordset):
                    return word and word.strip()
            res = list(filter(is_stopwords, sentence))
        except Exception as e:
            print(e)

        return res

    def savefile(self, savepath, content):
        '''
        save files
        '''
        try:
            fp = open(savepath, 'w', encoding='utf8', errors='ignore')
            fp.write(content)
            fp.close()
        except Exception as e:
            print(e)

    def readfile(self, path):
        '''
        read files
        '''
        try:
            fp = open(path, "r", encoding='utf8', errors='ignore')
            content = fp.read()
            fp.close()
        except Exception as e:
            print(e)

        return content

    def save_obj(self, obj, name):
        with open(name, 'wb') as f:
            pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)

    def load_obj(self, name):
        with open(name, 'rb') as f:
            return pickle.load(f)

    @contextmanager
    def prograssbar(self, maxvalue):
        self._bar.maxval = maxvalue
        self._bar.start()
        self._counter = 0
        yield
        self._bar.finish()

    def pool_map(self, _map, _data):
        '''
        多线程map
        '''
        with mp.Pool(processes=(mp.cpu_count() - 1)) as pool:
            return pool.map(_map, _data)
