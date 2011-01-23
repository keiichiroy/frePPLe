#
# Copyright (C) 2007-2010 by Johan De Taeye
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation; either version 2.1 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser
# General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
#

# file : $URL$
# revision : $LastChangedRevision$  $LastChangedBy$
# date : $LastChangedDate$

r'''
This module implements a generic view to presents lists and tables.

It provides the following functionality:
 - Pagination of the results.
 - Ability to filter on fields, using different operators.
 - Ability to sort on a field.
 - Export the results as a CSV file, ready for use in a spreadsheet.
 - Import CSV formatted data files.
 - Show time buckets to show data by time buckets.
   The time buckets and time boundaries can easily be updated.
'''

from datetime import date, datetime
import csv, StringIO

from django.conf import settings
from django.core.paginator import QuerySetPaginator, InvalidPage
from django.views.decorators.csrf import csrf_protect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.db.models.fields import Field
from django.db.models.fields.related import RelatedField, AutoField
from django.http import Http404, HttpResponse, HttpResponseRedirect, HttpResponseForbidden
from django.forms.models import modelform_factory
from django.template import RequestContext, loader
from django.utils.encoding import smart_str
from django.utils.translation import ugettext as _
from django.utils.translation import string_concat
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.text import capfirst, get_text_list
from django.utils.encoding import iri_to_uri, force_unicode
from django.contrib.admin.models import LogEntry, CHANGE, ADDITION
from django.contrib.contenttypes.models import ContentType

from freppledb.input.models import Parameter, BucketDetail


# Parameter settings
ON_EACH_SIDE = 3       # Number of pages show left and right of the current page
ON_ENDS = 2            # Number of pages shown at the start and the end of the page list

# URL parameters that are not query arguments
reservedParameters = ('o', 'p', 't', 'reporttype', 'pop', 'reportbucket', 'reportstart', 'reportend')

class Report(object):
  '''
  The base class for all reports.
  The parameter values defined here are used as defaults for all reports, but
  can be overwritten.
  '''
  # Points to templates to be used for different output formats
  template = {}
  # The title of the report. Used for the window title
  title = ''
  # The default number of entities to put on a page
  paginate_by = 25

  # The resultset that returns a list of entities that are to be
  # included in the report.
  basequeryset = None

  # Whether or not the breadcrumbs are reset when we open the report
  reset_crumbs = True

  # Extra javascript files to import for running the report
  javascript_imports = []

  # Specifies which column is used for an initial filter
  default_sort = '1a'

  # A model class from which we can inherit information.
  model = None

  # Allow editing in this report or not
  editable = True

  # Number of columns frozen in the report
  frozenColumns = 0
  
  # Time buckets in this report
  timebuckets = False


class ListReport(Report):
  '''
  Row definitions.

  Supported class methods:
    - resultlist1():
      Returns an iterable that returns the FROZEN data to be displayed.
      If not specified, the basequeryset is used.
    - resultlist2():
      Returns an iterable that returns the SCROLLABLE data to be displayed.
      If not specified, the basequeryset is used.

  Possible attributes for a row field are:
    - filter:
      Specifies a widget for filtering the data.
    - order_by:
      Model field to user for the sorting.
      It defaults to the name of the field.
    - title:
      Name of the row that is displayed to the user.
      It defaults to the name of the field.
    - sort:
      Whether or not this column can be used for sorting or not.
      The default is true.
    - javascript_imports:
      Extra javascript files to import for running the report
  '''
  rows = ()

  # A list with required user permissions to view the report
  permissions = []


class TableReport(Report):
  '''
  Row definitions.

  Supported class methods:
    - resultlist1():
      Returns an iterable that returns the data to be displayed.
      If not specified, the basequeryset is used.

  Possible attributes for a row field are:
    - filter:
      Specifies a widget for filtering the data.
    - order_by:
      Model field to user for the sorting.
      It defaults to the name of the field.
    - title:
      Name of the row that is displayed to the user.
      It defaults to the name of the field.
    - sort:
      Whether or not this column can be used for sorting or not.
      The default is true.
    - javascript_imports:
      Extra javascript files to import for running the report
  '''
  rows = ()

  # Cross definitions.
  # Possible attributes for a cross field are:
  #   - title:
  #     Name of the cross that is displayed to the user.
  #     It defaults to the name of the field.
  #   - editable:
  #     True when the field is editable in the page.
  #     The default value is false.
  crosses = ()

  # Column definitions
  # Possible attributes for a row field are:
  #   - title:
  #     Name of the cross that is displayed to the user.
  #     It defaults to the name of the field.
  columns = ()

  # A list with required user permissions to view the report
  permissions = []

  frozenColumns = 1000
  
  timebuckets = True


