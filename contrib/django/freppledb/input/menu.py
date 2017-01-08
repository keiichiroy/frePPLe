# Copyright (C) 2013 by frePPLe bvba
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero
# General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from freppledb.menu import menu

import freppledb.input.views
from freppledb.input.models import Buffer, Item, Customer, Location, Demand
from freppledb.input.models import DistributionOrder, OperationPlan, CalendarBucket
from freppledb.input.models import PurchaseOrder, Supplier, ItemSupplier,Flow
from freppledb.input.models import ItemDistribution, Skill, Resource, Load
from freppledb.input.models import ResourceSkill, SetupMatrix, SubOperation
from freppledb.input.models import Calendar, Operation


menu.addItem(
  "inventory", "buffer admin", url="/data/input/buffer/",
  report=freppledb.input.views.BufferList, index=1100, model=Buffer
  )
menu.addItem(
  "sales", "demand", url="/data/input/demand/",
  report=freppledb.input.views.DemandList, index=100, model=Demand
  )
menu.addItem(
  "sales", "item", url="/data/input/item/",
  report=freppledb.input.views.ItemList, index=1100, model=Item
  )
menu.addItem(
  "sales", "customer", url="/data/input/customer/",
  report=freppledb.input.views.CustomerList, index=1200, model=Customer
  )
menu.addItem(
  "purchasing", "purchase orders", url="/data/input/purchaseorder/",
  report=freppledb.input.views.PurchaseOrderList, index=100, model=PurchaseOrder
  )
menu.addItem(
  "purchasing", "suppliers", url="/data/input/supplier/",
  report=freppledb.input.views.SupplierList, index=1100, model=Supplier
  )
menu.addItem(
  "purchasing", "item suppliers", url="/data/input/itemsupplier/",
  report=freppledb.input.views.ItemSupplierList, index=1200, model=ItemSupplier
  )
menu.addItem(
  "capacity", "resources", url="/data/input/resource/",
  report=freppledb.input.views.ResourceList, index=1100, model=Resource
  )
menu.addItem(
  "capacity", "skills", url="/data/input/skill/",
  report=freppledb.input.views.SkillList, index=1200, model=Skill
  )
menu.addItem(
  "capacity", "resource skills", url="/data/input/resourceskill/",
  report=freppledb.input.views.ResourceSkillList, index=1300, model=ResourceSkill
  )
menu.addItem(
  "capacity", "setup matrices", url="/data/input/setupmatrix/",
  report=freppledb.input.views.SetupMatrixList, index=1400, model=SetupMatrix
  )
menu.addItem(
  "distribution", "distribution orders", url="/data/input/distributionorder/",
  report=freppledb.input.views.DistributionOrderList, index=100, model=DistributionOrder
  )
menu.addItem(
  "distribution", "item distributions", url="/data/input/itemdistribution/",
  report=freppledb.input.views.ItemDistributionList, index=1100, model=ItemDistribution
  )
menu.addItem(
  "manufacturing", "manufacturing orders", url="/data/input/operationplan/",
  report=freppledb.input.views.OperationPlanList, index=100, model=OperationPlan
  )
menu.addItem(
  "manufacturing", "locations", url="/data/input/location/",
  report=freppledb.input.views.LocationList, index=1100, model=Location
  )
menu.addItem(
  "manufacturing", "calendars", url="/data/input/calendar/",
  report=freppledb.input.views.CalendarList, index=1200, model=Calendar
  )
menu.addItem(
  "manufacturing", "calendarbucket", url="/data/input/calendarbucket/",
  report=freppledb.input.views.CalendarBucketList, index=1300, model=CalendarBucket
  )
menu.addItem(
  "manufacturing", "operations", url="/data/input/operation/",
  report=freppledb.input.views.OperationList, index=1400, model=Operation
  )
menu.addItem(
  "manufacturing", "flows", url="/data/input/flow/",
  report=freppledb.input.views.FlowList, index=1500, model=Flow
  )
menu.addItem(
  "manufacturing", "loads", url="/data/input/load/",
  report=freppledb.input.views.LoadList, index=1600, model=Load
  )
menu.addItem(
  "manufacturing", "suboperations", url="/data/input/suboperation/",
  report=freppledb.input.views.SubOperationList, index=1700, model=SubOperation
  )
