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

from datetime import datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect, Http404
from django.views.decorators.csrf import csrf_protect
from django.utils import simplejson
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import iri_to_uri, force_unicode

from freppledb.input.models import Resource, Forecast, Operation, Location, SetupMatrix 
from freppledb.input.models import Buffer, Customer, Demand, Parameter, Item, Load, Flow
from freppledb.input.models import Calendar, CalendarBucket, OperationPlan, SubOperation
from freppledb.input.models import Bucket, BucketDetail
from freppledb.common.report import ListReport, FilterText, FilterDate, FilterNumber, FilterBool


class uploadjson:
  '''
  This class allows us to process json-formatted post requests.

  The current implementation is only temporary until a more generic REST interface
  becomes available in Django: see http://code.google.com/p/django-rest-interface/
  '''
  @staticmethod
  @csrf_protect
  @staff_member_required
  def post(request):
    try:
      # Validate the upload form
      if request.method != 'POST':
        raise Exception(_('Only POST method allowed'))

      # Validate uploaded file is present
      if len(request.FILES)!=1 or 'data' not in request.FILES \
        or request.FILES['data'].content_type != 'application/json' \
        or request.FILES['data'].size > 1000000:
          raise Exception('Invalid uploaded data')

      # Parse the uploaded data and go over each record
      for i in simplejson.JSONDecoder().decode(request.FILES['data'].read()):
        try:
          entity = i['entity']

          # CASE 1: The maximum calendar of a resource is being edited
          if entity == 'resource.maximum':
            # Create a message
            try:
              msg = "capacity change for '%s' between %s and %s to %s" % \
                    (i['name'],i['startdate'],i['enddate'],i['value'])
            except:
              msg = "capacity change"
            # a) Verify permissions
            if not request.user.has_perm('input.change_resource'):
              raise Exception('No permission to change resources')
            # b) Find the calendar
            res = Resource.objects.using(request.database).get(name = i['name'])
            if not res.maximum_calendar:
              raise Exception('Resource "%s" has no max calendar' % res.name)
            # c) Update the calendar
            start = datetime.strptime(i['startdate'],'%Y-%m-%d')
            end = datetime.strptime(i['enddate'],'%Y-%m-%d')
            res.maximum_calendar.setvalue(
              start,
              end,
              float(i['value']) / (end - start).days,
              user = request.user)

          # CASE 2: The forecast quantity is being edited
          elif entity == 'forecast.total':
            # Create a message
            try:
              msg = "forecast change for '%s' between %s and %s to %s" % \
                      (i['name'],i['startdate'],i['enddate'],i['value'])
            except:
              msg = "forecast change"
            # a) Verify permissions
            if not request.user.has_perm('input.change_forecastdemand'):
              raise Exception('No permission to change forecast demand')
            # b) Find the forecast
            start = datetime.strptime(i['startdate'],'%Y-%m-%d')
            end = datetime.strptime(i['enddate'],'%Y-%m-%d')
            fcst = Forecast.objects.using(request.database).get(name = i['name'])
            # c) Update the forecast
            fcst.setTotal(start,end,i['value'])

          # All the rest is garbage
          else:
            msg = "unknown action"
            raise Exception(_("Unknown action type '%(msg)s'") % {'msg':entity})

        except Exception, e:
          messages.add_message(request, messages.ERROR, 'Error processing %s: %s' % (msg,e))

      # Processing went fine...
      return HttpResponse("OK")

    except Exception, e:
      print 'Error processing uploaded data: %s %s' % (type(e),e)
      return HttpResponseForbidden('Error processing uploaded data: %s' % e)


