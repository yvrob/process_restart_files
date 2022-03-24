#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Yves Robert"
__credits__ = ["Tatiana Siarafera"]
__version__ = "1.0"
__maintainer__ = "Yves Robert"
__email__ = "yves.robert@berkeley.edu"

""" Description: Library to write and read Serpent restart files, and process them"""

#%% Modules
import struct
import os
import matplotlib.pyplot as plt # can be commented if not installed

#%% Classes definition
class Restart_File:
    """Restart file objects are objects which read/write materials compositions at different points in time. 
       
       The structure is: 
       - Restart file (example: restart): contains snapshots, burnup points, time points. All dictionnaries
            - Snapshot 0: restart[0]. Contains all material objects in snapshot 0, which have the burnup 0 and time 0.
                - Material 0 (example: "mat0"): Material object containing material and nuclides information at given burnup and time.
                - Material 1 (example: "mat1")
                ...
            - Snapshot 1: restart[1]
            ...

        Initialization: only one initialization is needed and possible.
        1) If initialized with a path, it creates an empty object linked to the path, empty of snapshots.
            restart = Restart_File(path_to_file=path_in)
          Then to read the compositions path: 
            restart.read_restart()
          It will fill the object with all the snapshots contained in the restart file.

        2) If initialized with a list of snapshots (which are dictionnaries of Material objects), it creates an object with the corresponding snapshots.
            restart = Restart_File(snapshots=list_snapshots)
           It then needs to be linked to a path to write a binary file or text file.
            restart.path_to_file = path
           Binary: 
            restart.write_binary()
           Text:
            restart.write_text()

        3) If initialized with a dictionary Material objects (aka a snapshot), it creates a snapshot 0 with the materials.
           It then needs to be linked to a path to write a binary file or text file.
        
        
        Useful:
        * To print restart details, just type: <name of Restart_File>
        * To extract a snapshot: <name of Restart_File>.extract_snapshot(<snapshot id>)
        * To extract a specific material of a snapshot: <name of Restart_File>.extract_material("<name of Material>", <snapshot id>)
        * To extract the evolution of a specific material : <name of Restart_File>.follow_material("<name of Material>")

    """   

    def __init__(self, path_to_file=None, snapshots=None, materials=None):
        """Creates object

        Args: (only one to give)
            path_to_file (str, optional): path to restart file. Defaults to None.
            snapshots (str, optional): list of snapshots. Defaults to None.
            materials (str, optional): dictionary materials for a single snapshot. Defaults to None.
        """        
        self.snapshots = dict()
        test = [not isinstance(i, type(None)) for i in [path_to_file, snapshots, materials]]
        if sum(test) != 1:
            raise Exception('Just choose one option: path, snapshots or materials')
        elif test[0]:
            self.path_to_file = path_to_file
        elif test[1]:
            self.snapshots = snapshots
        elif test[2]:
            self.snapshots[0] = materials

    def __repr__(self):
        """Prints information

        Returns:
            str: Restart information
        """        
        s = 'Restart file: {}, snapshots ({} points):\n'.format(self.path_to_file, len(self.snapshots))
        for i in self.snapshots:
            s += '\t{}: BU = {:.2f} MWd/kg, time  = {:.2f} days, {} materials\n'.format(i, self._burnups[i], self._times[i], len(self.snapshots[i]))
        s += '\tWritten: {}'.format(os.path.exists(self.path_to_file))
        return s

    def read_restart(self):
        """Reads the linked file and creates snapshots.
        """ 
        print('Reading snapshots in {}'.format(self.path_to_file))
        
        # Initialization       
        self.snapshots = dict()
        self._burnups = dict()
        self._times = dict()
        current_step = -1

        # Read restart file
        with open(self.path_to_file, mode='rb') as file:  # b is important -> binary
            while True:
                # Create Material object and fill it with information from one material binary block
                mat = Material()
                read_ok = mat.read(file)

                # If error in reading, end of file
                if not read_ok:
                    break

                # Find the right snapshot to put the material in. 
                # If new, add new snapshot and record time and burnup 
                if len(self._burnups) == 0 or mat.bu_global != self._burnups[list(self._burnups.keys())[-1]]:
                    # Iterate step
                    current_step += 1

                    # New snapshot
                    self.snapshots[current_step] = dict()

                    # Store time/bu information
                    self._burnups[current_step] = mat.bu_global
                    self._times[current_step] = mat.bu_days
                # Store material
                self.snapshots[current_step][mat.name] = mat
        print('\tDone reading: found {} snapshots'.format(len(self.snapshots)))


    def write_binary(self, snapshot_ids=None, material_names=None):
        """Writes snapshots in a restart binary file.
           If no snapshot id is given, all time steps are written.
           Otherwise, it writes time steps corresponding to the snapshot_ids list.
           If no material name is given, all materials are written.
           Otherwise, writes the selected materials.

        Args:
            snapshot_ids (int, optional): List of snapshots to write. Defaults to None.
            material_names (str, optional): dictionary materials to write. Defaults to None.
        """        

        # If no id list is given, take all snapshots
        if isinstance(snapshot_ids, type(None)):
            snapshot_ids = list(self.snapshots.keys())

        print('Writing snapshots to binary {} in {}'.format(snapshot_ids, self.path_to_file))

        # Loop over selected snapshots
        contents = []
        for i_step, s in enumerate([self.snapshots[j] for j in snapshot_ids]):
            # If no material name is given, take all materials
            if isinstance(material_names, type(None)):
                material_names = list(s.keys())
            materials = [s[i] for i in material_names]

            # Loop over materials of the snapshot and add to the content to write
            print('\tProcessing snapshot {} with {} materials'.format(snapshot_ids[i_step], len(material_names)))
            
            for mat in materials:
                contents.append(mat.to_binary())
        
        # Write content
        print('\tWriting ...')
        with open(self.path_to_file, 'wb') as f:
            f.write(b''.join(contents))

        print('\tDone writing: wrote {} snapshots'.format(len(snapshot_ids)))

    def write_text(self, snapshot_ids=None, material_names=None, name_out=None):
        # If no output name is given, take the name/path of the linked binary file
        if isinstance(name_out, type(None)):
            prefix = '.'.join(self.path_to_file.split('.')[:-1])
        else:
            prefix = name_out

        # If no id list is given, take all snapshots
        if isinstance(snapshot_ids, type(None)):
            snapshot_ids = list(self.snapshots.keys())

        print('Writing snapshots to text {} with prefix'.format(snapshot_ids, prefix))

        # Loop over selected snapshots
        for i_step, s in enumerate([self.snapshots[j] for j in snapshot_ids]):
            # If no material name is given, take all materials
            if isinstance(material_names, type(None)):
                material_names = list(s.keys())

            print('\tWriting snapshot {} with {} materials'.format(snapshot_ids[i_step], len(material_names)))

            # Path where the file will be written, with snapshot id as suffix
            path_out = '{}_{}.txt'.format(prefix, snapshot_ids[i_step]) 

            # Loop over material and write to snapshot text file
            with open(path_out, 'w') as f:
                for j in s:
                    mat = s[j]
                    f.write(mat.to_text())
                    f.write('\n\n')

        print('\tDone writing: wrote {} snapshots'.format(len(snapshot_ids)))

    def extract_snapshot(self, snapshot_id):
        """Extracts a specific snapshot based on the id.
        If snapshot is -1, takes the latest added snapshot.

        Args:
            snapshot_id (int): step of the snapshot

        Returns:
            dict: specific snapshot (dictionary Material objects)
        """        
        if snapshot_id == -1:
            snapshot_id = list(self.snapshots.keys())[-1]
        return self.snapshots[snapshot_id]

    def extract_material(self, material_name, snapshot_id):
        """Extracts a specific material for a given snapshot.

        Args:
            material_name (str): name of the material to extract
            snapshot_id (id): step of the snapshot

        Returns:
            Material: extracted material
        """        
        if snapshot_id == -1:
            snapshot_id = list(self.snapshots.keys())[-1]
        return self.snapshots[snapshot_id][material_name]

    def follow_material(self, material_name):
        """Extracts all states for specific material.

        Returns:
            dict: dictionary containing all available material states.
        """               
        states = dict()
        for i in self.snapshots:
            try:
                states[i] = self.snapshots[i][material_name]
            except:
                print('No material {} in snapshot {}. Skipped'.format(material_name, i))
        return states