@staff_member_required
@csrf_protect
def view_report(request, entity=None, **args):
  '''
  This is a generic view for two types of reports:
    - List reports, showing a list of values are rows
    - Table reports, showing in addition values per time buckets as columns
  The following arguments can be passed to the view:
    - report:
      Points to a subclass of Report.
      This is a required attribute.
    - extra_context:
      An additional set of records added to the context for rendering the
      view.
  '''

  # Pick up the report class
  global reservedParameters
  reportclass = args['report']
  model = reportclass.model

  # Process uploaded data files
  if request.method == 'POST':
    if not reportclass.model or "csv_file" not in request.FILES:
      messages.add_message(request, messages.ERROR, _('Invalid upload request'))
      return HttpResponseRedirect(request.prefix + request.get_full_path())
    if not reportclass.editable or not request.user.has_perm('%s.%s' % (model._meta.app_label, model._meta.get_add_permission())):
      messages.add_message(request, messages.ERROR, _('Not authorized'))
      return HttpResponseRedirect(request.prefix + request.get_full_path())
    (warnings,errors,changed,added) = parseUpload(request, reportclass, request.FILES['csv_file'].read())
    if len(errors) > 0:
      messages.add_message(request, messages.INFO,
       _('File upload aborted with errors: changed %(changed)d and added %(added)d records') % {'changed': changed, 'added': added}
       )
      for i in errors: messages.add_message(request, messages.INFO, i)
    elif len(warnings) > 0:
      messages.add_message(request, messages.INFO,
        _('Uploaded file processed with warnings: changed %(changed)d and added %(added)d records') % {'changed': changed, 'added': added}
        )
      for i in warnings: messages.add_message(request, messages.INFO, i)
    else:
      messages.add_message(request, messages.INFO,
        _('Uploaded data successfully: changed %(changed)d and added %(added)d records') % {'changed': changed, 'added': added}
        )
    return HttpResponseRedirect(request.prefix + request.get_full_path())

  # Verify the user is authorirzed to view the report
  for perm in reportclass.permissions:
    if not request.user.has_perm(perm):
      return HttpResponseForbidden('<h1>%s</h1>' % _('Permission denied'))

  # Pick up the list of time buckets
  pref = request.user.get_profile()
  if reportclass.timebuckets:
    (bucket,start,end,bucketlist) = getBuckets(request, pref)
  else:
    bucket = start = end = bucketlist = None
  type = request.GET.get('reporttype','html')  # HTML or CSV (table or list) output

  # Is this a popup window?
  is_popup = request.GET.has_key('pop')

  # Pick up the filter parameters from the url
  counter = reportclass.basequeryset.using(request.database)
  fullhits = counter.count()
  if entity:
    # The url path specifies a single entity.
    # We ignore all other filters.
    counter = counter.filter(pk__exact=entity)
  else:
    # The url doesn't specify a single entity, but may specify filters
    # Convert URL parameters into queryset filters.
    for key, valuelist in request.GET.lists():
      # Ignore arguments that aren't filters
      if key not in reservedParameters:
        # Loop over all values, since the same filter key can be
        # used multiple times!
        for value in valuelist:
          if len(value)>0:
            counter = counter.filter( **{smart_str(key): value} )

  # Pick up the sort parameter from the url
  sortparam = request.GET.get('o', reportclass.default_sort)
  try:
    # Pick up the sorting arguments
    sortfield = 0
    for i in sortparam:
      if i.isdigit():
        sortfield = sortfield * 10 + int(i)
      else:
        break
    sortdirection = sortparam[-1]
    if not hasattr(reportclass,'default_sortfield'):
      # Create an attribute to store the index of the default sort
      reportclass.default_sortfield = 0
      for i in reportclass.default_sort:
        if i.isdigit():
          reportclass.default_sortfield = reportclass.default_sortfield * 10 + int(i)
        else:
          break
      reportclass.default_sortdirection = reportclass.default_sort[-1]
    if sortfield<=0 or sortfield > len(reportclass.rows) \
      or (reportclass.rows[sortfield-1][1].has_key('sort') and reportclass.rows[sortfield-1][1]['sort']):
        # Invalid sort
        raise
    # Create sort parameters
    if sortfield == reportclass.default_sortfield:
      if sortdirection == 'd':
        sortparam = '%dd' % sortfield
        counter = counter.order_by('-%s' % (('order_by' in reportclass.rows[sortfield-1][1] and reportclass.rows[sortfield-1][1]['order_by']) or reportclass.rows[sortfield-1][0]))
        sortsql = '%d desc' % sortfield
      else:
        sortparam = '%da' % sortfield
        counter = counter.order_by(('order_by' in reportclass.rows[sortfield-1][1] and reportclass.rows[sortfield-1][1]['order_by']) or reportclass.rows[sortfield-1][0])
        sortsql = '%d asc' % sortfield
    else:
      if sortdirection == 'd':
        sortparam = '%dd' % sortfield
        if reportclass.default_sortdirection == 'a':
          counter = counter.order_by(
            '-%s' % (('order_by' in reportclass.rows[sortfield-1][1] and reportclass.rows[sortfield-1][1]['order_by']) or reportclass.rows[sortfield-1][0]),
            ('order_by' in reportclass.rows[reportclass.default_sortfield-1][1] and reportclass.rows[reportclass.default_sortfield-1][1]['order_by']) or reportclass.rows[reportclass.default_sortfield-1][0]
            )
          sortsql = '%d desc, %d asc' % (sortfield, reportclass.default_sortfield)
        else:
          counter = counter.order_by(
            '-%s' % (('order_by' in reportclass.rows[sortfield-1][1] and reportclass.rows[sortfield-1][1]['order_by']) or reportclass.rows[sortfield-1][0]),
            '-%s' % (('order_by' in reportclass.rows[reportclass.default_sortfield-1][1] and reportclass.rows[reportclass.default_sortfield-1][1]['order_by']) or reportclass.rows[reportclass.default_sortfield-1][0])
            )
          sortsql = '%d desc, %d desc' % (sortfield, reportclass.default_sortfield)
      else:
        sortparam = '%da' % sortfield
        if reportclass.default_sortdirection == 'a':
          counter = counter.order_by(
            ('order_by' in reportclass.rows[sortfield-1][1] and reportclass.rows[sortfield-1][1]['order_by']) or reportclass.rows[sortfield-1][0],
            ('order_by' in reportclass.rows[reportclass.default_sortfield-1][1] and reportclass.rows[reportclass.default_sortfield-1][1]['order_by']) or reportclass.rows[reportclass.default_sortfield-1][0]
            )
          sortsql = '%d asc, %d asc' % (sortfield, reportclass.default_sortfield)
        else:
          counter = counter.order_by(
            ('order_by' in reportclass.rows[sortfield-1][1] and reportclass.rows[sortfield-1][1]['order_by']) or reportclass.rows[sortfield-1][0],
            '-%s' % (('order_by' in reportclass.rows[reportclass.default_sortfield-1][1] and reportclass.rows[reportclass.default_sortfield-1][1]['order_by']) or reportclass.rows[reportclass.default_sortfield-1][0])
            )
          sortsql = '%d asc, %d desc' % (sortfield, reportclass.default_sortfield)
  except:
    # A silent and safe exit in case of any exception
    sortparam = reportclass.default_sort
    sortfield = reportclass.default_sortfield
    sortdirection = reportclass.default_sortdirection
    sortsql = '%d asc' % sortfield
    if sortdirection == 'a':
      counter = counter.order_by(('order_by' in reportclass.rows[sortfield-1][1] and reportclass.rows[sortfield-1][1]['order_by']) or reportclass.rows[sortfield-1][0])
    else:
      counter = counter.order_by('-%s' % (('order_by' in reportclass.rows[sortfield-1][1] and reportclass.rows[sortfield-1][1]['order_by']) or reportclass.rows[sortfield-1][0]))

  # HTML output or CSV output?
  if type[:3] == 'csv':
    # CSV output
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=%s.csv' % iri_to_uri(reportclass.title.lower())
    if hasattr(reportclass,'resultlist2'):
      # SQL override provided of type 2
      response._container = _generate_csv(reportclass, reportclass.resultlist2(request, counter, bucket, start, end, sortsql=sortsql), type, bucketlist, pref)
    elif hasattr(reportclass,'resultlist1'):
      # SQL override provided of type 1
      response._container = _generate_csv(reportclass, reportclass.resultlist1(request, counter, bucket, start, end, sortsql=sortsql), type, bucketlist, pref)
    else:
      # No SQL override provided
      response._container = _generate_csv(reportclass, counter, type, bucketlist, pref)
    response._is_string = False
    return response

  # Build paginator
  page = int(request.GET.get('p', '1'))
  paginator = QuerySetPaginator(counter, reportclass.paginate_by)
  if paginator.page(page).start_index():
    counter = counter[paginator.page(page).start_index()-1:paginator.page(page).end_index()]    
  hits = paginator.count
    
  # Calculate the content of the page
  if hasattr(reportclass,'resultlist1'):
    # SQL override provided
    try:
      objectlist1 = reportclass.resultlist1(request, counter, bucket, start, end, sortsql=sortsql)
    except InvalidPage: raise Http404
  else:
    # No SQL override provided
    objectlist1 = counter
  if hasattr(reportclass,'resultlist2'):
    # SQL override provided
    try:
      objectlist2 = reportclass.resultlist2(request, counter, bucket, start, end, sortsql=sortsql)
    except InvalidPage: raise Http404
  else:
    # No SQL override provided
    objectlist2 = objectlist1

  # Build the paginator html
  page_htmls = _get_paginator_html(request, paginator, page)

  # Build the path for the complete list.
  # We need to treat URLs for a specific entity a bit differently
  if entity:
    base_request_path = "%s%s/" % (request.prefix, request.path.rstrip("/").rpartition("/")[0])
  else:
    base_request_path = "%s%s" %(request.prefix, request.path)

  # Prepare template context
  head_frozen, head_scroll = _create_rowheader(request, sortfield, sortdirection, reportclass)
  filterdef, filternew = _create_filter(request, reportclass)
  context = {
       'reportclass': reportclass,
       'model': model,
       'hasaddperm': reportclass.editable and model and request.user.has_perm('%s.%s' % (model._meta.app_label, model._meta.get_add_permission())),
       'haschangeperm': reportclass.editable and model and request.user.has_perm('%s.%s' % (model._meta.app_label, model._meta.get_change_permission())),
       'request': request,
       'object': entity or (hits == 1 and reportclass.model and counter[0].pk) or None,
       'objectlist1': objectlist1,
       'objectlist2': objectlist2,
       'reportbucket': bucket,
       'reportstart': start,
       'reportend': end,
       'paginator': paginator,
       'hits' : hits,
       'fullhits': fullhits,
       'is_popup': is_popup,
       'base_request_path': base_request_path,
       'paginator_html': mark_safe(page_htmls),
       'javascript_imports': _get_javascript_imports(reportclass),
       # Never reset the breadcrumbs if an argument entity was passed.
       # Otherwise depend on the value in the report class.
       'reset_crumbs': reportclass.reset_crumbs and entity == None,
       'title': (entity and '%s %s %s' % (unicode(reportclass.title),_('for'),entity)) or reportclass.title,
       'rowheader': head_scroll,
       'rowheaderfrozen': head_frozen,
       'filterdef': filterdef,
       'filternew': filternew,
       'crossheader': issubclass(reportclass, TableReport) and _create_crossheader(request, reportclass),
       'columnheader': issubclass(reportclass, TableReport) and _create_columnheader(request, reportclass, bucketlist),
     }
  if 'extra_context' in args: context.update(args['extra_context'])

  # Render the view, optionally setting the last-modified http header
  return HttpResponse(
    loader.render_to_string(reportclass.template, context, context_instance=RequestContext(request)),
    )