class pathreport:
  '''
  A report showing the upstream supply path or following downstream a
  where-used path.
  The supply path report shows all the materials, operations and resources
  used to make a certain item.
  The where-used report shows all the materials and operations that use
  a specific item.
  '''

  @staticmethod
  def getPath(request, type, entity, downstream):
    '''
    A generator function that recurses upstream or downstream in the supply
    chain.

    todo: The current code only supports 1 level of super- or sub-operations.
    '''
    from django.core.exceptions import ObjectDoesNotExist
    if type == 'buffer':
      # Find the buffer
      try: root = [ (0, Buffer.objects.using(request.database).get(name=entity), None, None, None, Decimal(1)) ]
      except ObjectDoesNotExist: raise Http404, "buffer %s doesn't exist" % entity
    elif type == 'item':
      # Find the item
      try:
        root = [ (0, r, None, None, None, Decimal(1)) for r in Buffer.objects.filter(item=entity).using(request.database) ]
      except ObjectDoesNotExist: raise Http404, "item %s doesn't exist" % entity
    elif type == 'operation':
      # Find the operation
      try: root = [ (0, None, None, Operation.objects.using(request.database).get(name=entity), None, Decimal(1)) ]
      except ObjectDoesNotExist: raise Http404, "operation %s doesn't exist" % entity
    elif type == 'resource':
      # Find the resource
      try: root = Resource.objects.using(request.database).get(name=entity)
      except ObjectDoesNotExist: raise Http404, "resource %s doesn't exist" % entity
      root = [ (0, None, None, i.operation, None, Decimal(1)) for i in root.loads.using(request.database).all() ]
    else:
      raise Http404, "invalid entity type %s" % type

    # Note that the root to start with can be either buffer or operation.
    visited = []
    while len(root) > 0:
      level, curbuffer, curprodflow, curoperation, curconsflow, curqty = root.pop()
      yield {
        'buffer': curbuffer,
        'producingflow': curprodflow,
        'operation': curoperation,
        'level': abs(level),
        'consumingflow': curconsflow,
        'cumquantity': curqty,
        }

      # Avoid infinite loops when the supply chain contains cycles
      if curbuffer in visited: continue
      else: visited.append(curbuffer)

      if downstream:
        # Find all operations consuming from this buffer...
        if curbuffer:
          start = [ (i, i.operation) for i in curbuffer.flows.filter(quantity__lt=0).select_related(depth=1).using(request.database) ]
        else:
          start = [ (None, curoperation) ]
        for cons_flow, curoperation in start:
          if not cons_flow and not curoperation: continue
          # ... and pick up the buffer they produce into
          ok = False

          # Push the next buffer on the stack, based on current operation
          for prod_flow in curoperation.flows.filter(quantity__gt=0).select_related(depth=1).using(request.database):
            ok = True
            root.append( (level+1, prod_flow.thebuffer, prod_flow, curoperation, cons_flow, curqty / prod_flow.quantity * (cons_flow and cons_flow.quantity * -1 or 1)) )

          # Push the next buffer on the stack, based on super-operations
          for x in curoperation.superoperations.select_related(depth=1).using(request.database):
            for prod_flow in x.suboperation.flows.filter(quantity__gt=0).using(request.database):
              ok = True
              root.append( (level+1, prod_flow.thebuffer, prod_flow, curoperation, cons_flow, curqty / prod_flow.quantity * (cons_flow and cons_flow.quantity * -1 or 1)) )

          # Push the next buffer on the stack, based on sub-operations
          for x in curoperation.suboperations.select_related(depth=1).using(request.database):
            for prod_flow in x.operation.flows.filter(quantity__gt=0).using(request.database):
              ok = True
              root.append( (level+1, prod_flow.thebuffer, prod_flow, curoperation, cons_flow, curqty / prod_flow.quantity * (cons_flow and cons_flow.quantity * -1 or 1)) )

          if not ok and cons_flow:
            # No producing flow found: there are no more buffers downstream
            root.append( (level+1, None, None, curoperation, cons_flow, curqty * cons_flow.quantity * -1) )

      else:
        # Find all operations producing into this buffer...
        if curbuffer:
          if curbuffer.producing:
            start = [ (i, i.operation) for i in curbuffer.producing.flows.filter(quantity__gt=0).select_related(depth=1).using(request.database) ]
          else:
            start = []
        else:
          start = [ (None, curoperation) ]
        for prod_flow, curoperation in start:
          if not prod_flow and not curoperation: continue
          # ... and pick up the buffer they produce into
          ok = False

          # Push the next buffer on the stack, based on current operation
          for cons_flow in curoperation.flows.filter(quantity__lt=0).select_related(depth=1).using(request.database):
            ok = True
            root.append( (level-1, cons_flow.thebuffer, prod_flow, cons_flow.operation, cons_flow, curqty / (prod_flow and prod_flow.quantity or 1) * cons_flow.quantity * -1) )

          # Push the next buffer on the stack, based on super-operations
          for x in curoperation.superoperations.select_related(depth=1).using(request.database):
            for cons_flow in x.suboperation.flows.filter(quantity__lt=0).using(request.database):
              ok = True
              root.append( (level-1, cons_flow.thebuffer, prod_flow, cons_flow.operation, cons_flow, curqty / (prod_flow and prod_flow.quantity or 1) * cons_flow.quantity * -1) )

          # Push the next buffer on the stack, based on sub-operations
          for x in curoperation.suboperations.select_related(depth=1).using(request.database):
            for cons_flow in x.operation.flows.filter(quantity__lt=0).using(request.database):
              ok = True
              root.append( (level-1, cons_flow.thebuffer, prod_flow, cons_flow.operation, cons_flow, curqty / (prod_flow and prod_flow.quantity or 1) * cons_flow.quantity * -1) )

          if not ok and prod_flow:
            # No consuming flow found: there are no more buffers upstream
            ok = True
            root.append( (level-1, None, prod_flow, prod_flow.operation, None, curqty / prod_flow.quantity) )


  @staticmethod
  @staff_member_required
  def viewdownstream(request, type, entity):
    return render_to_response('input/path.html', RequestContext(request,{
       'title': _('Where-used report for %(type)s %(entity)s') % {'type':_(type), 'entity':entity},
       'supplypath': pathreport.getPath(request, type, entity, True),
       'type': type,
       'entity': entity,
       'downstream': True,
       }))


  @staticmethod
  @staff_member_required
  def viewupstream(request, type, entity):
    return render_to_response('input/path.html', RequestContext(request,{
       'title': _('Supply path report for %(type)s %(entity)s') % {'type':_(type), 'entity':entity},
       'supplypath': pathreport.getPath(request, type, entity, False),
       'type': type,
       'entity': entity,
       'downstream': False,
       }))


