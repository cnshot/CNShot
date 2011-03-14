#!/usr/bin/python
#coding:utf-8

import os
import mmseg
import sys
import subprocess
import tempfile
import scipy
import math
import logging

from chinese_stop_words import chinese_stop_words
from scipy import spatial

chinese_dict = {}
chinese_dict_count = ord(u"龥") - ord(u"一") + 1

def build_dict():
    words = open(os.path.join(os.path.dirname(mmseg.__file__), 'data', 'words.dic'))
    try:
        for i in words:
            i = i.strip()
            if not i:continue
            b = i.split()
            b = b[-1]

            global chinese_dict, chinese_dict_count
            
            chinese_dict[b] = chinese_dict_count
            chinese_dict_count += 1
    finally:
        words.close()

def str2freqhash(s):
    r = {}
    for i in mmseg.seg_txt(s):
        # print i
        if chinese_stop_words.has_key(i):
            # print "Stop word: %s" % i
            continue
        if len(i) > 3:
            try:
                l = chinese_dict[i]
            except KeyError:
                # skip non-chinese words
                continue
            try:
                r[l] += 1
            except KeyError:
                r[l] = 1
        elif len(i) > 0:
            uc = i.decode("utf-8", "ignore")[0]
            if u"一" <= uc <= u"龥":
                # chinese characters only
                l = ord(uc) - ord(u"一")
                try:
                    r[l] += 1
                except KeyError:
                    r[l] = 1
    return r

def dump_freqhash_matrix(hashs, output=sys.stdout):
    items_count = 0
    for i in hashs:
        items_count += len(i.keys())
    print >>output, "%d %d %d" % (len(hashs), chinese_dict_count, items_count)
    for i in hashs:
        for k in i.keys():
            print>>output, "%d %d" % (k, i[k]) ,
        print >>output

def dump_matrix(m, output=sys.stdout):
    print >>output, "%d %d %d" % (m.shape[0], m.shape[1], len(m.keys()))
    n = 0
    while n < m.shape[0]:
        try:
            x = m[n,:]
            for k in x.keys():
                print>>output, "%d %d" % (k[1], x[k]) ,
        finally:
            print >>output
            n += 1

def cluto_vcluster(matrix_dump, matrix_size, cluster_sim_threshold=0.5,
                   vcluster_cmd='/usr/bin/vcluster'):
    cluster_file = tempfile.NamedTemporaryFile(delete=False)
    cluster_file_name = cluster_file.name
    cluster_file.close()

    # print cluster_file_name

    args = [vcluster_cmd, '/dev/stdin', '%d' % (matrix_size/50+1), '-clmethod=graph', '-sim=dist',
            '-agglofrom=%d' % (matrix_size/10+1), '-clustfile=%s'%cluster_file_name]
    p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    p.stdin.write(matrix_dump)
    p.stdin.close()

    p.stdout.read()

    f = open(cluster_file_name)
    l = 0
    r = {}
    for s in f:
        try:
            n = int(s)
            if n < 0:
                continue
            if not r.has_key(n):
                r[n] = []
            r[n].append(l)
        finally:
            l += 1

    f.close()
    os.unlink(cluster_file_name)

    return r

def sparse_hash_matrix(h,column_count):
    m = scipy.sparse.dok_matrix((len(h), column_count)) #@UndefinedVariable
    n = 0
    for i in h:
        for j in i.keys():
            m[n,j] = i[j]
        n += 1
    return m

def cluster_center(m):
    avg = scipy.sparse.dok_matrix(m.sum(axis=0) / m.shape[0]) #@UndefinedVariable
    return avg

def cluster_center_similarity(m):
    ma = m.toarray()
    x = spatial.distance.cdist(ma, ma, 'cos')
    i = scipy.zeros((1,1)) #@UndefinedVariable
    i[0,0] = math.e
    # print i
    t = i**scipy.array(-x) #@UndefinedVariable
    # print t
    # logger.debug("%s", str(t))        
    # print m.shape               # 
    similarity = (t.sum()-m.shape[0])/(m.shape[0])/(m.shape[0]-1)
    center_id = t.sum(axis=1).argmax(axis=0)
    return (similarity, center_id)