def _create_columnheader(req, cls, bucketlist):
  '''
  Generate html header row for the columns of a table report.
  '''
  # @todo not very clean and consistent with cross and row
  return mark_safe(' '.join(['<th><a title="%s - %s">%s</a></th>' % (j['startdate'], j['enddate'], j['name']) for j in bucketlist]))


def _create_crossheader(req, cls):
  '''
  Generate html for the crosses of a table report.
  '''
  res = []
  for crs in cls.crosses:
    title = capfirst((crs[1].has_key('title') and crs[1]['title']) or crs[0]).replace(' ','&nbsp;')
    # Editable crosses need to be a bit higher @todo Not very clean...
    if crs[1].has_key('editable'):
      if (callable(crs[1]['editable']) and crs[1]['editable'](req)) \
      or (not callable(crs[1]['editable']) and crs[1]['editable']):
        title = '<span style="line-height:18pt;">' + title + '</span>'
    res.append(title)
  return mark_safe('<br/>'.join(res))


def _get_paginator_html(request, paginator, page):
  # Django has standard some very similar code in the tags 'paginator_number'
  # and 'pagination' in the file django\contrib\admin\templatetags\admin_list.py.
  # Functionally there is no real difference. The implementation below relies
  # less on the template engine.
  global ON_EACH_SIDE
  global ON_ENDS
  page_htmls = []
  parameters = request.GET.copy()
  if 'p' in parameters: parameters.__delitem__('p')

  if paginator.num_pages <= 10 and paginator.num_pages > 1:
    # If there are less than 10 pages, show them all
    for n in paginator.page_range:
      if n == page:
        page_htmls.append('<span class="this-page">%d</span>' % page)
      elif n == 1 and len(parameters) == 0:
        page_htmls.append('<a href="%s%s">1</a>' % (request.prefix, request.path))
      else:
        if n>1: parameters.__setitem__('p', n)
        page_htmls.append('<a href="%s%s?%s">%s</a>' % (request.prefix, request.path, escape(parameters.urlencode()),n))
  elif paginator.num_pages > 1:
      # Insert "smart" pagination links, so that there are always ON_ENDS
      # links at either end of the list of pages, and there are always
      # ON_EACH_SIDE links at either end of the "current page" link.
      if page <= ON_ENDS + ON_EACH_SIDE + 1:
          # 1 2 *3* 4 5 6 ... 99 100
          for n in range(1, page + max(ON_EACH_SIDE, ON_ENDS)+1):
            if n == page:
              page_htmls.append('<span class="this-page">%d</span>' % page)
            elif n == 1 and len(parameters) == 0:
              page_htmls.append('<a href="%s%s">1</a>' % (request.prefix,  request.path))
            else:
              if n>1: parameters.__setitem__('p', n)
              page_htmls.append('<a href="%s%s?%s">%s</a>' % (request.prefix, request.path, escape(parameters.urlencode()),n))
          page_htmls.append('...')
          for n in range(paginator.num_pages - ON_ENDS, paginator.num_pages + 1):
            parameters.__setitem__('p', n)
            page_htmls.append('<a href="%s%s?%s">%s</a>' % (request.prefix, request.path, escape(parameters.urlencode()),n))
      elif page >= (paginator.num_pages - ON_EACH_SIDE - ON_ENDS):
          # 1 2 ... 95 96 97 *98* 99 100
          for n in range(1, ON_ENDS + 1):
            if n == 1 and len(parameters) == 0:
              page_htmls.append('<a href="%s%s">1</a>' % (request.prefix, request.path))
            else:
              if n>1: parameters.__setitem__('p', n)
              page_htmls.append('<a href="%s%s?%s">%s</a>' % (request.prefix, request.path, escape(parameters.urlencode()),n))
          page_htmls.append('...')
          for n in range(page - max(ON_EACH_SIDE, ON_ENDS), paginator.num_pages + 1):
            if n == page:
              page_htmls.append('<span class="this-page">%d</span>' % page)
            else:
              if n>1: parameters.__setitem__('p', n)
              page_htmls.append('<a href="%s%s?%s">%d</a>' % (request.prefix, request.path, escape(parameters.urlencode()),n))
      else:
          # 1 2 ... 45 46 47 *48* 49 50 51 ... 99 100
          for n in range(1, ON_ENDS + 1):
            if n == 1 and len(parameters) == 0:
              page_htmls.append('<a href="%s%s">1</a>' % (request.prefix, request.path))
            else:
              if n>1: parameters.__setitem__('p', n)
              page_htmls.append('<a href="%s%s?%s">%d</a>' % (request.prefix, request.path, escape(parameters.urlencode()),n))
          page_htmls.append('...')
          for n in range(page - ON_EACH_SIDE, page + ON_EACH_SIDE + 1):
            if n == page:
              page_htmls.append('<span class="this-page">%s</span>' % page)
            elif n == '.':
              page_htmls.append('...')
            else:
              if n>1: parameters.__setitem__('p', n)
              page_htmls.append('<a href="%s%s?%s">%s</a>' % (request.prefix, request.path, escape(parameters.urlencode()),n))
          page_htmls.append('...')
          for n in range(paginator.num_pages - ON_ENDS + 1, paginator.num_pages + 1):
              if n>1: parameters.__setitem__('p', n)
              page_htmls.append('<a href="%s%s?%s">%d</a>' % (request.prefix, request.path, escape(parameters.urlencode()),n))
  return mark_safe(' '.join(page_htmls))