class Material:
    """Material objects correspond to Serpent materials and include all the informations stored/needed in restart files.
    """    

    def __repr__(self):
        """Prints information

        Returns:
            str: Material information
        """        
        # Extract top inventory
        top = sorted(self.nuclides.items(), key=lambda nuc: nuc[1]['adens'], reverse=True)
        s = '{}, adens: {:.2E}, bu: {:.2E}, nnuc: {}, top 5: {}'.format(self.name, self.adens, self.bu, self.nnuc, ' '.join([translate(i[0]) for i in top[:5]]))
        return s

    def read(self, file):
        """Read binary file block

        Args:
            file (<class '_io.BufferedReader'>): open binary restart file 

        Returns:
            bool: True if the material was successfully read, False otherwise (end of file)
        """        
        # Link to binary file
        self.file_name = file.name

        # Populate material fields from linked binary file
        # Binary files are made of blocks of constant size. 
        # We just need to iterate with the right byte size to read fields

        # Read first sub-block, if not readable, the material is not valid, it is the end of file
        s = file.read(8)
        if not s:
            return False

        # Read snapshot/material fields
        n = struct.unpack("q", s)[0]  # length of material name
        self.name = struct.unpack("{}s".format(n), file.read(n))[0].decode('UTF-8') # material name
        self.bu_global = struct.unpack("d", file.read(8))[0] # BU of snapshot
        self.bu_days = struct.unpack("d", file.read(8))[0] # time of snapshot
        self.nnuc = struct.unpack("q", file.read(8))[0] # Number of nuclides in material
        self.adens = struct.unpack("d", file.read(8))[0] # Atomic density of material
        self.mdens = struct.unpack("d", file.read(8))[0] # Mass density of material
        self.bu = struct.unpack("d", file.read(8))[0] # Burnup of material

        # Read nuclides and populate a dictionary
        self.nuclides = dict()
        for i in range(self.nnuc):
            ZAI, adens = struct.unpack("qd", file.read(16))
            self.nuclides[str(ZAI)] = dict()
            self.nuclides[str(ZAI)]['adens'] = adens

        return True

    def to_binary(self):
        """Converts the material information to a binary block, which can be used for writing a binary restart file

        Returns:
            bytes: material information block
        """        

        # Populate block with necessary material information
        content = b''
        content += struct.pack('q', len(self.name))
        content += struct.pack('{}s'.format(len(self.name)), str.encode(self.name))
        content += struct.pack('d', self.bu_global)
        content += struct.pack('d', self.bu_days)
        content += struct.pack('q', self.nnuc)
        content += struct.pack('d', self.adens)
        content += struct.pack('d', self.mdens)
        content += struct.pack('d', self.bu)
        for i in self.nuclides:
            content += struct.pack('q', int(i))
            content += struct.pack('d', self.nuclides[i]['adens'])
        return content

    def to_text(self):  
        """Converts the material information to a text block.
        
        Returns:
            str: string containing material information
        """   
        s = 'Material {}\n'.format(self.name)
        for k in self.__dict__.keys():
            if k != 'nuclides' and k != 'name' and k != 'file_name':
                s += '\t{}\t{}\n'.format(k, getattr(self, k))
        s += '\tnuclides:\n'
        for k in self.nuclides:
            s += '\t\t{}\t{}\n'.format(k, self.nuclides[k]['adens'])
        return s

    def extract_nuclide(self, name_nuclide):
        if not str(name_nuclide).isdigit():
            name_nuclide = translate(name_nuclide)
        return self.nuclides[name_nuclide]['adens']

    def plot_densities(self, nnuc=None, logscale=True, translating=True):
        """Plot histogram of densities for the top nnuc nuclides

        Args:
            nnuc (int, optional): Number of nuclides to plot. If None, plot all. Defaults to None.
            logscale (bool, optional): If need to use logscale and not linear scale. Defaults to True.
            translating (bool, optional): If need to show real nuclides names. Defaults to True.
        """
        fig, ax = plt.subplots()
        ax.set_axisbelow(True)
        plt.grid()
        if isinstance(nnuc, type(None)):
            nnuc = self.nnuc
        top = sorted(self.nuclides.items(), key=lambda nuc: nuc[1]['adens'], reverse=True)[:nnuc]
        if translating:
            ZAI = [translate(i[0]) for i in top]
        else:
            ZAI = [i[0] for i in top]
        adens = [i[1]['adens'] for i in top]
        ax.bar(ZAI, adens)
        plt.xticks(rotation = 90)
        if logscale:
            plt.yscale('log')
        plt.ylabel('Atomic density [at/b.cm]')

