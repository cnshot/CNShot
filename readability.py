#!/usr/bin/python
# -*- coding: utf-8

import sys, logging, logging.config, os, html5lib, StringIO, re

from optparse import OptionParser
from config import Config, ConfigMerger
from lxml import etree
from BeautifulSoup import UnicodeDammit
from urlparse import urljoin

def LinkProcessorUpdateURL(div, attr, base_url):
    logger.debug("Processing link: %s", etree.tostring(div))
    try:
        if div.attrib[attr] is not None:
            div.attrib[attr] = urljoin(base_url, div.attrib[attr])
            logger.debug("New link: %s", div.attrib[attr])
    except KeyError:
        pass

def LinkProcessorRemoveTag(div, attr, base_url):
    remove_tag(div)

def LinkProcessorDeleteDiv(div, attr, base_url):
    div_p = div.getparent()
    i = div_p.index(div)
    if i == 0:
        if div_p.text is None:
            div_p.text = ''
        if div.tail is not None:
            div_p.text += div.tail
    else:
        pre = tag_p.getchildren()[i-1]
        if pre.tail is None:
            pre.tail = ''
        if div.tail is not None:
            pre.tail += div.tail

    div.getparent.remove(div)

def remove_tag(tag):
    tag_p = tag.getparent()
    i = tag_p.index(tag)
    if i == 0:
        if tag_p.text is None:
            tag_p.text = ''
        if tag.text is not None:
            tag_p.text += tag.text

        last_div = tag_p
        tag_cs = tag.getchildren()
        while tag_cs:
            tag_c=tag_cs.pop()
            tag.remove(tag_c)
            tag_p.insert(i,tag_c)
            last_div=tag_c

        if tag.tail is not None:
            if last_div ==  tag_p:
                tag_p.text += tag.tail
            else:
                if last_div.tail is None:
                    last_div.tail = ''
                last_div.tail += tag.tail
    else:
        pre = tag_p.getchildren()[i-1]
        if pre.tail is None:
            pre.tail = ''
        if tag.text is not None:
            pre.tail += tag.text

        last_div = tag_p
        tag_cs = tag.getchildren()
        while tag_cs:
            tag_c=tag_cs.pop()
            tag.remove(tag_c)
            tag_p.insert(i,tag_c)
            last_div=tag_c

        if tag.tail is not None:
            if last_div ==  pre:
                tag_p.tail += tag.tail
            else:
                if last_div.tail is None:
                    last_div.tail = ''
                last_div.tail += tag.tail

    tag_p.remove(tag)
    
def remove_tags(div, xpath):
    # get parents of <font></font>
    #   enumunate <font>
    #   add text of <font> to previous item's text
    #   remove <font>
    #
    # clear_tag(doc, '//xhtml:font',
    #           namespaces={'xhtml':'http://www.w3.org/1999/xhtml'})
    tag_ps = div.xpath(('//%s/..' % xpath),
                      namespaces={'xhtml':'http://www.w3.org/1999/xhtml'})
    for tag_p in tag_ps:
        tags = tag_p.xpath(xpath,
                             namespaces={'xhtml':'http://www.w3.org/1999/xhtml'})
        for tag in tags:
            remove_tag(tag)