def _get_javascript_imports(reportclass):
  '''
  Put in any necessary JavaScript imports.
  '''
  # Check for the presence of a date filter
  if issubclass(reportclass, TableReport):
    add = True
  else:
    add = False
    for row in reportclass.rows:
      if 'filter' in row[1] and isinstance(row[1]['filter'], FilterDate):
        add = True
  if add:
    return reportclass.javascript_imports + [
      "/media/js/core.js",
      "/media/js/calendar.js",
      "/media/js/admin/DateTimeShortcuts.js",
      ]
  else:
    return reportclass.javascript_imports


def _generate_csv(rep, qs, format, bucketlist, pref):
  '''
  This is a generator function that iterates over the report data and
  returns the data row by row in CSV format.
  '''
  sf = StringIO.StringIO()
  if pref.csvdelimiter == 'comma':
    writer = csv.writer(sf, quoting=csv.QUOTE_NONNUMERIC, delimiter=',')
  elif pref.csvdelimiter == 'semicolon':
    writer = csv.writer(sf, quoting=csv.QUOTE_NONNUMERIC, delimiter=';')
  else:
    raise Http404('Unknown CSV delimiter')    
  encoding = settings.DEFAULT_CHARSET

  # Write a header row
  fields = [ ('title' in s[1] and capfirst(_(s[1]['title']))) or capfirst(_(s[0])).encode(encoding,"ignore") for s in rep.rows ]
  if issubclass(rep,TableReport):
    if format == 'csvlist':
      fields.extend([ ('title' in s[1] and capfirst(_(s[1]['title']))) or capfirst(_(s[0])).encode(encoding,"ignore") for s in rep.columns ])
      fields.extend([ ('title' in s[1] and capfirst(_(s[1]['title']))) or capfirst(_(s[0])).encode(encoding,"ignore") for s in rep.crosses ])
    else:
      fields.extend( [capfirst(_('data field')).encode(encoding,"ignore")])
      fields.extend([ unicode(b['name']).encode(encoding,"ignore") for b in bucketlist])
  writer.writerow(fields)
  yield sf.getvalue()

  # Write the report content
  if issubclass(rep,ListReport):
    # Type 1: A "list report"
    # Iterate over all rows
    for row in qs:
      # Clear the return string buffer
      sf.truncate(0)
      # Build the return value, encoding all output
      if hasattr(row, "__getitem__"):
        fields = [ row[s[0]]==None and ' ' or unicode(row[s[0]]).encode(encoding,"ignore") for s in rep.rows ]
      else:
        fields = [ getattr(row,s[0])==None and ' ' or unicode(getattr(row,s[0])).encode(encoding,"ignore") for s in rep.rows ]
      # Return string
      writer.writerow(fields)
      yield sf.getvalue()
  elif issubclass(rep,TableReport):
    if format == 'csvlist':
      # Type 2: "table report in list format"
      # Iterate over all rows and columns
      for row in qs:
        # Clear the return string buffer
        sf.truncate(0)
        # Build the return value
        if hasattr(row, "__getitem__"):
          fields = [ row[s[0]]==None and ' ' or unicode(row[s[0]]).encode(encoding,"ignore") for s in rep.rows ]
          fields.extend([ row[s[0]]==None and ' ' or unicode(row[s[0]]).encode(encoding,"ignore") for s in rep.columns ])
          fields.extend([ row[s[0]]==None and ' ' or unicode(row[s[0]]).encode(encoding,"ignore") for s in rep.crosses ])
        else:
          fields = [ getattr(row,s[0])==None and ' ' or unicode(getattr(row,s[0])).encode(encoding,"ignore") for s in rep.rows ]
          fields.extend([ getattr(row,s[0])==None and ' ' or unicode(getattr(row,s[0])).encode(encoding,"ignore") for s in rep.columns ])
          fields.extend([ getattr(row,s[0])==None and ' ' or unicode(getattr(row,s[0])).encode(encoding,"ignore") for s in rep.crosses ])
        # Return string
        writer.writerow(fields)
        yield sf.getvalue()
    else:
      # Type 3: A "table report in table format"
      # Iterate over all rows, crosses and columns
      prev_row = None
      for row in qs:
        # We use the first field in the output to recognize new rows.
        # This isn't really generic.
        if not prev_row:
          prev_row = row[rep.rows[0][0]]
          row_of_buckets = [row]
        elif prev_row == row[rep.rows[0][0]]:
          row_of_buckets.append(row)
        else:
          # Write an entity
          for cross in rep.crosses:
            # Clear the return string buffer
            sf.truncate(0)
            fields = [ unicode(row_of_buckets[0][s[0]]).encode(encoding,"ignore") for s in rep.rows ]
            fields.extend( [('title' in cross[1] and capfirst(_(cross[1]['title']))) or capfirst(_(cross[0]))] )
            fields.extend([ unicode(bucket[cross[0]]).encode(encoding,"ignore") for bucket in row_of_buckets ])
            # Return string
            writer.writerow(fields)
            yield sf.getvalue()
          prev_row = row[rep.rows[0][0]]
          row_of_buckets = [row]
      # Write the last entity
      for cross in rep.crosses:
        # Clear the return string buffer
        sf.truncate(0)
        fields = [ unicode(row_of_buckets[0][s[0]]).encode(encoding,"ignore") for s in rep.rows ]
        fields.extend( [('title' in cross[1] and capfirst(_(cross[1]['title']))) or capfirst(_(cross[0]))] )
        fields.extend([ unicode(bucket[cross[0]]).encode(encoding,"ignore") for bucket in row_of_buckets ])
        # Return string
        writer.writerow(fields)
        yield sf.getvalue()
  else:
    raise Http404('Unknown report type')


