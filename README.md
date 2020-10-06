# Ur III Transaction Parser

Detect and retrieve transactions in the Ur III corpus.

Components
==

- CFG parser for semantic parsing
	
	jaworski.cfg CFG grammar, slightly enriched extraction patterns as defined by Jaworski (2008)
	jaworski.py for parsing plain text
	jaworski4conll.py for parsing with pre-annotations (CDLI-CoNLL: tokenization, morphology, CoNLL-U: dependency syntax)
	
	Note that current development focuses on jawoski4conll.py is currently maintained.
	
- Experimental conversion to UD. This also provides routines to connect all partial analyses into a single result graph.

	jaworski2deps.sh

- Workflow demonstration on sample data (CoNLL only)

	demo.sh

Note: The parser currently operates in development mode, i.e., not optimized for run-time. To produce partial parses, it re-iterates over the CFG grammar using different start symbols. For production mode, use *only* TRANSACTION as start symbol.

Acknowledgements
==

Author : Christian Chiarcos, Goethe Unviersität Frankfurt

Developed by the MTAAC project (2017-2020) for the CDLI.
Partially supported by the research group "Linked Open Dictionaries" (LiODi, funded 2015-2020 as an eHumanities research group by the German Federal 
Ministry of Education and Research, BMBF)

The CFG parser replicates the semantic parser described by Jaworski 2008 (https://dl.acm.org/doi/10.5555/1599081.1599128), albeit with a different technology.
