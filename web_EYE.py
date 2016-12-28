# -*- encoding:utf-8 -*-
from bs4 import BeautifulSoup
from urllib import parse
import requests
import re
import math
import posixpath
import bs4
import chardet


def _take_out_list(Data, target_type):
    """拆解嵌套列表"""
    def _break_up_list(data, List):
        for item in data:
            if isinstance(item, target_type):
                List.append(item)
            else:
                _break_up_list(item, List)
    temporary_list = []
    _break_up_list(Data, temporary_list)
    temporary_list = [i for i in temporary_list if i]
    return temporary_list


class EYE:
    def __init__(self, url, header=None, timeout=20, separator="\n", keep_gif=False, smallest_length=2, img_tag=True, word_with_format=False, img_with_format=True, shortest_length=18, encoding=None, with_date=False):
        self.url = url
        self.header = header
        self.timeout = timeout
        self.separator = separator
        self.keep_gif = keep_gif
        self.smallest_length = smallest_length
        self.img_tag = img_tag
        self.word_with_format = word_with_format
        self.img_with_format = img_with_format
        self.shortest_length = shortest_length
        self.encoding = encoding
        self.with_date = with_date

        self.title = None
        self.date = None
        self.elements = {
            "state": 1
        }


    regexps = {
        "unlikelyCandidates": re.compile(r"combx|comment|community|disqus|extra|foot|header|enu|remark|rss|shoutbox|"
                                         r"sidebar|sponsor|ad-break|agegate|pagination|pager|popup|tweet|twitter"),
        "okMaybeItsACandidate": re.compile(r"and|article|body|column|main|shadow"),
        "positive": re.compile(r"article|body|content|entry|hentry|main|page|pagination|post|text|blog|story"),
        "negative": re.compile(r"combx|comment|com|contact|foot|footer|footnote|masthead|media|meta|outbrain|promo|"
                               r"related|scroll|shoutbox|sidebar|sponsor|shopping|tags|tool|widget"),
        "extraneous": re.compile(r"print|archive|comment|discuss|e[\-]?mail|share|reply|all|login|sign|single"),
        "divToPElements": re.compile(r"<(a|blockquote|dl|div|img|ol|p|pre|table|ul)"),
        "trim": re.compile(r"^\s+|\s+$"),
        "normalize": re.compile(r"\s{2,}"),
        "videos": re.compile(r"http://(www\.)?(youtube|vimeo)\.com"),
        "skipFootnoteLink": re.compile(r"^\s*(\[?[a-z0-9]{1,2}\]?|^|edit|citation needed)\s*$"),
        "nextLink": re.compile(r"(next|weiter|continue|>([^|]|$)|»([^|]|$))"),
        "prevLink": re.compile(r"(prev|earl|old|new|<|«)"),
        "url": re.compile(
            r'(?i)\b((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:'
            r'[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|'
            r'[^\s`!()\[\]{};:\'".,<>?«»“”‘’]))'),
        "brackets": re.compile(r"<.*?>"),
        "symbol": re.compile(r"\r|&gt;|\xa0"),
        "chinese": re.compile(u"[\u4e00-\u9fa5]*"),
        "title": re.compile(r'<h[1-3].*'),
        "date": re.compile(r'(20[0-1][0-9]|[0-1][0-9])[^a-zA-Z0-9](1[0-2]|0?[0-9])[^a-zA-Z0-9](3[0-1]|2[0-9]|1[0-9]|0?[0-9]).?')
    }

    @property
    def main(self):
        try:
            request = requests.get(url=self.url, params=self.header, timeout=self.timeout)
        except requests.exceptions.Timeout:
            self.elements['state'] = 0
            self.elements['error'] = "ConnectionTimeout"
            return self.elements

        if self.encoding:
            charset = self.encoding
        else:
            charset = chardet.detect(request.content)['encoding']
            if not charset:
                charset = 'gb2312'
        request.encoding = charset
        bsobj = BeautifulSoup(request.text, "html.parser")
        alternative_dict = {}

        for tag in bsobj.body.find_all(True):
            if tag.name in ("script", "style", "link"):  # 如果是这三个标签之一，删除这个标签
                tag.extract()
            if tag.name == "p":  # 如果节点是p标签，找到字符和向上两层节点
                parent_tag = tag.parent
                grandparent_tag = parent_tag.parent
                inner_text = tag.text
                if not parent_tag or len(inner_text) < 20:  # 如果该节点为空或无有价值内容
                    continue
                parent_hash = hash(str(parent_tag))  # 内容太多放不进字典，计算字符串哈希值以取唯一值
                grand_parent_hash = hash(str(grandparent_tag))
                if parent_hash not in alternative_dict:  # 如果该节点内有内容，放入向上两层节点内容和分数
                    alternative_dict[parent_hash] = self._tag_score(parent_tag)
                if grandparent_tag and grand_parent_hash not in alternative_dict:
                    alternative_dict[grand_parent_hash] = self._tag_score(grandparent_tag)
                # 计算此节点分数，以逗号和长度作为参考，并使向上两层递减获得加权分
                content_score = 1
                content_score += inner_text.count(",")
                content_score += inner_text.count(u"，")
                content_score += min(math.floor(len(inner_text) / 100), 3)
                alternative_dict[parent_hash]["score"] += content_score
                if grandparent_tag:
                    alternative_dict[grand_parent_hash]["score"] += content_score / 2

        best_tag = None
        for key in alternative_dict:
            alternative_dict[key]["score"] *= 1 - self._link_score(alternative_dict[key]["tag"])
            if not best_tag or alternative_dict[key]["score"] > best_tag["score"]:
                best_tag = alternative_dict[key]
        if not best_tag:
            self.elements['state'] = 0
            self.elements['error'] = "Couldn't find the optimal node"
            return self.elements
        content_tag = best_tag["tag"]
        # 确定title
        self.title = self._find_title(content_tag)
        if not self.title:
            self.title = bsobj.title
        # 对最优节点格式清洗
        for tag in content_tag.find_all(True):
            del tag["class"]
            del tag["id"]
            del tag["style"]
        # 清理标签，清理无用字段
        content_tag = self._clean(content_tag, "h1")
        content_tag = self._clean(content_tag, "object")
        alternative_dict, content_tag = self._clean_alternative_dict(content_tag, "form", alternative_dict)
        if len(content_tag.find_all("h2")) == 1:
            content_tag = self._clean(content_tag, "h2")
        content_tag = self._clean(content_tag, "iframe")
        alternative_dict, content_tag = self._clean_alternative_dict(content_tag, "table", alternative_dict)
        alternative_dict, content_tag = self._clean_alternative_dict(content_tag, "ul", alternative_dict)
        alternative_dict, content_tag = self._clean_alternative_dict(content_tag, "div", alternative_dict)
        # 找寻图片地址
        imgs = content_tag.find_all("img")
        # 得到所有地址，清理无用地址
        for img in imgs:
            src = img.get("src", None)
            if not src:
                img.extract()
                continue
            elif "http://" != src[:7] and "https://" != src[:8]:
                newSrc = parse.urljoin(self.url, src)
                newSrcArr = parse.urlparse(newSrc)
                newPath = posixpath.normpath(newSrcArr[2])
                newSrc = parse.urlunparse((newSrcArr.scheme, newSrcArr.netloc, newPath,
                                           newSrcArr.params, newSrcArr.query, newSrcArr.fragment))
                img["src"] = newSrc
        # 正文内中文内容少于设定值，默认定位失败
        content_text = content_tag.get_text(strip=True, separator=self.separator)
        content_length = len("".join(self.regexps["chinese"].findall(content_text)))
        if content_length <= self.shortest_length:
            self.elements['state'] = 0
            self.elements['error'] = "Page is empty or without content"
            return self.elements

        content = self._parameter_correction(content_tag)
        if self.with_date:
            self._find_date(content_tag)
            self.elements['date'] = self.date
        self.elements['content'] = content
        self.elements['img'] = self.img
        self.elements['title'] = self.title
        return self.elements

    def _tag_score(self, tag):
        """加权框架分计算"""
        score = 0
        if tag.name == "div":
            score += 5
        elif tag.name == "blockquote":
            score += 3
        elif tag.name == "form":
            score -= 3
        elif tag.name == "th":
            score -= 5
        score += self._class_score(tag)
        return {"score": score, "tag": tag}

    def _class_score(self, tag):
        """加权类分计算"""
        score = 0
        if "class" in tag:
            if self.regexps["negative"].search(tag["class"]):
                score -= 25
            elif self.regexps["positive"].search(tag["class"]):
                score += 25
        if "id" in tag:
            if self.regexps["negative"].search(tag["id"]):
                score -= 25
            elif self.regexps["positive"].search(tag["id"]):
                score += 25
        return score

    @staticmethod
    def _link_score(tag):
        """加权标签内部分数"""
        links = tag.find_all("a")
        textLength = len(tag.text)
        if textLength == 0:
            return 0
        link_length = 0
        for link in links:
            link_length += len(link.text)
        return link_length / textLength

    def _clean(self, content, tag):
        """清理符合条件的标签"""
        target_list = content.find_all(tag)
        flag = False
        if tag == "object" or tag == "embed":
            flag = True
        for target in target_list:
            attribute_values = ""
            for attribute in target.attrs:
                get_attr = target.get(attribute[0])
                attribute_values += get_attr if get_attr is not None else ""
            if flag and self.regexps["videos"].search(attribute_values) \
                    and self.regexps["videos"].search(target.encode_contents().decode()):
                continue
            target.extract()
        return content

    def _clean_alternative_dict(self, content, tag, alternative_dict):
        """字典计分加权以清理无用字段"""
        tags_list = content.find_all(tag)
        # 对每一节点评分并调用存档评分
        for tempTag in tags_list:
            score = self._class_score(tempTag)
            hash_tag = hash(str(tempTag))
            if hash_tag in alternative_dict:
                content_score = alternative_dict[hash_tag]["score"]
            else:
                content_score = 0
            # 清理负分节点
            if score + content_score < 0:
                tempTag.extract()
            else:
                p = len(tempTag.find_all("p"))
                img = len(tempTag.find_all("img"))
                li = len(tempTag.find_all("li")) - 100
                input_html = len(tempTag.find_all("input_html"))
                embed_count = 0
                embeds = tempTag.find_all("embed")
                # 如果找到视频，考虑删除节点
                for embed in embeds:
                    if not self.regexps["videos"].search(embed["src"]):
                        embed_count += 1
                linkscore = self._link_score(tempTag)
                contentLength = len(tempTag.text)
                toRemove = False
                # 删除节点逻辑
                if img > p:
                    toRemove = True
                elif li > p and tag != "ul" and tag != "ol":
                    toRemove = True
                elif input_html > math.floor(p / 3):
                    toRemove = True
                elif contentLength < 25 and (img == 0 or img > 2):
                    toRemove = True
                elif score < 25 and linkscore > 0.2:
                    toRemove = True
                elif score >= 25 and linkscore > 0.5:
                    toRemove = True
                elif (embed_count == 1 and contentLength < 35) or embed_count > 1:
                    toRemove = True
                # 逻辑成立则删除节点
                if toRemove:
                    tempTag.extract()
        return alternative_dict, content

    def _parameter_correction(self, content):
        """依据选择参数的调整格式"""
        content_tag_list = []
        for tag in content:
            if not isinstance(tag, bs4.element.Tag):
                continue
            if "<img" in tag.decode():
                content_tag_list.extend(tag.find_all("img"))
            else:
                content_tag_list.append(tag)
        self.img = [tag.get("src") for tag in content_tag_list if tag.name == "img"]
        # 对于各种参数的选择，原地清理列表并筛选列表
        if not self.word_with_format:
            for v in range(len(content_tag_list)):
                if isinstance(content_tag_list[v], bs4.element.Tag):
                    if content_tag_list[v].name == 'img':
                        src = content_tag_list[v].get("src")
                        if not self.keep_gif and ('.gif' in src or '.GIF' in src):
                            src = None
                        if self.img_with_format and src:
                            src = '<img src="' + src + '"/>'
                        content_tag_list[v] = src
                    else:
                        if isinstance(content_tag_list[v], bs4.element.NavigableString):
                            content_tag_list[v] = content_tag_list[v].string
                        content_tag_list[v] = content_tag_list[v].get_text(strip=True)
                        content_tag_list[v] = self.regexps["symbol"].sub("", content_tag_list[v])
                        if len("".join(self.regexps["chinese"].findall(content_tag_list[v]))) < self.smallest_length:
                            content_tag_list[v] = None     # 清理每段低于最小长度的文字节点
        content_tag_list = filter(lambda x: x, content_tag_list)
        content_tag_list = list(map(lambda x: str(x), content_tag_list))
        content = self.separator.join(content_tag_list)
        return content

    def _find_title(self, content_tag):
        """由正文节点向前寻找标题（h1-h3)"""
        previous = content_tag.find_all_previous()
        for brother_tag in previous:
            title_list = self.regexps["title"].findall(str(brother_tag))
            if title_list:
                title = self.regexps['brackets'].sub("", title_list[0])
                if title:
                    return title
        return None

    def _find_date(self, content_tag):
        """由正文节点向前寻找时间
        注意，此模块尚未完善，谨慎使用！
        这个比较麻烦，一方面网上流传的正则表达式很多都无法使用，另一方面不同模板的日期格式各有不同，逻辑往往是互斥的
        因此在简单正则逻辑的基础上，加入投票的概念，当然，有可靠的日期正则也请发给我"""
        date_list = []
        previous = content_tag.find_all_previous()
        for brother_tag in previous:
            date = self.regexps["date"].search(str(brother_tag))
            if date:
                date_list.append(date.group())
        if date_list:
            date_list = [[x, date_list.count(x)] for x in date_list]
            date_list.sort(key=lambda x: x[1], reverse=True)
            self.date = date_list[0][0]

# 示例
if __name__ == "__main__":
    task = EYE(url=r"http://news.163.com/16/1228/07/C9BVN2SM0001875O.html", with_date=True)
    print(task.main)