@staff_member_required
def location_calendar(request, location):
  # Check to find a location availability calendar
  loc = Location.objects.using(request.database).get(pk=location)
  if loc: 
    cal = loc.available
  if cal: 
    # Go to the calendar
    return HttpResponseRedirect('%s/admin/input/calendar/%s/' % (request.prefix, iri_to_uri(cal.name)) )
  # Generate a message
  try: 
    url = request.META.get('HTTP_REFERER')
    messages.add_message(request, messages.ERROR, 
      force_unicode(_('No availability calendar found')))
    return HttpResponseRedirect(url)
  except: raise Http404
    

class ParameterList(ListReport):
  '''
  A list report to show all configurable parameters.
  '''
  template = 'input/parameterlist.html'
  title = _("Parameter List")
  basequeryset = Parameter.objects.all()
  model = Parameter
  frozenColumns = 1

  @staticmethod
  def resultlist1(request, basequery, bucket, startdate, enddate, sortsql='1 asc'):
    return basequery.values('name','value','description','lastmodified')

  rows = (
    ('name', {
      'title': _('name'),
      'filter': FilterText(),
      }),
    ('value', {
      'title': _('value'),
      'filter': FilterText(),
      }),
    ('description', {
      'title': _('description'),
      'filter': FilterText(),
      }),
    ('lastmodified', {
      'title': _('last modified'),
      'filter': FilterDate(),
      }),
    )
    

class BufferList(ListReport):
  '''
  A list report to show buffers.
  '''
  template = 'input/bufferlist.html'
  title = _("Buffer List")
  basequeryset = Buffer.objects.all()
  model = Buffer
  frozenColumns = 1

  @staticmethod
  def resultlist1(request, basequery, bucket, startdate, enddate, sortsql='1 asc'):
    return basequery.values(
      'name','description','category','subcategory','location','item','onhand',
      'owner','type','minimum','minimum_calendar','producing','carrying_cost','lastmodified'
      )

  rows = (
    ('name', {
      'title': _('name'),
      'filter': FilterText(),
      }),
    ('description', {
      'title': _('description'),
      'filter': FilterText(),
      }),
    ('category', {
      'title': _('category'),
      'filter': FilterText(),
      }),
    ('subcategory', {
      'title': _('subcategory'),
      'filter': FilterText(),
      }),
    ('location', {
      'title': _('location'),
      'filter': FilterText(field='location__name'),
      }),
    ('item', {
      'title': _('item'),
      'filter': FilterText(field='item__name'),
      }),
    ('onhand', {
      'title': _('onhand'),
      'filter': FilterNumber(size=5, operator="lt"),
      }),
    ('owner', {
      'title': _('owner'),
      'filter': FilterText(field='owner__name'),
      }),
    ('type', {
      'title': _('type'),
      'filter': FilterText(),
      }),
    ('minimum', {
      'title': _('minimum'),
      'filter': FilterNumber(size=5, operator="lt"),
      }),
    ('minimum_calendar', {
      'title': _('minimum calendar'),
      'filter': FilterText(field='minimum__name'),
      }),
    ('producing', {
      'title': _('producing'),
      'filter': FilterText(field='producing__name'),
      }),
    ('carrying_cost', {
      'title': _('carrying cost'),
      'filter': FilterNumber(size=5, operator="lt"),
      }),
    ('lastmodified', {
      'title': _('last modified'),
      'filter': FilterDate(),
      }),
    )