def filter_knowns(news, knowns, similarity_threshold=0.5):
    # logger.debug("%s", str(news))
    # logger.debug("%s", str(knowns))
    x = spatial.distance.cdist(news, knowns, 'cos')
    i = scipy.zeros((1,1)) #@UndefinedVariable
    i[0,0] = math.e
    x = i**scipy.array(-x) #@UndefinedVariable
    # logger.debug("%s", str(x))
    return map(lambda i: ((i < similarity_threshold) and [False] or [True])[0],
               x.max(axis=1))

def hash_filter_knowns(news, knowns, similarity_threshold=0.5):
    logger.debug("Size of news: %d", news.size)
    logger.debug("Size of knowns: %d", knowns.size)
    return filter_knowns(sparse_hash_matrix(news, chinese_dict_count).toarray(),
                         sparse_hash_matrix(knowns, chinese_dict_count).toarray(),
                         similarity_threshold)

def vcluster_with_sample(hashs,
                         cluster_sim_threshold=0.5,
                         cluster_item_threshold=4,
                         cluster_item_limit=20,
                         vcluster_cmd='/usr/bin/vcluster'):
    import StringIO
    output_stream = StringIO.StringIO()

    dump_freqhash_matrix(hashs, output=output_stream)
    
    s = output_stream.getvalue()
    output_stream.close()

    r = cluto_vcluster(s, len(hashs), vcluster_cmd=vcluster_cmd)
    
    clusters = []
    for k in r:
        # print "%d:%s" % (k, r[k])
        if len(r[k]) < cluster_item_threshold:
            continue
        if len(r[k]) > cluster_item_limit:
            logger.debug("Cluster with size over the limit %d: %d",
                         cluster_item_limit, len(r[k]))
        c = 0.0
        hm = []
        n = 0
        for i in r[k]:
            c += len(hashs[i])
            hm.append(hashs[i])
            n += 1
            if n>= cluster_item_limit:
                logger.debug("Stop sampling")
                break
        # print "%f" % (c/len(r[k]))
        m = sparse_hash_matrix(hm, chinese_dict_count)
        # ma = cluster_center(m)
        (s, c) = cluster_center_similarity(m)
        if s < cluster_sim_threshold:
            logger.debug("Ignore cluster with similarity less than threshold: %f",
                         s)
            continue
        clusters.append((s, r[k][c], r[k]))
        
    return clusters

build_dict()

if __name__ == '__main__':    
    # for k in chinese_dict.keys():
    #     print "%s : %d" % (k, chinese_dict[k])

    from optparse import OptionParser

    logging.basicConfig(level=logging.DEBUG)
    logger = logging

    description = '''Chinese word frequency and clustering.'''
    parser = OptionParser(usage="usage: %prog [options]",
                          version="%prog 0.1, Copyright (c) 2010 Chinese Shot",
                          description=description)

    parser.add_option("-v", "--vcluster",
                      dest="vcluster",
                      default='/usr/bin/vcluster',
                      type='string',
                      help='Path of vcluster command [default %default].',
                      metavar="VCLUSTER")

    (options,args) = parser.parse_args()
    if len(args) != 0:
        parser.error("incorrect number of arguments")

    print chinese_dict_count

    from tweet_samples import tweet_samples

    strings = ["开普敦为南非人口排名第二大城市，为西开普省省会，亦为南非立法首都，因为南非国会及很多政府部门亦座落于该市。",
               "我对新技术、新方法、新思路总是抱有较大的兴趣，善于自我学习。我有较强的毅力，注意自身素质的提高，包括身体素质和知识素质。我积极，敢于承担压力、敢于挑战。我敬业，能集中注意力完成当前的主要任务。我清楚团队的作用，能够有效地和同事合作，从他们身上学到不足的，并且努力影响他们共同进步。",
               "诺贝尔和平奖公布在即，4大门户的诺贝尔奖专题全被删除：网易：http://bit.ly/8ZEfo0 搜狐：http://bit.ly/amVmm6 腾讯：http://bit.ly/ao5BEZ 新浪：http://bit.ly/a8NX2T",
               ]

    rs = []

    for s in tweet_samples:
        # print s
        r = str2freqhash(s)
        # for k in r:
        #     print "%d : %d" % (k, r[k])
        rs.append(r)

    clusters = vcluster_with_sample(rs, vcluster_cmd=options.vcluster)

    for (s, c, r) in clusters:
        print
        print s
        print tweet_samples[c]
        print '----'
        for i in r:
            print tweet_samples[i]
