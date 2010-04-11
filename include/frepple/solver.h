/***************************************************************************
  file : $URL$
  version : $LastChangedRevision$  $LastChangedBy$
  date : $LastChangedDate$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 * Copyright (C) 2007 by Johan De Taeye                                    *
 *                                                                         *
 * This library is free software; you can redistribute it and/or modify it *
 * under the terms of the GNU Lesser General Public License as published   *
 * by the Free Software Foundation; either version 2.1 of the License, or  *
 * (at your option) any later version.                                     *
 *                                                                         *
 * This library is distributed in the hope that it will be useful,         *
 * but WITHOUT ANY WARRANTY; without even the implied warranty of          *
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser *
 * General Public License for more details.                                *
 *                                                                         *
 * You should have received a copy of the GNU Lesser General Public        *
 * License along with this library; if not, write to the Free Software     *
 * Foundation Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 *
 * USA                                                                     *
 *                                                                         *
 ***************************************************************************/

#ifndef SOLVER_H
#define SOLVER_H

#include "frepple/model.h"
#ifndef DOXYGEN
#include <deque>
#include <cmath>
#endif

namespace frepple
{

/** @brief This solver implements a heuristic algorithm for planning demands.
  *
  * One by one the demands are processed. The demand will consume step by step
  * any upstream materials, respecting all constraints on its path.<br>
  * The solver supports all planning constraints as defined in Solver
  * class.<br>
  * See the documentation of the different solve methods to understand the
  * functionality in more detail.
  *
  * The logging levels have the following meaning:
  * - 0: Silent operation. Default logging level.
  * - 1: Show solver progress for each demand.
  * - 2: Show the complete ask&reply communication of the solver.
  * - 3: Trace the status of all entities.
  */
class SolverMRP : public Solver
{
  protected:
    /** This variable stores the constraint which the solver should respect.
      * By default no constraints are enabled. */
    short constrts;

    /** Behavior of this solver method is:
      *  - It will ask the consuming flows for the required quantity.
      *  - The quantity asked for takes into account the quantity_per of the
      *    producing flow.
      *  - The date asked for takes into account the post-operation time
      *    of the operation.
      */
    DECLARE_EXPORT void solve(const Operation*, void* = NULL);

    /** Behavior of this solver method is:
      *  - Asks each of the routing steps for the requested quantity, starting
      *    with the last routing step.<br>
      *    The time requested for the operation is based on the start date of
      *    the next routing step.
      */
    DECLARE_EXPORT void solve(const OperationRouting*, void* = NULL);

    /** Behavior of this solver method is:
      *  - The solver loops through each alternate operation in order of
      *    priority. On each alternate operation, the solver will try to plan
      *    the quantity that hasn't been planned on higher priority alternates.
      *  - As a special case, operations with zero priority are skipped in the
      *    loop. These operations are considered to be temporarily unavailable.
      *  - The requested operation can be planned over multiple alternates.
      *    We don't garantuee that a request is planned using a single alternate
      *    operation.
      *  - The solver properly considers the quantity_per of all flows producing
      *    into the requested buffer, if such a buffer is specified.
      */
    DECLARE_EXPORT void solve(const OperationAlternate*,void* = NULL);

    /** Behavior of this solver method:
      *  - No propagation to upstream buffers at all, even if a producing
      *    operation has been specified.
      *  - Always give an answer for the full quantity on the requested date.
      */
    DECLARE_EXPORT void solve(const BufferInfinite*,void* = NULL);

    /** Behavior of this solver method:
      *  - Consider 0 as the hard minimum limit. It is not possible
      *    to plan with a 'hard' safety stock reservation.
      *  - Minimum inventory is treated as a 'wish' inventory. When replenishing
      *    a buffer we try to satisfy the minimum target. If that turns out
      *    not to be possible we use whatever available supply for satisfying
      *    the demand first.
      *  - Planning for the minimum target is part of planning a demand. There
      *    is no planning run independent of demand to satisfy the minimum
      *    target.<br>
      *    E.g. If a buffer has no demand on it, the solver won't try to
      *    replenish to the minimum target.<br>
      *    E.g. If the minimum target increases after the latest date required
      *    for satisfying a certain demand that change will not be considered.
      *  - The solver completely ignores the maximum target.
      */
    DECLARE_EXPORT void solve(const Buffer*, void* = NULL);

