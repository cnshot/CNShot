#!/usr/bin/python
# -*- coding: utf-8

import sys, logging, logging.config, os, html5lib, StringIO, re

from optparse import OptionParser
from config import Config, ConfigMerger
from lxml import etree, html
from BeautifulSoup import UnicodeDammit
from urlparse import urljoin

def LinkProcessorUpdateURL(div, attr, base_url):
    # logger.debug("Processing link: %s", etree.tostring(div))
    try:
        if div.attrib[attr] is not None:
            div.attrib[attr] = urljoin(base_url, div.attrib[attr])
            # logger.debug("New link: %s", div.attrib[attr])
    except KeyError:
        pass

def LinkProcessorRemoveTag(div, attr, base_url):
    div.drop_tag()

def LinkProcessorDeleteDiv(div, attr, base_url):
    # div_p = div.getparent()
    # i = div_p.index(div)
    # if i == 0:
    #     if div_p.text is None:
    #         div_p.text = ''
    #     if div.tail is not None:
    #         div_p.text += div.tail
    # else:
    #     pre = tag_p.getchildren()[i-1]
    #     if pre.tail is None:
    #         pre.tail = ''
    #     if div.tail is not None:
    #         pre.tail += div.tail

    # div.getparent.remove(div)
    div.drop_tree()

def remove_tag(tag):
    # tag_p = tag.getparent()
    # i = tag_p.index(tag)
    # if i == 0:
    #     if tag_p.text is None:
    #         tag_p.text = ''
    #     if tag.text is not None:
    #         tag_p.text += tag.text

    #     last_div = tag_p
    #     tag_cs = tag.getchildren()
    #     while tag_cs:
    #         tag_c=tag_cs.pop()
    #         tag.remove(tag_c)
    #         tag_p.insert(i,tag_c)
    #         last_div=tag_c

    #     if tag.tail is not None:
    #         if last_div ==  tag_p:
    #             tag_p.text += tag.tail
    #         else:
    #             if last_div.tail is None:
    #                 last_div.tail = ''
    #             last_div.tail += tag.tail
    # else:
    #     pre = tag_p.getchildren()[i-1]
    #     if pre.tail is None:
    #         pre.tail = ''
    #     if tag.text is not None:
    #         pre.tail += tag.text

    #     last_div = tag_p
    #     tag_cs = tag.getchildren()
    #     while tag_cs:
    #         tag_c=tag_cs.pop()
    #         tag.remove(tag_c)
    #         tag_p.insert(i,tag_c)
    #         last_div=tag_c

    #     if tag.tail is not None:
    #         if last_div ==  pre:
    #             tag_p.tail += tag.tail
    #         else:
    #             if last_div.tail is None:
    #                 last_div.tail = ''
    #             last_div.tail += tag.tail

    # tag_p.remove(tag)
    tag.drop_tag()
    
def remove_tags(div, xpath):
    # get parents of <font></font>
    #   enumunate <font>
    #   add text of <font> to previous item's text
    #   remove <font>
    #
    # clear_tag(doc, '//xhtml:font',
    #           namespaces={'xhtml':'http://www.w3.org/1999/xhtml'})
    # tag_ps = div.xpath(('//%s/..' % xpath),
    #                   namespaces={'xhtml':'http://www.w3.org/1999/xhtml'})
    # for tag_p in tag_ps:
    #     tags = tag_p.xpath(xpath,
    #                          namespaces={'xhtml':'http://www.w3.org/1999/xhtml'})
    #     for tag in tags:
    #         logger.debug("Remove tag %s: %s", xpath, etree.tostring(tag))
    #         remove_tag(tag)

    for tag in div.xpath('descendant-or-self::node()/%s' % xpath):
        tag.drop_tag()

