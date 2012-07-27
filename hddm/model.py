"""
.. module:: HDDM
   :platform: Agnostic
   :synopsis: Defvalueion of HDDM models.

.. moduleauthor:: Thomas Wiecki <thomas.wiecki@gmail.com>
                  Imri Sofer <imrisofer@gmail.com>


"""

from __future__ import division
from collections import OrderedDict

import numpy as np
import pymc as pm
import matplotlib.pyplot as plt

import hddm
import kabuki
import kabuki.step_methods as steps
from kabuki.hierarchical import Knode
from copy import deepcopy
import scipy as sp
from scipy import stats


class AccumulatorModel(kabuki.Hierarchical):
    def create_family_normal(self, name, value=0):
        knodes = OrderedDict()

        if self.is_group_model and name not in self.group_only_nodes:
            g = Knode(pm.Normal, '%s' % name, mu=0, tau=15**-2, value=value, depends=self.depends[name])
            var = Knode(pm.Uniform, '%s_var' % name, lower=1e-10, upper=100, value=.1)
            tau = Knode(pm.Deterministic, '%s_tau' % name, doc='%s_tau' % name, eval=lambda x: x**-2, x=var, plot=False, trace=False)
            subj = Knode(pm.Normal, '%s_subj' % name, mu=g, tau=tau, value=value, depends=('subj_idx',), subj=True)
            knodes['%s'%name] = g
            knodes['%s_var'%name] = var
            knodes['%s_tau'%name] = tau
            knodes['%s_subj'%name] = subj

        else:
            knodes[name] = Knode(pm.Normal, name, mu=0, tau=15**-2, value=value, depends=self.depends[name])

        return knodes


    def create_family_trunc_normal(self, name, value=0, lower=None,
                                   upper=None, var_lower=1e-10, var_upper=100, var_value=.1):
        knodes = OrderedDict()

        if self.is_group_model and name not in self.group_only_nodes:
            g = Knode(pm.Uniform, '%s' % name, lower=lower,
                      upper=upper, value=value, depends=self.depends[name])
            var = Knode(pm.Uniform, '%s_var' % name, lower=var_lower,
                        upper=var_upper, value=var_value)
            tau = Knode(pm.Deterministic, '%s_tau' % name,
                        doc='%s_tau' % name, eval=lambda x: x**-2, x=var,
                        plot=False, trace=False)
            subj = Knode(pm.TruncatedNormal, '%s_subj' % name, mu=g,
                         tau=tau, a=lower, b=upper, value=value,
                         depends=('subj_idx',), subj=True)

            knodes['%s'%name] = g
            knodes['%s_var'%name] = var
            knodes['%s_tau'%name] = tau
            knodes['%s_subj'%name] = subj

        else:
            knodes[name] = Knode(pm.Uniform, name, lower=lower,
                                 upper=upper, value=value, depends=self.depends[name])

        return knodes


    def create_family_invlogit(self, name, value, g_mu=0, g_tau=15**-2,
                               var_lower=1e-10, var_upper=100, var_value=.1):
        knodes = OrderedDict()

        if self.is_group_model and name not in self.group_only_nodes:
            g_trans = Knode(pm.Normal,
                      '%s_trans'%name,
                      mu=g_mu,
                      tau=g_tau,
                      #logit transformed value
                      value=np.log(value) - np.log(1-value),
                      depends=self.depends[name],
                      plot=False
            )

            g = Knode(pm.InvLogit, name, ltheta=g_trans, plot=True, trace=True)

            var = Knode(pm.Uniform, '%s_var'%name, lower=var_lower, upper=var_upper, value=var_value)

            tau = Knode(pm.Deterministic, '%s_tau'%name,
                        doc='%s_tau' % name, eval=lambda x: x**-2, x=var,
                        plot=False, trace=False)

            subj_trans = Knode(pm.Normal, '%s_subj_trans'%name, mu=g_trans,
                               tau=tau, value=np.log(value)-np.log(1-value), depends=('subj_idx',),
                               subj=True, plot=False)

            subj = Knode(pm.InvLogit, '%s_subj'%name, ltheta=subj_trans, depends=('subj_idx',),
                         plot=True, trace=True, subj=True)

            knodes['%s_trans'%name]      = g_trans
            knodes['%s'%name]            = g
            knodes['%s_var'%name]        = var
            knodes['%s_tau'%name]        = tau

            knodes['%s_subj_trans'%name] = subj_trans
            knodes['%s_subj'%name]       = subj

        else:
            g_trans = Knode(pm.Normal, '%s_trans'%name, mu=g_mu, tau=g_tau,
                            value=np.log(value), depends=self.depends[name],
                            plot=False)

            g = Knode(pm.InvLogit, '%s'%name, ltheta=g_trans, plot=True,
                      trace=True )

            knodes['%s_trans'%name] = g_trans
            knodes['%s'%name] = g

        return knodes

    def create_family_exp(self, name, value=0, g_mu=0, g_tau=15**-2, var_lower=1e-10, var_upper=100, var_value=.1):
        knodes = OrderedDict()
        if self.is_group_model and name not in self.group_only_nodes:
            g_trans = Knode(pm.Normal, '%s_trans' % name, mu=g_mu,
                            tau=g_tau, value=np.log(value),
                            depends=self.depends[name], plot=False)

            g = Knode(pm.Deterministic, '%s'%name, doc='%s'%name, eval=lambda x: np.exp(x), x=g_trans, plot=True)

            var = Knode(pm.Uniform, '%s_var' % name,
                        lower=var_lower, upper=var_upper, value=var_value)

            tau = Knode(pm.Deterministic, '%s_tau' % name,
                        doc='%s_tau' % name, eval=lambda x: x**-2, x=var,
                        plot=False, trace=False)

            subj_trans = Knode(pm.Normal, '%s_subj_trans'%name, mu=g_trans,
                         tau=tau, value=np.log(value), depends=('subj_idx',),
                         subj=True)

            subj = Knode(pm.Deterministic, '%s_subj'%name, doc='%s'%name, eval=lambda x: np.exp(x), x=subj_trans, depends=('subj_idx',), plot=True, trace=True, subj=True)

            knodes['%s_trans'%name] = g_trans
            knodes['%s'%name] = g
            knodes['%s_var'%name] = var
            knodes['%s_tau'%name] = tau
            knodes['%s_subj_trans'%name] = subj_trans
            knodes['%s_subj'%name]       = subj

        else:
            g_trans = Knode(pm.Normal, '%s_trans' % name, mu=g_mu,
                            tau=g_tau, value=np.log(value),
                            depends=self.depends[name], plot=False)

            g = Knode(pm.Deterministic, '%s'%name, doc='%s'%name, eval=lambda x: np.exp(x), x=g_trans, plot=True)
            knodes['%s_trans'%name] = g_trans
            knodes['%s'%name] = g

        return knodes


