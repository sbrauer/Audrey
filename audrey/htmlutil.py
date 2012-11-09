def sniff_html(s):
    """ Does some simple tests to sniff a string and return True if it smells like html. """
    if s is None: return False
    if '</' in s: return True
    if '/>' in s: return True
    return False

#  Converts HTML to text by stripping out HTML elements,
#  and in some cases handling elements in special ways.
#  Originally based on code in The Python Cookbook, recipe 10.8

import htmllib, formatter, cStringIO
import htmlentitydefs
import re

class HTML_to_text_parser(htmllib.HTMLParser):
    def __init__(self, formatter, show_link_urls=1, skip_tags=[], unknown_entity_replacement=None):
        htmllib.HTMLParser.__init__(self, formatter)
        self.last_href = None
        self.formatter = formatter
        self.show_link_urls = show_link_urls
        self.skip_tags = ["head", "script"]
        for x in skip_tags:
            if x not in self.skip_tags: self.skip_tags.append(x)
        self.unknown_entity_replacement = unknown_entity_replacement  # None signifies that the value should be passed through as-is.  In some cases, you may instead want "?" or "" or some such.
        self.skip_flag = 0

    def handle_starttag(self, tag, method, attrs):
        if(tag in self.skip_tags):
            self.skip_flag += 1
        if self.skip_flag: return

        if(tag == 'a'):
            self.last_href = None
            for attr in attrs:
                if(attr[0] == 'href'):
                    self.last_href = attr[1]
                    break
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.formatter.add_literal_data("\n\n")
        elif(tag == 'p'):
            self.formatter.add_literal_data("\n\n")
        elif(tag == 'br'):
            self.formatter.add_literal_data("\n")
        elif(tag == 'li'):
            self.formatter.add_literal_data("\n\n- ")

    def handle_endtag(self, tag, method):
        if(tag in self.skip_tags):
            if self.skip_flag: self.skip_flag -= 1
            return
        if self.skip_flag: return

        if(self.show_link_urls and tag == 'a' and self.last_href):
            self.formatter.add_literal_data(" [%s]" % self.last_href)

        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.formatter.add_literal_data("\n\n")
        #else:  # Prevent words from running together.
        #    self.formatter.add_literal_data(" ")

    def unknown_starttag(self, tag, attrs):
        return self.handle_starttag(tag, None, attrs)

    def unknown_endtag(self, tag):
        return self.handle_endtag(tag, None)

    def handle_data(self, data):
        if self.skip_flag: return
        data = data.replace('\xc2\xa0', ' ') # Replace non-breaking spaces with regular spaces.
        self.formatter.add_literal_data(data)

    def handle_charref(self, ref):
        # Handles &#ref;
        self.handle_data(unichr(int(ref)).encode('utf-8'))

    def handle_entityref(self, ref):
        # Handles &ref;
        match = htmlentitydefs.name2codepoint.get(ref, None)
        if match:
            self.handle_charref(match)
        elif self.unknown_entity_replacement:
            self.handle_data(self.unknown_entity_replacement)

SELF_CLOSING_FIX_RE = re.compile(r'(\S)/>')

# Assumes html is a Unicode string or UTF-8 encoded.
# The return value is the same type as the input.
def html_to_text(html, show_link_urls=1, skip_tags=[], unknown_entity_replacement=None):
    output_unicode = False
    if type(html) == unicode:
        html = html.encode('utf-8')
        output_unicode = True

    textout = cStringIO.StringIO()
    formtext = formatter.AbstractFormatter(formatter.DumbWriter(textout))
    parser = HTML_to_text_parser(formtext, show_link_urls, skip_tags, unknown_entity_replacement)

    # Annoyingly HTMLParser doesn't handle self-closing tags without a space
    # (such as "<br/>") properly.
    # So let's add any missing spaces (for example, "<br />").
    html = SELF_CLOSING_FIX_RE.sub(r'\1 />', html)

    parser.feed(html)
    parser.close()
    text = textout.getvalue().strip()
    del textout, formtext, parser
    if output_unicode: return unicode(text, 'utf-8')
    else: return text

def main():
    # Try to read stdin
    import sys
    html = sys.stdin.read()
    print html_to_text(html)

if __name__ == "__main__": main()