class ReadabilityProcessor:
    def __init__(self, config):
        self.cfg = config
        self.permited_attributes = []
        for a in self.cfg.readability.permited_attributes:
            self.permited_attributes.append(a)

    def get_url_pattern_matchs(self, div, cfg, url=None):
        result = []
        for c in cfg:
            if hasattr(c, 'url') and ((url is None) or (not re.match(c.url, url))):
                logger.debug("URL pattern failed to match: %s %s", c.url, url)
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
                x.drop_tree(),
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

        logger.debug("No xpath top div found.")

        p_ps = doc.xpath('//p/.. | //br/.. | //pre/..',
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
            
            ps = p_p.xpath('p | pre ',
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

        logger.debug("Readability counted.")
                            
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

    def process(self, html_doc, input_charset=None, output_charset=None, url=None,
                linkprocessor=None):
        output_title = None
        output_body = None

        if not html:
            return None

        # br_pattern = re.compile('<br ?/?>[ \r\n\s]*<br ?/?>')
        # html = br_pattern.sub ('</p><p>', html)

        if input_charset is None:
            html_doc = UnicodeDammit(html_doc, isHTML=True).unicode.encode('utf-8')
        elif input_charset.upper != 'UTF-8':
            html_doc = html_doc.decode(input_charset).encode('utf-8')

        # logger.debug("Parse file...")

        try:
            parser = html.HTMLParser(encoding='utf-8', remove_comments=True, remove_blank_text=True)
            doc   = html.parse(StringIO.StringIO(html_doc), parser)
        except etree.XMLSyntaxError, e:
            logger.warn("Failed to parse HTML with etree.HTMLParser.")
            return None
            # parser = html5lib.HTMLParser(tree=html5lib.treebuilders.getTreeBuilder("lxml"), namespaceHTMLElements=False)
            # doc = parser.parse(StringIO.StringIO(html_doc), encoding='utf-8')

        # parser = html5lib.HTMLParser(tree=html5lib.treebuilders.getTreeBuilder("lxml"), namespaceHTMLElements=False)
        # doc = parser.parse(StringIO.StringIO(html_doc), encoding='utf-8')
        # for d in doc.getiterator():
        #     setattr(d, 'a') = 1

        brs=doc.xpath('//br',namespaces={'xhtml':'http://www.w3.org/1999/xhtml'})

        # logger.debug("Removing font tags...")

        # remove_tags(doc,'font') 
        for tag in doc.xpath(self.cfg.readability.decorative_tags):
            tag.drop_tag()

        # doc.find('//font').drop_tag()
        logger.debug("Font's tag left: %d", len(doc.xpath('//font')))

        # logger.debug("XML without font tag: %s", etree.tostring(doc))

        # get title
        try:
            title = doc.xpath('/html/head/title',
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
        map(lambda x:x.set('style', ''), top_div.xpath('descendant-or-self::node()/*[@style!=""]', namespaces={'xhtml':'http://www.w3.org/1999/xhtml'}))
        # map(lambda x:x.set('class', ''), top_div.xpath('//*[@class!=""]', namespaces={'xhtml':'http://www.w3.org/1999/xhtml'}))

        #   removes DIV's that have more non <p> stuff than <p> stuff
        map(lambda x: \
                x.drop_tree(),
            filter(lambda div: \
                       len(div.xpath('p | br | pre', namespaces={'xhtml':'http://www.w3.org/1999/xhtml'})) * 2 < len(div.getchildren()),
                   top_div.xpath('descendant-or-self::node()/div', namespaces={'xhtml':'http://www.w3.org/1999/xhtml'})))

        #   Removes any consecutive <br />'s into just one <br />
        for br in top_div.xpath('descendant-or-self::node()/br', namespaces={'xhtml':'http://www.w3.org/1999/xhtml'}):
            logger.debug("Processing br: %s", etree.tostring(br))
            br_p = br.getparent()
            i = br_p.index(br)
            if i==0:
                continue
            pre = br_p.getchildren()[i-1]
            if (pre.tag != 'br'):
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
        # print top_div.xpath('//form | //object | //h1 | //iframe | //script | //style',
        #                     namespaces={'xhtml':'http://www.w3.org/1999/xhtml'})
        # defunct_divs = top_div.xpath('//form | //object | //h1 | //iframe | //script | //style',
        #                              namespaces={'xhtml':'http://www.w3.org/1999/xhtml'})
        defunct_divs = top_div.xpath(self.cfg.readability.defunct_tags,
                                     namespaces={'xhtml':'http://www.w3.org/1999/xhtml'})
        # print defunct_divs
        # logger.debug("Defunct divs count: %d", len(defunct_divs))
        # map(lambda x: x.drop_tree(), defunct_divs)
        for d in defunct_divs:
            logger.debug("Defunct div: %s", etree.tostring(d))
            d.drop_tree()

        #   remove small (<250 eng words or <20 chn sentences) tables
        map(lambda x: \
                x.drop_tree(),
            filter(lambda x: x.text is None or \
                       x.text.count(' ') < 250 or \
                       x.text.count(',') + x.text.count(u'，') + x.text.count(u'。') < 20 ,
                   top_div.xpath('table',
                          namespaces={'xhtml':'http://www.w3.org/1999/xhtml'})))

        if url is not None and linkprocessor is not None:
            for div in top_div.xpath('descendant-or-self::node()/img',
                                     namespaces={'xhtml':'http://www.w3.org/1999/xhtml'}):
                # logger.debug("Image div to fix: %s", etree.tostring(div))
                linkprocessor(div, 'src', url)
            for div in top_div.xpath('descendant-or-self::node()/a',
                                     namespaces={'xhtml':'http://www.w3.org/1999/xhtml'}):
                linkprocessor(div, 'href', url)

        # clear attributes
        for d in top_div.getiterator():
            for a in d.keys():
                if not a in self.permited_attributes:
                    d.attrib.pop(a)

        return {'title': title,
                'body': top_div,
                'text': etree.tostring(top_div, encoding='utf-8')}

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
        
        print etree.tostring(html, encoding='utf-8', pretty_print=True)