    /** Behavior of this solver method:
      *  - When the inventory drops below the minimum inventory level, a new
      *    replenishment is triggered.
      *    The replenishment brings the inventory to the maximum level again.
      *  - The minimum and maximum inventory are soft-constraints. The actual
      *    inventory can go lower than the minimum or exceed the maximum.
      *  - The minimum, maximum and multiple size of the replenishment are
      *    hard constraints, and will always be respected.
      *  - A minimum and maximum interval between replenishment is also
      *    respected as a hard constraint.
      *  - No propagation to upstream buffers at all, even if a producing
      *    operation has been specified.
      *  - The minimum calendar isn't used by the solver.
      *
      * @todo Optimize the solver method as follows for the common case of infinite
      * buying capability (ie no max quantity + min time):
      *  - beyond lead time: always reply OK, without rearranging the operation plans
      *  - at the end of the solver loop, we revisit the procurement buffers to establish
      *    the final purchasing profile
      */
    DECLARE_EXPORT void solve(const BufferProcure*, void* = NULL);

    /** Behavior of this solver method:
      *  - This method simply passes on the request to the referenced buffer.
      *    It is called from a solve(Operation*) method and passes on the
      *    control to a solve(Buffer*) method.
      * @see checkOperationMaterial
      */
    DECLARE_EXPORT void solve(const Flow*, void* = NULL);

    /** Behavior of this solver method:
      *  - The operationplan is checked for a capacity overload. When detected
      *    it is moved to an earlier date.
      *  - This move can be repeated until no capacity is found till a suitable
      *    time slot is found. If the fence and/or leadtime constraints are
      *    enabled they can restrict the feasible moving time.<br>
      *    If a feasible timeslot is found, the method exits here.
      *  - If no suitable time slot can be found at all, the operation plan is
      *    put on its original date and we now try to move it to a feasible
      *    later date. Again, successive moves are possible till a suitable
      *    slot is found or till we reach the end of the horizon.
      *    The result of the search is returned as the answer-date to the
      *    solver.
      */
    DECLARE_EXPORT void solve(const Resource*, void* = NULL);

    /** Behavior of this solver method:
      *  - Always return OK.
      */
    DECLARE_EXPORT void solve(const ResourceInfinite*,void* = NULL);

    /** Behavior of this solver method:
      *  - This method simply passes on the request to the referenced resource.
      *    With the current model structure it could easily be avoided (and
      *    thus gain a bit in performance), but we wanted to include it anyway
      *    to make the solver as generic and future-proof as possible.
      * @see checkOperationCapacity
      */
    DECLARE_EXPORT void solve(const Load*, void* = NULL);

    /** Behavior of this solver method:
      *  - Respects the following demand planning policies:<br>
      *     1) Maximum allowed lateness
      *     2) Minimum shipment quantity
      * This method is normally called from within the main solve method, but
      * it can also be called independently to plan a certain demand.
      * @see solve
      */
    DECLARE_EXPORT void solve(const Demand*, void* = NULL);

  public:
    /** This is the main solver method that will appropriately call the other
      * solve methods.<br>
      * The demands in the model will all be sorted with the criteria defined in
      * the demand_comparison() method. For each of demand the solve(Demand*)
      * method is called to plan it.
      */
    DECLARE_EXPORT void solve(void *v = NULL);

    /** Constructor. */
    SolverMRP(const string& n) : Solver(n), constrts(15), maxparallel(0),
      plantype(1), lazydelay(86400L), autocommit(true)
      {initType(metadata);}