#%% Functions
def translate(name):
    """Translate Serpent ZAI notation to human-readable notation for nuclides and vice versa

    Args:
        ZAI (str/int): Serpent ZAI/nuclide name

    Returns:
        str: nuclide name/Serpent ZAI
    """    
    elements = {1: 'H', 2: 'He', 3: 'Li', 4: 'Be', 5: 'B', 6: 'C', 7: 'N', 8: 'O', 9: 'F', 10: 'Ne', 11: 'Na', 12: 'Mg', 13: 'Al', 14: 'Si', 15: 'P', 16: 'S', 17: 'Cl', 18: 'Ar', 19: 'K', 20: 'Ca', 21: 'Sc', 22: 'Ti', 23: 'V', 24: 'Cr', 25: 'Mn', 26: 'Fe', 27: 'Co', 28: 'Ni', 29: 'Cu', 30: 'Zn', 31: 'Ga', 32: 'Ge', 33: 'As', 34: 'Se', 35: 'Br', 36: 'Kr', 37: 'Rb', 38: 'Sr', 39: 'Y', 40: 'Zr', 41: 'Nb', 42: 'Mo', 43: 'Tc', 44: 'Ru', 45: 'Rh', 46: 'Pd', 47: 'Ag', 48: 'Cd', 49: 'In', 50: 'Sn', 51: 'Sb', 52: 'Te', 53: 'I', 54: 'Xe', 55: 'Cs', 56: 'Ba', 57: 'La', 58: 'Ce', 59: 'Pr', 60: 'Nd', 61: 'Pm', 62: 'Sm', 63: 'Eu', 64: 'Gd', 65: 'Tb', 66: 'Dy', 67: 'Ho', 68: 'Er', 69: 'Tm', 70: 'Yb', 71: 'Lu', 72: 'Hf', 73: 'Ta', 74: 'W', 75: 'Re', 76: 'Os', 77: 'Ir', 78: 'Pt', 79: 'Au', 80: 'Hg', 81: 'Tl', 82: 'Pb', 83: 'Bi', 84: 'Po', 85: 'At', 86: 'Rn', 87: 'Fr', 88: 'Ra', 89: 'Ac', 90: 'Th', 91: 'Pa', 92: 'U', 93: 'Np', 94: 'Pu', 95: 'Am', 96: 'Cm', 97: 'Bk', 98: 'Cf', 99: 'Es', 100: 'Fm', 101: 'Md', 102: 'No', 103: 'Lr', 104: 'Rf', 105: 'Db', 106: 'Sg', 107: 'Bh', 108: 'Hs', 109: 'Mt', 110: 'Ds', 111: 'Rg', 112: 'Uub'}
    name = str(name)
    
    # Case where ZAI is given -> name
    if name.isdigit():
        if str(name)[-1] == '0':
            ZA = int(name)/10
            suffix = ''
        elif str(name)[-1] == '1':
            ZA = (int(name) - 1)/10
            suffix = 'm'

        Z = int(ZA/1000)
        element = elements[Z]
        A = int(ZA-Z*1000)
        if A == 0:
            A = 'nat'
        nuclide = '{}{}{}'.format(element, A, suffix)

    # Case where name is given -> ZAI
    else:
        if name[-1] == 'm':
            name = name[:-1]
            I = '1'
        else:
            I = '0'
        
        i = len(name)-1
        while name[i:].isdigit():
            i-=1
        A = name[i+1:]
        element = name[:i+1]
        Z = str(list(elements.keys())[list(elements.values()).index(element)])
        nuclide = Z+A+I

    return nuclide

