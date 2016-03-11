import pyurdme
import os
import tempfile
import subprocess
import shutil
import numpy
from pyurdme import get_N_HexCol
import json
import uuid

try:
    # This is only needed if we are running in an Ipython Notebook
    import IPython.display
except:
    pass

class sGFRDSolver(pyurdme.URDMESolver):
    """ Micro solver class.TODO: Add short description. """
    
    NAME = 'sGFRD'
    
    def __init__(self, model, solver_path=None, report_level=0, model_file=None, sopts=None):
        pyurdme.URDMESolver.__init__(self,model,solver_path,report_level,model_file,sopts)

        self.solver_name = 'hybrid'
        self.solver_path = ''
    
    def __getstate__(self):
        """ TODO: Implement"""
    
    def __getstate__(self):
        """ TODO: Implement"""
    
    def __del__(self):
        """ Remove the temporary output folder """
    #shutil.rmtree(self.outfolder_name)
    
    def serialize(self, filename=None, report_level=0,sopts=None):
        """ Write the mesh and derived datastructures needed by the 
            hybrid solver to file. """

    
    def create_input_file(self, filename):
    
        input_file = open(filename,'w')
        input_file.write("NAME "+self.model.name+"\n")
        
        
        # Write the model dimension
        (np,dim) = numpy.shape(self.model.mesh.coordinates())
        input_file.write("DIMENSION {0}\n".format(dim))
        input_file.write("BOUNDARY 0 100 0 100 0 100\n")
        input_file.write("VOXELS 5\n")
        
        self.model.resolve_parameters()
        params = ""
        for i, pname in enumerate(self.model.listOfParameters):
            P = self.model.listOfParameters[pname]
            params += "PARAMETER {0} {1}\n".format(pname, str(P.value))
        input_file.write(params)

        speciesdef = ""
        
        initial_data = self.model.u0
        spec_map = self.model.get_species_map()
        
        for i, sname in enumerate(self.model.listOfSpecies):
            S = self.model.listOfSpecies[sname]
            sum_mol = numpy.sum(self.model.u0[spec_map[sname],:])
            speciesdef += "SPECIES {0} {1} {2} {3} {4}\n".format(sname, str(S.diffusion_constant), str(S.reaction_radius), sum_mol, "MICRO")
            
        input_file.write(speciesdef)
    
        reacstr = ""
        for i, rname in enumerate(self.model.listOfReactions):
            R = self.model.listOfReactions[rname]
            reacstr += "REACTION "

            for j, reactant in enumerate(R.reactants):
                reacstr += str(reactant)+" "
            
            reacstr += "> "
            
            for j, product in enumerate(R.products):
                reacstr += str(product)
            reacstr += " {0}\n".format(str(R.marate.value))
            
        input_file.write(reacstr)

        input_file.write("T {0}\n".format(str(self.model.tspan[-1])))
        nint = (self.model.tspan[-1]-self.model.tspan[0])/(self.model.tspan[-1]-self.model.tspan[-2])
        input_file.write("NINT {0}\n".format(str(int(nint))))

    def run(self, number_of_trajectories=1, seed=None, input_file=None, loaddata=False):
        """ Run one simulation of the model.
            
            number_of_trajectories: How many trajectories should be run.
            seed: the random number seed (incimented by one for multiple runs).
            input_file: the filename of the solver input data file .
            loaddata: boolean, should the result object load the data into memory on creation.
            
            Returns:
            URDMEResult object.
            or, if number_of_trajectories > 1
            a list of URDMEResult objects
        """
        
        # Grab a working manually generated file for now.
        #  testfnm = os.path.dirname(__file__)+'/models/pyurdme_test.txt'
        #testfnm = '/Users/andreash/bitbucket/hybrid/models/nl_example3.txt'
        
        #print testfnm
        #with open(testfnm, 'r') as fh:
        #    model_str = fh.read()
        
        # Generate the input file
        infile = tempfile.NamedTemporaryFile(delete=False, dir=os.environ.get('PYURDME_TMPDIR'))
        self.infile_name = infile.name
        self.create_input_file(infile.name)
        #  print infile.read()
        with open('test.txt','w') as fh:
            fh.write(infile.read())
        #infile.write(model_str)
        infile.close()
        
        # Generate output directory
        outfolder_name = tempfile.mkdtemp(prefix="pyurdme_hybrid_")
        
        if self.report_level > 2:
            print model_str
        if number_of_trajectories > 1:
            result_list = []

        solver_str=os.path.dirname(__file__)+"/bin/hybrid"
        #solver_str="/Users/andreash/bitbucket/hybrid/bin/hybrid"

        solver_cmd = [solver_str,self.infile_name, outfolder_name]
        handle = subprocess.Popen(solver_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        handle.wait()
        
        
        try:
            result = MICROResult(self.model,outfolder_name)
            return result
        except IOError,e:
            print handle.stderr.read()
            raise

class MICROResult():

    def __init__(self,model, output_folder_name=None):
        self.output_folder_name=output_folder_name
        self.model = model
    
    def get_particles(self,time):
        """ Return all particles at a certain time point. """
        with open(self.output_folder_name+"/0_pos.txt", 'r') as fh:
            for line in fh.readlines():
                timepoint = json.loads(line)
                if timepoint['time'] == time:
                    return numpy.fromstring(timepoint['particles'],sep=' ').reshape((timepoint['number_of_particles'],8))
    
    def get_species(self,spec_name, time):
        """ Return copy number of spec_name. """
        
        with open(self.output_folder_name+"/0_pos.txt", 'r') as fh:
            print fh.read()


    def _export_to_particle_js(self,species,time_index, colors=None):
        """ Create a html string for displaying the particles as small spheres. """
        import random
        #with open(os.path.dirname(os.path.abspath(__file__))+"/data/three.js_templates/particles.html",'r') as fd:
            #template = fd.read()
        
        with open(os.path.dirname(pyurdme.__file__)+"/data/three.js_templates/particles.html",'r') as fd:
            template = fd.read()
        
        
        factor, coordinates = self.model.mesh.get_scaled_normalized_coordinates()
        dims = numpy.shape(coordinates)
        if dims[1]==2:
            is3d = 0
            vtxx = numpy.zeros((dims[0],3))
            for i, v in enumerate(coordinates):
                vtxx[i,:]=(list(v)+[0])
            coordinates = vtxx
        else:
            is3d = 1
        
        h = self.model.mesh.get_mesh_size()
        
        x=[]
        y=[]
        z=[]
        c=[]
        radius = []
        
        if colors == None:
            colors =  get_N_HexCol(len(species))
        
        particles = self.get_particles(time_index)
        vtx = particles[:,1:4]
        maxvtx = numpy.max(numpy.amax(vtx,axis=0))
        factor = 1/maxvtx
        
        vtx = factor*vtx
        centroid = numpy.mean(vtx,axis=0)
        # Shift so the centroid is now origo
        normalized_vtx = numpy.zeros(numpy.shape(vtx))
        for i,v in enumerate(vtx):
            normalized_vtx[i,:] = v - centroid
        vtx=normalized_vtx

        spec_map = self.model.get_species_map()
        for j,spec in enumerate(species):
            spec_ind=spec_map[spec]
            for k,p in enumerate(particles):
                type = int(p[0])
                if type == spec_ind:
                    x.append(vtx[k,0])
                    y.append(vtx[k,1])
                    z.append(vtx[k,2])
                    c.append(colors[j])
                    radius.append(0.01)
        
        template = template.replace("__X__",str(x))
        template = template.replace("__Y__",str(y))
        template = template.replace("__Z__",str(z))
        template = template.replace("__COLOR__",str(c))
        template = template.replace("__RADIUS__",str(radius))
        
        return template


    def display_particles(self,species, time_index):
        hstr = self._export_to_particle_js(species, time_index)
        displayareaid=str(uuid.uuid4())
        hstr = hstr.replace('###DISPLAYAREAID###',displayareaid)
        
        html = '<div id="'+displayareaid+'" class="cell"></div>'
        IPython.display.display(IPython.display.HTML(html+hstr))

    def __del__(self):
        shutil.rmtree(self.output_folder_name)