class SetupMatrixList(ListReport):
  '''
  A list report to show setup matrices.
  '''
  template = 'input/setupmatrixlist.html'
  title = _("Setup Matrix List")
  basequeryset = SetupMatrix.objects.all()
  model = SetupMatrix
  frozenColumns = 1

  @staticmethod
  def resultlist1(request, basequery, bucket, startdate, enddate, sortsql='1 asc'):
    return basequery.values('name','lastmodified')

  rows = (
    ('name', {
      'title': _('name'),
      'filter': FilterText(),
      }),
    ('lastmodified', {
      'title': _('last modified'),
      'filter': FilterDate(),
      }),
    )
     

class ResourceList(ListReport):
  '''
  A list report to show resources.
  '''
  template = 'input/resourcelist.html'
  title = _("Resource List")
  basequeryset = Resource.objects.all()
  model = Resource
  frozenColumns = 1

  @staticmethod
  def resultlist1(request, basequery, bucket, startdate, enddate, sortsql='1 asc'):
    return basequery.values(
      'name','description','category','subcategory','location','owner','type',
      'maximum','maximum_calendar','cost','maxearly','setupmatrix','setup','lastmodified'
      )

  rows = (
    ('name', {
      'title': _('name'),
      'filter': FilterText(),
      }),
    ('description', {
      'title': _('description'),
      'filter': FilterText(),
      }),
    ('category', {
      'title': _('category'),
      'filter': FilterText(),
      }),
    ('subcategory', {
      'title': _('subcategory'),
      'filter': FilterText(),
      }),
    ('location', {
      'title': _('location'),
      'filter': FilterText(field='location__name'),
      }),    
    ('owner', {
      'title': _('owner'),
      'filter': FilterText(field='owner__name'),
      }),
    ('type', {
      'title': _('type'),
      'filter': FilterText(),
      }),
    ('maximum', {
      'title': _('maximum'),
      'filter': FilterNumber(size=5, operator="lt"),
      }),
    ('maximum_calendar', {
      'title': _('maximum calendar'),
      'filter': FilterText(field='maximum_calendar__name'),
      }),
    ('cost', {
      'title': _('cost'),
      'filter': FilterNumber(size=5, operator="lt"),
      }),
    ('maxearly', {
      'title': _('max early'),
      'filter': FilterNumber(),
      }),
    ('setupmatrix', {
      'title': _('setup matrix'),
      'filter': FilterText(),
      }),
    ('setup', {
      'title': _('setup'),
      'filter': FilterText(),
      }),
    ('lastmodified', {
      'title': _('last modified'),
      'filter': FilterDate(),
      }),
    )


class LocationList(ListReport):
  '''
  A list report to show locations.
  '''
  template = 'input/locationlist.html'
  title = _("Location List")
  basequeryset = Location.objects.all()
  model = Location
  frozenColumns = 1

  @staticmethod
  def resultlist1(request, basequery, bucket, startdate, enddate, sortsql='1 asc'):
    return basequery.values(
      'name','description','category','subcategory','available','owner',
      'lastmodified'
      )

  rows = (
    ('name', {
      'title': _('name'),
      'filter': FilterText(),
      }),
    ('description', {
      'title': _('description'),
      'filter': FilterText(),
      }),
    ('category', {
      'title': _('category'),
      'filter': FilterText(),
      }),
    ('subcategory', {
      'title': _('subcategory'),
      'filter': FilterText(),
      }),
    ('available', {
      'title': _('available'),
      'filter': FilterText(field='available__name'),
      }),
    ('owner', {
      'title': _('owner'),
      'filter': FilterText(field='owner__name'),
      }),
    ('lastmodified', {
      'title': _('last modified'),
      'filter': FilterDate(),
      }),
    )