def getBuckets(request, pref=None, bucket=None, start=None, end=None):
  '''
  This function gets passed a name of a bucketization.
  It returns a list of buckets.
  The data are retrieved from the database table dates, and are
  stored in a python variable for performance
  '''

  # Select the bucket size (unless it is passed as argument)
  if pref == None: pref = request.user.get_profile()
  if not bucket:
    bucket = request.GET.get('reportbucket')
    if not bucket:
      try: bucket = pref.buckets
      except: bucket = 'default'
    elif pref.buckets != bucket:
      pref.buckets = bucket
      pref.save()

  # Select the start date (unless it is passed as argument)
  if not start:
    start = request.GET.get('reportstart')
    if start:
      try:
        (y,m,d) = start.split('-')
        start = date(int(y),int(m),int(d))
        if pref.startdate != start:
          pref.startdate = start
          pref.save()
      except:
        try: start = pref.startdate
        except: pass
        if not start: 
          try: start = datetime.strptime(Parameter.objects.get(name="currentdate").value, "%Y-%m-%d %H:%M:%S").date()
          except: start = datetime.now()
    else:
      try: start = pref.startdate
      except: pass
      if not start: 
        try: start = datetime.strptime(Parameter.objects.get(name="currentdate").value, "%Y-%m-%d %H:%M:%S").date()
        except: start = datetime.now()

  # Select the end date (unless it is passed as argument)
  if not end:
    end = request.GET.get('reportend')
    if end:
      try:
        (y,m,d) = end.split('-')
        end = date(int(y),int(m),int(d))
        if pref.enddate != end:
          pref.enddate = end
          pref.save()
      except:
        try: end = pref.enddate
        except: pass
    else:
      try: end = pref.enddate
      except: pass
    
  # Filter based on the start and end date
  res = BucketDetail.objects.using(request.database).filter(bucket=bucket)
  if start: res = res.filter(startdate__gte=start)
  if end: res = res.filter(startdate__lt=end)
  return (bucket, start, end, res.values('name','startdate','enddate'))
  
  
