"""
Functions for interacting with the BEAST model
"""

# system imports
from __future__ import (absolute_import, division, print_function)

# other package imports
import numpy as np
import h5py
from tqdm import tqdm


def read_lnp_data(filename, nstars):
    """
    Read in the sparse lnp for all the stars in the hdf5 file

    Parameters
    ----------
    filename: string
       name of the file with the sparse lnp values

    nstars: int
       number of stars expected in the file

    Returns
    -------
    lnp_data: dictonary
       contains arrays of the lnp values and indexs to the BEAST model grid
    """
    lnp_hdf = h5py.File(filename, 'r')

    if len(lnp_hdf.keys()) != nstars:
        print('Error: number of stars not equal between nstars image and ' +
              'lnp file')
        lnp_hdf.close()
        exit()
    else:
        # loop over all the stars (groups)
        lnp_init = False
        for k, sname in enumerate(lnp_hdf.keys()):
            if not lnp_init:
                istar_lnp = lnp_hdf[sname]['lnp'].value
                n_ivals, = istar_lnp.shape
                lnp_vals = np.zeros((n_ivals, nstars), dtype=float)
                lnp_indxs = np.zeros((n_ivals, nstars), dtype=int)
                lnp_init = True

            lnp_vals[:, k] = lnp_hdf[sname]['lnp'].value
            lnp_indxs[:, k] = np.int64(np.array(lnp_hdf[sname]['idx'].value))
        lnp_hdf.close()

        # shift the log(likelihood) values to have a max of 0.0
        #  ok if the same shift is applied to all stars in a pixel
        #  avoids numerical issues later when we go to intergrate probs
        lnp_vals -= np.max(lnp_vals)

        return {'vals': lnp_vals, 'indxs': lnp_indxs}


def read_beast_data(filename,
                    noise_filename,
                    beast_params=['Av', 'Rv', 'f_A',
                                  'M_ini', 'logA', 'Z',
                                  'completeness'],
                    verbose=True):
    """
    Read in the beast data needed by all the pixels

    Parameters
    ----------
    filename: string
       name of the file with the BEAST physicsmodel grid

    noise_filename: string
       name of the file with the BEAST observationmodel grid

    beast_params: strings
       contains the set of BEAST parameters to extract
       default = [completeness, Av, Rv, f_A, M_ini, logA, Z]

    Returns
    -------
    beast_data: dictonary
       contains arrays of the beast parameters, priors, and completeness
    """
    beast_data = {}

    # open the full BEAST observationmodel file for reading
    beast_noise_hdf = h5py.File(noise_filename, 'r')

    # open the full BEAST physicsmodel file for reading
    beast_seds_hdf = h5py.File(filename, 'r')

    # get beast physicsmodel params
    for cparam in tqdm(beast_params, desc='reading beast data'):
        if cparam == 'completeness':
            beast_data[cparam] = np.max(beast_noise_hdf[cparam], axis=1)
        else:
            beast_data[cparam] = beast_seds_hdf['grid'][cparam]

    beast_noise_hdf.close()
    beast_seds_hdf.close()

    return beast_data


def extract_beast_data(beast_data, lnp_data):
    """
    Read in the beast data for the locations where the lnp values
    were saved

    Parameters
    ----------
    beast_data: dictonary
       contains arrays of the beast parameters and priors

    lnp_data: dictonary
       contains arrays of the lnp values and indexs to the BEAST model grid

    Returns
    -------
    beast_on_lnp: dictonary
       contains arrays of the beast parameters and priors for the sparse
       lnp saved model grid points
    """
    # get the keys in beast_data
    beast_params = beast_data.keys()

    # setup the output
    beast_on_lnp = {}
    n_lnps, n_stars = lnp_data['indxs'].shape
    for cparam in beast_params:
        beast_on_lnp[cparam] = np.empty((n_lnps, n_stars), dtype=float)

    # loop over the stars and extract the requested BEAST data
    # for k in tqdm(range(n_stars), desc='extracting beast data'):
    for k in range(n_stars):
        for cparam in beast_params:
            beast_on_lnp[cparam][:, k] = \
                            beast_data[cparam][lnp_data['indxs'][:, k]]

    return beast_on_lnp