class CustomerList(ListReport):
  '''
  A list report to show locations.
  '''
  template = 'input/customerlist.html'
  title = _("Customer List")
  basequeryset = Customer.objects.all()
  model = Customer
  frozenColumns = 1

  @staticmethod
  def resultlist1(request, basequery, bucket, startdate, enddate, sortsql='1 asc'):
    return basequery.values(
      'name','description','category','subcategory','owner','lastmodified'
      )

  rows = (
    ('name', {
      'title': _('name'),
      'filter': FilterText(),
      }),
    ('description', {
      'title': _('description'),
      'filter': FilterText(),
      }),
    ('category', {
      'title': _('category'),
      'filter': FilterText(),
      }),
    ('subcategory', {
      'title': _('subcategory'),
      'filter': FilterText(),
      }),
    ('owner', {
      'title': _('owner'),
      'filter': FilterText(field='owner__name'),
      }),
    ('lastmodified', {
      'title': _('last modified'),
      'filter': FilterDate(),
      }),
    )


class ItemList(ListReport):
  '''
  A list report to show items.
  '''
  template = 'input/itemlist.html'
  title = _("Item List")
  basequeryset = Item.objects.all()
  model = Item
  frozenColumns = 1

  @staticmethod
  def resultlist1(request, basequery, bucket, startdate, enddate, sortsql='1 asc'):
    return basequery.values(
      'name','description','category','subcategory','operation','owner',
      'price','lastmodified'
      )

  rows = (
    ('name', {
      'title': _('name'),
      'filter': FilterText(),
      }),
    ('description', {
      'title': _('description'),
      'filter': FilterText(),
      }),
    ('category', {
      'title': _('category'),
      'filter': FilterText(),
      }),
    ('subcategory', {
      'title': _('subcategory'),
      'filter': FilterText(),
      }),
    ('operation', {
      'title': _('operation'),
      'filter': FilterText(field='operation__name'),
      }),
    ('owner', {
      'title': _('owner'),
      'filter': FilterText(field='owner__name'),
      }),
    ('price', {
      'title': _('price'),
      'filter': FilterNumber(size=5, operator="lt"),
      }),
    ('lastmodified', {
      'title': _('last modified'),
      'filter': FilterDate(),
      }),
    )


class LoadList(ListReport):
  '''
  A list report to show loads.
  '''
  template = 'input/loadlist.html'
  title = _("Load List")
  basequeryset = Load.objects.all()
  model = Load
  frozenColumns = 1

  @staticmethod
  def resultlist1(request, basequery, bucket, startdate, enddate, sortsql='1 asc'):
    return basequery.values(
      'id','operation','resource','quantity','effective_start','effective_end',
      'name','alternate','priority','setup','search','lastmodified'
      )

  rows = (
    ('id', {
      'title': _('identifier'),
      'filter': FilterNumber(),
      }),
    ('operation', {
      'title': _('operation'),
      'filter': FilterText(field='operation__name'),
      }),
    ('resource', {
      'title': _('resource'),
      'filter': FilterText(field='resource__name'),
      }),
    ('quantity', {
      'title': _('quantity'),
      'filter': FilterNumber(),
      }),
    ('effective_start', {
      'title': _('effective start'),
      'filter': FilterDate(),
      }),
    ('effective_end', {
      'title': _('effective end'),
      'filter': FilterDate(),
      }),
    ('name', {
      'title': _('name'),
      'filter': FilterText(),
      }),
    ('alternate', {
      'title': _('alternate'),
      'filter': FilterText(),
      }),
    ('priority', {
      'title': _('priority'),
      'filter': FilterNumber(),
      }),
    ('setup', {
      'title': _('setup'),
      'filter': FilterText(),
      }),
    ('search', {
      'title': _('search mode'),
      'filter': FilterText(),
      }),
    ('lastmodified', {
      'title': _('last modified'),
      'filter': FilterDate(),
      }),
    )


