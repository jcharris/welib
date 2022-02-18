import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
# Local 
from welib.tools.clean_exceptions import *
from welib.weio import FASTInputFile

# Submodules
from welib.fast.hydrodyn_morison import Morison
from welib.fast.hydrodyn_waves import Waves


class HydroDyn:

    def __init__(self, filename=None, hdData=None):

        self._graph=None
        self.File=None

        # Read SubDyn file
        if filename is not None:
            self.File = FASTInputFile(filename)
        elif hdData is not None:
            self.File = hdData

        # Internal
        self.p={}
        self.m={}
        self._graph=None

    def __repr__(self):
        s='<{} object>:\n'.format(type(self).__name__)
        s+='|properties:\n'
        s+='|- File: (input file data)\n'
        s+='|methods:\n'
        s+='|- init\n'
        return s

    # --------------------------------------------------------------------------------}
    # --- Functions for general FEM model (jacket, flexible floaters)
    # --------------------------------------------------------------------------------{
    def init(self, Gravity = 9.81, WtrDens='1025', WtrDpth=0, MSL2SWL=0):
        """
        Initialize HydroDyn model 

        gravity: position of transition point
        """
        f = self.File
        # Handle "default" value in input file
        try:
            WtrDpth=float(f['WtrDpth']) # If default
        except:
            if WtrDpth is None:
                raise Exception('Provide WtrDepth if default in file')
        try:
            MSL2SWL=float(f['MSL2SWL']) # If default
        except:
            if MSL2SWL is None:
                raise Exception('Provide MSL2SWL if default in file')
        try:
            WtrDens=float(f['WtrDens']) # If default
        except:
            if WtrDens is None:
                raise Exception('Provide WtrDens if default in file')

        self.p['WtrDpth'] = WtrDpth + MSL2SWL
        self.p['WtrDens'] = WtrDens 
        self.p['Gravity'] = Gravity

        graph = self.graph

        # --- Morison
        # NOTE: graph will be copied
        # Division occurs in constructor
        self.morison = Morison(graph=self.graph, File=self.File, WtrDpth=self.p['WtrDpth'], MSL2SWL=MSL2SWL)
        # TODO there is  mess with MSL2SWL
        Nodes = self.morison.NodesBeforeSwap

        # --- Transfer of nodes 
        Waves_WaveKin_Nodes = Nodes
        Current_NodesZ      = Nodes[:,2]

        # --- Waves Inits
        self.Waves = Waves(File=self.File, WtrDpth=self.p['WtrDpth'], MSL2SWL=MSL2SWL)
        self.Waves.init(Gravity=self.p['Gravity'])

        # --- WvStretch_Init in HydroDyn.f90
        NStepWave   = self.Waves.p['NStepWave']
        nodeInWater = np.zeros( (NStepWave, len(Waves_WaveKin_Nodes)    ))
        WaveDynP    = np.zeros( (NStepWave, len(Waves_WaveKin_Nodes)    ))
        WaveVel     = np.zeros( (NStepWave, len(Waves_WaveKin_Nodes), 3 ))
        WaveAcc     = np.zeros( (NStepWave, len(Waves_WaveKin_Nodes), 3 ))
        WtrDpth   = self.p['WtrDpth']
        if f['WaveStMod']==0:
            for j, p in enumerate(Waves_WaveKin_Nodes):
                if p[2] < -WtrDpth or p[2] >0:
                    pass # all is zero
                else:
                    nodeInWater[:,j] = 1 # for all time steps
        else:
            raise NotImplementedError()
        #             CASE ( 1 )                 ! Vertical stretching.
        #                ! Vertical stretching says that the wave kinematics above the mean sea level
        #                !   equal the wave kinematics at the mean sea level.  The wave kinematics
        #                !   below the mean sea level are left unchanged:
        #                IF (   ( WaveKinzi(J) < -WtrDpth ) .OR. ( WaveKinzi(J) > WaveElev(I,J) ) ) THEN   ! .TRUE. if the elevation of the point defined by WaveKinzi(J) lies below the seabed or above the instantaneous wave elevation (exclusive)
        #                   WaveDynP   (I,J  )  = 0.0
        #                   WaveVel    (I,J,:)  = 0.0
        #                   WaveAcc    (I,J,:)  = 0.0
        #                   nodeInWater(I,J  )  = 0
        #                ELSE 
        #                   nodeInWater(I,J  )  = 1
        #                   IF   ( WaveKinzi(J) >= 0.0_ReKi ) THEN
        #                      ! Set the wave kinematics to the kinematics at mean sea level for locations above MSL, but below the wave elevation.
        #                      WaveDynP   (I,J  )  = WaveDynP0  (I,J  )
        #                      WaveVel    (I,J,:)  = WaveVel0   (I,J,:)
        #                      WaveAcc    (I,J,:)  = WaveAcc0   (I,J,:)
        #                   END IF
        #                   ! Otherwise, do nothing because the kinematics have already be set correctly via the various Waves modules
        #                END IF
        #             CASE ( 2 )                 ! Extrapolation stretching.
        #             ! Extrapolation stretching uses a linear Taylor expansion of the wave
        #             !   kinematics (and their partial derivatives with respect to z) at the mean
        #             !   sea level to find the wave kinematics above the mean sea level.  The
        #             !   wave kinematics below the mean sea level are left unchanged:
        #                IF (   ( WaveKinzi(J) < -WtrDpth ) .OR. ( WaveKinzi(J) > WaveElev(I,J) ) ) THEN   ! .TRUE. if the elevation of the point defined by WaveKinzi(J) lies below the seabed or above the instantaneous wave elevation (exclusive)
        #                   WaveDynP   (I,J  )  = 0.0
        #                   WaveVel    (I,J,:)  = 0.0
        #                   WaveAcc    (I,J,:)  = 0.0
        #                   nodeInWater(I,J  )  = 0
        #                ELSE 
        #                   nodeInWater(I,J  )  = 1
        #                   wavekinzloc = WaveKinzi(J)
        #                   WavePVel0loc = WavePVel0   (I,J,1)
        #                   IF   ( WaveKinzi(J) >= 0.0_ReKi ) THEN
        #                      ! Set the wave kinematics to the kinematics at mean sea level for locations above MSL, but below the wave elevation.
        #                      WaveDynP   (I,J  )  = WaveDynP0  (I,J  ) + WaveKinzi(J)*WavePDynP0  (I,J  )
        #                      WaveVel    (I,J,:)  = WaveVel0   (I,J,:) + WaveKinzi(J)*WavePVel0   (I,J,:)
        #                      WaveAcc    (I,J,:)  = WaveAcc0   (I,J,:) + WaveKinzi(J)*WavePAcc0   (I,J,:)
        #                   END IF
        #                   ! Otherwise, do nothing because the kinematics have already be set correctly via the various Waves modules
        #    ! Set the ending timestep to the same as the first timestep
        WaveDynP[NStepWave-1,:  ]  = WaveDynP [0,:  ]
        WaveVel [NStepWave-1,:,:]  = WaveVel  [0,:,:]
        WaveAcc [NStepWave-1,:,:]  = WaveAcc  [0,:,:]

        # --- Morison Init
        initData = {}
        initData['nodeInWater'] = nodeInWater
        initData['WaveVel']     = WaveVel
        initData['WaveAcc']     = WaveAcc
        initData['WaveDynP']    = WaveDynP
        initData['WaveTime']    = self.Waves.p['WaveTime']
        initData['Gravity']     = self.p['Gravity']
        initData['WtrDens']     = self.p['WtrDens']
        print('WaveTime',self.Waves.p['WaveTime'])
        self.morison.init(initData)
   
    @property
    def graph(self):
        import copy
        if self._graph is None:
            self._graph = self.File.toGraph()
        return copy.deepcopy(self._graph)




    def elementDivisions(self, e):
        n1, n2 = e.nodes
