#!/usr/bin/env python
#coding=utf-8

'''
@author: Marco Damonte (s1333293@inf.ed.ac.uk)
@since: 2-06-16
'''

import sys
sys.path.append("..")
import re
import src.amr
from alignments import Alignments as Alignments

reload(sys)
sys.setdefaultencoding('utf8')

import decimal
import random

def format_number(num):
    try:
        dec = decimal.Decimal(num)
    except:
        return 'bad'
    tup = dec.as_tuple()
    delta = len(tup.digits) + tup.exponent
    digits = ''.join(str(d) for d in tup.digits)
    if delta <= 0:
        zeros = abs(tup.exponent) - len(tup.digits)
        val = '0.' + ('0'*zeros) + digits
    else:
        val = digits[:delta] + ('0'*tup.exponent) + '.' + digits[delta:]
    val = val.rstrip('0')
    if val[-1] == '.':
        val = val[:-1]
    if tup.sign:
        return '-' + val
    return val

class AMRSentence:
        def __init__(self, tokens, pos, lemmas, nes, dependencies, variables = None, relations = None, graph = None, alignments = None, amr_api = None):
                self.tokens = tokens
                self.pos = pos
                self.lemmas = lemmas
                self.nes = nes
                self.dependencies = dependencies
                if variables is not None:
                    self.variables = [(str(k),str(variables[k])) for k in variables] 
                if relations is not None:
                    self.relations = [r for r in relations if r[0] != r[2]]
                self.graph = graph
                self.alignments = alignments
                self.amr_api = amr_api