class HDDMBase(AccumulatorModel):
    """Implements the hierarchical Ratcliff drift-diffusion model
    using the Navarro & Fuss likelihood and numerical integration over
    the variability parameters.

    :Arguments:
        data : numpy.recarray
            Input data with a row for each trial.
             Must contain the following columns:
              * 'rt': Reaction time of trial in seconds.
              * 'response': Binary response (e.g. 0->error, 1->correct)
             May contain:
              * 'subj_idx': A unique ID (int) of the subject.
              * Other user-defined columns that can be used in depends on keyword.
    :Example:
        >>> data, params = hddm.generate.gen_rand_data() # gen data
        >>> model = hddm.HDDM(data) # create object
        >>> mcmc = model.mcmc() # Create pymc.MCMC object
        >>> mcmc.sample() # Sample from posterior
    :Optional:
        include : iterable
            Optional inter-trial variability parameters to include.
             Can be any combination of 'sv', 'sz' and 'st'. Passing the string
            'all' will include all three.

            Note: Including 'sz' and/or 'st' will increase run time significantly!

            is_group_model : bool
                If True, this results in a hierarchical
                model with separate parameter distributions for each
                subject. The subject parameter distributions are
                themselves distributed according to a group parameter
                distribution.

                If not provided, this parameter is set to True if data
                provides a column 'subj_idx' and False otherwise.

            depends_on : dict
                Specifies which parameter depends on data
                of a column in data. For each unique element in that
                column, a separate set of parameter distributions will be
                created and applied. Multiple columns can be specified in
                a sequential container (e.g. list)

                :Example:

                    >>> hddm.HDDM(data, depends_on={'v':'difficulty'})

                    Separate drift-rate parameters will be estimated
                    for each difficulty. Requires 'data' to have a
                    column difficulty.


            bias : bool
                Whether to allow a bias to be estimated. This
                is normally used when the responses represent
                left/right and subjects could develop a bias towards
                responding right. This is normally never done,
                however, when the 'response' column codes
                correct/error.

            plot_var : bool
                 Plot group variability parameters when calling pymc.Matplot.plot()
                 (i.e. variance of Normal distribution.)

            wiener_params : dict
                 Parameters for wfpt evaluation and
                 numerical integration.

                 :Parameters:
                     * err: Error bound for wfpt (default 1e-4)
                     * n_st: Maximum depth for numerical integration for st (default 2)
                     * n_sz: Maximum depth for numerical integration for Z (default 2)
                     * use_adaptive: Whether to use adaptive numerical integration (default True)
                     * simps_err: Error bound for Simpson integration (default 1e-3)

    """

    def __init__(self, data, bias=False,
                 include=(), wiener_params=None, group_only_nodes=(), **kwargs):

        # Flip sign for lower boundary RTs
        data = hddm.utils.flip_errors(data)

        self.all_param_names = ('v', 'sv', 'a', 'z', 'sz', 't', 'st')

        include_params = set()

        if include is not None:
            if include == 'all':
                [include_params.add(param) for param in ('st','sv','sz')]
            else:
                [include_params.add(param) for param in include]

        if bias:
            include_params.add('z')

        if wiener_params is None:
            self.wiener_params = {'err': 1e-4, 'n_st':2, 'n_sz':2,
                                  'use_adaptive':1,
                                  'simps_err':1e-3}
        else:
            self.wiener_params = wiener_params
        wp = self.wiener_params

        #set wfpt
        self.wfpt = deepcopy(hddm.likelihoods.wfpt_like)
        self.wfpt.rv.wiener_params = wp
        cdf_bound = max(np.abs(data['rt'])) + 1;
        self.wfpt.cdf_range = (-cdf_bound, cdf_bound)

        self.group_only_nodes = group_only_nodes

        super(HDDMBase, self).__init__(data, include=include_params, **kwargs)

    def create_wfpt_knode(self, knodes):
        knode_name = {}
        for param_name in self.all_param_names:
            if self.is_group_model and param_name not in self.group_only_nodes:
                knode_name[param_name] = '{name}_subj'.format(name=param_name)
            else:
                knode_name[param_name] = param_name

        wfpt_parents = OrderedDict()
        wfpt_parents['a'] = knodes[knode_name['a']]
        wfpt_parents['v'] = knodes[knode_name['v']]
        wfpt_parents['t'] = knodes[knode_name['t']]

        wfpt_parents['sv'] = knodes[knode_name['sv']] if 'sv' in self.include else 0
        wfpt_parents['sz'] = knodes[knode_name['sz']] if 'sz' in self.include else 0
        wfpt_parents['st'] = knodes[knode_name['st']] if 'st' in self.include else 0
        wfpt_parents['z'] = knodes[knode_name['z']] if 'z' in self.include else 0.5

        return Knode(self.wfpt, 'wfpt', observed=True, col_name='rt', **wfpt_parents)

    def plot_posterior_predictive(self, *args, **kwargs):
        if 'value_range' not in kwargs:
            kwargs['value_range'] = np.linspace(-5, 5, 100)
        kabuki.analyze.plot_posterior_predictive(self, *args, **kwargs)

