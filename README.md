#web_EYE
v_0.1  
对不同模板的静态网页，分析并提取正文、标题、时间等元素。  

仅支持python3
##示例
    if __name__ == "__main__":  
        task = EYE(url=r"http://news.163.com/16/1228/07/C9BVN2SM0001875O.html", with_date=True, separator="")  
        task.main  
则返回  
{  
'state': 1  
'title': '白宫新闻官刚任命便辞职 或因与女顾问发生婚外情'  
'date': '2016-12-28'
'img': ['http://cms-bucket.nosdn.127.net/be7bcded46024f749862a991119f754820161228075353.jpeg?imageView&thumbnail=550x0']  
'content': '（原标题：白宫新闻官刚任命就辞职 或因与一女性顾问发生婚外情）<img src="http://cms-bucket.nosdn.127.net/be7bcded46024f749862a991119f754820161228075353.jpeg?imageView&thumbnail=550x0"/>【环球时报综合报道】特朗普高级顾问杰森・米勒被任命为白宫新闻办主任才两天就提出辞职。据媒体爆料，米勒因为竞选期间同一名女性顾问发生婚外情才“引火上身”。据美国有线电视新闻网(CNN)26日报道，米勒对外表示，自己将不会追随特朗普进入白宫。声明称：“过去一周是2015年3月以来我在家人身边待得最久的一次。我清醒地认识到，家庭才是我优先考虑的问题，现在并不是我出任白宫新闻办主任这一严苛职位的最好时机。...'  
}  
##快速开始
构建EYE类并传入参数后，调用main方法，即可得到提取到的元素。  
返回值包括：  
+ state：int，返回状态识别状态，成功返回1。  
+ error：str，返回错误详情。  
+ title：str，返回新闻的纯文本标题。  
+ content：str，视参数返回不同格式的正文。  
+ date：str，视参数返回。  
+ img：[str]-字符串，返回正文中的图片链接，视参数返回gif格式图片。
  
##参数
+ url：必填，目标网址。
+ header:选填，默认None，基于requests的请求头，例如 {'user-agent': 'my-app/0.0.1'}。
+ timeout：选填，默认20（s），请求等待时间，超时以requests报timeout错误。
+ word_with_format：选填，默认False，可选content返回是否带原网页文本格式（只保留p/font/color等标签），参数为False时返回纯文本。
+ separator：选填，默认'\n'，当word_with_forma参数问False时，选择连接字符来连接段落。
+ img_with_format：选填，默认True，可选content返回是否带原网页图片格式（只保留img标签，不保留其它属性），参数为False时返回图片链接。
+ keep_gif：选填，默认False，可选返回的img元素和content元素是否保留gif，参数为false时不保留。
+ smallest_length：选填，默认2，可选每个文本段（可以理解为每个p标签内文本）小于等于smallest_lengt时不计入该文本段。
+ shortest_length：选填，默认18，可选返回的content元素，共计中文字符小于等于shortest_length时报error。
+ encoding：选填，默认auto，可选网页解码方式，建议不填，chardet判断失效时会使用gb2312进行解码，已经较完美的解决识别编码问题。
+ with_date：选填，默认False，（注：该功能尚未完善）可选是否返回找到的发布日期（非文本日期），常用于新闻日期的抓取。
+ img_tag：保留字。
  
##错误
+ error："ConnectionTimeout"，连接超时。
+ error："Page is empty or without content"，中文字符小于shortest_length的设定值，往往是由于编码错误或英文内容导致的。
+ error："Couldn't find the optimal node"，正文定义失败。
  
##待扩展内容
+ 正文内部的table格式解析
+ 正文内部的视频连接解析
+ 发布日期优化，增加发布时间返回值。