class AMRDataset:
    def __init__(self, prefix, amrs, normalize = True):
        self.normalize = normalize
        self.sentences = []

        alltokens, allpos, alllemmas, allnes, alldepslines = self._loadFromFile(prefix + ".out")
        if amrs:
            allgraphs = open(prefix + ".graphs").read().split("\n\n")
            a = Alignments(prefix + ".alignments", allgraphs)
            allalignments = a.alignments

            for graph, alignments, depslines, tokens, pos, lemmas, nes in zip(allgraphs, allalignments, alldepslines, alltokens, allpos, alllemmas, allnes):
                    graph = graph.strip()
                    amr_api = src.amr.AMR(graph)
                    variables = amr_api.var2concept()
                    v2c = amr_api.var2concept()
                    root_v = str(amr_api.triples(rel=':top')[0][2])
                    root_c = str(amr_api.triples(head=src.amr.Var(root_v))[0][2])
                    relations = []
                    relations.append(("TOP",":top",root_v))
                    for (var1,label,var2) in amr_api.role_triples():
                            relations.append((str(var1),str(label),str(var2)))

                    dependencies = []
                    for line in depslines.split("\n"):
                            pattern = "^(.+)\(.+-([0-9]+), .+-([0-9]+)\)"
                            regex = re.match(pattern, line)
                            if regex is not None:
                                    label = regex.group(1)
                                    a = int(regex.group(2)) - 1
                                    b = int(regex.group(3)) - 1
                                    if a == -1:
                                            dependencies.append((b, 'ROOT', b))
                                    elif a != b:
                                            dependencies.append((a, label, b))

                    self.sentences.append(AMRSentence(tokens, pos, lemmas, nes, dependencies, variables, relations, graph, alignments, amr_api))
        else:
            for depslines, tokens, pos, lemmas, nes in zip(alldepslines, alltokens, allpos, alllemmas, allnes):
                    dependencies = []
                    for line in depslines.split("\n"):
                            pattern = "^(.+)\(.+-([0-9]+), .+-([0-9]+)\)"
                            regex = re.match(pattern, line)
                            if regex is not None:
                                    label = regex.group(1)
                                    a = int(regex.group(2)) - 1
                                    b = int(regex.group(3)) - 1
                                    if a == -1:
                                            dependencies.append((b, 'ROOT', b))
                                    elif a != b:
                                            dependencies.append((a, label, b))

                    self.sentences.append(AMRSentence(tokens, pos, lemmas, nes, dependencies))


    def getSent(self, index):
        return self.sentences[index]

    def getAllSents(self):
        return self.sentences

    def _loadFromFile(self, stanfordOutput):
            alltokens = []
            allpos = []
            alllemmas = []
            allnes = []
            alldepslines = []
            blocks = open(stanfordOutput, 'r').read().split("\n\n")
            while True:
                    if len(blocks) == 1:
                            break
                    block = blocks.pop(0).strip().split("\n")
                    
		    i = 2
                    tokens = []
                    lemmas = []
                    nes = []
                    pos = []
                    while block[i].startswith("[Text"):
                        tokens.extend([t[5:-1] for t in re.findall('Text=[^\s]* ', block[i])])
                        pos.extend([t[13:-1] for t in re.findall('PartOfSpeech=[^\s]* ', block[i])])
                        lemmas.extend([t[6:-1] for t in re.findall('Lemma=[^\s]* ', block[i])])
                        nes.extend([t[15:] for t in re.findall('NamedEntityTag=[^\]]*', block[i])])
                        i += 1
                    allpos.append(pos)
                    #tokens = [t[5:-1] for t in re.findall('Text=[^\s]* ', block[2])]
                    #allpos.append([t[13:-1] for t in re.findall('PartOfSpeech=[^\s]* ', block[2])])
                    #lemmas = [t[6:-1] for t in re.findall('Lemma=[^\s]* ', block[2])]
                    #nes = [t[15:] for t in re.findall('NamedEntityTag=[^\]]*', block[2])]
                    if blocks[0].startswith("\n"):
                            b = ""
                    else:
                            b = blocks.pop(0)
                    depslines = b
                    tokens2 = []
                    lemmas2 = []
                    nes2 = []
                    for token, lemma, ne in zip(tokens, lemmas, nes):
                            nesplit = ne.split()
                            if len(nesplit) > 1:
                                    mne = re.match("^([a-zA-Z\%\>\<\$\~\=]*)([0-9\.]*.*)", nesplit[1][25:].encode('ascii', 'ignore'))
                            else:
                                    mne = None
                            if nesplit[0] == "DATE" and re.match("^(\d{4}|XXXX)(-\d{2})?(-\d{2})?$",nesplit[1][25:]) is not None:
                                norm = nesplit[1][25:]
                                lastnorm = norm
                                tokens2.append(norm)
                                lemmas2.append(norm)
                                nes2.append(nesplit[0])

                            elif (nesplit[0] == "MONEY" or nesplit[0] == "PERCENT") and self.normalize and len(nesplit) == 2 and mne is not None:
                                    [name, norm] = nesplit
                                    curr = mne.groups()[0]
                                    norm = mne.groups()[1]
                                    curr = curr.replace("<","").replace(">","").replace("~","").replace("=","")
                                    if curr == "$":
                                            curr = "dollar"
                                    if curr == "":
                                            w = nesplit[1][25:].replace("<","").replace(">","").replace("~","").replace("=","")
                                            if w.startswith(u"\u00A5"):
                                                    curr = "yen"
                                            elif w.startswith(u"\u5143"):
                                                     curr = "yuan"
                                            elif w.startswith(u"\u00A3"):
                                                    curr = "pound"
                                            elif w.startswith(u"\u20AC"):
                                                    curr = "euro"
                                            else:
                                                    curr = "NULL"
                                    m = re.match("([0-9\.][0-9\.]*)E([0-9][0-9]*)$",norm)
                                    if m is not None:
                                            n = m.groups()[0]
                                            z = "".join(["0"]*int(m.groups()[1]))
                                            #norm = format_number(float(n)*int("1"+z))
                     			    #norm = '{:f}'.format(float(n)*float("1"+z))
					    norm = format(float(n)*float("1"+z), ".32f")
					    norm = re.sub("\.00*$","",norm)
                                    if token.endswith(".0") == False:
                                            norm = re.sub("\.0$","",norm)
                                    if token.replace(",","").replace(".","").isdigit() == False and lastnorm is not None:
                                            norm = "," #use commas because I know it will be dropped and I want to preserve the number of tokens
                                            token = ","
                                            name = "O"
                                    lastnorm = norm
                                    if norm == ",":
                                            tokens2.append(norm)
                                    else:
                                            tokens2.append(norm + "_" + curr)
                                    lemmas2.append(token)
                                    nes2.append(name)
                            elif self.normalize and len(nesplit) == 2 and re.match("^[0-9].*", nesplit[1][25:]) is not None: #numbers
                                    [name, norm] = nesplit
                                    norm = norm[25:]
                                    m = re.match("([0-9\.][0-9\.]*)E([0-9][0-9]*)$",norm)
                                    if m is not None:
                                            n = m.groups()[0]
                                            z = "".join(["0"]*int(m.groups()[1]))
                                            norm = str(float(n)*int("1"+z))
                                    if token.endswith(".0") == False:
                                            norm = re.sub("\.0$","",norm)
                                    if token.replace(",","").replace(".","").isdigit() == False and lastnorm is not None:
                                            norm = "," #use commas because I know it will be dropped and I want to preserve the number of tokens
                                            token = ","
                                            name = "O"
                                    lastnorm = norm
                                    tokens2.append(norm)
                                    lemmas2.append(token)
                                    nes2.append(name)
                            else:
                                    lastnorm = None
                                    tokens2.append(token)
                                    lemmas2.append(lemma)
                                    nes2.append(nesplit[0])
                    alltokens.append(tokens2)
                    alllemmas.append(lemmas2)
                    allnes.append(nes2)
                    alldepslines.append(depslines)
            return (alltokens, allpos, alllemmas, allnes, alldepslines)

    def _normalize(self, token):
            if re.match("[0-9]+,[0-9]+", token) != None:
                    token = token.replace(",",".")
            return token