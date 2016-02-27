# -*- coding: utf-8 -*-
"""
Created on Fri Feb 26 19:16:38 2016

@author: yiyuezhuo
"""

import requests
from lxml import etree
from bs4 import BeautifulSoup
from collections import Counter
import bs4

def getXPathMode(el):
    l=[]
    while True:
        l.append(el.name)
        if el.parent!=None:
            el=el.parent
        else:
            break
    l.reverse()
    return '/'.join(l)
    
def getIndexPath(el):
    '''通过children中位置，即index序列来定位元素并进行外推'''
    l=[]
    eel=el
    while eel.parent!=None:
        l.append(eel.parent.index(eel))
        eel=eel.parent
    l.reverse()
    return l
    
def applyIndexPath(root,indexPath):
    el=root
    for index in indexPath:
        el=list(el.children)[index]
    return el
    
class Pattern(object):
    def __init__(self,**kwarg):
        pass
    def setup(self):
        '''获取模式'''
        raise Exception('Error access to null method')
    def get(self,root):
        '''按照模式获取特例soup/root的特定元素'''
        raise Exception('Error access to null method')
    
class IndexPattern(Pattern):
    '''这个类抽象了一种特定元素于页面/顶层元素的位置关系与模式'''
    def __init__(self,root=None,**kwarg):
        super(IndexPattern,self).__init__(**kwarg)
        self.index_path=None
        self.root=root
        if root!=None:
            self.setup(root,**kwarg)
    def setup(self,**kwarg):
        '''这个方法用于取模式的顶层表示'''
        self.get_index_path(self,**kwarg)
    def get(self,root):
        '''这个模式作用于一个root时返回这个模式所确定的位置的元素，默认行为是使用
        IndexPath表示模式。重写match来通过一个特定的定位确定具体模式'''
        return applyIndexPath(root,self.index_path)
    def get_index_path(self,**kwarg):
        self.index_path=getIndexPath(self.match(**kwarg))
    def match(self,root=None):
        '''在不重写模式整体作用方式时应当重写match来实现对于一
        个特例的特定元素搜索规则'''
        pass
    
class BigImgPattern(IndexPattern):
    '''模式是文档中图片大小最大的那个'''
    def __init__(self,root=None,host=None):
        super(BigImgPattern,self).__init__()
        #由于没有传入root参数所以并不自动引发setup
        self.root=root
        self.host=host
        if root!=None and host!=None:
            self.setup(root=root,host=host)
    def match(self,root=None,host=None):
        return get_big_image(root,host=host)
        
class BigTextPattern(IndexPattern):
    '''这个应该就不用重写构造器函数了.寻找最大文本地区，具体实现还没放进来'''
    def __init__(self,root=None,cut=0.5):
        super(BigTextPattern,self).__init__()
        self.root=root
        self.cut=cut
        if root!=None:
            self.setup(root=root,cut=cut)
    def match(self,root,cut=0.5):
        return max_keep(root,cut=cut)
    
#python的未命名参数也可以通过指定名称来赋值或跳跃赋值。
def max_keep(root,cut=0.5):
    '''从文档树顶层向下搜索，始终查找节点中使文本量保持比最大的那个（应该也是文本最多的）
    的那个，到一个瞬间，此时搜索的所有子节点文本量最大值与上层子节点文本量最大值差得很多
    如此就终止搜索'''
    node=root
    max_text_length=len(root.text)
    while True:
        #print node.name
        tl=[]
        nl=[]
        children=list(node.children)
        if len(children)==0:
            raise 'error'
        for child in children:
            if hasattr(child,'text'):
                tl.append(len(child.text))
                nl.append(child)
        max_text_length_ing=max(tl)
        if float(max_text_length_ing)/max_text_length<cut:
            print float(max_text_length_ing)/max_text_length
            return node
        else:
            max_text_length=max_text_length_ing
            node=nl[tl.index(max_text_length)]