class FlowList(ListReport):
  '''
  A list report to show flows.
  '''
  template = 'input/flowlist.html'
  title = _("Flow List")
  basequeryset = Flow.objects.all()
  model = Flow
  frozenColumns = 1

  @staticmethod
  def resultlist1(request, basequery, bucket, startdate, enddate, sortsql='1 asc'):
    return basequery.values(
      'id','operation','thebuffer','type','quantity','effective_start',
      'effective_end','name','alternate','priority','search','lastmodified'
      )

  rows = (
    ('id', {
      'title': _('identifier'),
      'filter': FilterNumber(),
      }),
    ('operation', {
      'title': _('operation'),
      'filter': FilterText(field='operation__name'),
      }),
    ('thebuffer', {
      'title': _('buffer'),
      'filter': FilterText(field='thebuffer__name'),
      }),
    ('type', {
      'title': _('type'),
      'filter': FilterText(),
      }),
    ('quantity', {
      'title': _('quantity'),
      'filter': FilterNumber(),
      }),
    ('effective_start', {
      'title': _('effective start'),
      'filter': FilterDate(),
      }),
    ('effective_end', {
      'title': _('effective end'),
      'filter': FilterDate(),
      }),
    ('name', {
      'title': _('name'),
      'filter': FilterText(),
      }),
    ('alternate', {
      'title': _('alternate'),
      'filter': FilterText(),
      }),
    ('priority', {
      'title': _('priority'),
      'filter': FilterNumber(),
      }),
    ('search', {
      'title': _('search mode'),
      'filter': FilterText(),
      }),
    ('lastmodified', {
      'title': _('last modified'),
      'filter': FilterDate(),
      }),
    )


class DemandList(ListReport):
  '''
  A list report to show demands.
  '''
  template = 'input/demandlist.html'
  title = _("Demand List")
  basequeryset = Demand.objects.all()
  model = Demand
  frozenColumns = 1

  @staticmethod
  def resultlist1(request, basequery, bucket, startdate, enddate, sortsql='1 asc'):
    return basequery.values(
      'name','item','customer','description','category','subcategory',
      'due','quantity','operation','priority','owner','maxlateness',
      'minshipment','lastmodified'
      )

  rows = (
    ('name', {
      'title': _('name'),
      'filter': FilterText(),
      }),
    ('item', {
      'title': _('item'),
      'filter': FilterText(field="item__name"),
      }),
    ('customer', {
      'title': _('customer'),
      'filter': FilterText(field="customer__name"),
      }),
    ('description', {
      'title': _('description'),
      'filter': FilterText(),
      }),
    ('category', {
      'title': _('category'),
      'filter': FilterText(),
      }),
    ('subcategory', {
      'title': _('subcategory'),
      'filter': FilterText(),
      }),
    ('due', {
      'title': _('due'),
      'filter': FilterDate(),
      }),
    ('quantity', {
      'title': _('quantity'),
      'filter': FilterNumber(),
      }),
    ('operation', {
      'title': _('delivery operation'),
      'filter': FilterText(),
      }),
    ('priority', {
      'title': _('priority'),
      'filter': FilterNumber(),
      }),
    ('owner', {
      'title': _('owner'),
      'filter': FilterText(field='owner__name'),
      }),
    ('maxlateness', {
      'title': _('maximum lateness'),
      'filter': FilterNumber(),
      }),
    ('minshipment', {
      'title': _('minimum shipment'),
      'filter': FilterNumber(),
      }),
    ('lastmodified', {
      'title': _('last modified'),
      'filter': FilterDate(),
      }),
    )


class ForecastList(ListReport):
  '''
  A list report to show forecasts.
  '''
  template = 'input/forecastlist.html'
  title = _("Forecast List")
  basequeryset = Forecast.objects.all()
  model = Forecast
  frozenColumns = 1

  @staticmethod
  def resultlist1(request, basequery, bucket, startdate, enddate, sortsql='1 asc'):
    return basequery.values(
      'name','item','customer','calendar','description','category',
      'subcategory','operation','priority','minshipment','maxlateness',
      'discrete','lastmodified'
      )

  rows = (
    ('name', {
      'title': _('name'),
      'filter': FilterText(),
      }),
    ('item', {
      'title': _('item'),
      'filter': FilterText(field="item__name"),
      }),
    ('customer', {
      'title': _('customer'),
      'filter': FilterText(field="customer__name"),
      }),
    ('calendar', {
      'title': _('calendar'),
      'filter': FilterText(field="calendar__name"),
      }),
    ('description', {
      'title': _('description'),
      'filter': FilterText(),
      }),
    ('category', {
      'title': _('category'),
      'filter': FilterText(),
      }),
    ('subcategory', {
      'title': _('subcategory'),
      'filter': FilterText(),
      }),
    ('operation', {
      'title': _('operation'),
      'filter': FilterText(),
      }),
    ('priority', {
      'title': _('priority'),
      'filter': FilterNumber(),
      }),
    ('minshipment', {
      'title': _('minshipment'),
      'filter': FilterNumber(),
      }),
    ('maxlateness', {
      'title': _('maxlateness'),
      'filter': FilterNumber(),
      }),
    ('discrete', {
      'title': _('discrete'),
      'filter': FilterBool(),
      }),
    ('lastmodified', {
      'title': _('last modified'),
      'filter': FilterDate(),
      }),
    )


