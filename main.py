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
import os
import json
import random

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
        

def mkdir(path):
    path=path.replace('\\','/')
    path_l=path.split('/')
    for i in range(len(path_l)):
        try:
            os.mkdir('/'.join(path_l[0:i+1]))
        except WindowsError:
            pass
        
class Crawler(object):
    '''起码需要重写
    self.start_urls
    self.next_urls'''
    def __init__(self,bind_path,start_urls):
        self.start_urls=start_urls
        self.bind_path=bind_path
        self.byte=''
        if not(os.path.isdir(bind_path)):
            mkdir(bind_path)
    def url_to_name(self,url):
        '''url如何编码为path的尾名称，这个不要单独存文件，否则非常麻烦。默认方法是把/替换
        成..'''
        return url.replace('/','..').replace(':',';')
    def url_to_path(self,url):
        return self.bind_path+'/'+self.url_to_name(url)
    def name_to_url(self,name):
        return name.replace("..",'/').replace(';',':')
    def path_to_url(self,path):
        name=path.replace(self.bind_path+'/','')
        return self.name_to_url(name)
    def all_path(self):
        return [self.bind_path+'/'+name for name in os.listdir(self.bind_path)]
    def all_url(self):
        return [self.name_to_url(name) for name in os.listdir(self.bind_path)]
    def load_from_file(self,url):
        '''限制为只能从本地文件读取，否则报错，不然过于混乱'''
        f=open(self.url_to_path(url),'r'+self.byte)
        content=f.read()
        f.close()
        return content
    def save_to_file(self,url,content):
        '''保存到文件'''
        f=open(self.url_to_path(url),'w'+self.byte)
        f.write(content)
        f.close()
    def state(self,url):
        '''返回url当前状态，是未下载还是已下载，还可能包括其他状态如在内存等'''
        if os.path.isfile(self.url_to_path(url)):
            return 'local'
        else:
            return 'undownload'
    def url_to_host(self,url):
        ul=url.split('/')
        return '/'.join(ul[0:3])
    def url_to_ancestors(self,url):
        ul=url.split('/')
        return '/'.join(ul[:-1])
    def concat(self,href,url):
        host=self.url_to_host(url)
        ancestors=self.url_to_ancestors(url)
        if href=='#':
            return url
        if host[-1]!='/' and href[0]!='/':
            return ancestors+'/'+href
        else:
            return host+href
    def download(self,url):
        '''具体如何下载，这个方法被定义在这里使得更换下载方法容易'''
        res=requests.get(url)
        return res.content
    def start(self,report=True):
        end_urls=[]#end_urls是已经结束check的url，它可能的超链接已经耗尽
        checking_urls=self.start_urls
        new_urls=[]
        while True:
            if len(checking_urls)==0:
                break
            if report:
                print 'finished/ready',len(end_urls),'/',len(checking_urls)
            for check_url in checking_urls:
                print 'request',check_url
                if self.state(check_url)!='local':
                    content=self.download(check_url)
                    self.save_to_file(check_url,content)
                else:
                    content=self.load_from_file(check_url)
                for url in self.next_urls(check_url,content):
                    if self.state(url)!='local' and not(url in checking_urls) and not(url in new_urls):
                        #没必要哦检查它是不是在checking_urls里
                        new_urls.append(url)
                print 'clear',check_url
            end_urls.extend(checking_urls)
            checking_urls=new_urls
            new_urls=[]
    def next_urls(self,url,content):
        '''如何葱一个url得到下一组url'''
        pass

            
class SubPageCrawler(Crawler):
    def __init__(self,bind_path,start_urls):
        Crawler.__init__(self,bind_path,start_urls=start_urls)
    def next_urls(self,url,content):
        #host=self.url_to_host(url)
        #return [host+a.attrs['href'] if a.attrs['href']!='#' else url for a in find_series(BeautifulSoup(content))]
        return [self.concat(a.attrs['href'],url) for a in find_series(BeautifulSoup(content))]

class ForkCrawler(Crawler):
    '''Fork爬虫类似依附依附一个主爬虫，以每个主爬虫爬取的页面中的url与content
    （即类似next_urls）的product方法生成start_urls，但绝不爬取以外的页面'''
    def __init__(self,bind_path,master_crawler):
        Crawler.__init__(self,bind_path,[])
        self.master_crawler=master_crawler
    def next_urls(self,url,content):
        '''这里这个next_urls判定的是怎么从主页转移(加入恰当连接
        )，又怎么从分页终止(返回空表)'''
        return []
    def conduct(self):
        '''返回用来给start_urls赋值的东西'''
        build_urls=set()
        for url in self.master_crawler.all_url():
            content=self.master_crawler.load_from_file(url)
            build_urls=build_urls | set(self.product(url,content))
        return list(build_urls)
    def start(self):
        self.master_crawler.start()
        self.start_urls=self.conduct()
        Crawler.start(self)
    def product(self,url,content):
        '''需要覆盖'''
        pass

        
class DiffCrawler(ForkCrawler):
    '''这个爬虫判别有意义信息的方式是比较两个(或多个)类似的网页，取其中不同的部分，而不是
    单独对每个url,content判别'''
    def conduct(self):
        urls=self.master_crawler.all_url()
        contents=[self.master_crawler.load_from_file(url) for url in urls]
        length=len(urls)
        ls=set()
        for i in range(-1,length-1):
            #soup1,soup2=BeautifulSoup(contents[i]),BeautifulSoup(contents[i+1])
            ls=ls | set(self.diff(urls[i],contents[i],urls[i+1],contents[i+1]))
        return list(ls)
    def diff(self,url1,content1,url2,content2):
        '''具体实行diff的部分'''
        pass
      