#         if e.data['Pot'] is False:
#             numDiv = np.ceil(e.length/e.data['DivSize']).astype(int)
#             dl = e.length/numDiv
#             SubNodesPositions = np.zeros((numDiv-1,3))
#             for j in range(numDiv-1):
#                 s = (j+1)/numDiv
#                 SubNodesPositions[j,:] = n1.point * (1-s) + n2.point * s
#                 nodeCount+=1
#             Positions = np.vstack( (n1.point, SubNodesPositions, n2.point ) )
# 
#             N=numDiv
#         else:
#             Positions=np.vstack((n1.point, n2.point))
#             dl=e.length
#             N=1
#         member['MGdensity']=np.zeros(N+1) # TODO
#         member['tMG'] = np.zeros(N+1)   # TODO
#         prop1 = e.nodeProps[0]  # NOTE: t&D are not stored in nodes since they are member dependent
#         prop2 = e.nodeProps[1] 
#         t             = np.linspace(prop1.data['t']  , prop2.data['t']  , N+1)
#         member['R']   = np.linspace(prop1.data['D']/2, prop2.data['D']/2, N+1)
#         member['RMG'] = member['R']+member['tMG']
#         member['Rin'] = member['R']-t


    def memberVolumeSubmerged(self, e, useDiv=False):
        from welib.hydro.tools import tapered_cylinder_geom
        prop1 = e.nodeProps[0]  # NOTE: t&D are not stored in nodes since they are member dependent
        prop2 = e.nodeProps[1] 
        Za = e.nodes[0].point[2]
        Zb = e.nodes[1].point[2]
        if Za>=0 and Zb>=0:
            return 0   # Fully above water
        elif Za<0 and Zb<0: # Fully submerged 
            return self.memberVolumeStructure(e, useDiv=useDiv)
        elif Za < -self.p['WtrDpth'] or Zb < -self.p['WtrDpth']:
            raise NotImplementedError()
        # Partially submerged, interpolated to "0"
        if not useDiv:
            Z0  = np.array([Za, Zb])
            tMG0= np.array([0,0]) # TODO
            R0  = np.array([prop1.data['D']/2, prop2.data['D']/2])
            # Stopping at 0
            Z   = np.array([np.min(Z0), 0])
            tMG = np.interp(Z , Z0, tMG0)
            R   = np.interp(Z , Z0, R0)
            RMG = R + tMG
            l=e.length * np.abs(Z[1]-Z[0])/ np.abs(Z0[1]-Z0[0])
            # get V and CV for marine growth displacement
            Vouter, cVouter = tapered_cylinder_geom(RMG[0], RMG[1], l)
        else:
            raise NotImplementedError()
        return Vouter

    def memberVolumeStructure(self, e, useDiv=False):
        from welib.hydro.tools import tapered_cylinder_geom
        prop1 = e.nodeProps[0]  # NOTE: t&D are not stored in nodes since they are member dependent
        prop2 = e.nodeProps[1] 
        Za = e.nodes[0].point[2]
        Zb = e.nodes[1].point[2]
        if Za < -self.p['WtrDpth'] or Zb < -self.p['WtrDpth']:
            raise NotImplementedError()
        if not useDiv:
            tMG = np.array([0,0]) # TODO
            R   = np.array([prop1.data['D']/2, prop2.data['D']/2])
            RMG = R + tMG
            # get V and CV for marine growth displacement
            Vouter, cVouter = tapered_cylinder_geom(RMG[0], RMG[1], e.length)
        else:
            raise NotImplementedError()
        return Vouter



    def VolumeStructure(self, method='NoDiv'):
        if method=='Morison':
            return self.morison.VolumeStructure
        return np.sum([self.memberVolumeStructure(e, useDiv=method=='Div') for e in self.graph.Elements])

    def VolumeSubmerged(self, method='NoDiv'):
        if method=='Morison':
            return self.morison.VolumeSubmerged
        return np.sum([self.memberVolumeSubmerged(e, useDiv=method=='Div') for e in self.graph.Elements])


    # --------------------------------------------------------------------------------}
    # --- IO/Converters
    # --------------------------------------------------------------------------------{
    def writeSummary(self, filename):
        with open(filename, 'w') as fid:
            self.morison.writeSummary(fid=fid)

    def toYAML(self, filename):
        if self._FEM is None:
            raise Exception('Call `initFEM()` before calling `toYAML`')
        subdyntoYAMLSum(self._FEM, filename, more = self.File['OutAll'])


    def toYAMSData(self, shapes=[0,4], main_axis='z'):
        """ 
        Convert to Data needed by YAMS
        """
        from welib.mesh.gradient import gradient_regular
        p=dict()
        return p


