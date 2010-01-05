# -*- coding: utf-8 -*-
# Copyright (c) 2008-2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

import re, os.path
from urllib2 import HTTPError
from xml.dom import minidom

from helpers import openTestFile
from Products.Five.testbrowser import Browser

Z3C_CONTENTS = ['Silva Document', 'Silva Link',
                'Silva Indexer', 'Silva Find',
                'Silva File', 'Silva Image']

# Define types of forms.
SILVA_FORM = object()
Z3CFORM_FORM = object()
FORMLIB_FORM = object()

class SilvaBrowser(object):
    def __init__(self):
        self.form_type = SILVA_FORM
        self.new_browser()

    def new_browser(self):
        self.browser = Browser()
        #self.browser.handleErrors = False

    def go_back(self):
        return self.browser.goBack()

    def click_control_labeled(self, value_name):
        """Click on the real button called value_name
        """
        self.browser.getControl(value_name).click()

    def click_button_labeled(self, value_name):
        """Click on a button or pseudo button (an href) with a
        specific label.
        """
        # for some reason the browser object does not expose
        # enough input and form info, however we can reach what
        # we want through the mech_... objects. Since they are not
        # private (no underscore) this is maybe not too bad...

        button = None
        # get middleground pseudo buttons
        if button is None and 'class="middleground"' in self.browser.contents:
            # no button found yet, check if there are anchors in
            # the middleground div that match value_name
            # they sort of look like buttons too, right..
            doc = minidom.parseString(
                self.browser.contents.replace('&nbsp;', ' '))
            divs = doc.getElementsByTagName('div')
            for div in divs:
                if div.getAttribute('class') != 'middleground':
                    continue
                anchors = div.getElementsByTagName('a')
                for anchor in anchors:
                    text = self.html2text(anchor.toxml())
                    if text == value_name:
                        url = anchor.getAttribute('href')
                        return self.go(url)

        # get all forms
        for form in self.browser.mech_browser.forms():
            for control in form.controls:
                if not control.type in ['button', 'submit']:
                    continue
                if control.value == value_name:
                    # found the button
                    button = control

        assert button != None, 'No button labeled: "%s" found' % value_name
        # we cannot click this control, we need to get a browser
        # control, since all controls have a name, we can use that to
        # get the real control.
        self.browser.getControl(name=button.name).click()
        return self.get_status_and_url()

    def click_href_labeled(self, value_name):
        """Click on a link with a specific label
        """
        if 'logout' in value_name:
            # logout always results in a 401 error, login window. since
            # you can't access the popup, i accept that a logout is, an href
            # value_name that has logout in it, and clicking the link there is
            # a 401 HTTPError
            try:
                self.browser.getLink(value_name).click()
            except HTTPError, err:
                if err.code == 401:
                    return self.get_status_and_url()
        else:
            self.browser.getLink(value_name).click()
            return self.get_status_and_url()

    def click_tab_named(self, name):
        """click on a tab with a specific label
        """
        link = self.browser.getLink(name)
        link.click()

    def get_addables_list(self):
        """
        return a list of addable meta_types
        """
        try:
            addables = self.browser.getControl(name='meta_type').options
            addables.remove('None')
        except:
            # there probably is no 'meta_type' control
            addables = []
        return addables

    def get_addform_title(self):
        """
        return a normalized <h2> title for add forms
        """
        start = self.browser.contents.find('<h2>')
        if start == -1:
            return ''
        end = self.browser.contents.find('</h2>', start)
        return self.html2text(self.browser.contents[start:end+5])

    def get_alert_feedback(self):
        """
        return the alert message in the page, or an empty string
        """
        div = '<div class="fixed-alert">'
        start = self.browser.contents.find(div)
        if start == -1:
            return ''
        start += len(div)
        end = self.browser.contents.find('</div>', start)
        return self.browser.contents[start:end].strip()

    def get_frame_url(self,frameindex):
        """
        return the src of the [frameindex] frame of a frameset
        """
        doc = minidom.parseString(self.browser.contents.replace('&nbsp;', ' '))
        result = []
        frames = doc.getElementsByTagName('frame')
        if len(frames) >= frameindex + 1:
            return frames[0].getAttribute('src')
        return None

    def get_content_data(self):
        """
        return a list of dictionaries describing the content objects
        """
        doc = minidom.parseString(self.browser.contents.replace('&nbsp;', ' '))
        result = []
        for form in doc.getElementsByTagName('form'):
            if form.getAttribute('name') == 'silvaObjects':
                for tbody in form.getElementsByTagName('tbody'):
                    for row in tbody.getElementsByTagName('tr')[1:]:
                        count = 1
                        data = {}
                        for cell in row.getElementsByTagName('td'):
                            if count == 1:
                                data['id'] = cell.getElementsByTagName('input')[0].getAttribute('id')
                            elif count == 2:
                                anchor = cell.getElementsByTagName('a')[-1]
                                data['url'] = anchor.getAttribute('href')
                            elif count == 3:
                                anchor = cell.getElementsByTagName('a')[-1]
                                data['name'] = anchor.childNodes[0].nodeValue
                                css = anchor.getAttribute('class')
                                if css == 'published':
                                    data['closed'] = False
                                    data['published'] = True
                                    data['publishable'] = True
                                elif css == 'draft':
                                    data['closed'] = True
                                    data['published'] = False
                                    data['publishable'] = True
                                else:
                                    data['closed'] = True
                                    data['publishable'] = False
                            elif count == 5:
                                anchors = cell.getElementsByTagName('a')
                                if anchors:
                                    data['author'] = anchors[-1].childNodes[0].nodeValue
                                else:
                                    data['author'] = cell.childNodes[0].nodeValue.strip()
                            count +=1
                        result.append(data)
        return result

    def get_content_ids(self):
        """
        return a list of ids for objects in current container
        """
        return [o['id'] for o in self.get_content_data()]

    def get_href_named(self, value_name):
        """
        return an href with a specific label
        """
        href = self.browser.getLink(value_name)
        return href

    def get_listing_h2(self):
        """
        return the content type and name of the <h2> in the listing table
        """
        doc = minidom.parseString(self.browser.contents.replace('&nbsp;', ' '))
        tables = doc.getElementsByTagName('table')
        for table in tables:
            if table.getAttribute('class') != 'listing':
                continue
            trs = doc.getElementsByTagName('tr')
            for tr in trs:
                tds = doc.getElementsByTagName('td')
                for td in tds:
                    if td.getAttribute('class') != 'top':
                        continue
                    h2s = doc.getElementsByTagName('h2')
                    for h2 in h2s:
                        text = self.html2text(h2.toxml())
                        return text

    def get_status_and_url(self):
        """Return status and url of current page
        """
        status = self.browser.headers.getheader('Status')
        status = int(status.split(' ')[0])
        return (status, self.browser.url)

    def get_status_feedback(self):
        """Return the status message in the page, or an empty string
        """
        div = '<div class="fixed-feedback">'
        start = self.browser.contents.find(div)
        if start == -1:
            return ''
        start += len(div)
        end = self.browser.contents.find('</div>', start)
        return self.browser.contents[start:end].strip()

    def get_tabs(self):
        """Get all tabs on the page
        """
        doc = minidom.parseString(self.browser.contents.replace('&nbsp;', ' '))
        divs = doc.getElementsByTagName('div')
        for div in divs:
            if div.getAttribute('class') != 'tabs':
                continue
            anchors = div.getElementsByTagName('a')
            for anchor in anchors:
                yield self.html2text(anchor.toxml())

    def get_tab_named(self, value_name):
        """Get a tab with a specific label.
        """
        tabs = list(self.get_tabs())
        return value_name in tabs and value_name or None

    def get_middleground_buttons(self):
        """Get all middleground buttons on the page.
        """
        doc = minidom.parseString(self.browser.contents.replace('&nbsp;', ' '))
        divs = doc.getElementsByTagName('div')
        for div in divs:
            if div.getAttribute('class') != 'middleground':
                continue
            anchors = div.getElementsByTagName('a')
            for anchor in anchors:
                yield self.html2text(anchor.toxml())

    def get_middleground_button_named(self, value_name):
        """Get a middleground button from the page with a specific name.
        """
        buttons = list(self.get_middleground_buttons())
        return value_name in buttons and value_name or None

    def get_url(self):
        """Return the current URL
        """
        return self.browser.url

    def get_root_url(self):
        """Return the ZMI root URL
        """
        return 'http://nohost/root'

    def go(self, url):
        """Same as browser.open, but handles http exceptions, and returns http
        status and url tuple.
        """
        try:
            self.browser.open(str(url))
        except HTTPError, err:
            # there is no way to read status from browser,
            # so we'll just have to use the error str, ugh
            return (err.code, None)

        # read status code from first http header
        return self.get_status_and_url()

    def html2text(self, htmlstring):
        """Return children of an html element, stripping out child elements,
        and normalizing text nodes
        """
        # replace all text within <> with an empty string
        text = re.compile('<([^>]+)>').sub('', htmlstring)
        # replace multiple whitespace characters with a space
        text = re.compile('(\s+)').sub(' ', text)
        return text.strip()

    def login(self, username='manager', password='secret', url=None):
        """Authentificate.
        """
        # it seems the Browser object gets confused if 401's are
        # raised. Because of this we always use a new Browser
        # when logginf in
        url = url or self.get_root_url()
        self.new_browser()
        self.browser.addHeader('Authorization', 'Basic %s:%s' % (
                          username, password))
        self.browser.addHeader('Accept-Language', 'en-US')
        return self.go(url)

    def logout(self, url=None):
        """Logout
        """
        url = url or self.get_root_url()
        url = '%s/manage_zmi_logout' % url
        try:
            self.browser.open(url)
        except HTTPError, err:
            return (err.code, None)

    def make_content(self, content_type, **fields):
        """Makes content of a specific type, with one or more fields
        filled in.
        """
        # save form type, and set it if it's a known one
        current_form_type = None
        if content_type in Z3C_CONTENTS:
            current_form_type = self.form_type
            self.form_type = Z3CFORM_FORM

        fields_needed = self.content_type_fields.get(content_type, None)
        # do some testing to determine if needed fields are supplied
        assert fields_needed != None, 'Unknown Content Type'
        for field_name in fields_needed:
            if not fields.has_key(field_name):
                raise ValueError('Missing field "%s" for "%s"' % (field_name,
                                                                  content_type))
        self.select_addable(content_type)
        self.click_button_labeled('new...')
        id = fields.get('id', 'test_object')
        fields['id'] = id
        self.set_field(**fields)
        self.click_button_labeled('save')

        if current_form_type:
            self.form_type = current_form_type

    def make_default_content(self, content_type):
        """ """
        field_names = self.content_type_fields[content_type]
        fields = {}
        for field_name in field_names:
            fields[field_name] = self.default_field_values[field_name]

        return self.make_content(content_type, **fields)

    def open_file(self, filename):
        """
        format the path to data/ for test files
        """
        return openTestFile(filename)

    def select_addable(self, meta_type):
        """
        select a meta_type from the addables list
        """
        self.browser.getControl(name='meta_type').value = [meta_type]

    def select_all_content(self, data):
        """
        toggle all content item checkboxes
        """
        # Hack way to select all the checkboxes, since this is done
        # with js
        ids = [item['id'] for item in data]
        self.browser.getControl(name='ids:list').value = ids

    def select_content(self, content_id):
        """
        toggle a content item checkbox
        """
        self.browser.getControl(name='ids:list').value = [content_id]

    def select_delete_content(self, content_id):
        """
        select and then delete a content item
        """
        self.select_content(content_id)
        self.click_button_labeled('delete')
        return self.get_status_and_url()

    def smi_url(self, url=None):
        """return the smi url of current url, or url parameter if present"""
        # XXX this should be a bit smarter
        url = url or self.get_root_url()
        assert url != None, 'Cannot go to SMI here, url does not exist'
        if not url.endswith('/edit') and not '/edit/' in url:
            url += '/edit'
        return url

    def set_field(self, **kwargs):
        """
        fill (multiple) field_object controls where keyword
        is a fieldname and value the value
        for example, to fill the id and title field call
        sb.set_field(id='test', title='A test object')
        """
        for field_name, field_value in kwargs.items():
            self.fields[field_name](self, field_value)

    def get_field_id(self, name):
        """
        get the html for that field.
        """
        if self.form_type is SILVA_FORM:
            if name in ['id', 'title']:
                name = 'object_' + name
            return 'field_' + name
        if self.form_type is Z3CFORM_FORM:
            return 'form.widgets.' + name
        if self.form_type is FORMLIB_FORM:
            raise NotImplementedError
        raise NotImplementedError

    def set_id_field(self, id):
        """
        set the id field
        """
        name = self.get_field_id('id')
        self.browser.getControl(name=name).value = id

    def set_title_field(self, title):
        """
        set the title field
        """
        name = self.get_field_id('title')
        self.browser.getControl(name=name).value = title

    def set_policy_field(self, content_type='Silva Document'):
        """
        set the policy field
        """
        name = self.get_field_id('policy_name')
        self.browser.getControl(name=name).value = [content_type]

    def set_image_field(self, image):
        """
        set the image upload field
        """
        name = self.get_field_id('file')
        self.browser.getControl(name=name).add_file(
            self.open_file(image),
            'image/jpg', image)

    def set_file_field(self, file):
        """
        set the file upload field
        """
        name = self.get_field_id('file')
        self.browser.getControl(name=name).add_file(
            self.open_file(file),
            'text/plain', file)

    def set_ghost_url_field(self, reference):
        """
        set the ghost url field
        """
        name = self.get_field_id('content_url')
        self.browser.getControl(name=name).value = reference

    def set_url_field(self, link_url):
        """
        set the url field
        """
        name = self.get_field_id('url')
        self.browser.getControl(name=name).value = link_url

    def set_depth_field(self, depth):
        """
        set the depth field
        """
        name = self.get_field_id('depth')
        self.browser.getControl(name=name).value = '-1'

    # map default field values to field names
    default_field_values = {
        'id':           'test_object',
        'title':        'A test object',
        'policy':       'Silva Document',
        'image':        'torvald.jpg',
        'file':         'test.txt',
        'reference':    'index',
        'url':          'http://www.infrae.com',
        'depth':        '-1',
    }

    # existing content type fields
    fields = {
        'id':           set_id_field,
        'title':        set_title_field,
        'policy':       set_policy_field,
        'image':        set_image_field,
        'file':         set_file_field,
        'reference':    set_ghost_url_field,
        'url':          set_url_field,
        'depth':        set_depth_field,
    }

    # map field_names to content_types
    content_type_fields = {
        'Silva Document':       ['id', 'title'],
        'Silva Folder':         ['id', 'title', 'policy'],
        'Silva Publication':    ['id', 'title', 'policy'],
        'Silva Image':          ['id', 'title', 'image'],
        'Silva File':           ['id', 'title', 'file'],
        'Silva Find':           ['id', 'title'],
        'Silva Ghost':          ['id', 'reference'],
        'Silva Indexer':        ['id', 'title'],
        'Silva Link':           ['id', 'title', 'url'],
        'Silva AutoTOC':        ['id', 'title', 'depth'],
    }

    @property
    def contents(self):
        """
        return contents of the browser.
        """
        return self.browser.contents