    /** Destructor. */
    virtual ~SolverMRP() {}

    DECLARE_EXPORT void writeElement(XMLOutput*, const Keyword&, mode=DEFAULT) const;
    DECLARE_EXPORT void endElement(XMLInput& pIn, const Attribute& pAttr, const DataElement& pElement);
    virtual DECLARE_EXPORT PyObject* getattro(const Attribute&);
    virtual DECLARE_EXPORT int setattro(const Attribute&, const PythonObject&);
    static int initialize();

    virtual const MetaClass& getType() const {return *metadata;}
    static DECLARE_EXPORT const MetaClass* metadata;
    virtual size_t getSize() const {return sizeof(SolverMRP);}

    /** Static constant for the LEADTIME constraint type.<br>
      * The numeric value is 1.
      * @see MATERIAL
      * @see CAPACITY
      * @see FENCE
      */
    static const short LEADTIME = 1;

    /** Static constant for the MATERIAL constraint type.<br>
      * The numeric value is 2.
      * @see LEADTIME
      * @see CAPACITY
      * @see FENCE
      */
    static const short MATERIAL = 2;

    /** Static constant for the CAPACITY constraint type.<br>
      * The numeric value is 4.
      * @see MATERIAL
      * @see LEADTIME
      * @see FENCE
      */
    static const short CAPACITY = 4;

    /** Static constant for the FENCE constraint type.<br>
      * The numeric value is 8.
      * @see MATERIAL
      * @see CAPACITY
      * @see LEADTIME
      */
    static const short FENCE = 8;

    /** Update the constraints to be considered by this solver. This field may
      * not be applicable for all solvers. */
    void setConstraints(short i) {constrts = i;}

    /** Returns the constraints considered by the solve. */
    short getConstraints() const {return constrts;}

    /** Returns true if this solver respects the operation release fences.
      * The solver isn't allowed to create any operation plans within the
      * release fence.
      */
    bool isFenceConstrained() const {return (constrts & FENCE)>0;}

    /** Returns true if the solver respects the current time of the plan.
      * The solver isn't allowed to create any operation plans in the past.
      */
    bool isLeadtimeConstrained() const {return (constrts & LEADTIME)>0;}

    /** Returns true if the solver respects the material procurement 
      * constraints on procurement buffers.
      */
    bool isMaterialConstrained() const {return (constrts & MATERIAL)>0;}

    /** Returns true if the solver respects capacity constraints. */
    bool isCapacityConstrained() const {return (constrts & CAPACITY)>0;}

    /** Returns true if any constraint is relevant for the solver. */
    bool isConstrained() const {return constrts>0;}

    /** Returns the plan type:
      *  - 1: Constrained plan.<br>
      *       This plan doesn't not violate any constraints.<br>
      *       In case of material or capacity shortages the demand is delayed
      *       or planned short.
      *  - 2: Unconstrained plan with alternate search.<br>
      *       This unconstrained plan leaves material, capacity and operation
      *       problems when shortages are found. Availability is searched across
      *       alternates and the remaining shortage is shown on the primary 
      *       alternate.<br>
      *       The demand is always fully met on time.
      *  - 3: Unconstrained plan without alternate search.<br>
      *       This unconstrained plan leaves material, capacity and operation
      *       problems when shortages are found. It doesn't evaluate availability
      *       on alternates.<br>
      *       The demand is always fully met on time.
      */
    short getPlanType() const {return plantype;}

    void setPlanType(short b) {plantype = b;}

    /** This function defines the order in which the demands are being
      * planned.<br>
      * The following sorting criteria are appplied in order:
      *  - demand priority: smaller priorities first
      *  - demand due date: earlier due dates first
      *  - demand quantity: smaller quantities first
      */
    static DECLARE_EXPORT bool demand_comparison(const Demand*, const Demand*);