def _create_rowheader(req, sortfield, sortdirection, cls):
  '''
  Generate html header row for the columns of a table or list report.
  '''
  number = 0
  args = req.GET.copy()  # used for the urls used in the sort header
  args2 = req.GET.copy() # used for additional, hidden filter fields
  result1 = []
  result2 = []
  
  # When we update the sorting, we always want to see page 1 again
  if 'p' in args: del args['p']

  # A header cell for each row
  for row in cls.rows:
    number = number + 1
    title = capfirst(escape((row[1].has_key('title') and row[1]['title']) or row[0]))
    if not row[1].has_key('sort') or row[1]['sort']:
      # Sorting is allowed
      if sortfield == number:
        if sortdirection == 'a':
          # Currently sorting in ascending order on this column
          args['o'] = '%dd' % number
          y = 'class="sorted ascending"'
        else:
          # Currently sorting in descending order on this column
          args['o'] = '%da' % number
          y = 'class="sorted descending"'
      else:
        # Sorted on another column
        args['o'] = '%da' % number
        y = ''
      # Which widget to use
      if 'filter' in row[1]:
        # Filtering allowed
        if issubclass(cls,ListReport) and number <= cls.frozenColumns:       
          result1.append( u'<th %s><a href="%s%s?%s">%s</a></th>' \
            % (y, req.prefix, escape(req.path), escape(args.urlencode()), title) )
        else:
          result2.append( u'<th %s><a href="%s%s?%s">%s</a></th>' \
            % (y, req.prefix, escape(req.path), escape(args.urlencode()), title) )
        rowfield = row[1]['filter'].field or row[0]
      else:
        # No filtering allowed
        if issubclass(cls,ListReport) and number <= cls.frozenColumns:       
          result1.append( u'<th %s><a href="%s%s?%s">%s</a></th>' \
            % (y, req.prefix, escape(req.path), escape(args.urlencode()), title) )
        else:
          result2.append( u'<th %s><a href="%s%s?%s">%s</a></th>' \
            % (y, req.prefix, escape(req.path), escape(args.urlencode()), title) )
        rowfield = row[0]
      for i in args:
        field, sep, operator = i.rpartition('__')
        if (field or operator) == rowfield and i in args2: del args2[i]
    else:
      # No sorting is allowed on this field
      # If there is no sorting allowed, then there is also no filtering
      if issubclass(cls,ListReport) and number <= cls.frozenColumns:       
        result1.append( u'<th>%s</th>' % title )
      else:
        result2.append( u'<th>%s</th>' % title )

  if issubclass(cls,TableReport):
    result2.append('<th>&nbsp;</th>')

  # Final result
  return (mark_safe(string_concat(*result1)), mark_safe(string_concat(*result2)))

  
