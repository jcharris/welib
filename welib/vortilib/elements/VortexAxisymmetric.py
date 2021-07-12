"""
Axisymmetric flow field (tangential vorticity)

References
 [1] Branlard - Wind turbine aerodynamics and vorticity based methods, Springer 2017

"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
# Local 
import weio
from vortilib.elements.VortexRing import rings_u



def axisym_u(Rcp, Zcp, r, z, omega_t, epsilon=0):
    """ 
    Velocity field from distribution of tangential vorticity
    INPUTS:
      - Rcp, Zcp: array or control points coordinates, where velocity will be computed
      - r, z : 1d-array or points where vorticity is defined
      - omega_t : 2d-array consistent with np.meshgrid(r,z) of tangential vorticity
                  nz x nr
    """
    Rr,Zr = np.meshgrid(r,z)
    Yr = np.zeros_like(Rr) 
    Xr = np.zeros_like(Rr) 
    DR, DZ = getDrDz(r, z)

    Xcp     = Rcp
    Zcp     = Zcp
    Ycp     = np.zeros_like(Rcp)
    Gamma_r = omega_t * DR * DZ # convert from vorticity to ring intensity
    ur,uz = rings_u(Xcp, Ycp, Zcp, Gamma_r.flatten(), Rr.flatten(), Xr.flatten(), Yr.flatten(), Zr.flatten(), epsilon=epsilon)
    return ur, uz


def getDrDz(r, z):
    """ 
    Return grid cell sizes. For non uniform grid, uses average be tween adjacent cell size
    """
    dr0=np.diff(r)
    dr1=np.concatenate(([dr0[0]], dr0))
    dr2=np.concatenate((dr0, [dr0[-1]]))
    dr = (dr1+dr2)/2
    dz0=np.diff(z)
    dz1=np.concatenate(([dz0[0]], dz0))
    dz2=np.concatenate((dz0, [dz0[-1]]))
    dz = (dz1+dz2)/2
    DR, DZ = np.meshgrid(dr,dz)
    return DR, DZ


def axisym_predefined_distributions(r, z, params=None, distribution='singular_ring', velocity=False):
    """ 
    Return vorticity field and optional velcoity field for some predefined distributions
    """
    from vortilib.elements.VortexRing import rings_u, ring_u
    from vortilib.elements.VortexCylinder import cylinder_tang_u, vc_tang_u

    nz, nr = len(z), len(r)
    om     = np.zeros((nz,nr))
    DR, DZ = getDrDz(r, z)
    Rcp,Zcp = np.meshgrid(r,z)

    if distribution=='zero':
        # omega = zero
        if velocity:
            ur = np.zeros_like(om)
            uz = np.ones(om.shape)

    elif distribution=='singular_ring':
        if params is not None:
            Gamma = params['Gamma']
            zRing = params['z']
            rRing = params['r']
        else:
            Gamma = -1
            zRing = 0
            rRing = 1
        ir = np.argmin(np.abs(r-rRing))
        iz = np.argmin(np.abs(z-zRing))
        d= np.sqrt((r[ir]-rRing)**2 + (z[ir]-zRing)**2)
        if d>1e-6:
            print('[WARN] Grid does not contain ring point. Ring placed at:',r[ir],z[iz], 'instead of ', rRing, zRing)
        om[iz,ir] = Gamma/(DR[iz,ir]*DZ[iz,ir])

        if velocity:
            ur,uz= ring_u(Rcp, Rcp*0, Zcp-zRing, Gamma=Gamma, R=rRing)

    elif distribution=='cylinder':
        if params is not None:
            gamma_t = params['gamma']
            zCyl   = params['z']
            rCyl   = params['r']
            lCyl   = params['l']
        else:
            gamma_t = -1
            zCyl = 0
            rCyl = 1
            lCyl = 1
        ir    = np.argmin(np.abs(r-rCyl))
        iz    = np.argmin(np.abs(z-zCyl))
        izEnd = np.argmin(np.abs(z-(zCyl+lCyl)))
        d= np.sqrt((r[ir]-rCyl)**2 + (z[iz]-zCyl)**2)
        if d>1e-6:
            print('[WARN] Grid does not contain ring point. Cyl placed at:',r[ir],z[iz], 'instead of ', rCyl, zCyl)
        om[iz:izEnd,ir] = gamma_t/(DR[iz:izEnd,ir])

        if velocity:
            if ((zCyl+lCyl)>np.max(z)):
                print('[WARN] Cylinder extends beyond domain, assuming an infinite cylinder for flow field')
                ur, uz = vc_tang_u      (Rcp, Rcp*0, Zcp-zCyl, gamma_t, R=rCyl, polar_out=True)
            else:
                ur, uz = cylinder_tang_u(Rcp, Rcp*0, Zcp, gamma_t, R=rCyl, z1=zCyl, z2=zCyl+lCyl, polar_out=True)

    elif distribution=='regularized_ring':
        # Using inviscid vorticity patch to distribute the vorticity onto a compact core
        # TODO verify equations Gamma scaling, rc/=1
        # Ref [1] p 402 
        if params is not None:
            Gamma = params['Gamma']
            z0    = params['z']
            r0    = params['r']
            rc    = params['rc']
            k     = params['k']
        else:
            Gamma = -1
            z0    = 0
            r0    = 1
            rc    = 0.2
            k     = 2 # e.g. between 1/2 and 4
        # Gamma = pi/(k+1)

        # Distance to ring
        rr = np.sqrt( (Rcp-r0)**2 + (Zcp-z0)**2)/rc
        bIn= rr<=1
        om[bIn] = (1-rr[bIn]**2)**k
        om[bIn] *= Gamma * (k+1)/np.pi*(1/rc)**2 # TODO this isfor 2D vortex not axi-symmetric

        if velocity:
            ur = None # TODO
            uz = None
            ur,uz= ring_u(Rcp, Rcp*0, Zcp-z0, Gamma=Gamma, R=r0, epsilon=rc)

    if velocity:
        return om, ur, uz
    else:
        return om


if __name__ == '__main__':

    from pybra.curves import streamQuiver
    distribution='singular_ring'
    distribution='cylinder'
    distribution='regularized_ring'

    # Define a 2d-grid
    nz = 201
    nr = 137 # number of nodes
    zmin = -1
    zmax = 2
    rmin = 0
    rmax = 2
    r = np.linspace(rmin,rmax,nr)
    z = np.linspace(zmin,zmax,nz)
    print('dz',z[1]-z[0])
    Rcp,Zcp = np.meshgrid(r,z)

    print(Rcp.shape)

    # Vorticity and reference velocity field
    om, ur0, uz0  = axisym_predefined_distributions(r, z, distribution=distribution, velocity=True)

    # Compute velocity using axisym function
    ur,uz= axisym_u(Rcp, Zcp, r, z, om)

    if ur0 is not None:
        vel0 = np.sqrt(ur0**2 + uz0**2)
    vel  = np.sqrt(ur**2 + uz**2)

    minSpeed=np.nanmin(vel)
    maxSpeed=np.nanmax(vel)
    levels=np.linspace(minSpeed,maxSpeed,50)
    rStart=np.array([0.25,0.5,0.75,1.25,1.5])
    start=np.array([rStart*0,rStart])

    fig,axes = plt.subplots(3, 1, sharex=True, figsize=(6.4,6.8)) # (6.4,4.8)
    fig.subplots_adjust(left=0.12, right=0.95, top=0.95, bottom=0.11, hspace=0.20, wspace=0.20)
    ax=axes[0]
    img = ax.contourf(z, r, vel.T, levels=levels, vmin=minSpeed, vmax=maxSpeed)
    sp=ax.streamplot(z, r, uz.T, ur.T,color='k',start_points=start.T,linewidth=0.7,density=30,arrowstyle='-')
    qv=streamQuiver(ax,sp,n=5,scale=40,angles='xy')
    ax.set_ylabel('r [m]')
    ax.set_title('u - Axisym function')
    fig.colorbar(img, ax=ax)

    if ur0 is not None:
        ax=axes[1]
        img = ax.contourf(z, r, vel0.T, levels=levels, vmin=minSpeed, vmax=maxSpeed)
        sp=ax.streamplot(z, r, uz0.T, ur0.T,color='k',start_points=start.T,linewidth=0.7,density=30,arrowstyle='-')
        qv=streamQuiver(ax,sp,n=5,scale=40,angles='xy')
        fig.colorbar(img, ax=ax)
    ax.set_ylabel('r [m]')
    ax.set_title('u - Analytical function')

    ax=axes[2]
    img = ax.contourf(z, r, om.T)
    fig.colorbar(img, ax=ax)
    ax.set_ylabel('r [m]')
    ax.set_xlabel('z [m]')
    ax.set_title('Vorticity')

    plt.show()

#     fig,ax = plt.subplots(1, 1, sharey=False, figsize=(6.4,4.8)) # (6.4,4.8)
#     fig.subplots_adjust(left=0.12, right=0.95, top=0.95, bottom=0.11, hspace=0.20, wspace=0.20)
#     ax.plot(z, uz0[:,0]    , label='Analytical')
#     ax.plot(z, uz [:,0]    , label='Numerical')
#     ax.set_xlabel('z [m]')
#     ax.set_ylabel('uz [m/s]')
#     ax.legend()
# 
# 
#         pass