    /** Update the number of parallel solver threads.<br>
      * The default value depends on whether the solver is run in verbose mode
      * or not:
      *  - In normal mode the solver uses as many threads as specified by
      *    the environment variable NUMBER_OF_PROCESSORS.
      *  - In verbose mode the solver runs in a single thread to avoid
      *    mangling the debugging output of different threads.
      */
    void setMaxParallel(int i)
    {
      if (i >= 1) maxparallel = i;
      else throw DataException("Invalid number of parallel solver threads");
    }

    /** Return the number of threads used for planning. */
    int getMaxParallel() const
    {
      // Or: Explicitly specified number of threads
      if (maxparallel) return maxparallel;
      // Or: Default number of threads
      else return getLogLevel()>0 ? 1 : Environment::getProcessors();
    }

    /** Return the time increment between requests when the answered reply
      * date isn't usable. */
    TimePeriod getLazyDelay() const {return lazydelay;}

    /** Update the time increment between requests when the answered reply
      * date isn't usable. */
    void setLazyDelay(TimePeriod l)
    {
      if (l > 0L) lazydelay = l;
      else throw DataException("Invalid lazy delay");
    }

    /** Return whether or not we automatically commit the changes after
      * planning a demand. */
    bool getAutocommit() const {return autocommit;}

    /** Update whether or not we automatically commit the changes after
      * planning a demand. */
    void setAutocommit(const bool b) {autocommit = b;}

    /** Specify a Python function that is called before solving a flow. */
    DECLARE_EXPORT void setUserExitFlow(const string& n) {userexit_flow = n;}

    /** Specify a Python function that is called before solving a flow. */
    DECLARE_EXPORT void setUserExitFlow(PyObject* p) {userexit_flow = p;}

    /** Return the Python function that is called before solving a flow. */
    PythonFunction getUserExitFlow() const {return userexit_flow;}

    /** Specify a Python function that is called before solving a demand. */
    DECLARE_EXPORT void setUserExitDemand(const string& n) {userexit_demand = n;}

    /** Specify a Python function that is called before solving a demand. */
    DECLARE_EXPORT void setUserExitDemand(PyObject* p) {userexit_demand = p;}

    /** Return the Python function that is called before solving a demand. */
    PythonFunction getUserExitDemand() const {return userexit_demand;}

    /** Specify a Python function that is called before solving a buffer. */
    DECLARE_EXPORT void setUserExitBuffer(const string& n) {userexit_buffer = n;}

    /** Specify a Python function that is called before solving a buffer. */
    DECLARE_EXPORT void setUserExitBuffer(PyObject* p) {userexit_buffer = p;}

    /** Return the Python function that is called before solving a buffer. */
    PythonFunction getUserExitBuffer() const {return userexit_buffer;}

    /** Specify a Python function that is called before solving a resource. */
    DECLARE_EXPORT void setUserExitResource(const string& n) {userexit_resource = n;}

    /** Specify a Python function that is called before solving a resource. */
    DECLARE_EXPORT void setUserExitResource(PyObject* p) {userexit_resource = p;}

    /** Return the Python function that is called before solving a resource. */
    PythonFunction getUserExitResource() const {return userexit_resource;}

    /** Specify a Python function that is called before solving a operation. */
    DECLARE_EXPORT void setUserExitOperation(const string& n) {userexit_operation = n;}

    /** Specify a Python function that is called before solving a operation. */
    DECLARE_EXPORT void setUserExitOperation(PyObject* p) {userexit_operation = p;}

    /** Return the Python function that is called before solving a operation. */
    PythonFunction getUserExitOperation() const {return userexit_operation;}

    /** Python method for running the solver. */
    static DECLARE_EXPORT PyObject* solve(PyObject*, PyObject*);

    /** Python method for commiting the plan changes. */
    static DECLARE_EXPORT PyObject* commit(PyObject*, PyObject*);

    /** Python method for undoing the plan changes. */
    static DECLARE_EXPORT PyObject* undo(PyObject*, PyObject*);