filteroperator = {
  'icontains': _('contains (no case)'), 
  'contains': _('contains'),
  'istartswith': _('starts (no case)'),  
  'startswith': _('starts'),  
  'iendswith': _('ends (no case)'), 
  'endswith': _('ends'),  
  'iexact': _('equals (no case)'), 
  'exact': _('equals'),
  'isnull': _('is null'),
  '': _('='),
  'lt': u'&lt;',
  'gt': u'&gt;',
  'lte': u'&lt;=',
  'gte': u'&gt;=',
}

  
def _create_filter(req, cls):
  # Initialisation
  result1 = [u'<form id="filters" action="%s%s">' % (req.prefix,escape(req.path))]
  result2 = [u'<div id="fields" style="display: none"><form action="">\n']
  empty = True
    
  # Loop over the row fields - to make sure the filters are shown in the same order
  filtercounter = 0
  for row, attribs in cls.rows:
    try: filtertitle = attribs['title']
    except: filtertitle = row
    try: 
      filter = attribs['filter']
      filterfield = filter.field or row
      result2.append(u'<span title="%s" class="%s">' % (filterfield, filter.__class__.__name__))
      if hasattr(filter, "text2"):
        result2.append(filter.text2(filtertitle, filterfield, cls, req))
      else:
        result2.append(filtertitle)      
      result2.append(u'</span>\n')
    except: 
      filter = None
      filterfield = ''
      result2.append(u'<span>%s</span>\n' % filtertitle)
    for i in req.GET:
      if i in reservedParameters: 
        if filtercounter > 1: continue
        result1.append(u'<input type="hidden" name="%s" value="%s"/>' % (i,escape(req.GET[i])))
      field, sep, operator = i.rpartition('__')
      if field == '':
        field = operator
        operator = 'exact'
      if filterfield == field:
        if empty: 
          result1.append(u'where\n')
          empty = False
        else:
          result1.append(u' and\n')
        if filter:
          result1.append(filter.text1(filtertitle, operator, i, escape(req.GET[i]), cls, req))
        else:
          result1.append(u'%s %s <input type="text" class="filter" onChange="filterform()" name="%s" value="%s"/>' % (filtertitle, filteroperator[operator], i, escape(req.GET[i])))
        filtercounter += 1
      
  # Return result
  result2.append(u'</form></div>')
  if empty: return (None, mark_safe(string_concat(*result2)))
  result1.append(u'</form>')
  return ( mark_safe(string_concat(*result1)), mark_safe(string_concat(*result2)) )


class FilterText(object):
  def __init__(self, operator="icontains", field=None, size=10):
    self.operator = operator
    self.field = field
    self.size = size
    
  def text1(self, a,b,c,d,cls, req):
    return string_concat(a, u' ', filteroperator[b], u' <input type="text" class="filter" onChange="javascript:this.form.submit();" name="', c, u'" value="', d, u'" size="', max(len(d),self.size), u'"/>')


class FilterNumber(object):
  def __init__(self, operator="lt", field=None, size=9):
    self.operator = operator
    self.field = field
    self.size = size
    
  def text1(self, a,b,c,d,cls, req):
    return string_concat(a, u' ', filteroperator[b], u' <input type="text" class="filter" onChange="javascript:this.form.submit();" name="', c, u'" value="', d, u'" size="', self.size, u'"/>')


class FilterDate(object):
  def __init__(self, operator="lt", field=None, size=9):
    self.operator = operator
    self.field = field
    self.size = size
    
  def text1(self, a,b,c,d,cls, req):
    return string_concat(a, u' ', filteroperator[b], u' <input type="text" class="vDateField filter" onChange="javascript:this.form.submit();" name="', c, u'" value="', d, u'" size="', self.size, u'"/>')
    

class FilterChoice(object):
  def __init__(self, field=None, choices=None):
    self.field = field
    self.choices = choices
    
  def text1(self, a,b,c,d,cls, req):
    result = [string_concat(a, u' ', filteroperator[b], u'<select class="filter" onChange="javascript:this.form.submit();" name="', c, u'" >')]
    try:
      for code, label in callable(self.choices) and self.choices(req) or self.choices:    
        if (code == d):
          result.append(string_concat(u'<option value="',code,u'" selected="yes">',unicode(label),u'</option>\n'))
        else:
          result.append(string_concat(u'<option value="',code,u'">',unicode(label),u'</option>\n'))
    except TypeError: pass
    result.append(u'</select>\n')
    return string_concat(*result)
    
  def text2(self, a,b,cls, req):
    result = [string_concat(a, u'<select>')]
    try:
      for code, label in callable(self.choices) and self.choices(req) or self.choices:    
        result.append(string_concat(u'<option value="',code,u'">',unicode(label),u'</option>\n'))
    except TypeError: pass
    result.append(u'</select>\n')
    return string_concat(*result)


