#!/usr/bin/env python
# -*- coding: utf-8 -*-

import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
from nipype.interfaces.base import BaseInterface, \
    BaseInterfaceInputSpec, traits, File, TraitedSpec

import os
import numpy as np
import nibabel as nb
from nilearn.connectome import ConnectivityMeasure


class FunctionalConnectivityInputSpec(BaseInterfaceInputSpec):
    functional = traits.File(exists=True, desc='Functional file. It can be 2-D or a 4-D.',
                             mandatory=True)
    metric = traits.Enum('correlation', 'partial correlation', 'partial', 'tangent',
                         desc='The measure to be used to compute the connectivity matrix',
                         mandatory=True)
    vectorize = traits.Bool(desc='If True, connectivity matrices are reshaped into 1D '
                                 'arrays and only their flattened lower triangular '
                                 'parts are returned.', usedefault=True)


class FunctionalConnectivityOutputSpec(TraitedSpec):
    connectivity = File(exists=True, desc="The connectivity matrix or vector")


class FunctionalConnectivity(BaseInterface):
    input_spec = FunctionalConnectivityInputSpec
    output_spec = FunctionalConnectivityOutputSpec

    def _run_interface(self, runtime):
        img = nb.load(self.inputs.functional)
        data = np.array(img.get_data())
        data = data.reshape((np.prod(data.shape[0:-1]), -1)).T

        # Normalize input for nilearn component
        metric = self.inputs.metric
        if metric == 'partial':
            metric = 'partial correlation'

        # Normalize input for file name
        metric_name = self.inputs.metric
        if metric_name == 'partial correlation':
            metric_name = 'partial'

        correlation_measure = ConnectivityMeasure(kind=metric,
                                                  vectorize=self.inputs.vectorize,
                                                  discard_diagonal=True)
        correlation_matrix = correlation_measure.fit_transform([data])[0]

        correlation_file = os.path.join(
            os.getcwd(), 'correlation_%s.npy' % metric_name)
        np.save(correlation_file, correlation_matrix)

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()

        # Normalize input for file name
        metric_name = self.inputs.metric
        if metric_name == 'partial correlation':
            metric_name = 'partial'

        correlation_file = os.path.join(
            os.getcwd(), 'correlation_%s.npy' % metric_name)
        outputs['connectivity'] = correlation_file
        return outputs


def create_connectome_study(configuration, name='connectivity'):
    """
    Functional Connectivity
    
    This workflow computes different kinds of functional connectivity matrices.
    
    Parameters
    ----------
    name : string, optional
        Name of the workflow.
        
    Returns
    -------
    workflow : nipype.pipeline.engine.Workflow
        Connectivity workflow.
        
    Notes
    -----
    
    Workflow Inputs::
    
        inputspec.functional : string
            Path of the subject's functional nifti file.
        inputspec.metric : string
            Metric to compute connectivity: correlation,
                                            partial correlation (or partial),
                                            tangent
        
    Workflow Outputs::

        outputspec.connectivity : string
           Path to numpy file with correlation matrix
    
    References
    ----------
    .. [1] G. Varoquaux et al. “Detection of brain functional-connectivity difference in post-stroke patients using group-level covariance modeling, MICCAI 2010.
    
    """

    inputspec = pe.Node(util.IdentityInterface(fields=[]),
                        name='inputspec')

    outputspec = pe.Node(util.IdentityInterface(fields=[]),
                         name='outputspec')

    wf = pe.Workflow(name=name)

    {
    'classifier': [{'parameters': None, 'type': 'knn'},
                    {'parameters': None, 'type': 'random_forest'},
                    {'parameters': None, 'type': 'naive_bayes'},
                    {'parameters': None, 'type': 'ridge'},
                    {'feature_extraction': [{'parameters': {'percentile': 10},
                                             'type': 'anova'}],
                     'parameters': {'penalty': 'l1'},
                     'type': 'svc'},
                    {'feature_extraction': [{'parameters': {'percentile': 10},
                                             'type': 'anova'}],
                     'parameters': {'penalty': 'l2'},
                     'type': 'svc'},
                    {'parameters': {'penalty': 'l1'}, 'type': 'svc'},
                    {'parameters': {'penalty': 'l2'}, 'type': 'svc'},
                    {'parameters': {'penalty': 'l1'},
                     'type': 'logistic'},
                    {'parameters': {'penalty': 'l2'}, 'type': 'logistic'}],

    'connectivity': ['partial', 'tangent', 'correlation'],

    'roi': ['aal', 'harvard_oxford', 'power', 'basc', 'ward', 'k_means', 'group_ica', 'dict_learning']}


    conn = pe.Node(FunctionalConnectivity(),
                   name='connectivity')
    
    conn.inputs.vectorize = True
    conn.iterables = ('metric', [
        'correlation',
        'partial',
        'tangent',
    ])

    wf.connect(inputspec, 'functional',
               conn, 'functional')

    wf.connect(conn, 'connectivity',
               outputspec, 'connectivity')

    return wf