  private:
    typedef map < int, deque<Demand*>, less<int> > classified_demand;
    typedef classified_demand::iterator cluster_iterator;
    classified_demand demands_per_cluster;

    /** Number of parallel solver threads.<br>
      * The default value depends on whether the solver is run in verbose mode
      * or not:
      *  - In normal mode the solver uses NUMBER_OF_PROCESSORS threads.
      *  - In verbose mode the solver runs in a single thread to avoid
      *    mangling the debugging output of different threads.
      */
    int maxparallel;

    /** Type of plan to be created. */
    short plantype;

    /** Time increments for a lazy replan.<br>
      * The solver is expected to return always a next-feasible date when the
      * request can't be met. The solver can then retry the request with an
      * updated request date. In some corner cases and in case of a bug it is
      * possible that no valid date is returned. The solver will then try the
      * request with a request date incremented by this value.<br>
      * The default value is 1 day.
      */
    TimePeriod lazydelay;

    /** Enable or disable automatically committing the changes in the plan
      * after planning each demand.<br>
      * The flag is only respected when planning incremental changes, and
      * is ignored when doing a complete replan.
      */
    bool autocommit;

    /** A Python callback function that is called for each alternate
      * flow. If the callback function returns false, that alternate
      * flow is an invalid choice.
      */
    PythonFunction userexit_flow;

    /** A Python callback function that is called for each demand. The return
      * value is not used.
      */
    PythonFunction userexit_demand;

    /** A Python callback function that is called for each buffer. The return
      * value is not used.
      */
    PythonFunction userexit_buffer;

    /** A Python callback function that is called for each resource. The return
      * value is not used.
      */
    PythonFunction userexit_resource;

    /** A Python callback function that is called for each operation. The return
      * value is not used.
      */
    PythonFunction userexit_operation;

  protected:
    /** @brief This class is used to store the solver status during the
      * ask-reply calls of the solver.
      */
    struct State
    {
      /** Points to the demand being planned.<br>
        * This field is only non-null when planning the delivery operation. 
        */
      Demand* curDemand;

      /** Points to the current owner operationplan. This is used when
        * operations are nested. */
      OperationPlan* curOwnerOpplan;

      /** Points to the current buffer. */
      Buffer* curBuffer;

      /** A flag to force the resource solver to move the operationplan to
        * a later date where it is feasible.<br>
        * Admittedly this is an ugly hack...
        */
      bool forceLate;

      /** This is the quantity we are asking for. */
      double q_qty;

      /** This is the date we are asking for. */
      Date q_date;

      /** This is the maximum date we are asking for.<br>
        * In case of a post-operation time there is a difference between
        * q_date and q_date_max.
        */
      Date q_date_max;

      /** This is the quantity we can get by the requested Date. */
      double a_qty;

      /** This is the Date when we can get extra availability. */
      Date a_date;

      /** This is a pointer to a LoadPlan. It is used for communication
        * between the Operation-Solver and the Resource-Solver. */
      LoadPlan* q_loadplan;

      /** This is a pointer to a FlowPlan. It is used for communication
        * between the Operation-Solver and the Buffer-Solver. */
      FlowPlan* q_flowplan;

      /** A pointer to an operationplan currently being solved. */
      OperationPlan* q_operationplan;

      /** Cost of the reply.<br>
        * Only the direct cost should be returned in this field.
        */
      double a_cost;

      /** Penalty associated with the reply.<br>
        * This field contains indirect costs and other penalties that are
        * not strictly related to the request. Examples are setup costs,
        * inventory carrying costs, ...
        */
      double a_penalty;
    };

    /** @brief This class is a helper class of the SolverMRP class.
      *
      * It stores the solver state maintained by each solver thread.
      * @see SolverMRP
      */
    class SolverMRPdata : public CommandList
    {
        friend class SolverMRP;
      public:
        /** Return the solver. */
        SolverMRP* getSolver() const {return sol;}