class HDDMTruncated(HDDMBase):
   def create_knodes(self):
        """Returns list of model parameters.
        """

        knodes = OrderedDict()
        knodes.update(self.create_family_trunc_normal('a', lower=1e-3, upper=1e3, value=1))
        knodes.update(self.create_family_normal('v', value=0))
        knodes.update(self.create_family_trunc_normal('t', lower=1e-3, upper=1e3, value=.01))
        if 'sv' in self.include:
            knodes.update(self.create_family_trunc_normal('sv', lower=0, upper=1e3, value=1))
        if 'sz' in self.include:
            knodes.update(self.create_family_trunc_normal('sz', lower=0, upper=1, value=.1))
        if 'st' in self.include:
            knodes.update(self.create_family_trunc_normal('st', lower=0, upper=1e3, value=.01))
        if 'z' in self.include:
            knodes.update(self.create_family_trunc_normal('z', lower=0, upper=1, value=.5))

        knodes['wfpt'] = self.create_wfpt_knode(knodes)

        return knodes.values()


class HDDM(HDDMBase):
    trans_nodes = ('a', 't', 'z', 'sz', 'sv', 'st')
    def pre_sample(self):
        if not self.is_group_model:
            return

        params = []
        for name in self.all_param_names:
            if name in self.include and name not in self.group_only_nodes:
                if name in self.trans_nodes:
                    params.append(name + '_trans')
                else:
                    params.append(name)

        nodes = self.nodes_db['node'][self.nodes_db['knode_name'].isin(params)]
        for node in nodes:
            self.mc.use_step_method(steps.kNormalNormal, node)

    def create_knodes(self):
        knodes = OrderedDict()
        knodes.update(self.create_family_exp('a', value=1))
        knodes.update(self.create_family_normal('v', value=0))
        knodes.update(self.create_family_exp('t', value=.01))
        if 'sv' in self.include:
            knodes.update(self.create_family_exp('sv', value=1))
        if 'sz' in self.include:
            knodes.update(self.create_family_exp('sz', value=.1))
        if 'st' in self.include:
            knodes.update(self.create_family_exp('st', value=.01))
        if 'z' in self.include:
            knodes.update(self.create_family_invlogit('z', value=.5))

        knodes['wfpt'] = self.create_wfpt_knode(knodes)

        return knodes.values()

if __name__ == "__main__":
    import doctest
    doctest.testmod()