class ReadabilityProcessor:
    def __init__(self, config):
        self.cfg = config

    def get_url_pattern_matchs(self, div, cfg, url=None):
        result = []
        for c in cfg:
            if hasattr(c, 'url') and ((url is None) or (not re.match(c.url, url))):
                continue
            logger.debug("Try xpath: %s", c.xpath)
            try:
                matches = div.xpath(c.xpath, namespaces={'xhtml':'http://www.w3.org/1999/xhtml'})
                for m in matches:
                    logger.debug("Matched %s: %s", c.xpath, etree.tostring(m))
                result += matches
            except etree.XPathEvalError:
                logger.warn("Invalid xpath: %s", c.xpath)
        return result

    def remove_noise_divs(self, div, url=None):
        map(lambda x: \
                x.getparent().remove(x),
            self.get_url_pattern_matchs(div, self.cfg.readability.noise_div, url=url))

    def get_known_body_path_div(self, div, url=None):
        try:
            return self.get_url_pattern_matchs(div, self.cfg.readability.known_body_path, url=url)[0]
        except IndexError:
            # print "No xpath top div matched."
            return None

    def get_text_readability(self, text):
        result = 0

        if text is None or re.match('^\s*$', text):
            return 0

        if len(text) > 10:
            result += 1

        valuable_chars = [',', u'，', u'。']
        for c in valuable_chars:
            result += text.count(c)

        logger.debug("Text readability is %d: [%d] %s", result, len(text), text)

        return result

    def get_div_text_readability(self, div):
        result = self.get_text_readability(div.text)

        for c in div.getchildren():
            result += self.get_text_readability(c.tail)

        return result

    def get_top_div(self, doc, url=None):
        top_div = self.get_known_body_path_div(doc, url=url)
        if top_div is not None:
            logger.debug("Got xpath matched top div.")
            return top_div

        # enum paragraphs
        #   get parent
        #   Initialize readability data or get exisitng readability
        #     Look for a special classname
        #     Look for a special ID
        #   add a point for the paragraph found
        #   add a point for every pair of doubled-up <BR>
        #   add points for symbols within this paragraph

        p_ps = doc.xpath('//xhtml:p/.. | //xhtml:br/.. | //xhtml:pre/..',
                         namespaces={'xhtml':'http://www.w3.org/1999/xhtml'})
        for p_p in p_ps:
            logger.debug("Evaluating P parent div: %s", etree.tostring(p_p))
            if not p_p.get('readability'):
                p_p.set('readability', str(0))
                att_patterns = [{'att': 'class',
                                 'pattern': re.compile('(comment|meta|footer|footnote|articleReview|sideBars)'),
                                 'score' : -50},
                                {'att': 'class',
                                 'pattern': re.compile('((^|\s)(post|hentry|entry[-]?(content|text|body)?|blkContainerSblkCon|blkContainerPblk|article[-]?(content|text|body)?)(\s|$))'),
                                 'score' : 25},
                                {'att': 'id',
                                 'pattern': re.compile('(comment|meta|footer|footnote)'),
                                 'score' : -50},
                                {'att': 'id',
                                 'pattern': re.compile('^(C-Main-Article-QQ|main|content|post|hentry|entry[-]?(content|text|body)?|artibody|article[-]?(content|text|body)?)$'),
                                 'score' : 25},
                                ]
                
                for att_ptn in att_patterns:
                    try:
                        if att_ptn['pattern'].match(p_p.attrib[att_ptn['att']]):
                            new_readability = int(p_p.get('readability')) + att_ptn['score']
                            logger.debug("Assign readability: %d", new_readability)
                            p_p.set('readability', str(new_readability))
                    except KeyError:
                        pass
            
            ps = p_p.xpath('xhtml:p | xhtml:pre ',
                           namespaces={'xhtml':'http://www.w3.org/1999/xhtml'})
            logger.debug("Count text readability in div: %s", p_p.text)
            n = self.get_div_text_readability(p_p)
            p_p.set('readability', str(int(p_p.get('readability')) + n))
            for p in ps:
                # n = self.get_text_readability(p.text) + self.get_text_readability(p.tail)
                n = self.get_div_text_readability(p)
                logger.debug("Readability addon: %d", n)
                p_p.set('readability', str(int(p_p.get('readability')) + n))
                # try:
                #     if len(p.text) > 10:
                #         new_readability = int(p_p.get('readability')) + 1
                #         logger.debug("Assign readability: %d", new_readability)
                #         p_p.set('readability', str(new_readability))
                # except TypeError:
                #     continue
                    
                # valuable_chars = [',', u'，', u'。']
                # for c in valuable_chars:
                #     new_readability = int(p_p.get('readability')) + p.text.count(c)
                #     logger.debug("Assign readability: %d", new_readability)
                #     p_p.set('readability', str(new_readability))
            logger.debug("Final readability: %s", p_p.get('readability'))
                            
        # find topDiv
        max_readability = 0
        for d in doc.iter():
            try:
                if int(d.get('readability')) > max_readability:
                    top_div = d
                    max_readability = int(d.get('readability'))
            except (TypeError, AttributeError):
                pass

        return top_div

    def process(self, html, input_charset=None, output_charset=None, url=None,
                linkprocessor=None):
        output_title = None
        output_body = None

        # br_pattern = re.compile('<br ?/?>[ \r\n\s]*<br ?/?>')
        # html = br_pattern.sub ('</p><p>', html)

        if input_charset is None:
            html = UnicodeDammit(html, isHTML=True).unicode.encode('utf-8')
        elif input_charset.upper != 'UTF-8':
            html = html.decode(input_charset).encode('utf-8')

        parser = html5lib.HTMLParser(tree=html5lib.treebuilders.getTreeBuilder("lxml"))
        doc = parser.parse(StringIO.StringIO(html), encoding='utf-8')
        brs=doc.xpath('//xhtml:br',namespaces={'xhtml':'http://www.w3.org/1999/xhtml'})
        p=etree.Element("{http://www.w3.org/1999/xhtml}p")
        p.text="jaifj"

        remove_tags(doc,'xhtml:font') 

        # logger.debug("XML without font tag: %s", etree.tostring(doc))

        # get title
        try:
            title = doc.xpath('/xhtml:html/xhtml:head/xhtml:title',
                              namespaces={'xhtml':'http://www.w3.org/1999/xhtml'})[0].text
        except IndexError:
            title = None

        top_div = self.get_top_div(doc, url=url)

        # get paragraphs
        if top_div is None:
            logger.warn("No text body found.")
            return None

        # if found topDiv

        # remove noise divs
        # map(lambda x: \
        #         x.getparent().remove(x),
        #     top_div.xpath('//*[contains(@class,"otherContent_01")] | //*[contains(@class,"contentPlayer")]', namespaces={'xhtml':'http://www.w3.org/1999/xhtml'}))
        self.remove_noise_divs(top_div, url=url)

        #   clear styles
        map(lambda x:x.set('style', ''), top_div.xpath('//*[@style!=""]', namespaces={'xhtml':'http://www.w3.org/1999/xhtml'}))
        # map(lambda x:x.set('class', ''), top_div.xpath('//*[@class!=""]', namespaces={'xhtml':'http://www.w3.org/1999/xhtml'}))

        #   removes DIV's that have more non <p> stuff than <p> stuff
        map(lambda x: \
                x.getparent().remove(x),
            filter(lambda div: \
                       len(div.xpath('xhtml:p | xhtml:br | xhtml:pre', namespaces={'xhtml':'http://www.w3.org/1999/xhtml'})) * 2 > len(div.getchildren()),
                   top_div.xpath('//div', namespaces={'xhtml':'http://www.w3.org/1999/xhtml'})))

        #   Removes any consecutive <br />'s into just one <br />
        for br in top_div.xpath('//xhtml:br', namespaces={'xhtml':'http://www.w3.org/1999/xhtml'}):
            logger.debug("Processing br: %s", etree.tostring(br))
            br_p = br.getparent()
            i = br_p.index(br)
            if i==0:
                continue
            pre = br_p.getchildren()[i-1]
            if (pre.tag != '{http://www.w3.org/1999/xhtml}br'):
                continue
            if (pre.tail is not None and not re.match('^(\s|&nbsp;)*$', pre.tail)):
                logger.debug("Skip br.")
                continue
            br_p.remove(pre)

        #   remove forms
        #   remove objects
        #   remove h1
        #   remove iframe
        #   remove script
        # print top_div.xpath('//xhtml:form | //xhtml:object | //xhtml:h1 | //xhtml:iframe | //xhtml:script | //xhtml.style',
        #                     namespaces={'xhtml':'http://www.w3.org/1999/xhtml'})
        defunct_divs = top_div.xpath('//xhtml:form | //xhtml:object | //xhtml:h1 | //xhtml:iframe | //xhtml:script | //xhtml:style',
                                     namespaces={'xhtml':'http://www.w3.org/1999/xhtml'})
        # print defunct_divs
        map(lambda x: x.getparent().remove(x), defunct_divs)

        #   remove small (<250 eng words or <20 chn sentences) tables
        map(lambda x: \
                x.getparent().remove(x),
            filter(lambda x: x.text is None or \
                       x.text.count(' ') < 250 or \
                       x.text.count(',') + x.text.count(u'，') + x.text.count(u'。') < 20 ,
                   top_div.xpath('xhtml:table',
                          namespaces={'xhtml':'http://www.w3.org/1999/xhtml'})))

        if url is not None and linkprocessor is not None:
            for div in top_div.xpath('//xhtml:img',
                                     namespaces={'xhtml':'http://www.w3.org/1999/xhtml'}):
                linkprocessor(div, 'src', url)
            for div in top_div.xpath('//xhtml:a',
                                     namespaces={'xhtml':'http://www.w3.org/1999/xhtml'}):
                linkprocessor(div, 'href', url)

        return {'title': title, 'body': top_div}