class FilterBool(FilterChoice):
  '''
  A boolean filter is a special case of the choice filter: the choices
  are limited to 0/false and 1/true.
  '''
  def __init__(self, field=None):
    super(FilterBool, self).__init__(
      field=field,
      choices=( ('0',_('False')), ('1',_('True')), ),
      )


def parseUpload(request, reportclass, data):
    '''
    This method reads CSV data from a string (in memory) and creates or updates
    the database records.
    The data must follow the following format:
      - the first row contains a header, listing all field names
      - a first character # marks a comment line
      - empty rows are skipped

    Limitation: SQLite doesnt validate the input data appropriately.
    E.g. It is possible to store character strings in a number field. An error
    is generated only when reading the record and trying to convert it to a
    Python number.
    E.g. It is possible to store invalid strings in a Date field.
    '''
    entityclass = reportclass.model
    headers = []
    rownumber = 0
    changed = 0
    added = 0
    warnings = []
    errors = []
    content_type_id = ContentType.objects.get_for_model(entityclass).pk
    
    transaction.enter_transaction_management(using=request.database)
    transaction.managed(True, using=request.database)
    try:
      # Loop through the data records
      has_pk_field = False
      for row in csv.reader(data.splitlines()):
        rownumber += 1
  
        ### Case 1: The first line is read as a header line
        if rownumber == 1:
          for col in row:
            col = col.strip().strip('#').lower()
            if col == "": 
              headers.append(False)
              continue
            ok = False
            for i in entityclass._meta.fields:
              if col == i.name.lower() or col == i.verbose_name.lower():
                if i.editable == True:
                  headers.append(i)
                else:
                  headers.append(False)
                ok = True
                break
            if not ok: errors.append(_('Incorrect field %(column)s') % {'column': col})
            if col == entityclass._meta.pk.name.lower() \
              or col == entityclass._meta.pk.verbose_name.lower():
                has_pk_field = True
          if not has_pk_field and not isinstance(entityclass._meta.pk, AutoField):
            # The primary key is not an auto-generated id and it is not mapped in the input...
            errors.append(_('Missing primary key field %(key)s') % {'key': entityclass._meta.pk.name})
          # Abort when there are errors
          if len(errors) > 0: return (warnings,errors,0,0)
          # Create a form class that will be used to validate the data
          def createmultidbformfield(f):
            if isinstance(f, RelatedField):
              return f.formfield(using=request.database)
            else:
              return f.formfield()
          UploadForm = modelform_factory(entityclass, 
            fields = tuple([i.name for i in headers if isinstance(i,Field)]),
            formfield_callback = createmultidbformfield
            )
  
        ### Case 2: Skip empty rows and comments rows
        elif len(row) == 0 or row[0].startswith('#'):
          continue
  
        ### Case 3: Process a data row
        else:
          try:
            # Step 1: Build a dictionary with all data fields
            d = {}
            colnum = 0
            for col in row:
              # More fields in data row than headers. Move on to the next row.
              if colnum >= len(headers): break      
              if isinstance(headers[colnum],Field): d[headers[colnum].name] = col.strip()
              colnum += 1
  
            # Step 2: Fill the form with data, either updating an existing
            # instance or creating a new one.
            if has_pk_field:
              # A primary key is part of the input fields
              try:
                # Try to find an existing record with the same primary key
                it = entityclass.objects.using(request.database).get(pk=d[entityclass._meta.pk.name])
                form = UploadForm(d, instance=it)
              except entityclass.DoesNotExist:
                form = UploadForm(d)
                it = None
            else:
              # No primary key required for this model
              form = UploadForm(d)
              it = None
            
            # Step 3: Validate the data and save to the database
            if form.has_changed():
              try:
                obj = form.save()
                LogEntry(
                    user_id         = request.user.pk,
                    content_type_id = content_type_id,
                    object_id       = obj.pk,
                    object_repr     = force_unicode(obj),
                    action_flag     = it and CHANGE or ADDITION,
                    change_message  = _('Changed %s.') % get_text_list(form.changed_data, _('and'))
                ).save(using=request.database)
                if it:
                  changed += 1
                else: 
                  added += 1
              except Exception, e:
                # Validation fails
                for error in form.non_field_errors():
                  warnings.append(
                    _('Row %(rownum)s: %(message)s') % {
                      'rownum': rownumber, 'message': error
                    })
                for field in form:
                  for error in field.errors:
                    warnings.append(
                      _('Row %(rownum)s field %(field)s: %(data)s: %(message)s') % {
                        'rownum': rownumber, 'data': d[field.name],
                        'field': field.name, 'message': error
                      })
  
            # Step 4: Commit the database changes from time to time
            if rownumber % 500 == 0: transaction.commit(using=request.database)
          except Exception, e:
            errors.append(_("Exception during upload: %(message)s") % {'message': e,})
    finally:
      transaction.commit(using=request.database)
      transaction.leave_transaction_management(using=request.database)

    # Report all failed records
    return (warnings, errors, changed, added)