def find_series(root,limit=3):
    #寻找列表页里下面1,2,3那种分页.
    al=[a for a  in root.findAll('a') if len(a.contents)>0 and type(a.contents[0])==bs4.element.NavigableString and a.contents[0].isdigit()]
    match_mode=Counter(map(getXPathMode,al)).most_common(1)[0][0]
    aal=filter(lambda a:getXPathMode(a)==match_mode,al)
    if len(al)!=len(aal):
        print 'warning it is possible match series wrong by mode'
    tl=[int(a.contents[0]) for a in aal]
    if len(tl)!=max(tl)-min(tl)+1:
        print 'warning it is possible match series wrong by order'
    if len(tl)<limit:
        print 'warning it is possible match series wrong by number'
    return aal
    
def get_big_image(soup,host=None):
    '''这个函数请求root下所有图片。返回最大者'''
    a_l=[]
    url_l=[]
    for a in soup.findAll('img'):
        a_l.append(a)
        url=a.attrs['src']
        if url[0]=='/':
            url=host+url
        url_l.append(url)
    img_res_l=[]
    for url in url_l:
        img_res_l.append(requests.get(url))
    #return max(img_res_l,key=lambda res:len(res.content))
    max_index=img_res_l.index(max(img_res_l,key=lambda res:len(res.content)))
    return a_l[max_index]
    
def string_sim(s1,s2):
    '''这个用于计算两个超链接的相似性，用于系统聚类'''
    '''
    su=0
    for i in range(min(len(s1),len(s2))):
        if s1[i]!=s2[i]:
            break
        su+=1
    return float(su)/max(len(s1),len(s2))
    '''
    c=0
    i1,i2=0,0
    n1,n2=0,0
    m1,m2=len(s1),len(s2)
    while True:
        if i1==m1:
            break
        elif i2==m2:
            i1+=1
            n1+=1
            i2=n2
        elif s1[i1]==s2[i2]:
            c+=1
            i1+=1
            i2+=1
            n1+=1
            n2+=1
        else:
            i2+=1
    return float(c)/max(m1,m2)
    
def cluster(ssl,cut=0.9,key=None):
    '''系统聚类。接受一个字符串列表，返回它们的聚类。当相似性低于cut时停止聚类'''
    if key==None:
        sl=ssl
    else:
        sl=map(key,ssl)
    sid_list=range(len(sl))
    cluster_l=[]
    sid_of_cluster={}
    for sid in sid_list:
        sid_c=[sid]
        sid_of_cluster[sid]=sid_c
        cluster_l.append(sid_c)
    sim_mat=[((i,j),string_sim(sl[i],sl[j])) for i in sid_list for j in sid_list]
    sim_mat.sort(key=lambda x:x[1],reverse=True)
    #开始聚类
    for (left,right),sim in sim_mat:
        if sim<cut:
            break
        #合并
        left_cl=sid_of_cluster[left]
        right_cl=sid_of_cluster[right]
        if left_cl==right_cl:
            continue
        new_cluster=left_cl+right_cl
        #print new_cluster
        for i in new_cluster:
            sid_of_cluster[i]=new_cluster
        cluster_l.remove(left_cl)
        cluster_l.remove(right_cl)
        cluster_l.append(new_cluster)
    raw_cluster=[[ssl[sid] for sid in cluster] for cluster in cluster_l]
    return raw_cluster
    
def cache(s,fname):
    f=open(fname,'w')
    f.write(s)
    f.close()
def read(fname):
    f=open(fname,'r')
    s=f.read()
    f.close()
    return s
def show(res_content,temp_path='temp_image',format=None):
    import matplotlib.pyplot as plt
    f=open(temp_path,'wb')
    f.write(res_content)
    f.close()
    img=plt.imread(temp_path,format=format)
    plt.imshow(img)
    plt.show()


article_url='http://www.90bbbb.com/html/article/index43203.html'
index_url='http://www.90bbbb.com/html/part/index27.html'
'''
article_s=requests.get(article_url).content
index_s=requests.get(index_url).content

article_root=BeautifulSoup(article_s)
index_root=BeautifulSoup(index_s)

fa=list(index_root.findAll('a'))
ffa=filter(lambda a:type(a.contents[0])==bs4.element.NavigableString,fa)
c=cluster(ffa,key=lambda a:a.attrs['href'])

url_l=['http://www.90bbbb.com'+a.attrs['href'] for a in c[-2]]

'''