class DiffMaxClusterCrawler(DiffCrawler):
    '''这个类将两个url中对称差的超链接打包返回'''
    def diff(self,url1,content1,url2,content2):
        root1,root2=map(BeautifulSoup,[content1,content2])
        host=self.master_crawler.url_to_host(url1)
        al=[sub_url for sub_url in diff(root1,root2)]
        rl=[host+sub_url for sub_url in max(string_cluster(al),key=len)]
        return rl
        
class Extractor(ForkCrawler):
    '''资源提取器，主要是从爬虫对象取已有资源，不过也可能去下载。它的start
    类似爬虫，会将资源映射到bind_path里'''
    def start(self):
        #self.master_crawler.start()
        for url in self.master_crawler.all_url():
            try:
                url,asset=self.url_to_asset(url,self.master_crawler.load_from_file(url))
            except Exception,e:
                print 'miss',url
                #raise e
            self.save_to_file(url,asset.encode('utf8'))
    def url_to_asset(self,url,content):
        '''将主爬虫的url与content映射成资源文件，此文件将以原url而不是这里下载
        （如果有）被编制path以求简单对应.需要覆盖'''
        pass
    
class PatternExtractor(Extractor):
    #TODO 暂时先用更简单/稳健的方法提取资源使用pattern这边的封装
    def __init__(self,bind_path,master_crawler,pattern):
        '''pattern是pattern子类中的一个,暂时不发展'''
        super(PatternExtractor,self).__init__(self,bind_path,master_crawler)
        self.pattern=pattern
    
class ArticleExtractor(Extractor):
    '''文章提取器,主要利用max_keep函数'''
    def url_to_asset(self,url,content):
        root=BeautifulSoup(content)
        return url,max_keep(root).text
        
class MaxImageExtractor(Extractor):
    '''最大图片提取器，提取content中所指明的最大图片'''
    def url_to_asset(self,url,content):
        host=self.url_to_host(url)
        print 'url_to_asset',url
        res=get_big_image(BeautifulSoup(content),host=host,res=True)
        return res.url,res.content
        
class DiffMaxImgCrawler(DiffCrawler):
    '''这个类将两个url中对称差的最大图片打包返回,不进行聚类'''
    def __init__(self,bind_path,master_crawler):
        DiffCrawler.__init__(self,bind_path,master_crawler)
        self.byte='b'#swich on b IO mode
    def diff(self,url1,content1,url2,content2):
        root1,root2=map(BeautifulSoup,[content1,content2])
        #host=self.master_crawler.url_to_host(url1)
        #url_l=[self.concat(sub_url,url1) for sub_url in diff_img(root1,root2)]
        url_l=[sub_url for sub_url in diff_img(root1,root2)]
        res_l=map(requests.get,url_l)
        max_ix=max(range(len(url_l)),key=lambda i:len(res_l[i].content))
        #TODO这样设可能会使图下两遍，先这样弄
        print 'put',url_l[max_ix]
        return [url_l[max_ix]]
        
        
        



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
    
def get_big_image(soup,host=None,res=False):
    '''这个函数请求root下所有图片。返回最大者(BeautifulSoup <a>元素)'''
    a_l=[]
    url_l=[]
    for a in soup.findAll('img'):
        a_l.append(a)
        url=a.attrs['src']
        print url
        if url[0]=='/':
            url=host+url
        url_l.append(url)
    img_res_l=[]
    for url in url_l:
        img_res_l.append(requests.get(url))
    #return max(img_res_l,key=lambda res:len(res.content))
    max_index=img_res_l.index(max(img_res_l,key=lambda res:len(res.content)))
    if res:
        return img_res_l[max_index]
    else:
        return a_l[max_index]
    
def string_sim(s1,s2):
    '''这个用于计算两个超链接的相似性，用于系统聚类'''
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
    
def cluster(ssl,sim_function,cut=0.9,key=None):
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
    sim_mat=[((i,j),sim_function(sl[i],sl[j])) for i in sid_list for j in sid_list]
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
    
def string_cluster(ssl,cut=0.9,key=None):
    return cluster(ssl,string_sim,cut=cut,key=key)
    
def diff(root1,root2):
    al1=root1.findAll('a')
    al2=root2.findAll('a')
    h1=set([a.attrs['href'] for a in al1])
    h2=set([a.attrs['href'] for a in al2])
    return (h1-h2) | (h2-h1)
    
def diff_img(root1,root2):
    al1=root1.findAll('img')
    al2=root2.findAll('img')
    h1=set([a.attrs['src'] for a in al1])
    h2=set([a.attrs['src'] for a in al2])
    return (h1-h2) | (h2-h1)

    
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

spc=SubPageCrawler('data/test',[index_url])
dmcc=DiffMaxClusterCrawler('data/content',spc)
dmcc.start()

shana_url='http://www.benziku.cc/shaonv/5898.html'
shana_soup=BeautifulSoup(requests.get(shana_url).content)

shana_url2='http://www.benziku.cc/shaonv/5898_4.html'
shana_soup2=BeautifulSoup(requests.get(shana_url2).content)

shana=SubPageCrawler('data/shana_list',[shana_url])
shana.start()

url=shana.all_url()[4]
html=shana.load_from_file(url)
soup=BeautifulSoup(html)
img=get_big_image(soup,host='http://www.benziku.cc/',res=True).content
show(img)

shana_img=DiffMaxImgCrawler('data/shana_img',shana)
shana_img.start()

shana_img=MaxImageExtractor('data/shana_img',shana)
shana_img.start()

index_url='http://www.90bbbb.com/html/part/index27.html'
spc=SubPageCrawler('data/test',[index_url])
dmcc=DiffMaxClusterCrawler('data/content',spc)
dmcc.start()

ae=ArticleExtractor("data/story",dmcc)
ae.start()
'''