#%% Tatiana application
if __name__ == "__main__":
    # 1) Extract last snapshot in main input and remove materials in "m"
    ## Input
    file_in1 = './ATR147Amref4step1.wrk' 

    ## Read restart
    restart1 = Restart_File(path_to_file=file_in1)
    restart1.read_restart()
    # restart1.write_text() ### just for tests

    ## Extract latest snapshot
    materials1 = restart1.extract_snapshot(-1)

    ## Remove materials in "m" (could just replace, but for the sake of clarity we do it)
    to_keep = [] # list of material names to keep in this snapshot
    ### Loop over snapshot's materials
    for name in materials1:
        ### My criteria: length of 4, first letter is "m" and the rest is numbers
        if len(name) == 4 and name[0] == 'm' and name[1:].isdigit():
            pass
        else:
            ### Keep if conditions are not met
            to_keep.append(name)
    
    materials1 = {name: materials1[name] for name in materials1.keys() & to_keep}

    ## Quick check
    print('\tCheck: {} materials in restart file, {} extracted, {} removed'.format(len(restart1.extract_snapshot(-1)), len(materials1), len(restart1.extract_snapshot(-1))- len(materials1)))
    # print(to_keep) # Uncomment to see what is left

    # 2) Extract all materials in burnATR at last step (burnt materials)
    ## Input
    file_in2 = './burnATR.wrk'
    
    ## Read restart
    restart2 = Restart_File(path_to_file=file_in2)
    restart2.read_restart()
    # restart.write_text() # just for tests

    ## Extract latest snapshot
    materials2 = restart2.extract_snapshot(-1)

    ## IMPORTANT: correct all burnups to match latest burnup step in main (point 1))
    bu_global = list(materials1.values())[0].bu_global # take whatever material which is in materials1
    bu_days = list(materials1.values())[0].bu_days
    for name in materials2:
        mat = materials2[name]
        mat.bu_global = bu_global
        mat.bu_days = bu_days

    ## Quick check
    print('\tCheck: {} materials in restart file'.format(len(materials2)))


    # 3) Merge materials and write new binary restart file
    ## Input
    file_out = './new_compos.wrk'

    ## Merge materials
    materials3 = {**materials2, **materials1}

    ## Create Restart_file object from materials
    restart3 = Restart_File(materials=materials3)

    ## Write restart file
    restart3.path_to_file = file_out
    restart3.write_binary()
    restart3.write_text() # just for tests

    ## Quick check
    print('\tCheck: {} materials in restart file'.format(len(materials3)))

    ### Plot both densities for m111 material in restart1 restart 2 and restart3, check if they are different
    mat_name = 'm111'
    ax = restart1.extract_material(mat_name, -1).plot_densities(nnuc=10)
    ax = restart2.extract_material(mat_name, -1).plot_densities(nnuc=10)
    ax = restart3.extract_material(mat_name, 0).plot_densities(nnuc=10)


    # Show Xe135 densities
    adens1 = restart1.extract_material(mat_name, -1).extract_nuclide('Xe135')
    adens2 = restart2.extract_material(mat_name, -1).extract_nuclide('Xe135')
    adens3 = restart3.extract_material(mat_name,  0).extract_nuclide('Xe135')
    print('Restart 1: N_Xe135 = {:.2E} at/b.cm'.format(adens1))
    print('Restart 2: N_Xe135 = {:.2E} at/b.cm'.format(adens2))
    print('Restart 3: N_Xe135 = {:.2E} at/b.cm'.format(adens3))
    