class CalendarList(ListReport):
  '''
  A list report to show calendars.
  '''
  template = 'input/calendarlist.html'
  title = _("Calendar List")
  basequeryset = Calendar.objects.all()
  model = Calendar
  frozenColumns = 1
  rows = (
    ('name', {
      'title': _('name'),
      'filter': FilterText(),
      }),
    ('type', {
      'title': _('type'),
      'filter': FilterText(),
      }),
    ('description', {
      'title': _('description'),
      'filter': FilterText(),
      }),
    ('category', {
      'title': _('category'),
      'filter': FilterText(),
      }),
    ('subcategory', {
      'title': _('subcategory'),
      'filter': FilterText(),
      }),
    ('defaultvalue', {
      'title': _('default value'),
      'sort': FilterNumber(),
      }),
    ('currentvalue', {      # @todo this field doesn't show up nice in the CSV export
      'title': _('current value'),
      'sort': False,
      }),
    ('lastmodified', {
      'title': _('last modified'),
      'filter': FilterDate(),
      }),
    )


class CalendarBucketList(ListReport):
  '''
  A list report to show calendar buckets.
  '''
  template = 'input/calendarbucketlist.html'
  title = _("Calendar Bucket List")
  basequeryset = CalendarBucket.objects.all()
  model = CalendarBucket
  frozenColumns = 1
  rows = (
    ('id', {
      'title': _('id'),
      'filter': FilterNumber(),
      }),
    ('calendar', {
      'title': _('calendar'),
      'filter': FilterText(field='calendar__name'),
      }),
    ('startdate', {
      'title': _('start date'),
      'filter': FilterDate(),
      }),
    ('enddate', {
      'title': _('end date'),
      'filter': FilterDate(),
      }),
    ('value', {
      'title': _('value'),
      'filter': FilterNumber(),
      }),
    ('priority', {
      'title': _('priority'),
      'filter': FilterNumber(),
      }),
    ('name', {
      'title': _('name'),
      'sort': FilterText(),
      }),
    ('lastmodified', {
      'title': _('last modified'),
      'filter': FilterDate(),
      }),
    )


class OperationList(ListReport):
  '''
  A list report to show operations.
  '''
  template = 'input/operationlist.html'
  title = _("Operation List")
  basequeryset = Operation.objects.all()
  model = Operation
  frozenColumns = 1

  @staticmethod
  def resultlist1(request, basequery, bucket, startdate, enddate, sortsql='1 asc'):
    return basequery.values(
      'name','description','category','subcategory','type','location','duration','duration_per','fence','pretime','posttime','sizeminimum',
      'sizemultiple','sizemaximum','cost','search','lastmodified'
      )

  rows = (
    ('name', {
      'title': _('name'),
      'filter': FilterText(),
      }),
    ('description', {
      'title': _('description'),
      'filter': FilterText(),
      }),
    ('category', {
      'title': _('category'),
      'filter': FilterText(),
      }),
    ('subcategory', {
      'title': _('subcategory'),
      'filter': FilterText(),
      }),
    ('type', {
      'title': _('type'),
      'filter': FilterText(),
      }),
    ('location', {
      'title': _('location'),
      'filter': FilterText(field='location__name'),
      }),
    ('duration', {
      'title': _('duration'),
      'filter': FilterNumber(),
      }),
    ('duration_per', {
      'title': _('duration_per'),
      'filter': FilterNumber(),
      }),
    ('fence', {
      'title': _('fence'),
      'filter': FilterNumber(),
      }),
    ('pretime', {
      'title': _('pre-op time'),
      'filter': FilterNumber(),
      }),
    ('posttime', {
      'title': _('post-op time'),
      'filter': FilterNumber(),
      }),
    ('sizeminimum', {
      'title': _('size minimum'),
      'filter': FilterNumber(),
      }),
    ('sizemultiple', {
      'title': _('size multiple'),
      'filter': FilterNumber(),
      }),
    ('sizemaximum', {
      'title': _('size maximum'),
      'filter': FilterNumber(),
      }),
    ('cost', {
      'title': _('cost'),
      'filter': FilterNumber(size=5, operator="lt"),
      }),
    ('search', {
      'title': _('search mode'),
      'filter': FilterText(),
      }),
    ('lastmodified', {
      'title': _('last modified'),
      'filter': FilterDate(),
      }),
    )


