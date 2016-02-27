# 通用爬虫

## 介绍

写爬虫向来是自己撸资源定位之类的太烦，某些“立足美国为华人服务”的网站风格十分类似，
如果能够搞出一个通用爬虫去抓资源而不是每次都定位半天就好了。

对于这类网站的“文章”部分，对于一个文章页面，我对DOM树向下搜索，每步
选择一个文本量/比最大的节点下降，当一个节点的文本数量与
其子节点的最大文本数量相差很大时，中止搜索，直接输出节点的全部文本作为小说内容。这是考虑
小说的文本数量应当占据网页的主体部分，因而在触及文章区域总体前每步下降无非是丢掉了一些
广告栏之类的信息，下降比应该不大，但一旦进入文章区，单一段落不可能占据大量的文本。所以
那一瞬间就是全体文本块组成的区域，直接输出就应该是文章了。

对于文章外面的几十页那种目录页面，我取页面之间对称差移除相同的超链接，剩下来的进行聚类，
选择最大的一类作为文章链接，效果还行。

目录页之间的索引移动直接匹配1,2,3，。。的超链接，基本上不用做出任何修改

爬取漫画的方法差不多，图片是选择各种img中大小最大的那一张。

## 使用

一般来说，你只要选择相应爬虫类，给它一个绑定路径与初始URL或“主爬虫”即可

下载漫画

	shana_url='http://www.benziku.cc/shaonv/5898.html'
	shana=SubPageCrawler('data/shana_list',[shana_url])
	shana_img=DiffMaxImgCrawler('data/shana_img',shana)
	shana_img.start()
	
下载文章

	index_url='http://www.90bbbb.com/html/part/index27.html'
	spc=SubPageCrawler('data/test',[index_url])
	dmcc=DiffMaxClusterCrawler('data/content',spc)
	dmcc.start()
	
	ae=ArticleExtractor("data/story",dmcc)
	ae.start()
	
可以下载列表下所有文章