if __name__ == '__main__':
    import sys
    if len(sys.argv)>=1:
        filename=sys.argv[1]
    else:
        #filename='../../data/SparNoRNA/SparNoRNA_HD_RefH.dat'
        filename='_SparNoRNA_HD_RefH.dat'
        filename='_HD_T.dat'
        filename='_HD_T2.dat'
    import welib


    import  welib.weio

    driverfilename=filename.replace('.dat','.dvr')
    dvr=welib.weio.FASTInputFile(driverfilename)
    Gravity = dvr['Gravity']
    WtrDens = dvr['WtrDens']
    WtrDpth = dvr['WtrDpth']


#     hd = welib.weio.FASTInputFile(filename)
# #     hd.write('Out.dat')
#     graph = hd.toGraph()
#     print(graph)

    hd = HydroDyn(filename)
    hd.init(Gravity=Gravity, WtrDens=WtrDens, WtrDpth=WtrDpth)
#     hd.MorisonPositions
    hd.writeSummary(filename.replace('.dat','.HD_python.sum'))
#     print(hd.graph)

    EM = hd.morison.graph.Elements[13]
    E  = hd.graph.Elements[13]
    EM = hd.morison.graph.Elements[0]
    E  = hd.graph.Elements[0]
    print(E)
    print(EM)
    print(EM.MorisonData.keys())
    print()
    print(EM.MorisonData['R'])
    print(EM.MorisonData['Vouter']    , hd.memberVolumeStructure(E, useDiv=False))
    print(EM.MorisonData['Vsubmerged'], hd.memberVolumeSubmerged(E, useDiv=False))

    for e,em in zip(hd.graph.Elements, hd.morison.graph.Elements):
        if abs(em.MorisonData['Vouter']-hd.memberVolumeStructure(e))>1e-8:
           print('ID',e.ID,'V',em.MorisonData['Vouter'], hd.memberVolumeStructure(e)  )
    for e,em in zip(hd.graph.Elements, hd.morison.graph.Elements):
        if abs(em.MorisonData['Vsubmerged']-hd.memberVolumeSubmerged(e) )>1e-8:
            print('ID',e.ID,'V',em.MorisonData['Vsubmerged'], hd.memberVolumeSubmerged(e),   )

#     graph.divideElements(3)
#     print(graph)
#     import numpy as np
#     import matplotlib.pyplot as plt
#     from matplotlib import collections  as mc
#     from mpl_toolkits.mplot3d import Axes3D
#     fig = plt.figure()
#     ax = fig.add_subplot(1,2,1,projection='3d')
#     lines=graph.toLines(output='coord')
#     for l in lines:
#     #     ax.add_line(l)
#         ax.plot(l[:,0],l[:,1],l[:,2])

#     ax.autoscale()
    # ax.set_xlim([-40,40])
    # ax.set_ylim([-40,40])
    # ax.set_zlim([-40,40])
    # ax.margins(0.1)
#     plt.show()

# 
# if __name__ == '__main__':
#     pass