        /** Constructor. */
        SolverMRPdata(SolverMRP* s = NULL, int c = 0, deque<Demand*>* d = NULL)
          : sol(s), cluster(c), demands(d), constrainedPlanning(true), 
          state(statestack), prevstate(statestack-1) {}

        /** Verbose mode is inherited from the solver. */
        unsigned short getLogLevel() const {return sol ? sol->getLogLevel() : 0;}

        /** This function runs a single planning thread. Such a thread will loop
          * through the following steps:
          *    - Use the method next_cluster() to find another unplanned cluster.
          *    - Exit the thread if no more cluster is found.
          *    - Sort all demands in the cluster, using the demand_comparison()
          *      method.
          *    - Loop through the sorted list of demands and plan each of them.
          *      During planning the demands exceptions are caught, and the
          *      planning loop will simply move on to the next demand.
          *      In this way, an error in a part of the model doesn't ruin the
          *      complete plan.
          * @see demand_comparison
          * @see next_cluster
          */
        virtual DECLARE_EXPORT void execute();

        virtual const MetaClass& getType() const {return *SolverMRP::metadata;}
        virtual size_t getSize() const {return sizeof(SolverMRPdata);}

        bool getVerbose() const
        {
          throw LogicException("Use the method SolverMRPdata::getLogLevel() instead of SolverMRPdata::getVerbose()");
        }

        /** Add a new state to the status stack. */
        inline void push(double q = 0.0, Date d = Date::infiniteFuture)
        {
          if (state >= statestack + MAXSTATES)
            throw RuntimeException("Maximum recursion depth exceeded");
          ++state;
          ++prevstate;
          state->q_qty = q;
          state->q_date = d;
          state->curOwnerOpplan = NULL;
          state->q_loadplan = NULL;
          state->q_flowplan = NULL;
          state->q_operationplan = NULL;
          state->curDemand = NULL;
          state->a_cost = 0.0;
          state->a_penalty = 0.0;
        }

        /** Removes a state from the status stack. */
        inline void pop()
        {
          if (--state < statestack)
            throw LogicException("State stack empty");
          --prevstate;
        }

      private:
        static const int MAXSTATES = 256;

        /** Points to the solver. */
        SolverMRP* sol;

        /** An identifier of the cluster being replanned. Note that it isn't
          * always the complete cluster that is being planned.
          */
        int cluster;

        /** A deque containing all demands to be (re-)planned. */
        deque<Demand*>* demands;

        /** Stack of solver status information. */
        State statestack[MAXSTATES];
        
        /** True when planning in constrained mode. */
        bool constrainedPlanning;

        /** Flags whether or not constraints are being tracked. */
        bool logConstraints;

        /** Points to the demand being planned. */
        Demand* planningDemand;

      public:
        /** Pointer to the current solver status. */
        State* state;

        /** Pointer to the solver status one level higher on the stack. */
        State* prevstate;
    };

    /** When autocommit is switched off, this command structure will contain
      * all plan changes.
      */
    SolverMRPdata commands;

    /** This function will check all constraints for an operationplan
      * and propagate it upstream. The check does NOT check eventual
      * sub operationplans.<br>
      * The return value is a flag whether the operationplan is
      * acceptable (sometimes in reduced quantity) or not.
      */
    DECLARE_EXPORT bool checkOperation(OperationPlan*, SolverMRPdata& data);

    /** Verifies whether this operationplan violates the leadtime
      * constraints. */
    DECLARE_EXPORT bool checkOperationLeadtime(OperationPlan*, SolverMRPdata&, bool);

    /** Verifies whether this operationplan violates the capacity constraint.<br>
      * In case it does the operationplan is moved to an earlier or later
      * feasible date.
      */
    DECLARE_EXPORT void checkOperationCapacity(OperationPlan*, SolverMRPdata&);
};


/** @brief This class holds functions that used for maintenance of the solver
  * code.
  */
class LibrarySolver
{
  public:
    static void initialize();
};


} // end namespace


#endif