if __name__ == '__main__':
    description = '''HTML readability.'''
    parser = OptionParser(usage="usage: %prog [options]",
                          version="%prog 0.1, Copyright (c) 2010 Chinese Shot",
                          description=description)

    parser.add_option("-c", "--config",
                      dest="config",
                      default="readability.cfg",
                      type="string",
                      help="Config file [default %default].",
                      metavar="CONFIG")

    parser.add_option("-f", "--file",
                      dest="file",
                      type="string",
                      help="Input filename [default STDIN].",
                      metavar="FILE")

    parser.add_option("-t", "--to",
                      dest="to",
                      type="string",
                      help="Output filename [default STDOUT].",
                      metavar="TO")

    parser.add_option("-u", "--url",
                      dest="url",
                      default=None,
                      type="string",
                      help="Original URL of the page [default None].",
                      metavar="URL")

    parser.add_option("--charset",
                      dest="charset",
                      default=None,
                      type="string",
                      help="Original charset of the page [default None].",
                      metavar="CHARSET")

    (options,args) = parser.parse_args()
    if len(args) != 0:
        parser.error("incorrect number of arguments")

    cfg=Config(file(filter(lambda x: os.path.isfile(x),
                           [options.config,
                            os.path.expanduser('~/.readability.cfg'),
                            '/etc/readability.cfg'])[0]))

    logging.config.fileConfig(cfg.common.log_config)
    logger = logging.getLogger("readability")

    src_file = sys.stdin
    if(options.file):
        src_file = file(options.file)

    dst_file = sys.stdout
    if(options.to):
        dst_file = file(options.to)

    html_text = src_file.read()

    p = ReadabilityProcessor(cfg)
    r = p.process(html_text, url=options.url, input_charset=options.charset,
                  linkprocessor = LinkProcessorUpdateURL)
    if r:
        html = etree.Element("{http://www.w3.org/1999/xhtml}html",
                             nsmap={None:'http://www.w3.org/1999/xhtml'})
        head = etree.SubElement(html, 'head')
        title = etree.SubElement(head, 'title')
        title.text = r['title']

#        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        meta = etree.SubElement(head, 'meta')
        meta.set('http-equiv',"Content-Type")
        meta.set('content',"text/html; charset=utf-8")

        r['body'].tag = '{http://www.w3.org/1999/xhtml}body'
        html.append(r['body'])
        
        print etree.tostring(html, encoding='utf-8')
