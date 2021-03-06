b'This module needs Python 2.7.x'

# Special variables #
__version__ = '0.0.1'

# Built-in modules #
import multiprocessing

# Internal modules #
from seqsearch.blast import BLASTquery, BLASTdb
from seqsearch.vsearch import VSEARCHquery
from plumbing.cache import property_cached
from plumbing.autopaths import FilePath

# Third party modules #

################################################################################
class SeqSearch(object):
    """A sequence similarity search. Could use different algorithms such
    as BLAST, USEARCH, BLAT etc.

    Input: - Serie of sequences in a FASTA file.
           - The type of the sequences.
           - A database to search against.
           - The type of algorithm to use. Currently BLAST or VSEARCH.
           - Number of threads to use.
           - The desired output path.
           - An extra set of parameters to be given to the search command.
           - The filtering options:
              * BLAST supported:   - e-value
                                   - Maximum targets
                                   - Minimum identity (via manual output format)
                                   - Minimum query coverage (via manual output format)
              * VSEARCH supported: - ?

    Output: - List of identifiers in the database
              (object with significance value and identity attached)

    Other possible alogrithms:
        * http://www.ncbi.nlm.nih.gov/pubmed/11932250
        * http://ab.inf.uni-tuebingen.de/software/pauda/
        * http://www.animalgenome.org/bioinfo/resources/manuals/wu-blast/
    """

    def __repr__(self): return '<%s object on %s>' % (self.__class__.__name__, self.input_fasta)

    def __init__(self, input_fasta, database,
                 seq_type    = 'prot' or 'nucl',      # What sequence type is the input fasta
                 algorithm   = 'blast' or 'vsearch',  # Which implementation do you want
                 num_threads = None,                  # How many processes to use
                 filtering   = None,                  # The result filtering options
                 out_path    = None,                  # Where the .blastout file will be
                 params      = None):                 # Add extra params for the command line
        # Base parameters #
        self.input_fasta = input_fasta
        self.database = database
        self.seq_type = seq_type
        # Optional #
        self.algorithm = algorithm
        # The filtering options #
        if filtering is None: self.filtering = {}
        else:                 self.filtering = filtering
        # Output path #
        if out_path is None: self.out_path = FilePath(self.input_fasta.prefix_path + '.' + algorithm + 'out')
        else: self.out_path = FilePath(out_path)
        # Number of cores to use #
        if num_threads is None: self.num_threads = multiprocessing.cpu_count()
        else:                   self.num_threads = num_threads
        # Extra params to be given to the search algorithm #
        if params is None: self.params = {}
        else:              self.params = params

    @property
    def query(self):
        """The actual search object with all the relevant parameters."""
        if self.algorithm == 'blast':   return self.blast_query
        if self.algorithm == 'vsearch': return self.vsearch_query
        raise NotImplemented("The algorithm '%s' is not supported" % self.algorithm)

    def run(self):
        """Run the search."""
        return self.query.run()

    def filter(self):
        """Filter the results accordingly."""
        return self.query.filter(self.filtering)

    @property
    def results(self):
        """Parse the results in a meaningful manner."""
        return self.query.results

    #-------------------------- BLAST IMPLEMTATION -------------------------#
    @property_cached
    def blast_params(self):
        """A dictionary of options to pass to the blast executable.
        The params should depend on the filtering options."""
        params = self.params.copy()
        if 'e_value'      in self.filtering: params['-evalue']          = self.filtering['e_value']
        if 'max_targets'  in self.filtering: params['-max_target_seqs'] = self.filtering['max_targets']
        return params

    def select_blast_algo(self):
      """Depends on the query type and the database type"""
      self.database = BLASTdb(self.database)
      if self.seq_type == 'nucl' and self.database.seq_type == 'nucl': return 'blastn'
      if self.seq_type == 'prot' and self.database.seq_type == 'prot': return 'blastp'
      if self.seq_type == 'nucl' and self.database.seq_type == 'prot': return 'blastx'
      if self.seq_type == 'prot' and self.database.seq_type == 'nucl': return 'tblastn'

    @property_cached
    def blast_query(self):
        """Make a BLAST search object."""
        return BLASTquery(query_path = self.input_fasta,
                          db_path    = self.database,
                          seq_type   = self.seq_type,
                          params     = self.blast_params,
                          algorithm  = self.select_blast_algo(),
                          version    = "plus",
                          cpus       = self.num_threads,
                          out_path   = self.out_path)

    #-------------------------- VSEARCH IMPLEMTATION -------------------------#
    @property_cached
    def vsearch_query(self):
        """Make a VSEARCH search object."""
        params = {}
        query = VSEARCHquery(self.input_fasta, self.database, params)
        return query