class SubOperationList(ListReport):
  '''
  A list report to show suboperations.
  '''
  template = 'input/suboperationlist.html'
  title = _("Suboperation List")
  basequeryset = SubOperation.objects.all()
  model = SubOperation
  frozenColumns = 1

  @staticmethod
  def resultlist1(request, basequery, bucket, startdate, enddate, sortsql='1 asc'):
    return basequery.values(
      'id','operation','suboperation','priority','effective_start','effective_end',
      'lastmodified'
      )

  rows = (
    ('id', {
      'title': _('identifier'),
      'filter': FilterNumber(),
      }),
    ('operation', {
      'title': _('operation'),
      'filter': FilterText(field='operation__name'),
      }),
    ('suboperation', {
      'title': _('suboperation'),
      'filter': FilterText(field='suboperation__name'),
      }),
    ('priority', {
      'title': _('priority'),
      'filter': FilterNumber(),
      }),
    ('effective_start', {
      'title': _('effective start'),
      'filter': FilterDate(),
      }),
    ('effective_end', {
      'title': _('effective end'),
      'filter': FilterDate(),
      }),
    ('lastmodified', {
      'title': _('last modified'),
      'filter': FilterDate(),
      }),
    )


class OperationPlanList(ListReport):
  '''
  A list report to show operationplans.
  '''
  template = 'input/operationplanlist.html'
  title = _("Operationplan List")
  basequeryset = OperationPlan.objects.all()
  model = OperationPlan
  frozenColumns = 1

  @staticmethod
  def resultlist1(request, basequery, bucket, startdate, enddate, sortsql='1 asc'):
    return basequery.values(
      'id','operation','startdate','enddate','quantity','locked',
      'lastmodified'
      )

  rows = (
    ('id', {
      'title': _('identifier'),
      'filter': FilterNumber(),
      }),
    ('operation', {
      'title': _('operation'),
      'filter': FilterText(field='operation__name'),
      }),
    ('startdate', {
      'title': _('start date'),
      'filter': FilterDate(),
      }),
    ('enddate', {
      'title': _('end date'),
      'filter': FilterDate(),
      }),
    ('quantity', {
      'title': _('quantity'),
      'filter': FilterNumber(),
      }),
    ('locked', {
      'title': _('locked'),
      'filter': FilterBool(),
      }),
    ('lastmodified', {
      'title': _('last modified'),
      'filter': FilterDate(),
      }),
    )


class BucketList(ListReport):
  '''
  A list report to show dates.
  '''
  template = 'input/bucketlist.html'
  title = _("Bucket List")
  basequeryset = Bucket.objects.all()
  model = Bucket
  frozenColumns = 1
  rows = (
    ('name', {
      'title': _('name'),
      'filter': FilterText(),
      }),
    ('description', {
      'title': _('description'),
      'filter': FilterText(),
      }),
    ('lastmodified', {
      'title': _('last modified'),
      'filter': FilterDate(),
      }),
    )


class BucketDetailList(ListReport):
  '''
  A list report to show dates.
  '''
  template = 'input/bucketdetaillist.html'
  title = _("Bucket Detail List")
  basequeryset = BucketDetail.objects.all()
  model = BucketDetail
  frozenColumns = 1
  rows = (
    ('id', {
      'title': _('id'),
      'filter': FilterNumber(),
      }),
    ('bucket', {
      'title': _('bucket'),
      'filter': FilterText(field='bucket__name'),
      }),
    ('startdate', {
      'title': _('start date'),
      'filter': FilterDate(),
      }),
    ('enddate', {
      'title': _('end date'),
      'filter': FilterDate(),
      }),
    ('lastmodified', {
      'title': _('last modified'),
      'filter': FilterDate(),
      }),
    )
    