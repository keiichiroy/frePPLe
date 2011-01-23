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

from django.db import connections
from django.utils.translation import ugettext_lazy as _
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.template import RequestContext, loader

from freppledb.input.models import Item
from freppledb.output.models import Demand
from freppledb.common.db import python_date, sql_datediff, sql_overlap
from freppledb.common.report import TableReport, ListReport, FilterText, FilterNumber, FilterDate, getBuckets


class OverviewReport(TableReport):
  '''
  A report showing the independent demand for each item.
  '''
  template = 'output/demand.html'
  title = _('Demand report')
  basequeryset = Item.objects.all()
  model = Item
  rows = (
    ('item',{
      'filter': FilterText(field='name'),
      'order_by': 'name',
      'title': _('item')
      }),
    )
  crosses = (
    ('forecast',{'title': _('net forecast')}),
    ('orders',{'title': _('orders')}),
    ('demand',{'title': _('total demand')}),
    ('supply',{'title': _('total supply')}),
    ('backlog',{'title': _('backlog')}),
    )
  columns = (
    ('bucket',{'title': _('bucket')}),
    )

  javascript_imports = ['/static/FusionCharts.js',]

  @staticmethod
  def resultlist1(request, basequery, bucket, startdate, enddate, sortsql='1 asc'):
    return basequery.values('name')

  @staticmethod
  def resultlist2(request, basequery, bucket, startdate, enddate, sortsql='1 asc'):
    basesql, baseparams = basequery.query.get_compiler(basequery.db).as_sql(with_col_aliases=True)
    cursor = connections[request.database].cursor()

    # Assure the item hierarchy is up to date
    Item.rebuildHierarchy(database=basequery.db)
    
    # Execute a query to get the backlog at the start of the horizon
    startbacklogdict = {}
    query = '''
      select items.name, sum(quantity)
      from (%s) items
      inner join item 
      on item.lft between items.lft and items.rght
      inner join out_demand
      on item.name = out_demand.item
        and (plandate is null or plandate >= '%s')
        and due < '%s'
      group by items.name
      ''' % (basesql, startdate, startdate)
    cursor.execute(query, baseparams)
    for row in cursor.fetchall():
      if row[0]: startbacklogdict[row[0]] = float(row[1])

    # Execute the query
    query = '''
        select y.name as row1,
               y.bucket as col1, y.startdate as col2, y.enddate as col3,
               min(y.orders),
               coalesce(sum(fcst.quantity * %s / %s),0),
               min(y.planned), y.lft as lft, y.rght as rght
        from (
          select x.name as name, x.lft as lft, x.rght as rght,
               x.bucket as bucket, x.startdate as startdate, x.enddate as enddate,
               coalesce(sum(demand.quantity),0) as orders,
               min(x.planned) as planned
          from (
          select items.name as name, items.lft as lft, items.rght as rght,
                 d.bucket as bucket, d.startdate as startdate, d.enddate as enddate,
                 coalesce(sum(out_demand.quantity),0) as planned
          from (%s) items
          -- Multiply with buckets
          cross join (
             select name as bucket, startdate, enddate
             from bucketdetail
             where bucket_id = '%s' and startdate >= '%s' and startdate < '%s'
             ) d
          -- Include hierarchical children
          inner join item
          on item.lft between items.lft and items.rght
          -- Planned quantity
          left join out_demand
          on item.name = out_demand.item 
          and d.startdate <= out_demand.plandate
          and d.enddate > out_demand.plandate
          -- Grouping
          group by items.name, items.lft, items.rght, d.bucket, d.startdate, d.enddate
        ) x
        -- Requested quantity
        inner join item
        on item.lft between x.lft and x.rght
        left join demand
        on item.name = demand.item_id
        and x.startdate <= demand.due
        and x.enddate > demand.due
        -- Grouping
        group by x.name, x.lft, x.rght, x.bucket, x.startdate, x.enddate
        ) y
        -- Forecasted quantity
        inner join item
        on item.lft between y.lft and y.rght
        left join (select forecast.item_id as item_id, out_forecast.startdate as startdate,
		        out_forecast.enddate as enddate, out_forecast.net as quantity
          from out_forecast, forecast
          where out_forecast.forecast = forecast.name
          ) fcst
        on item.name = fcst.item_id
        and fcst.enddate >= y.startdate
        and fcst.startdate <= y.enddate
        -- Ordering and grouping
        group by y.name, y.lft, y.rght, y.bucket, y.startdate, y.enddate
        order by %s, y.startdate
       ''' % (sql_overlap('fcst.startdate','fcst.enddate','y.startdate','y.enddate'),
         sql_datediff('fcst.enddate','fcst.startdate'),
         basesql,bucket,startdate,enddate,sortsql)
    cursor.execute(query,baseparams)

    # Build the python result
    previtem = None
    for row in cursor.fetchall():
      if row[0] != previtem:
        try: backlog =  startbacklogdict[row[0]]
        except: backlog = 0
        previtem = row[0]
      backlog += float(row[4]) + float(row[5]) - float(row[6])
      yield {
        'item': row[0],
        'bucket': row[1],
        'startdate': python_date(row[2]),
        'enddate': python_date(row[3]),
        'orders': row[4],
        'forecast': row[5],
        'demand': float(row[4]) + float(row[5]),
        'supply': row[6],
        'backlog': backlog,
        }


class DetailReport(ListReport):
  '''
  A list report to show delivery plans for demand.
  '''
  template = 'output/demandplan.html'
  title = _("Demand plan detail")
  reset_crumbs = False
  basequeryset = Demand.objects.extra(select={'forecast': "select name from forecast where out_demand.demand like forecast.name || ' - %%'",})
  model = Demand
  frozenColumns = 0
  editable = False
  rows = (
    ('demand', {
      'filter': FilterText(),
      'title': _('demand')
      }),
    ('item', {
      'title': _('item'),
      'filter': FilterText(),
      }),
    ('customer', {
      'title': _('customer'),
      'filter': FilterText(),
      }),
    ('quantity', {
      'title': _('quantity'),
      'filter': FilterNumber(),
      }),
    ('planquantity', {
      'title': _('planned quantity'),
      'filter': FilterNumber(),
      }),
    ('due', {
      'title': _('due date'),
      'filter': FilterDate(field='due'),
      }),
    ('plandate', {
      'title': _('planned date'),
      'filter': FilterDate(field='plandate'),
      }),
    ('operationplan', {'title': _('operationplan')}),
    )


@staff_member_required
def GraphData(request, entity):
  basequery = Item.objects.filter(pk__exact=entity)
  (bucket,start,end,bucketlist) = getBuckets(request)
  demand = []
  supply = []
  backlog = []
  for x in OverviewReport.resultlist2(request, basequery, bucket, start, end):
    demand.append(x['demand'])
    supply.append(x['supply'])
    backlog.append(x['backlog'])
  context = { 
    'buckets': bucketlist, 
    'demand': demand, 
    'supply': supply, 
    'backlog': backlog, 
    'axis_nth': len(bucketlist) / 20 + 1,
    }
  return HttpResponse(
    loader.render_to_string("output/demand.xml", context, context_instance=RequestContext(request)),
    )